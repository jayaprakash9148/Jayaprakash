from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "supersecretkey123"  # Change to a strong random string
DB_FILE = "voters.db"

# Create database if it doesn't exist
def init_db():
    if not os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        conn.execute("""
            CREATE TABLE voters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                fingerprint_id TEXT UNIQUE NOT NULL,
                has_voted INTEGER DEFAULT 0
            )
        """)
        # Example voters
        conn.executemany("INSERT INTO voters (name, fingerprint_id) VALUES (?, ?)", [
            ("Alice", "FP1001"),
            ("Bob", "FP1002"),
            ("Charlie", "FP1003"),
        ])
        conn.commit()
        conn.close()

init_db()

# Helper function for DB connection
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# Admin login page
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == "admin" and password == "password":  # change credentials
            session["admin"] = True
            return redirect(url_for("show_voters"))
        else:
            flash("Invalid credentials", "danger")
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Login</title>
        <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap" rel="stylesheet">
        <style>
            body { font-family: 'Roboto', sans-serif; background-color: #f2f2f2; text-align: center; padding-top: 50px; }
            form { background-color: white; padding: 30px; border-radius: 10px; display: inline-block; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            input { padding: 10px; margin: 10px 0; width: 200px; border-radius: 5px; border: 1px solid #ccc; }
            button { padding: 10px 20px; border: none; border-radius: 5px; background-color: #4CAF50; color: white; cursor: pointer; }
        </style>
    </head>
    <body>
        <h2>Admin Login</h2>
        <form method="POST">
            <input type="text" name="username" placeholder="Username" required><br>
            <input type="password" name="password" placeholder="Password" required><br>
            <button type="submit">Login</button>
        </form>
    </body>
    </html>
    """
    return render_template_string(html)

# Show all voters (admin only)
@app.route("/voters")
def show_voters():
    if not session.get("admin"):
        return redirect(url_for("login"))
    conn = get_db_connection()
    voters = conn.execute("SELECT * FROM voters").fetchall()
    conn.close()
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Voters Database</title>
        <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap" rel="stylesheet">
        <style>
            body { font-family: 'Roboto', sans-serif; background-color: #f9f9f9; text-align: center; margin: 0; padding: 0; }
            h2 { background-color: #4CAF50; color: white; padding: 20px 0; margin: 0; }
            table { border-collapse: collapse; width: 80%; margin: 30px auto; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            th, td { border: 1px solid #ddd; padding: 12px; text-align: center; }
            th { background-color: #4CAF50; color: white; }
            tr:nth-child(even) { background-color: #f2f2f2; }
            tr:hover { background-color: #ddd; }
            .status-yes { color: green; font-weight: bold; }
            .status-no { color: red; font-weight: bold; }
            a { display: inline-block; margin: 20px; padding: 10px 20px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 5px; }
        </style>
    </head>
    <body>
        <h2>Voters Database</h2>
        <a href="/add_voter">Add Voter</a>
        <a href="/logout">Logout</a>
        <table>
            <tr><th>ID</th><th>Name</th><th>Fingerprint ID</th><th>Has Voted</th></tr>
            {% for voter in voters %}
            <tr>
                <td>{{ voter['id'] }}</td>
                <td>{{ voter['name'] }}</td>
                <td>{{ voter['fingerprint_id'] }}</td>
                <td class="{{ 'status-yes' if voter['has_voted'] else 'status-no' }}">{{ 'Yes' if voter['has_voted'] else 'No' }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """
    return render_template_string(html, voters=voters)

# Add a voter (admin only)
@app.route("/add_voter", methods=["GET", "POST"])
def add_voter():
    if not session.get("admin"):
        return redirect(url_for("login"))
    if request.method == "POST":
        name = request.form.get("name")
        fingerprint_id = request.form.get("fingerprint_id")
        try:
            conn = get_db_connection()
            conn.execute("INSERT INTO voters (name, fingerprint_id) VALUES (?, ?)", (name, fingerprint_id))
            conn.commit()
            conn.close()
            flash("Voter added successfully!", "success")
            return redirect(url_for("show_voters"))
        except sqlite3.IntegrityError:
            flash("Fingerprint ID already exists!", "danger")
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Add Voter</title>
        <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap" rel="stylesheet">
        <style>
            body { font-family: 'Roboto', sans-serif; background-color: #f2f2f2; text-align: center; padding-top: 50px; }
            form { background-color: white; padding: 30px; border-radius: 10px; display: inline-block; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            input { padding: 10px; margin: 10px 0; width: 200px; border-radius: 5px; border: 1px solid #ccc; }
            button { padding: 10px 20px; border: none; border-radius: 5px; background-color: #4CAF50; color: white; cursor: pointer; }
            a { display: inline-block; margin-top: 20px; text-decoration: none; color: #4CAF50; }
        </style>
    </head>
    <body>
        <h2>Add Voter</h2>
        <form method="POST">
            <input type="text" name="name" placeholder="Name" required><br>
            <input type="text" name="fingerprint_id" placeholder="Fingerprint ID" required><br>
            <button type="submit">Add</button>
        </form>
        <br>
        <a href="/voters">Back to Voters List</a>
    </body>
    </html>
    """
    return render_template_string(html)

# API for voting (optional, keeps your original)
@app.route('/api/verify', methods=['POST'])
def verify():
    data = request.get_json()
    fingerprint_id = data.get("fingerprint_id")

    conn = get_db_connection()
    voter = conn.execute("SELECT * FROM voters WHERE fingerprint_id = ?", (fingerprint_id,)).fetchone()

    if voter is None:
        response = {"status": "error", "message": "Fingerprint not found"}
    elif voter["has_voted"]:
        response = {"status": "error", "message": "Already voted"}
    else:
        conn.execute("UPDATE voters SET has_voted = 1 WHERE fingerprint_id = ?", (fingerprint_id,))
        conn.commit()
        response = {"status": "success", "message": "Vote allowed"}
    
    conn.close()
    return jsonify(response)

# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
