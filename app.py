from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
import sqlite3
import os
import base64

app = Flask(__name__)
app.secret_key = "supersecretkey"
DB_FILE = "voters.db"

# Create database if it doesn't exist
if not os.path.exists(DB_FILE):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE voters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            fingerprint_id TEXT UNIQUE NOT NULL,
            fingerprint_template BLOB,
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

# Admin credentials
ADMIN_USER = "admin"
ADMIN_PASS = "password"  # change before deployment

# --------- Routes ---------
@app.route('/')
def home():
    return render_template_string(HOME_HTML)

@app.route('/admin', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USER and password == ADMIN_PASS:
            session["admin"] = True
            return redirect(url_for("voters_page"))
        else:
            return render_template_string(LOGIN_HTML, error="Invalid credentials")
    return render_template_string(LOGIN_HTML, error=None)

@app.route('/logout')
def logout():
    session.pop("admin", None)
    return redirect(url_for("home"))

@app.route('/voters', methods=['GET', 'POST'])
def voters_page():
    if not session.get("admin"):
        return redirect(url_for("login"))

    conn = get_db_connection()
    if request.method == "POST":
        # Adding voter
        if "add_voter" in request.form:
            name = request.form.get("name")
            fingerprint_id = request.form.get("fingerprint_id")
            fingerprint_template = request.form.get("fingerprint_template")  # base64 string
            if name and fingerprint_id:
                try:
                    fingerprint_blob = base64.b64decode(fingerprint_template) if fingerprint_template else None
                    conn.execute("INSERT INTO voters (name, fingerprint_id, fingerprint_template) VALUES (?, ?, ?)",
                                 (name, fingerprint_id, fingerprint_blob))
                    conn.commit()
                except:
                    pass
        # Reset votes
        elif "reset_votes" in request.form:
            # Ask for admin confirmation
            session["reset_confirm"] = True
            return redirect(url_for("reset_votes"))

    voters = conn.execute("SELECT * FROM voters").fetchall()
    conn.close()
    return render_template_string(VOTERS_HTML, voters=voters)

@app.route('/reset_votes', methods=['GET', 'POST'])
def reset_votes():
    if not session.get("admin") or not session.get("reset_confirm"):
        return redirect(url_for("voters_page"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USER and password == ADMIN_PASS:
            conn = get_db_connection()
            conn.execute("UPDATE voters SET has_voted = 0")
            conn.commit()
            conn.close()
            session.pop("reset_confirm")
            return redirect(url_for("voters_page"))
        else:
            return render_template_string(RESET_HTML, error="Invalid credentials")
    return render_template_string(RESET_HTML, error=None)

@app.route('/api/verify', methods=['POST'])
def verify():
    data = request.get_json()
    fingerprint_id = data.get("fingerprint_id")
    fingerprint_template = data.get("fingerprint_template")  # optional, base64 string

    conn = get_db_connection()
    voter = conn.execute("SELECT * FROM voters WHERE fingerprint_id = ?", (fingerprint_id,)).fetchone()

    if voter is None:
        # Optional: store fingerprint template if new voter
        if fingerprint_template:
            blob = base64.b64decode(fingerprint_template)
            conn.execute("INSERT INTO voters (name, fingerprint_id, fingerprint_template) VALUES (?, ?, ?)",
                         ("Unknown", fingerprint_id, blob))
            conn.commit()
        response = {"status": "error", "message": "Fingerprint not found"}
    elif voter["has_voted"]:
        response = {"status": "error", "message": "Already voted"}
    else:
        conn.execute("UPDATE voters SET has_voted = 1 WHERE fingerprint_id = ?", (fingerprint_id,))
        conn.commit()
        response = {"status": "success", "message": "Vote allowed"}

    conn.close()
    return jsonify(response)

# --------- HTML Templates ---------
HOME_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Voting Server</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Roboto', sans-serif; background-color: #f2f2f2; text-align: center; padding-top: 100px; }
        .btn { background-color: #4CAF50; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-size: 18px; }
        h1 { color: #333; }
    </style>
</head>
<body>
    <h1>Voting Server</h1>
    <a href="/admin" class="btn">Admin Login</a>
</body>
</html>
"""

LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin Login</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Roboto', sans-serif; background-color: #f2f2f2; display: flex; justify-content: center; align-items: center; height: 100vh; }
        .login-box { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); width: 300px; }
        input { width: 100%; padding: 10px; margin: 10px 0; border-radius: 5px; border: 1px solid #ccc; }
        button { width: 100%; padding: 10px; background-color: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer; }
        .error { color: red; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>Admin Login</h2>
        {% if error %}<p class="error">{{ error }}</p>{% endif %}
        <form method="POST">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
    </div>
</body>
</html>
"""

RESET_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Confirm Reset Votes</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Roboto', sans-serif; background-color: #f2f2f2; display: flex; justify-content: center; align-items: center; height: 100vh; }
        .login-box { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); width: 300px; }
        input { width: 100%; padding: 10px; margin: 10px 0; border-radius: 5px; border: 1px solid #ccc; }
        button { width: 100%; padding: 10px; background-color: #f44336; color: white; border: none; border-radius: 5px; cursor: pointer; }
        .error { color: red; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>Confirm Admin</h2>
        {% if error %}<p class="error">{{ error }}</p>{% endif %}
        <form method="POST">
            <input type="text" name="username" placeholder="Admin Username" required>
            <input type="password" name="password" placeholder="Admin Password" required>
            <button type="submit">Confirm Reset Votes</button>
        </form>
    </div>
</body>
</html>
"""

VOTERS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Voters Database</title>
    <link href="https://fonts.googleapis.com/css2?family
