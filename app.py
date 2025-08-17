from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Replace with a strong secret key
DB_FILE = "voters.db"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"  # Replace with a secure password

# Create database if it doesn't exist
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

# ------------------- Routes -------------------

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('voters'))
        else:
            message = "Invalid credentials"
    return render_template_string(LOGIN_HTML, message=message)

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('login'))

@app.route('/voters')
def voters():
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    voters = conn.execute("SELECT * FROM voters").fetchall()
    conn.close()
    return render_template_string(VOTERS_HTML, voters=voters)

@app.route('/add_voter', methods=['GET', 'POST'])
def add_voter():
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))
    message = ""
    if request.method == 'POST':
        name = request.form.get('name')
        fingerprint_id = request.form.get('fingerprint_id')
        try:
            conn = get_db_connection()
            conn.execute(
                "INSERT INTO voters (name, fingerprint_id) VALUES (?, ?)",
                (name, fingerprint_id)
            )
            conn.commit()
            conn.close()
            message = "Voter added successfully!"
        except Exception as e:
            message = f"Error: {e}"
            print(message)  # Shows in Render logs
    return render_template_string(ADD_VOTER_HTML, message=message)

@app.route('/reset_votes', methods=['POST'])
def reset_votes():
    # First ask for admin password if not already provided
    if 'admin_logged_in' not in session:
        return redirect(url_for('login'))
    password = request.form.get('password')
    if password != ADMIN_PASSWORD:
        return "Invalid password!"
    try:
        conn = get_db_connection()
        conn.execute("UPDATE voters SET has_voted = 0")
        conn.commit()
        conn.close()
        return redirect(url_for('voters'))
    except Exception as e:
        print(e)
        return f"Error resetting votes: {e}"

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

# ------------------- HTML Templates -------------------

LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin Login</title>
    <style>
        body { font-family: Arial; background: #f2f2f2; text-align:center; padding-top:100px; }
        input { padding:10px; margin:5px; }
        button { padding:10px 20px; }
        .message { color:red; font-weight:bold; }
    </style>
</head>
<body>
    <h2>Admin Login</h2>
    <form method="post">
        <input type="text" name="username" placeholder="Username" required><br>
        <input type="password" name="password" placeholder="Password" required><br>
        <button type="submit">Login</button>
    </form>
    {% if message %}<p class="message">{{ message }}</p>{% endif %}
</body>
</html>
"""

VOTERS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Voters Database</title>
    <style>
        body { font-family: Arial; background:#f9f9f9; text-align:center; }
        h2 { background:#4CAF50; color:white; padding:20px; }
        table { margin:auto; border-collapse: collapse; width:80%; box-shadow:0 2px 10px rgba(0,0,0,0.1); }
        th, td { border:1px solid #ddd; padding:12px; text-align:center; }
        th { background:#4CAF50; color:white; }
        tr:nth-child(even){background:#f2f2f2;}
        tr:hover{background:#ddd;}
        .status-yes{color:green; font-weight:bold;}
        .status-no{color:red; font-weight:bold;}
        button { padding:8px 15px; margin:10px; }
        a { text-decoration:none; padding:8px 15px; background:#2196F3; color:white; border-radius:5px; }
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
    <form method="post" action="/reset_votes">
        <input type="password" name="password" placeholder="Enter Admin Password to Reset Votes" required>
        <button type="submit">Reset Votes</button>
    </form>
</body>
</html>
"""

ADD_VOTER_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Add Voter</title>
    <style>
        body { font-family: Arial; background:#f2f2f2; text-align:center; padding-top:50px; }
        input { padding:10px; margin:5px; }
        button { padding:10px 20px; }
        .message { font-weight:bold; color:green; }
    </style>
</head>
<body>
    <h2>Add Voter</h2>
    <form method="post">
        <input type="text" name="name" placeholder="Voter Name" required><br>
        <input type="text" name="fingerprint_id" placeholder="Fingerprint ID" required><br>
        <button type="submit">Add Voter</button>
    </form>
    {% if message %}<p class="message">{{ message }}</p>{% endif %}
    <br><a href="/voters">Back to Voters List</a>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
