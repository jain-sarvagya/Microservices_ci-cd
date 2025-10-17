# # auth_service/app.py
# from flask import Flask, request, jsonify,render_template,redirect, url_for, session
# from flask_httpauth import HTTPBasicAuth
# from werkzeug.security import generate_password_hash, check_password_hash
# import os
# import re
# import mysql.connector

# app = Flask(__name__)
# auth = HTTPBasicAuth()

# # ENV variables (docker-compose passes these from .env)
# host = os.environ.get("MYSQL_HOST", "mysql_db")
# user = os.environ.get("MYSQL_USER", "root")
# password = os.environ.get("MYSQL_PASSWORD", "rootpassword")
# database = os.environ.get("MYSQL_DB", "auth_db")
# root_password = os.environ.get("MYSQL_ROOT_PASSWORD", "rootpassword")

# # Connect to the central auth DB (this user must have rights to read/write the users table)
# auth_db = mysql.connector.connect(
#     host=host,
#     user=user,
#     password=password,
#     database=database
# )
# auth_cursor = auth_db.cursor(dictionary=True)

# # In-memory stores (per-process)
# user_db_connections = {}
# logged_in_users = {}

# # simple username validation to avoid SQL identifier injection
# USERNAME_RE = re.compile(r"^[A-Za-z0-9_]+$")


# @auth.verify_password
# def verify_password(username, password):
#     try:
#         auth_cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
#         user = auth_cursor.fetchone()
#         if not user:
#             return None

#         if not check_password_hash(user["password_hash"], password):
#             return None

#         # Try connecting to user’s private DB using the created MySQL user
#         try:
#             conn = mysql.connector.connect(
#                 host=host,
#                 user=username,
#                 password=password,
#                 database=user["db_name"]
#             )
#             user_db_connections[username] = conn
#             logged_in_users[username] = user
#             # returning username so auth.current_user() returns it in other endpoints
#             return username
#         except mysql.connector.Error as err:
#             print(f"DB connection error for {username}: {err}")
#             return None

#     except mysql.connector.Error as err:
#         print(f"Auth DB error: {err}")
#         return None


# @app.route("/register", methods=["POST"])
# def register():
#     data = request.json or {}
#     username = (data.get("username") or "").strip()
#     password_plain = data.get("password") or ""

#     if not username or not password_plain:
#         return jsonify({"error": "username and password are required"}), 400

#     if not USERNAME_RE.match(username):
#         return jsonify({"error": "username may only contain letters, numbers and underscore"}), 400

#     db_name = f"inv_{username}"

#     # use root user to create DB and user
#     try:
#         root_conn = mysql.connector.connect(
#             host=host,
#             user="root",
#             password=root_password
#         )
#         root_cursor = root_conn.cursor()
#     except mysql.connector.Error as err:
#         print(f"Could not connect as root: {err}")
#         return jsonify({"error": "database root connection failed"}), 500

#     try:
#         # 1. Create DB for the user
#         root_cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")

#         # 2. Create MySQL user (we validated username above)
#         # Note: IDENTIFIED BY accepts a literal; we place password as a parameter to avoid injection where possible.
#         # However MySQL parameterization doesn't work for identifiers; since username and db_name are validated it's acceptable.
#         root_cursor.execute(f"CREATE USER IF NOT EXISTS '{username}'@'%' IDENTIFIED BY %s", (password_plain,))

#         # 3. Grant full privileges on user’s DB
#         root_cursor.execute(f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{username}'@'%'")
#         root_cursor.execute("FLUSH PRIVILEGES")
#         root_conn.commit()

#         # 4. Insert user into central `users` table (store hashed password)
#         pw_hash = generate_password_hash(password_plain)
#         auth_cursor.execute(
#             "INSERT INTO users (username, password_hash, db_name) VALUES (%s, %s, %s)",
#             (username, pw_hash, db_name)
#         )
#         auth_db.commit()

#         # 5. Create schema (products + orders) in new DB
#         user_conn = mysql.connector.connect(
#             host=host,
#             user="root",
#             password=root_password,
#             database=db_name
#         )
#         user_cursor = user_conn.cursor()
#         user_cursor.execute("""
#             CREATE TABLE IF NOT EXISTS products (
#                 id INT AUTO_INCREMENT PRIMARY KEY,
#                 name VARCHAR(100) NOT NULL,
#                 price DECIMAL(10,2) NOT NULL,
#                 stock INT NOT NULL
#             );
#         """)
#         user_cursor.execute("""
#             CREATE TABLE IF NOT EXISTS orders (
#                 id INT AUTO_INCREMENT PRIMARY KEY,
#                 user_id INT NOT NULL,
#                 product_id INT NOT NULL,
#                 quantity INT NOT NULL,
#                 status VARCHAR(50) DEFAULT 'pending',
#                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#             );
#         """)
#         user_conn.commit()
#         user_cursor.close()
#         user_conn.close()

#     except mysql.connector.Error as err:
#         print(f"Error during registration: {err}")
#         try:
#             root_conn.rollback()
#         except Exception:
#             pass
#         return jsonify({"error": "Could not register user", "details": str(err)}), 500
#     finally:
#         try:
#             root_cursor.close()
#             root_conn.close()
#         except Exception:
#             pass

#     return jsonify({"message": "User registered successfully", "db": db_name}), 201


# @app.route("/users", methods=["GET"])
# def list_users():
#     """
#     Returns a list of users with id, username and password_hash.
#     WARNING: password_hash is shown (NOT plaintext). Showing plaintext passwords is insecure.
#     """
#     try:
#         auth_cursor.execute("SELECT id, username, password_hash, db_name, created_at FROM users")
#         rows = auth_cursor.fetchall()
#         return jsonify(rows)
#     except mysql.connector.Error as err:
#         print(f"Error listing users: {err}")
#         return jsonify({"error": "Could not fetch users"}), 500


# @app.route("/login", methods=["POST"])
# @auth.login_required
# def login():
#     # return jsonify({"message": "Login successful"})
#     return render_template("login.html")


# @app.route("/logout", methods=["POST"])
# @auth.login_required
# def logout():
#     username = auth.current_user()
#     if username in logged_in_users:
#         del logged_in_users[username]
#     if username in user_db_connections:
#         try:
#             user_db_connections[username].close()
#         except Exception:
#             pass
#         del user_db_connections[username]
#     return jsonify({"message": "Logout successful"})


# @app.route("/profile", methods=["GET"])
# @auth.login_required
# def get_profile():
#     username = auth.current_user()
#     return jsonify(logged_in_users.get(username))


# @app.route("/profile", methods=["PUT"])
# @auth.login_required
# def update_profile():
#     username = auth.current_user()
#     data = request.json or {}
#     new_username = data.get("username")

#     if not new_username or not USERNAME_RE.match(new_username):
#         return jsonify({"error": "New valid username required"}), 400

#     try:
#         auth_cursor.execute(
#             "UPDATE users SET username=%s WHERE username=%s",
#             (new_username, username)
#         )
#         auth_db.commit()
#         return jsonify({"message": "Profile updated"})
#     except mysql.connector.Error as err:
#         print(f"Error updating profile: {err}")
#         return jsonify({"error": "Could not update profile"}), 500


# if __name__ == "__main__":
#     app.run(debug=True, host="0.0.0.0", port=5000)


# auth_service/app.py
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
import os
import re
import mysql.connector

app = Flask(__name__)
auth = HTTPBasicAuth()
app.secret_key = "supersecretkey"

# ENV variables (docker-compose passes these from .env)
host = os.environ.get("MYSQL_HOST", "mysql_db")
user = os.environ.get("MYSQL_USER", "root")
password = os.environ.get("MYSQL_PASSWORD", "rootpassword")
database = os.environ.get("MYSQL_DB", "auth_db")
root_password = os.environ.get("MYSQL_ROOT_PASSWORD", "rootpassword")

# Connect to the central auth DB (this user must have rights to read/write the users table)
auth_db = mysql.connector.connect(
    host=host,
    user=user,
    password=password,
    database=database
)
auth_cursor = auth_db.cursor(dictionary=True)

# In-memory stores (per-process)
user_db_connections = {}
logged_in_users = {}

# simple username validation to avoid SQL identifier injection
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]+$")


@auth.verify_password
def verify_password(username, password):
    try:
        auth_cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = auth_cursor.fetchone()
        if not user:
            return None

        if not check_password_hash(user["password_hash"], password):
            return None

        # Try connecting to user’s private DB using the created MySQL user
        try:
            conn = mysql.connector.connect(
                host=host,
                user=username,
                password=password,
                database=user["db_name"]
            )
            user_db_connections[username] = conn
            logged_in_users[username] = user
            return username
        except mysql.connector.Error as err:
            print(f"DB connection error for {username}: {err}")
            return None

    except mysql.connector.Error as err:
        print(f"Auth DB error: {err}")
        return None


@app.route("/register", methods=["POST"])
def register():
    data = request.json or {}
    username = (data.get("username") or "").strip()
    password_plain = data.get("password") or ""

    if not username or not password_plain:
        return jsonify({"error": "username and password are required"}), 400

    if not USERNAME_RE.match(username):
        return jsonify({"error": "username may only contain letters, numbers and underscore"}), 400

    db_name = f"inv_{username}"

    try:
        root_conn = mysql.connector.connect(
            host=host,
            user="root",
            password=root_password
        )
        root_cursor = root_conn.cursor()
    except mysql.connector.Error as err:
        print(f"Could not connect as root: {err}")
        return jsonify({"error": "database root connection failed"}), 500

    try:
        root_cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
        root_cursor.execute(f"CREATE USER IF NOT EXISTS '{username}'@'%' IDENTIFIED BY %s", (password_plain,))
        root_cursor.execute(f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{username}'@'%'")
        root_cursor.execute("FLUSH PRIVILEGES")
        root_conn.commit()

        pw_hash = generate_password_hash(password_plain)
        auth_cursor.execute(
            "INSERT INTO users (username, password_hash, db_name) VALUES (%s, %s, %s)",
            (username, pw_hash, db_name)
        )
        auth_db.commit()

        user_conn = mysql.connector.connect(
            host=host,
            user="root",
            password=root_password,
            database=db_name
        )
        user_cursor = user_conn.cursor()
        user_cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                stock INT NOT NULL
            );
        """)
        user_cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                product_id INT NOT NULL,
                quantity INT NOT NULL,
                status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        user_conn.commit()
        user_cursor.close()
        user_conn.close()

    except mysql.connector.Error as err:
        print(f"Error during registration: {err}")
        try:
            root_conn.rollback()
        except Exception:
            pass
        return jsonify({"error": "Could not register user", "details": str(err)}), 500
    finally:
        try:
            root_cursor.close()
            root_conn.close()
        except Exception:
            pass

    return jsonify({"message": "User registered successfully", "db": db_name}), 201


@app.route("/users", methods=["GET"])
def list_users():
    try:
        auth_cursor.execute("SELECT id, username, password_hash, db_name, created_at FROM users")
        rows = auth_cursor.fetchall()
        return jsonify(rows)
    except mysql.connector.Error as err:
        print(f"Error listing users: {err}")
        return jsonify({"error": "Could not fetch users"}), 500


@app.route("/login", methods=["POST"])
@auth.login_required
def login():
    session["username"] = auth.current_user()
    return jsonify({"message": "Login successful"})


@app.route("/logout", methods=["POST"])
@auth.login_required
def logout():
    username = auth.current_user()
    session.pop("username", None)
    if username in logged_in_users:
        del logged_in_users[username]
    if username in user_db_connections:
        try:
            user_db_connections[username].close()
        except Exception:
            pass
        del user_db_connections[username]
    return jsonify({"message": "Logout successful"})


@app.route("/profile", methods=["GET"])
@auth.login_required
def get_profile():
    username = auth.current_user()
    return jsonify(logged_in_users.get(username))


@app.route("/profile", methods=["PUT"])
@auth.login_required
def update_profile():
    username = auth.current_user()
    data = request.json or {}
    new_username = data.get("username")

    if not new_username or not USERNAME_RE.match(new_username):
        return jsonify({"error": "New valid username required"}), 400

    try:
        auth_cursor.execute(
            "UPDATE users SET username=%s WHERE username=%s",
            (new_username, username)
        )
        auth_db.commit()
        return jsonify({"message": "Profile updated"})
    except mysql.connector.Error as err:
        print(f"Error updating profile: {err}")
        return jsonify({"error": "Could not update profile"}), 500


# --------------------------------------------------------------------
# HTML rendering routes (Frontend pages)
# --------------------------------------------------------------------

@app.route("/")
def home():
    return redirect(url_for('login_page'))


@app.route("/register_page")
def register_page():
    return render_template("register.html")


@app.route("/login_page")
def login_page():
    return render_template("login.html")


@app.route("/profile_page")
@auth.login_required
def profile_page():
    username = auth.current_user()
    user = logged_in_users.get(username)
    return render_template("profile.html", user=user)


@app.route("/logout_page")
def logout_page():
    return render_template("logout.html")

@app.route("/users_page")
def users_page():
    return render_template("users.html")


# --------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
