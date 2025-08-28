from flask import Flask, request, jsonify
from flask_httpauth import HTTPBasicAuth
import mysql.connector

app = Flask(__name__)
auth = HTTPBasicAuth()

import os

host = os.getenv("MYSQL_HOST", "localhost")
user = os.getenv("MYSQL_USER", "root")
password = os.getenv("MYSQL_PASSWORD", "sar761@SARVAG")
database = os.getenv("MYSQL_DB", "auth_db")

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
            host="localhost",
            user=username,
            password=password,
            database=user['db_name']
        )
        user_db_connections[username] = conn
        logged_in_users[username] = user
        return username
    return None

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    db_name = f"inv_{username}"
    
    # Create MySQL user and their DB
    
    cursor = auth_db.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
    cursor.execute(f"CREATE USER IF NOT EXISTS '{username}'@'localhost' IDENTIFIED BY '{password}'")
    cursor.execute(f"GRANT ALL PRIVILEGES ON {db_name}.* TO '{username}'@'localhost'")
    cursor.execute("INSERT INTO users (username, password_hash, db_name) VALUES (%s, %s, %s)",
                   (username, password, db_name))
    auth_db.commit()
    return jsonify({"message": "User registered", "db": db_name})

@app.route("/login", methods=["POST"])
@auth.login_required
def login():
    return jsonify({"message": "Login successful"})

@app.route("/profile", methods=["GET"])
@auth.login_required
def get_profile():
    username = auth.current_user()
    return jsonify(logged_in_users.get(username))

@app.route("/logout",methods=["GET"])
@auth.login_required
def logout():
    return jsonify({"message": "Logout successful"})

@app.route("/profile", methods=["PUT"])
@auth.login_required
def update_profile():
    username = auth.current_user()
    data = request.json
    auth_cursor.execute(
        "UPDATE users SET username=%s WHERE username=%s",
        (data.get("username"), username)
    )
    auth_db.commit()
    return jsonify({"message": "Profile updated"})

if __name__ == "__main__":
    app.run(debug=True)