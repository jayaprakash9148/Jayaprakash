from flask import Flask, request, jsonify, render_template_string
import sqlite3

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect("voters.db")
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

@app.route('/')
def home():
    return "Voting Server is Running!"

# ----------------- New route to show voter table -----------------
@app.route('/voters')
def show_voters():
    conn = get_db_connection()
    voters = conn.execute("SELECT * FROM voters").fetchall()
    conn.close()

    html = '''
    <h2>Voter List</h2>
    <table border="1" cellpadding="5" cellspacing="0">
        <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Has Voted</th>
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
    return render_template_string(html, voters=voters)

# ----------------- Run Server -----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
