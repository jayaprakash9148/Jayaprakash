from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"  # change this to a strong secret

DB_FILE = "voters.db"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# Create database if it doesn't exist
def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS voters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            fingerprint_id TEXT UNIQUE NOT NULL,
            has_voted INTEGER DEFAULT 0
        )
    """)
    # Insert example voters only if table is empty
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM voters")
    if cur.fetchone()[0] == 0:
        conn.executemany("INSERT INTO voters (name, fingerprint_id) VALUES (?, ?)", [
            ("Alice", "FP1001"),
            ("Bob", "FP1002"),
            ("Charlie", "FP1003"),
        ])
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# Admin login
@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("dashboard"))
        else:
            return render_template_string(LOGIN_HTML, error="Invalid credentials")
    return render_template_string(LOGIN_HTML)

# Admin dashboard
@app.route("/dashboard")
def dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    conn = get_db_connection()
    voters = conn.execute("SELECT * FROM voters").fetchall()
    conn.close()
    return render_template_string(DASHBOARD_HTML, voters=voters)

# Add voter
@app.route("/add_voter", methods=["POST"])
def add_voter():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    
    name = request.form.get("name", "").strip()
    fingerprint_id = request.form.get("fingerprint_id", "").strip()

    if not name or not fingerprint_id:
        return redirect(url_for("dashboard"))

    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO voters (name, fingerprint_id) VALUES (?, ?)", 
            (name, fingerprint_id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("dashboard"))
    except sqlite3.IntegrityError:
        conn.close()
        # Reload dashboard with error message for duplicate fingerprint ID
        conn = get_db_connection()
        voters = conn.execute("SELECT * FROM voters").fetchall()
        conn.close()
        return render_template_string(DASHBOARD_HTML, voters=voters, error="Fingerprint ID already exists")
    except Exception as e:
        conn.close()
        conn = get_db_connection()
        voters = conn.execute("SELECT * FROM voters").fetchall()
        conn.close()
        return render_template_string(DASHBOARD_HTML, voters=voters, error=f"Error adding voter: {e}")

# Reset votes
@app.route("/reset_votes", methods=["POST"])
def reset_votes():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    username = request.form.get("username")
    password = request.form.get("password")
    if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
        return redirect(url_for("dashboard"))
    conn = get_db_connection()
    conn.execute("UPDATE voters SET has_voted = 0")
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))

# Admin logout
@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))

# API to verify fingerprint
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

# HTML Templates with enhanced UI
LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Admin Login</title>
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap" rel="stylesheet">
<style>
body { font-family: 'Roboto', sans-serif; background:#e0f7fa; display:flex; justify-content:center; align-items:center; height:100vh; }
.login-box { background:white; padding:30px; border-radius:10px; box-shadow:0 5px 15px rgba(0,0,0,0.3); width:300px; text-align:center; }
input { width:90%; padding:10px; margin:10px 0; border-radius:5px; border:1px solid #ccc; }
input[type=submit] { background:#00796b; color:white; border:none; cursor:pointer; }
input[type=submit]:hover { background:#004d40; }
.error { color:red; }
</style>
</head>
<body>
<div class="login-box">
<h2>Admin Login</h2>
{% if error %}<p class="error">{{ error }}</p>{% endif %}
<form method="post">
<input type="text" name="username" placeholder="Username" required>
<input type="password" name="password" placeholder="Password" required>
<input type="submit" value="Login">
</form>
</div>
</body>
</html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Voting Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap" rel="stylesheet">
<style>
body { font-family: 'Roboto', sans-serif; background:#f2f2f2; text-align:center; margin:0; padding:0; }
h2 { background:#00796b; color:white; padding:20px 0; margin:0; }
.dashboard { padding:20px; }
table { border-collapse: collapse; margin:auto; width:90%; box-shadow:0 5px 15px rgba(0,0,0,0.1); }
th, td { padding:12px; border:1px solid #ddd; text-align:center; }
th { background:#004d40; color:white; }
tr:nth-child(even){background:#e0f2f1;}
.status-yes { color:green; font-weight:bold; }
.status-no { color:red; font-weight:bold; }
form { margin:20px; display:inline-block; }
input { padding:10px; margin:5px; border-radius:5px; border:1px solid #ccc; }
input[type=submit] { background:#00796b; color:white; border:none; cursor:pointer; }
input[type=submit]:hover { background:#004d40; }
.logout { display:block; margin-top:20px; background:#c62828; padding:10px 20px; color:white; text-decoration:none; border-radius:5px; width:120px; margin-left:auto; margin-right:auto; }
.logout:hover { background:#b71c1c; }
</style>
</head>
<body>
<h2>Voting Dashboard</h2>
{% if error %}
<p style="color:red; font-weight:bold;">{{ error }}</p>
{% endif %}
<div class="dashboard">
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

<h3>Add Voter</h3>
<form method="post" action="/add_voter">
<input type="text" name="name" placeholder="Name" required>
<input type="text" name="fingerprint_id" placeholder="Fingerprint ID" required>
<input type="submit" value="Add">
</form>

<h3>Reset Votes</h3>
<form method="post" action="/reset_votes">
<input type="text" name="username" placeholder="Username" required>
<input type="password" name="password" placeholder="Password" required>
<input type="submit" value="Reset Votes">
</form>

<a class="logout" href="/logout">Logout</a>
</div>
</body>
</html>
"""

@app.route('/')
def home():
    return redirect(url_for("admin_login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
