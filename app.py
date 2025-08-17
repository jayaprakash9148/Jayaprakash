from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "your_super_secret_key"  # Change this in production
DB_FILE = "voters.db"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"  # Change this in production

# Create database if it doesn't exist
if not os.path.exists(DB_FILE):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE voters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            fingerprint_id TEXT UNIQUE NOT NULL,
            fingerprint_template TEXT,
            has_voted INTEGER DEFAULT 0
        )
    """)
    # Example voters
    conn.executemany("INSERT INTO voters (name, fingerprint_id, fingerprint_template) VALUES (?, ?, ?)", [
        ("Alice", "FP1001", "template1"),
        ("Bob", "FP1002", "template2"),
        ("Charlie", "FP1003", "template3"),
    ])
    conn.commit()
    conn.close()


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# ------------------ FRONT PAGE ------------------
@app.route('/')
def home():
    if "admin_logged_in" in session:
        return redirect(url_for('admin_dashboard'))
    return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Voting Server</title>
            <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap" rel="stylesheet">
            <style>
                body { font-family: 'Roboto', sans-serif; background-color: #f0f4f7; display:flex; justify-content:center; align-items:center; height:100vh; margin:0; }
                button { padding:20px 40px; font-size:20px; background-color:#4CAF50; color:white; border:none; border-radius:8px; cursor:pointer; box-shadow:0 4px 6px rgba(0,0,0,0.2); }
                button:hover { background-color:#45a049; transform:translateY(-2px); }
            </style>
        </head>
        <body>
            <a href="{{ url_for('admin_login') }}"><button>Admin Login</button></a>
        </body>
        </html>
    """)

# ------------------ ADMIN LOGIN ------------------
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return "Invalid credentials. <a href='/admin'>Try again</a>"
    return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Admin Login</title>
            <style>
                body { display:flex; justify-content:center; align-items:center; height:100vh; font-family:sans-serif; background:#e2f0f1; margin:0; }
                form { background:white; padding:30px; border-radius:10px; box-shadow:0 4px 6px rgba(0,0,0,0.2); }
                input { display:block; width:100%; padding:10px; margin:10px 0; border-radius:5px; border:1px solid #ccc; }
                button { padding:10px 20px; background:#4CAF50; color:white; border:none; border-radius:5px; cursor:pointer; }
                button:hover { background:#45a049; }
            </style>
        </head>
        <body>
            <form method="POST">
                <h2>Admin Login</h2>
                <input type="text" name="username" placeholder="Username" required>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit">Login</button>
            </form>
        </body>
        </html>
    """)

# ------------------ ADMIN DASHBOARD ------------------
@app.route('/dashboard')
def admin_dashboard():
    if "admin_logged_in" not in session:
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    voters = conn.execute("SELECT * FROM voters").fetchall()
    conn.close()

    DASHBOARD_HTML = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Dashboard</title>
        <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap" rel="stylesheet">
        <style>
            body { font-family: 'Roboto', sans-serif; background-color: #f0f4f7; margin:0; padding:0; text-align:center; }
            h2 { background-color:#4CAF50; color:white; padding:20px 0; margin:0; }
            table { border-collapse: collapse; width:90%; margin:30px auto; box-shadow:0 4px 8px rgba(0,0,0,0.1); }
            th, td { border:1px solid #ddd; padding:12px; text-align:center; }
            th { background-color:#4CAF50; color:white; }
            tr:nth-child(even){background-color:#f9f9f9;}
            tr:hover{background-color:#ddd;}
            .status-yes { color:green; font-weight:bold; }
            .status-no { color:red; font-weight:bold; }
            button { padding:10px 20px; margin:10px; background:#4CAF50; color:white; border:none; border-radius:5px; cursor:pointer; }
            button:hover { background:#45a049; }
        </style>
    </head>
    <body>
        <h2>Admin Dashboard - Voters List</h2>
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
        <form action="/reset_votes" method="POST" style="display:inline;">
            <button type="submit">Reset Votes</button>
        </form>
        <form action="/add_voter" method="GET" style="display:inline;">
            <button type="submit">Add Voter</button>
        </form>
        <form action="/logout" method="POST" style="display:inline;">
            <button type="submit">Logout</button>
        </form>
    </body>
    </html>
    """
    return render_template_string(DASHBOARD_HTML, voters=voters)

# ------------------ RESET VOTES ------------------
@app.route('/reset_votes', methods=['POST'])
def reset_votes():
    if "admin_logged_in" not in session:
        return redirect(url_for('admin_login'))
    
    # Ask password again for security
    return render_template_string("""
        <form method="POST" action="/reset_votes_confirm">
            <h3>Enter password to confirm reset:</h3>
            <input type="password" name="password" required>
            <button type="submit">Confirm Reset</button>
        </form>
    """)

@app.route('/reset_votes_confirm', methods=['POST'])
def reset_votes_confirm():
    if "admin_logged_in" not in session:
        return redirect(url_for('admin_login'))
    password = request.form.get("password")
    if password != ADMIN_PASSWORD:
        return "Incorrect password. <a href='/dashboard'>Back</a>"
    
    conn = get_db_connection()
    conn.execute("UPDATE voters SET has_voted = 0")
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

# ------------------ ADD VOTER ------------------
@app.route('/add_voter', methods=['GET', 'POST'])
def add_voter():
    if "admin_logged_in" not in session:
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        name = request.form.get("name")
        fingerprint_id = request.form.get("fingerprint_id")
        fingerprint_template = request.form.get("fingerprint_template")
        conn = get_db_connection()
        conn.execute("INSERT INTO voters (name,fingerprint_id,fingerprint_template) VALUES (?,?,?)",
                     (name, fingerprint_id, fingerprint_template))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_dashboard'))
    return render_template_string("""
        <form method="POST">
            <h3>Add Voter</h3>
            <input type="text" name="name" placeholder="Name" required>
            <input type="text" name="fingerprint_id" placeholder="Fingerprint ID" required>
            <input type="text" name="fingerprint_template" placeholder="Fingerprint Template" required>
            <button type="submit">Add</button>
        </form>
    """)

# ------------------ LOGOUT ------------------
@app.route('/logout', methods=['POST'])
def logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for
