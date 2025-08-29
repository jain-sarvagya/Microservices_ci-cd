from flask import Flask, request, jsonify
from flask_httpauth import HTTPBasicAuth
import os
import mysql.connector

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

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    db_name = f"inv_{username}"
    
    # Create MySQL user and their DB    
    
    conn = mysql.connector.connect(
        host=host,
        user="root",
        password=os.environ.get("MYSQL_ROOT_PASSWORD"), 
        database=database
    )
    cursor = conn.cursor()

    try: 
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        cursor.execute(f"CREATE USER IF NOT EXISTS '{username}'@'172.18.%' IDENTIFIED BY '{password}'")
        cursor.execute(f"GRANT ALL PRIVILEGES ON {db_name}.* TO '{username}'@'172.18.%'")
        cursor.execute("FLUSH PRIVILEGES")
        cursor.execute("INSERT INTO users (username, password_hash, db_name) VALUES (%s, %s, %s)",
                    (username, password, db_name))
        
        # Create the 'products' and 'orders' tables inside the new user's db
        cursor.execute(f"USE {db_name}")
        cursor.execute("""
            CREATE TABLE products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                quantity INT NOT NULL,
                price DECIMAL(10, 2) NOT NULL
            );
        """)
        cursor.execute("""
            CREATE TABLE orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                product_id INT NOT NULL,
                quantity INT NOT NULL,
                status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.commit()
    except mysql.connector.Error as err:
        print(f"Error during registration: {err}")
        conn.rollback() # Undo changes if an error occurs
        return jsonify({"error": "Could not register user"}), 500
    finally:
        cursor.close()
        conn.close()
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