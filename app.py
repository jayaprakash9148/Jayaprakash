from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)

# ---------------- Database Connection ----------------
def get_db_connection():
    conn = sqlite3.connect("voters.db")
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- Home Route ----------------
@app.route('/')
def home():
    return "Voting Server is Running!"

# ---------------- Verify Fingerprint Route ----------------
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

# ---------------- Voter List Route ----------------
@app.route('/voters')
def voters():
    conn = get_db_connection()
    all_voters = conn.execute("SELECT * FROM voters").fetchall()
    conn.close()

    html = "<h2>Voter List</h2>"
    html += "<table border='1' style='border-collapse: collapse; padding: 8px;'>"
    html += "<tr><th>ID</th><th>Name</th><th>Has Voted</th></tr>"
    for voter in all_voters:
        has_voted = "Yes" if voter["has_voted"] else "No"
        html += f"<tr><td>{voter['id']}</td><td>{voter['name']}</td><td>{has_voted}</td></tr>"
    html += "</table>"
    return html

# ---------------- Run Server ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
