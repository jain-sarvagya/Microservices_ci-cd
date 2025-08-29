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


# PRODUCTS SECTION

@app.route("/products", methods=["GET"])
@auth.login_required
def list_products():
    conn = user_db_connections[auth.current_user()]
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products")
    return jsonify(cursor.fetchall())

@app.route("/products/<int:product_id>", methods=["GET"])
@auth.login_required
def product_details(product_id):
    conn = user_db_connections[auth.current_user()]
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE id=%s", (product_id,))
    return jsonify(cursor.fetchone())

@app.route("/products/search", methods=["GET"])
@auth.login_required
def search_products():
    query = request.args.get("q", "")
    conn = user_db_connections[auth.current_user()]
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE name LIKE %s", (f"%{query}%",))
    return jsonify(cursor.fetchall())

if __name__=="__main__":
    app.run(debug=True)