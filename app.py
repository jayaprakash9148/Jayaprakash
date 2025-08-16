from flask import Flask, request, jsonify, render_template_string
import sqlite3
import os

app = Flask(__name__)

DB_FILE = "voters.db"

# Initialize database if not exists
def init_db():
    if not os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE voters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                has_voted INTEGER DEFAULT 0
            )
        ''')
        # Example voters (optional)
        c.execute("INSERT INTO voters (name, has_voted) VALUES ('Alice', 0)")
        c.execute("INSERT INTO voters (name, has_voted) VALUES ('Bob', 1)")
        conn.commit()
        conn.close()

# Get DB connection
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def home():
    return "Voting Server is Running!"

@app.route('/api/verify', methods=['POST'])
def verify():
    data = request.get_json()
    fingerprint_id = data.get("fingerprint_id")

    conn = get_db_connection()
    voter = conn.execute("SELECT * FROM voters WHERE id = ?", (fingerprint_id,)).fetchone()

    if voter is None:
        response = {"status": "error", "message": "Fingerprint not found"}
    elif voter["has_voted"]:
        response = {"status": "error", "message": "Already voted"}
    else:
        conn.execute("UPDATE voters SET has_voted = 1 WHERE id = ?", (fingerprint_id,))
        conn.commit()
        response = {"status": "success", "message": "Vote allowed"}

    conn.close()
    return jsonify(response)

# Voters list page
@app.route('/voters')
def list_voters():
    conn = get_db_connection()
    voters = conn.execute("SELECT * FROM voters").fetchall()
    conn.close()
    
    # Simple HTML table
    html = '''
    <h2>Voter List</h2>
    <table border="1" cellpadding="5" cellspacing="0">
        <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Voted</th>
        </tr>
        {% for voter in voters %}
        <tr>
            <td>{{ voter.id }}</td>
            <td>{{ voter.name }}</td>
            <td>{{ 'Yes' if voter.has_voted else 'No' }}</td>
        </tr>
        {% endfor %}
    </table>
    '''
    return render_template_string(html, voters=voters)

if __name__ == "__main__":
    init_db()  # Ensure DB is created
    app.run(host="0.0.0.0", port=5000, debug=True)
