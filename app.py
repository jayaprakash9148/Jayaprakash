from flask import Flask, request, jsonify, render_template_string
import sqlite3
import os

app = Flask(__name__)

# ---------------- Database Setup ----------------
DB_FOLDER = "data"
DB_PATH = f"{DB_FOLDER}/voters.db"

# Create folder if it doesn't exist
if not os.path.exists(DB_FOLDER):
    os.makedirs(DB_FOLDER)

# Initialize DB if it doesn't exist
def init_db():
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        conn.execute('''
            CREATE TABLE voters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                has_voted INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- Routes ----------------

@app.route('/')
def home():
    return "Voting Server is Running!"

# Display all voters
@app.route('/voters')
def voters():
    conn = get_db_connection()
    voter_list = conn.execute("SELECT * FROM voters").fetchall()
    conn.close()

    html = '''
    <h1>Voter List</h1>
    <table border="1" cellpadding="5">
        <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Has Voted?</th>
        </tr>
        {% for voter in voters %}
        <tr>
            <td>{{ voter['id'] }}</td>
            <td>{{ voter['name'] }}</td>
            <td>{{ 'Yes' if voter['has_voted'] else 'No' }}</td>
        </tr>
        {% endfor %}
    </table>
    '''
    return render_template_string(html, voters=voter_list)

# Add new voter
@app.route('/add_voter', methods=['POST'])
def add_voter():
    data = request.get_json()
    name = data.get("name")
    if not name:
        return jsonify({"status": "error", "message": "Name is required"}), 400

    conn = get_db_connection()
    conn.execute("INSERT INTO voters (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": f"Voter {name} added"})

# Verify voter (fingerprint simulation)
@app.route('/api/verify', methods=['POST'])
def verify():
    data = request.get_json()
    voter_id = data.get("id")  # here we assume fingerprint_id maps to voter id

    conn = get_db_connection()
    voter = conn.execute("SELECT * FROM voters WHERE id = ?", (voter_id,)).fetchone()

    if voter is None:
        response = {"status": "error", "message": "Voter not found"}
    elif voter["has_voted"]:
        response = {"status": "error", "message": "Already voted"}
    else:
        conn.execute("UPDATE voters SET has_voted = 1 WHERE id = ?", (voter_id,))
        conn.commit()
        response = {"status": "success", "message": "Vote allowed"}
    conn.close()
    return jsonify(response)

# ---------------- Run Server ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
