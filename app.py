from flask import Flask, request, jsonify, render_template_string
import sqlite3
import os

app = Flask(__name__)
DB_FILE = "voters.db"

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
    # Example voters (you can replace with real data)
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


# Endpoint for ESP fingerprint verification
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


# Endpoint to view all voters in browser
@app.route('/voters')
def show_voters():
    conn = get_db_connection()
    voters = conn.execute("SELECT * FROM voters").fetchall()
    conn.close()

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Voters List</title>
        <style>
            table { border-collapse: collapse; width: 50%; margin: auto; }
            th, td { border: 1px solid black; padding: 8px; text-align: center; }
            th { background-color: #f2f2f2; }
        </style>
    </head>
    <body>
        <h2 style="text-align:center;">Voters Database</h2>
        <table>
            <tr><th>ID</th><th>Name</th><th>Has Voted</th></tr>
            {% for voter in voters %}
            <tr>
                <td>{{ voter['id'] }}</td>
                <td>{{ voter['name'] }}</td>
                <td>{{ 'Yes' if voter['has_voted'] else 'No' }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """
    return render_template_string(html, voters=voters)


# Home page
@app.route('/')
def home():
    return "Voting Server is Running!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
