from flask import Flask, request, jsonify, render_template, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Keep this secret!

# Admin credentials
ADMIN_USER = "admin"
ADMIN_PASS = "password123"  # Change this to your own secure password

# Database setup
DB_NAME = "voters.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS voters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            fingerprint_id TEXT UNIQUE NOT NULL,
            has_voted INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

# -------------------- Admin Login --------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USER and password == ADMIN_PASS:
            session['admin'] = True
            return redirect('/voters')
        else:
            return "Invalid credentials!"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/login')

# -------------------- Voter Management --------------------
@app.route('/voters')
def voters():
    if not session.get('admin'):
        return redirect('/login')
    conn = get_db_connection()
    voters_list = conn.execute("SELECT * FROM voters").fetchall()
    conn.close()
    return render_template('voters.html', voters=voters_list)

@app.route('/add_voter', methods=['POST'])
def add_voter():
    if not session.get('admin'):
        return redirect('/login')
    name = request.form.get('name')
    fingerprint_id = request.form.get('fingerprint_id')
    if not name or not fingerprint_id:
        return "Name and Fingerprint ID are required!"
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO voters (name, fingerprint_id) VALUES (?, ?)",
            (name, fingerprint_id)
        )
        conn.commit()
        message = "Voter added successfully!"
    except sqlite3.IntegrityError:
        message = "Fingerprint ID already exists!"
    conn.close()
    return redirect('/voters')

# -------------------- Fingerprint Verification API --------------------
@app.route('/api/verify', methods=['POST'])
def verify():
    data = request.get_json()
    fingerprint_id = data.get("fingerprint_id")
    conn = get_db_connection()
    voter = conn.execute(
        "SELECT * FROM voters WHERE fingerprint_id = ?",
        (fingerprint_id,)
    ).fetchone()

    if voter is None:
        response = {"status": "error", "message": "Fingerprint not found"}
    elif voter["has_voted"]:
        response = {"status": "error", "message": "Already voted"}
    else:
        conn.execute(
            "UPDATE voters SET has_voted = 1 WHERE fingerprint_id = ?",
            (fingerprint_id,)
        )
        conn.commit()
        response = {"status": "success", "message": "Vote allowed"}
    conn.close()
    return jsonify(response)

@app.route('/')
def home():
    return redirect('/login')

# -------------------- Templates --------------------
# Create "templates/login.html" and "templates/voters.html" in your folder.

# login.html
'''
<!DOCTYPE html>
<html>
<head><title>Admin Login</title></head>
<body>
<h2>Admin Login</h2>
<form method="POST">
  Username: <input type="text" name="username" required><br><br>
  Password: <input type="password" name="password" required><br><br>
  <input type="submit" value="Login">
</form>
</body>
</html>
'''

# voters.html
'''
<!DOCTYPE html>
<html>
<head><title>Voter List</title></head>
<body>
<h2>Voter List (Admin)</h2>
<a href="/logout">Logout</a>
<h3>Add New Voter</h3>
<form method="POST" action="/add_voter">
  Name: <input type="text" name="name" required>
  Fingerprint ID: <input type="text" name="fingerprint_id" required>
  <input type="submit" value="Add Voter">
</form>

<h3>Existing Voters</h3>
<table border="1">
  <tr><th>ID</th><th>Name</th><th>Fingerprint ID</th><th>Has Voted</th></tr>
  {% for voter in voters %}
    <tr>
      <td>{{ voter['id'] }}</td>
      <td>{{ voter['name'] }}</td>
      <td>{{ voter['fingerprint_id'] }}</td>
      <td>{{ 'Yes' if voter['has_voted'] else 'No' }}</td>
    </tr>
  {% endfor %}
</table>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
