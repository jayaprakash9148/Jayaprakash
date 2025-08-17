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


@app.route('/voters')
def show_voters():
    conn = get_db_connection()
    voters = conn.execute("SELECT * FROM voters").fetchall()
    conn.close()

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Voters Database</title>
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
        </style>
    </head>
    <body>
        <h2>Voters Database</h2>
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
    </body>
    </html>
    """
    return render_template_string(html, voters=voters)


@app.route('/')
def home():
    return "<h2 style='text-align:center;'>Voting Server is Running!</h2>"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
