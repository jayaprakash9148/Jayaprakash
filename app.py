from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # change to a strong secret key

DB_FILE = "voters.db"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password123"  # change to your secure password

# --- Create database if it doesn't exist ---
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


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


# --- Home page ---
@app.route('/')
def home():
    if session.get("admin_logged_in"):
        return redirect(url_for("dashboard"))
    html = """
    <h2 style='text-align:center;'>Voting Server</h2>
    <div style='text-align:center; margin-top:50px;'>
        <a href="/login"><button style='padding:10px 20px;font-size:16px;'>Admin Login</button></a>
    </div>
    """
    return html


# --- Admin login ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("dashboard"))
        else:
            return "<h3 style='color:red;text-align:center;'>Invalid credentials</h3><a href='/login'>Try again</a>"
    html = """
    <h2 style='text-align:center;'>Admin Login</h2>
    <form method='POST' style='text-align:center;margin-top:50px;'>
        <input type='text' name='username' placeholder='Username' required><br><br>
        <input type='password' name='password' placeholder='Password' required><br><br>
        <button type='submit'>Login</button>
    </form>
    """
    return html


# --- Admin dashboard ---
@app.route('/dashboard')
def dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))

    conn = get_db_connection()
    voters = conn.execute("SELECT * FROM voters").fetchall()
    conn.close()

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Dashboard</title>
        <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap" rel="stylesheet">
        <style>
            body { font-family: 'Roboto', sans-serif; background-color: #f9f9f9; margin:0; padding:0; }
            h2 { background-color: #4CAF50; color: white; padding: 20px; margin: 0; text-align:center; }
            table { border-collapse: collapse; width: 80%; margin: 30px auto; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            th, td { border: 1px solid #ddd; padding: 12px; text-align: center; }
            th { background-color: #4CAF50; color: white; }
            tr:nth-child(even) { background-color: #f2f2f2; }
            tr:hover { background-color: #ddd; }
            .status-yes { color: green; font-weight: bold; }
            .status-no { color: red; font-weight: bold; }
            .button { padding: 10px 20px; margin: 10px; font-size: 16px; }
            .form-inline input { padding:5px; margin-right:5px; }
        </style>
    </head>
    <body>
        <h2>Admin Dashboard</h2>

        <div style='text-align:center;'>
            <form class='form-inline' action="/add_voter" method="POST">
                <input type='text' name='name' placeholder='Voter Name' required>
                <input type='text' name='fingerprint_id' placeholder='Fingerprint ID' required>
                <button type='submit' class='button'>Add Voter</button>
            </form>

            <form action="/reset_votes" method="POST" style='display:inline-block;'>
                <button type='submit' class='button'>Reset Votes</button>
            </form>

            <a href="/logout"><button class='button'>Logout</button></a>
        </div>

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


# --- Add voter ---
@app.route('/add_voter', methods=['POST'])
def add_voter():
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))

    name = request.form.get("name")
    fingerprint_id = request.form.get("fingerprint_id")

    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO voters (name, fingerprint_id) VALUES (?, ?)", (name, fingerprint_id))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return "<h3 style='color:red;text-align:center;'>Fingerprint ID already exists!</h3><a href='/dashboard'>Back</a>"

    conn.close()
    return redirect(url_for("dashboard"))


# --- Reset votes with secondary login ---
@app.route('/reset_votes', methods=['POST'])
def reset_votes():
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))

    # Ask for secondary username/password
    html = """
    <h2 style='text-align:center;'>Confirm Reset Votes</h2>
    <form method='POST' action='/reset_confirm' style='text-align:center;margin-top:50px;'>
        <input type='text' name='username' placeholder='Username' required><br><br>
        <input type='password' name='password' placeholder='Password' required><br><br>
        <button type='submit'>Confirm Reset</button>
    </form>
    """
    return html


@app.route('/reset_confirm', methods=['POST'])
def reset_confirm():
    username = request.form.get("username")
    password = request.form.get("password")

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        conn = get_db_connection()
        conn.execute("UPDATE voters SET has_voted = 0")
        conn.commit()
        conn.close()
        return "<h3 style='color:green;text-align:center;'>All votes have been reset!</h3><a href='/dashboard'>Back</a>"
    else:
        return "<h3 style='color:red;text-align:center;'>Invalid credentials!</h3><a href='/dashboard'>Back</a>"


# --- Logout ---
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("home"))


# --- Fingerprint verification API ---
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
