from flask import Flask, request, jsonify
from flask_httpauth import HTTPBasicAuth
import mysql.connector
import os

app = Flask(__name__)
auth = HTTPBasicAuth()

host = os.environ.get("MYSQL_HOST")
user = os.environ.get("MYSQL_USER")
password = os.environ.get("MYSQL_PASSWORD")
database = os.environ.get("MYSQL_DB")

auth_db = mysql.connector.connect(
    host=host,
    user=user,
    password=password,
    database=database
)
auth_cursor = auth_db.cursor(dictionary=True)

user_db_connections = {}
logged_in_users = {} 

# AUTH SECTION

@auth.verify_password
def verify_password(username, password):
    auth_cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
    user = auth_cursor.fetchone()
    if not user:
        return None
    if user['password_hash'] == password:  
        conn = mysql.connector.connect(
            host=host,
            user=username,
            password=password,
            database=user['db_name']
        )
        user_db_connections[username] = conn
        logged_in_users[username] = user
        return username
    return None

# ORDERS SECTION

@app.route("/orders", methods=["POST"])
@auth.login_required
def create_order():
    data = request.json
    conn = user_db_connections[auth.current_user()]
    cursor = conn.cursor(dictionary=True)

    # 1. Check stock
    cursor.execute("SELECT quantity FROM products WHERE id=%s", (data['product_id'],))
    product = cursor.fetchone()

    if not product:
        return jsonify({"error": "Product not found"}), 404

    if product['quantity'] < data['quantity']:
        return jsonify({"error": "Not enough stock"}), 400

    # 2. Reduce stock
    new_stock = product['quantity'] - data['quantity']
    cursor.execute("UPDATE products SET quantity=%s WHERE id=%s", (new_stock, data['product_id']))

    # 3. Create order
    cursor.execute(
        "INSERT INTO orders (user_id, product_id, quantity, status) VALUES (%s, %s, %s, %s)",
        (data['user_id'], data['product_id'], data['quantity'], 'pending')
    )

    conn.commit()
    return jsonify({"message": "Order created, stock updated"})


@app.route("/orders/user/<int:user_id>", methods=["GET"])
@auth.login_required
def user_orders(user_id):
    conn = user_db_connections[auth.current_user()]
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM orders WHERE user_id=%s", (user_id,))
    return jsonify(cursor.fetchall())

@app.route("/orders/<int:order_id>/status", methods=["PATCH"])
@auth.login_required
def update_order_status(order_id):
    data = request.json
    conn = user_db_connections[auth.current_user()]
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status=%s WHERE id=%s", (data['status'], order_id))
    conn.commit()
    return jsonify({"message": "Order status updated"})


if __name__ == "__main__":
    app.run(debug=True)