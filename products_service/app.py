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


def get_user_conn_or_400():
    username = auth.current_user()
    if username not in user_db_connections:
        return None, (jsonify({"error": "User DB connection not found"}), 500)
    return user_db_connections[username], None


@app.route("/products", methods=["GET"])
@auth.login_required
def list_products():
    conn, err = get_user_conn_or_400()
    if err:
        return err
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products")
    rows = cursor.fetchall()
    cursor.close()
    return jsonify(rows)


@app.route("/products/<int:product_id>", methods=["GET"])
@auth.login_required
def product_details(product_id):
    conn, err = get_user_conn_or_400()
    if err:
        return err
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE id=%s", (product_id,))
    row = cursor.fetchone()
    cursor.close()
    if not row:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(row)


@app.route("/products/search", methods=["GET"])
@auth.login_required
def search_products():
    q = request.args.get("q", "")
    conn, err = get_user_conn_or_400()
    if err:
        return err
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name LIKE %s", (f"%{q}%",))
    rows = cursor.fetchall()
    cursor.close()
    return jsonify(rows)

@app.route("/products", methods=["POST"])
@auth.login_required
def product_post():
    conn, err = get_user_conn_or_400()
    if err:
        return err
    cur = conn.cursor()
    name = request.json["name"]
    price = request.json["price"]
    stock = request.json["stock"]
    cur.execute("INSERT INTO products (name, price, stock) VALUES (%s, %s, %s)", (name, price, stock))
    cur.execute("SELECT LAST_INSERT_ID()")  # fetch last inserted id
    last_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    return jsonify({"message": "Product added successfully", "id": last_id}), 201

from flask import render_template

@app.route("/add_product_page")
def add_product_page():
    return render_template("add_product.html")

@app.route("/list_products_page")
def list_products_page():
    return render_template("list_products.html")

@app.route("/search_products_page")
def search_products_page():
    return render_template("search_products.html")

@app.route("/product_details_page")
def product_details_page():
    return render_template("product_details.html")



if __name__ == "__main__":
    # Note: on docker this service is exposed on port 5000 inside container and mapped to 5002 on host by docker-compose
    app.run(debug=True, host="0.0.0.0", port=5000)
