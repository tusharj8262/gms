from flask import Flask, request, render_template, redirect, url_for, session, jsonify
import pymongo
import bcrypt
from datetime import datetime
import uuid

# Initialize Flask
app = Flask(__name__)
app.secret_key = "your_secret_key"  # Secret key for session management

# MongoDB Connection
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["user_auth_db"]
users_collection = db["users"]
product_collection = db["products"]
invoice_collection = db["invoices"]

# Routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = users_collection.find_one({"email": email})
        if not user:
            return render_template("login.html", error="Email not registered.")

        if bcrypt.checkpw(password.encode("utf-8"), user["password"]):
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Incorrect password.")

    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        if users_collection.find_one({"email": email}):
            return render_template("signup.html", error="Email already registered.")

        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        users_collection.insert_one({
            "username": username,
            "email": email,
            "password": hashed_password
        })
        return redirect(url_for("login"))

    return render_template("signup.html")

@app.route("/dashboard")
def dashboard():
    username = session.get("username", "Guest")
    return render_template("dashboard.html", username=username)

@app.route("/products", methods=["GET", "POST"])
def products():
    if request.method == "POST":
        product_id = request.form.get("product_id")
        product_name = request.form.get("product_name")
        product_price = float(request.form.get("product_price"))
        now = datetime.now()

        product = {
            "product_id": str(uuid.uuid4()),
            "product_id1": product_id,
            "product_name": product_name,
            "product_price": product_price,
            "add_date": now,
            "update_date": None,
            "delete_date": None,
            "status": 0  # Not deleted
        }

        product_collection.insert_one(product)
        return redirect(url_for("products"))

    product_list = list(product_collection.find({"status": 0}))
    return render_template("products.html", products=product_list)

@app.route("/product/<product_id>")
def view_product(product_id1):
    product = product_collection.find_one({"product_id1": product_id1, "status": 0})
    if not product:
        return "Product not found or has been deleted.", 404
    return render_template("view_products.html", product=product)

@app.route("/delete_product/<product_id>", methods=["POST"])
def delete_product(product_id):
    product_collection.update_one(
        {"product_id": product_id},
        {"$set": {"status": 1, "delete_date": datetime.now()}}
    )
    return redirect(url_for("products"))

@app.route("/update_product/<product_id>", methods=["POST"])
def update_product(product_id):
    product_name = request.form.get("product_name")
    product_price = float(request.form.get("product_price"))
    now = datetime.now()

    product_collection.update_one(
        {"product_id": product_id},
        {"$set": {"product_name": product_name, "product_price": product_price, "update_date": now}}
    )
    return redirect(url_for("products"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/adddinvoices", methods=["GET", "POST"])
def adddinvoices():
    if request.method == "POST":
        invoice_data = request.json.get("invoice")
        if not invoice_data:
            return jsonify({"error": "No invoice data provided"}), 400

        try:
            for item in invoice_data:
                product = product_collection.find_one({"product_id1": item["product_id"], "status": 0})
                if not product:
                    return jsonify({"error": f"Product {item['product_id']} not found"}), 404

                invoice = {
                    "invoice_id": str(uuid.uuid4()),
                    "customer_name": item.get("customer_name", "Unknown"),
                    "product_id": item["product_id"],
                    "product_name": item["product_name"],
                    "product_price": item["product_price"],
                    "product_quantity": item["product_quantity"],
                    "total": item["total"],
                    "created_date": datetime.now()
                }
                invoice_collection.insert_one(invoice)

            return jsonify({"success": True})
        except Exception as e:
            print(f"Error saving invoice: {e}")
            return jsonify({"error": "Error saving invoice"}), 500

    invoice_list = list(invoice_collection.find())
    return render_template("adddinvoices.html", invoices=invoice_list)

@app.route("/fetch_product", methods=["GET"])
def fetch_product():
    product_id = request.args.get("product_id")
    if not product_id:
        return jsonify({"error": "No product ID provided"}), 400

    product = product_collection.find_one({"product_id1": product_id, "status": 0})
    if not product:
        return jsonify({"error": "Product not found"}), 404

    return jsonify({
        "product_name": product["product_name"],
        "product_price": product["product_price"]
    })
    
    
@app.route("/save_invoice", methods=["POST"])
def save_invoice():
    invoice_data = request.json.get("invoice", [])
    customer_name = request.json.get("customer_name", None)  # Capture customer name

    if not invoice_data or not customer_name:
        return jsonify({"error": "No invoice data or customer name provided"}), 400

    try:
        invoice_id = str(uuid.uuid4())
        created_date = datetime.now()
        invoice_items = []

        for item in invoice_data:
            invoice_items.append({
                "product_id": item["product_id"],
                "product_name": item["product_name"],
                "product_price": item["product_price"],
                "product_quantity": item["product_quantity"],
                "total": item["total"]
            })

        # Store customer name along with the invoice details
        invoice = {
            "invoice_id": invoice_id,
            "created_date": created_date,
            "customer_name": customer_name,  # Store customer name
            "items": invoice_items
        }

        invoice_collection.insert_one(invoice)
        return jsonify({"success": True}), 200

    except Exception as e:
        print(f"Error saving invoice: {e}")
        return jsonify({"error": "Error saving invoice"}), 500


@app.route("/fetch_invoice", methods=["GET"])
@app.route("/fetch_all_invoices", methods=["GET"])
def fetch_invoice():
    # Fetch all invoices from the database
    invoices = list(invoice_collection.find())

    # If no invoices are found, return an error message
    if not invoices:
        return jsonify({"error": "No invoices found"}), 404

    # Render the invoices in an HTML table format
    return render_template("invoices_table.html", invoices=invoices)

@app.route("/get_invoice_details/<invoice_id>", methods=["GET"])
def get_invoice_details(invoice_id):
    # Fetch the invoice details by its ObjectId
    invoice = invoice_collection.find_one({"_id": ObjectId(invoice_id)})
    
    if not invoice:
        return jsonify({"error": "Invoice not found"}), 404
    
    # Format the invoice details
    invoice_data = {
        "invoice_id": invoice["invoice_id"],
        "created_date": invoice["created_date"].strftime("%Y-%m-%d %H:%M:%S"),
        "customer_name": invoice["customer_name"],
        "items": invoice["items"]
    }
    
    return jsonify(invoice_data)

@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "username" not in session:
        return redirect(url_for("login"))

    user = users_collection.find_one({"username": session["username"]})

    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        update_data = {"username": username, "email": email}
        if password:
            update_data["password"] = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        users_collection.update_one({"_id": user["_id"]}, {"$set": update_data})
        session["username"] = username
        return redirect(url_for("profile"))

    return render_template("profile.html", user=user)

if __name__ == "__main__":
    app.run(debug=True)
