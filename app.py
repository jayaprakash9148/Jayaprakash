from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Needed for sessions

DB_FILE = "voters.db"

# Admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password123"

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


@app.route('/')
def home():
    return redirect(url_for('admin_login'))


# Admin login page
@app.route('/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('show_voters'))
        else:
            return render_template_string(LOGIN_HTML, error="Invalid credentials")
    return render_template_string(LOGIN_HTML, error=None)


# Admin logout
@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))


# Show voters list (admin only)
@app.route('/voters')
def show_voters():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    voters = conn.execute("SELECT * FROM voters").fetchall()
    conn.close()
    return render_template_string(VOTERS_HTML, voters=voters)


# Add voter page (admin only)
@app.route('/add_voter', methods=['GET', 'POST'])
def add_voter():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    message = ""
    if request.method == "POST":
        name = request.form.get("name")
        fingerprint_id = request.form.get("fingerprint_id")
        try:
            conn = get_db_connection()
            conn.execute("INSERT INTO voters (name, fingerprint_id) VALUES (?, ?)", (name, fingerprint_id))
            conn.commit()
            conn.close()
            message = f"Voter '{name}' added successfully!"
        except sqlite3.IntegrityError:
            message = "Fingerprint ID already exists!"
    return render_template_string(ADD_VOTER_HTML, message=message)


# Reset votes (admin only)
@app.route('/reset_votes', methods=['POST'])
def reset_votes():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    conn.execute("UPDATE voters SET has_voted = 0")
    conn.commit()
    conn.close()
    return redirect(url_for('show_voters'))


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


# HTML Templates
LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin Login</title>
    <style>
        body { font-family: Arial; background-color: #f4f4f4; text-align: center; padding-top: 50px; }
        input { padding: 10px; margin: 5px; }
        .error { color: red; font-weight: bold; }
    </style>
</head>
<body>
    <h2>Admin Login</h2>
    {% if error %}<p class="error">{{ error }}</p>{% endif %}
    <form method="post">
        <input type="text" name="username" placeholder="Username" required><br>
        <input type="password" name="password" placeholder="Password" required><br>
        <input type="submit" value="Login">
    </form>
</body>
</html>
"""

VOTERS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Voters List</title>
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
        a { margin: 10px; display: inline-block; text-decoration: none; color: white; background-color: #4CAF50; padding: 8px 15px; border-radius: 5px; }
        form { display: inline-block; }
    </style>
</head>
<body>
    <h2>Voters Database</h2>
    <a href="/add_voter">Add Voter</a>
    <a href="/logout">Logout</a>
    <form method="post" action="/reset_votes" onsubmit="return confirm('Are you sure you want to reset all votes?');">
        <input type="submit" value="Reset Votes">
    </form>
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

ADD_VOTER_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Add Voter</title>
    <style>
        body { font-family: Arial; background-color: #f4f4f4; text-align: center; padding-top: 50px; }
        input { padding: 10px; margin: 5px; }
        .message { color: green; font-weight: bold; }
    </style>
</head>
<body>
    <h2>Add New Voter</h2>
    {% if message %}<p class="message">{{ message }}</p>{% endif %}
    <form method="post">
        <input type="text" name="name" placeholder="Voter Name" required><br>
        <input type="text" name="fingerprint_id" placeholder="Fingerprint ID" required><br>
        <input type="submit" value="Add Voter">
    </form>
    <br>
    <a href="/voters">Back to Voters List</a>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
