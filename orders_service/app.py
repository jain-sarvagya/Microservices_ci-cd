# products_service/app.py
from flask import Flask, request, jsonify
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import check_password_hash
import mysql.connector
import os

app = Flask(__name__)
auth = HTTPBasicAuth()

host = os.environ.get("MYSQL_HOST", "mysql_db")
user = os.environ.get("MYSQL_USER", "root")
password = os.environ.get("MYSQL_PASSWORD", "rootpassword")
database = os.environ.get("MYSQL_DB", "auth_db")

# connection to central auth DB (to verify users)
auth_db = mysql.connector.connect(
    host=host,
    user=user,
    password=password,
    database=database
)
auth_cursor = auth_db.cursor(dictionary=True)

# in-memory per-process stores
user_db_connections = {}
logged_in_users = {}


@auth.verify_password
def verify_password(username, password_plain):
    try:
        auth_cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = auth_cursor.fetchone()
        if not user:
            return None

        if not check_password_hash(user["password_hash"], password_plain):
            return None

        # connect to the user's DB using the MySQL user created during registration
        try:
            conn = mysql.connector.connect(
                host=host,
                user=username,
                password=password_plain,
                database=user["db_name"]
            )
            user_db_connections[username] = conn
            logged_in_users[username] = user
            return username
        except mysql.connector.Error as err:
            print(f"User DB connection failed for {username}: {err}")
            return None

    except mysql.connector.Error as err:
        print(f"Auth DB error: {err}")
        return None

# ORDERS SECTION

# @app.route("/orders", methods=["POST"])
# @auth.login_required
# def create_order():
#     data = request.json
#     conn = user_db_connections[auth.current_user()]
#     cursor = conn.cursor(dictionary=True)

#     # 1. Check stock
#     cursor.execute("SELECT quantity FROM products WHERE id=%s", (data['product_id'],))
#     product = cursor.fetchone()

#     if not product:
#         return jsonify({"error": "Product not found"}), 404

#     if product['quantity'] < data['quantity']:
#         return jsonify({"error": "Not enough stock"}), 400

#     # 2. Reduce stock
#     new_stock = product['quantity'] - data['quantity']
#     cursor.execute("UPDATE products SET quantity=%s WHERE id=%s", (new_stock, data['product_id']))

#     # 3. Create order
#     cursor.execute(
#         "INSERT INTO orders (user_id, product_id, status) VALUES (%s, %s, %s, %s)",
#         (data['user_id'], data['product_id'], 'pending')
#     )

#     conn.commit()
#     return jsonify({"message": "Order created, stock updated"})

@app.route("/orders", methods=["POST"])
@auth.login_required
def create_order():
    cur = user_db_connections[auth.current_user()].cursor()

    product_id = request.json["product_id"]
    user_id = request.json["user_id"]
    quantity = request.json["quantity"]

    # 1. Check stock
    cur.execute("SELECT stock FROM products WHERE id = %s", (product_id,))
    result = cur.fetchone()

    if not result:
        return jsonify({"message": "Product not found"}), 404

    current_stock = result[0]

    if quantity > current_stock:
        return jsonify({"message": "Not enough stock"}), 400

    new_stock = current_stock - quantity

    # 2. Create order
    cur.execute(
        "INSERT INTO orders (user_id, product_id, quantity, status) VALUES (%s, %s, %s, %s)",
        (user_id, product_id, quantity, "pending")
    )

    # 3. Update stock
    cur.execute("UPDATE products SET stock = %s WHERE id = %s", (new_stock, product_id))

    # 4. Get last inserted order id
    cur.execute("SELECT LAST_INSERT_ID()")
    order_id = cur.fetchone()[0]

    user_db_connections[auth.current_user()].commit()
    cur.close()

    return jsonify({
        "message": "Order created successfully",
        "order_id": order_id,
        "stock_after_purchase": new_stock
    }), 201



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