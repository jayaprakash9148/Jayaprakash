from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)

# Database connection
def get_db_connection():
    conn = sqlite3.connect("voters.db")
    conn.row_factory = sqlite3.Row
    return conn

# Home route
@app.route('/')
def home():
    return "Voting Server is Running!"

# API route to verify fingerprint
@app.route('/api/verify', methods=['POST'])
def verify():
    try:
        data = request.get_json()
        fingerprint_id = data.get("fingerprint_id")

        if fingerprint_id is None:
            return jsonify({"status": "error", "message": "Fingerprint ID missing"}), 400

        conn = get_db_connection()
        voter = conn.execute("SELECT * FROM voters WHERE fingerprint_id = ?", 
                             (fingerprint_id,)).fetchone()

        if voter is None:
            response = {"status": "error", "message": "Fingerprint not found"}
        elif voter["has_voted"]:
            response = {"status": "error", "message": "Already voted"}
        else:
            conn.execute("UPDATE voters SET has_voted = 1 WHERE fingerprint_id = ?", 
                         (fingerprint_id,))
            conn.commit()
            response = {"status": "success", "message": "Vote allowed"}

        conn.close()
        return jsonify(response)

    except Exception as e:
        return jsonify({"status": "error", "message": f"Server error: {e}"}), 500

# Route to view all voters
@app.route('/voters')
def list_voters():
    try:
        conn = get_db_connection()
        voters = conn.execute("SELECT id, name, has_voted FROM voters").fetchall()
        conn.close()
    except Exception as e:
        return f"Database error: {e}", 500

    table_html = "<h2>Voter List</h2>"
    table_html += "<table border='1' style='border-collapse: collapse;'>"
    table_html += "<tr><th>ID</th><th>Name</th><th>Has Voted</th></tr>"

    for voter in voters:
        voted_status = "Yes" if voter["has_voted"] else "No"
        table_html += f"<tr><td>{voter['id']}</td><td>{voter['name']}</td><td>{voted_status}</td></tr>"

    table_html += "</table>"
    return table_html

# Run server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
