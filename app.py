from flask import Flask, request, jsonify, render_template_string
import sqlite3
import os

app = Flask(__name__)
DB_PATH = "voters.db"

# Initialize database if not exists
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

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def home():
    return "Voting Server is Running!"

# View all voters
@app.route('/voters', methods=['GET'])
def voters_list():
    conn = get_db_connection()
    voters = conn.execute("SELECT * FROM voters").fetchall()
    conn.close()
    
    html = "<h2>Voter List</h2><table border='1'><tr><th>ID</th><th>Name</th><th>Voted</th></tr>"
    for v in voters:
        html += f"<tr><td>{v['id']}</td><td>{v['name']}</td><td>{'Yes' if v['has_voted'] else 'No'}</td></tr>"
    html += "</table>"
    return html

# Add a voter
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
    return jsonify({"status": "success", "message": f"Voter '{name}' added successfully"})

# Verify vote
@app.route('/api/verify', methods=['POST'])
def verify():
    data = request.get_json()
    voter_id = data.get("voter_id")
    if voter_id is None:
        return jsonify({"status": "error", "message": "Voter ID required"}), 400

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

if __name__ == "__main__":
    init_db()  # Ensure DB is ready before server starts
    app.run(host="0.0.0.0", port=5000, debug=True)
