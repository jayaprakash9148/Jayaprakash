from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Change to something secure
DB_FILE = "voters.db"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password123"  # Change to your secure password

# Create database if it doesn't exist
if not os.path.exists(DB_FILE):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE voters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            fingerprint_template TEXT UNIQUE NOT NULL,
            has_voted INTEGER DEFAULT 0
        )
    """)
    # Example voters
    conn.executemany("INSERT INTO voters (name, fingerprint_template) VALUES (?, ?)", [
        ("Alice", "FP_TEMPLATE_1001"),
        ("Bob", "FP_TEMPLATE_1002"),
        ("Charlie", "FP_TEMPLATE_1003"),
    ])
    conn.commit()
    conn.close()


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def home():
    if "admin_logged_in" in session:
        return redirect(url_for('admin_dashboard'))
    return render_template_string("""
        <h2 style='text-align:center;'>Voting Server is Running!</h2>
        <div style='text-align:center; margin-top:20px;'>
            <a href="{{ url_for('admin_login') }}">
                <button style='padding:10px 20px; font-size:16px;'>Admin Login</button>
            </a>
        </div>
    """)


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            return "<h3 style='color:red; text-align:center;'>Invalid credentials</h3>"
    return render_template_string("""
        <h2 style='text-align:center;'>Admin Login</h2>
        <form method="post" style='text-align:center; margin-top:20px;'>
            <input type="text" name="username" placeholder="Username" required><br><br>
            <input type="password" name="password" placeholder="Password" required><br><br>
            <button type="submit">Login</button>
        </form>
    """)


@app.route('/admin/dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if "admin_logged_in" not in session:
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    if request.method == 'POST':
        if 'add_voter' in request.form:
            name = request.form.get("name")
            fingerprint_template = request.form.get("fingerprint_template")
            if name and fingerprint_template:
                try:
                    conn.execute(
                        "INSERT INTO voters (name, fingerprint_template) VALUES (?, ?)",
                        (name, fingerprint_template)
                    )
                    conn.commit()
                except sqlite3.IntegrityError:
                    return "<h3 style='color:red; text-align:center;'>Fingerprint already exists!</h3>"
        elif 'reset_votes' in request.form:
            # Extra password confirmation for reset
            reset_password = request.form.get("reset_password")
            if reset_password == ADMIN_PASSWORD:
                conn.execute("UPDATE voters SET has_voted = 0")
                conn.commit()
            else:
                return "<h3 style='color:red; text-align:center;'>Incorrect password for reset!</h3>"

    voters = conn.execute("SELECT * FROM voters").fetchall()
    conn.close()

    DASHBOARD_HTML = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Dashboard - Voters</title>
        <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap" rel="stylesheet">
        <style>
            body { font-family: 'Roboto', sans-serif; background-color: #f9f9f9; margin:0; padding:0;}
            h2 { background-color: #4CAF50; color: white; padding: 20px 0; margin:0; text-align:center;}
            table { border-collapse: collapse; width: 80%; margin: 20px auto; box-shadow: 0 2px 10px rgba(0,0,0,0.1);}
            th, td { border: 1px solid #ddd; padding: 12px; text-align:center;}
            th { background-color: #4CAF50; color: white; }
            tr:nth-child(even) { background-color: #f2f2f2;}
            tr:hover { background-color: #ddd;}
            .status-yes { color: green; font-weight:bold;}
            .status-no { color: red; font-weight:bold;}
            .form-container { width: 60%; margin:20px auto; text-align:center;}
            input[type=text], input[type=password] { padding:8px; width:60%; margin:5px 0;}
            button { padding:10px 20px; margin-top:10px; font-size:16px; }
        </style>
    </head>
    <body>
        <h2>Admin Dashboard</h2>

        <div class="form-container">
            <h3>Add Voter</h3>
            <form method="post">
                <input type="text" name="name" placeholder="Voter Name" required><br>
                <input type="text" name="fingerprint_template" placeholder="Fingerprint Template" required><br>
                <button type="submit" name="add_voter">Add Voter</button>
            </form>
        </div>

        <div class="form-container">
            <h3>Reset Votes</h3>
            <form method="post">
                <input type="password" name="reset_password" placeholder="Enter password to reset"><br>
                <button type="submit" name="reset_votes">Reset All Votes</button>
            </form>
        </div>

        <table>
            <tr><th>ID</th><th>Name</th><th>Has Voted</th></tr>
            {% for voter in voters %}
            <tr>
                <td>{{ voter['id'] }}</td>
                <td>{{ voter['name'] }}</td>
                <td class="{{ 'status-yes' if voter['has_voted'] else 'status-no' }}">{{ 'Yes' if voter['has_voted'] else 'No' }}</td>
            </tr>
            {% endfor %}
        </table>

        <div style="text-align:center; margin:20px;">
            <a href="{{ url_for('admin_logout') }}">
                <button>Logout</button>
            </a>
        </div>
    </body>
    </html>
    """
    return render_template_string(DASHBOARD_HTML, voters=voters)


@app.route('/admin/logout')
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for('home'))


@app.route('/api/verify', methods=['POST'])
def verify():
    data = request.get_json()
    fingerprint_template = data.get("fingerprint_template")

    conn = get_db_connection()
    voter = conn.execute("SELECT * FROM voters WHERE fingerprint_template = ?", (fingerprint_template,)).fetchone()

    if voter is None:
        response = {"status": "error", "message": "Fingerprint not found"}
    elif voter["has_voted"]:
        response = {"status": "error", "message": "Already voted"}
    else:
        conn.execute("UPDATE voters SET has_voted = 1 WHERE fingerprint_template = ?", (fingerprint_template,))
        conn.commit()
        response = {"status": "success", "message": "Vote allowed"}

    conn.close()
    return jsonify(response)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
