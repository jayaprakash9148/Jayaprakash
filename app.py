from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3, os

app = Flask(__name__)
app.secret_key = "supersecretkey"  # change this

DB_NAME = "voters.db"
ADMIN_PASSWORD = "admin123"        # change this

# ---------- DATABASE SETUP ----------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Persistent table; NO dummy seeding
    c.execute("""
        CREATE TABLE IF NOT EXISTS voters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            fingerprint_template BLOB NOT NULL,
            has_voted INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# ---------- ROUTES ----------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        pwd = request.form.get('password', '')
        if pwd == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('voters'))
        flash("Invalid password", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('home'))

@app.route('/voters')
def voters():
    if 'admin' not in session: 
        return redirect(url_for('login'))
    conn = get_db()
    rows = conn.execute("SELECT * FROM voters ORDER BY id").fetchall()
    conn.close()
    return render_template('voters.html', voters=rows)

@app.route('/add_voter', methods=['POST'])
def add_voter():
    if 'admin' not in session: 
        return redirect(url_for('login'))
    name = (request.form.get('name') or '').strip()
    template_text = (request.form.get('fingerprint_template') or '').strip()
    if not name or not template_text:
        flash("Name and fingerprint template are required.", "danger")
        return redirect(url_for('voters'))

    # Store raw template bytes (server-side matching)
    tpl_bytes = template_text.encode('utf-8')
    conn = get_db()
    conn.execute("INSERT INTO voters (name, fingerprint_template) VALUES (?, ?)", (name, tpl_bytes))
    conn.commit()
    conn.close()
    flash("Voter added successfully.", "success")
    return redirect(url_for('voters'))

@app.route('/delete_voter/<int:vid>', methods=['POST'])
def delete_voter(vid):
    if 'admin' not in session: 
        return redirect(url_for('login'))

    password = request.form.get('password', '')
    if password != ADMIN_PASSWORD:
        flash("❌ Wrong admin password. Voter not deleted.", "danger")
        return redirect(url_for('voters'))

    conn = get_db()
    conn.execute("DELETE FROM voters WHERE id=?", (vid,))
    conn.commit()

    # Resequence IDs to keep them tidy
    rows = conn.execute("SELECT id FROM voters ORDER BY id").fetchall()
    new_id = 1
    for r in rows:
        old_id = r['id']
        if old_id != new_id:
            conn.execute("UPDATE voters SET id=? WHERE id=?", (new_id, old_id))
        new_id += 1
    conn.commit()
    conn.close()

    flash("✅ Voter deleted and IDs resequenced.", "success")
    return redirect(url_for('voters'))

@app.route('/reset_votes', methods=['POST'])
def reset_votes():
    if 'admin' not in session: 
        return redirect(url_for('login'))
    password = request.form.get('password', '')
    if password != ADMIN_PASSWORD:
        flash("❌ Wrong admin password. Votes not reset.", "danger")
        return redirect(url_for('voters'))

    conn = get_db()
    conn.execute("UPDATE voters SET has_voted=0")
    conn.commit()
    conn.close()
    flash("✅ All votes reset.", "success")
    return redirect(url_for('voters'))

@app.route('/reset_all', methods=['POST'])
def reset_all():
    # Optional: full DB wipe (kept for completeness; not used by UI)
    if 'admin' not in session: 
        return redirect(url_for('login'))
    password = request.form.get('password', '')
    if password != ADMIN_PASSWORD:
        flash("❌ Wrong admin password. Nothing reset.", "danger")
        return redirect(url_for('voters'))
    conn = get_db()
    conn.execute("DELETE FROM voters")
    conn.commit()
    conn.close()
    flash("✅ All voters cleared.", "success")
    return redirect(url_for('voters'))

# ---------- VOTE (optional demo endpoint) ----------
@app.route('/vote/<int:vid>', methods=['POST'])
def vote(vid):
    conn = get_db()
    voter = conn.execute("SELECT has_voted FROM voters WHERE id=?", (vid,)).fetchone()
    if not voter:
        conn.close()
        return jsonify({"status":"error","message":"Voter not found"})
    if voter['has_voted'] == 1:
        conn.close()
        return jsonify({"status":"error","message":"Already voted"})
    conn.execute("UPDATE voters SET has_voted=1 WHERE id=?", (vid,))
    conn.commit()
    conn.close()
    return jsonify({"status":"success","message":"Vote cast"})

# ---------- FINGERPRINT MATCH (ESP32 -> Server) ----------
@app.route('/match_fingerprint', methods=['POST'])
def match_fingerprint():
    """
    ESP32 sends JSON: { "fingerprint_template": "<raw_serialized_string>" }
    Server compares raw bytes with stored templates (exact match baseline).
    """
    payload = request.get_json(silent=True) or {}
    tpl_text = payload.get("fingerprint_template", "")
    if not tpl_text:
        return jsonify({"status":"error","message":"No template provided"}), 400

    tpl_bytes = tpl_text.encode('utf-8')
    conn = get_db()
    rows = conn.execute("SELECT id, name, fingerprint_template, has_voted FROM voters").fetchall()
    conn.close()

    for r in rows:
        if r['fingerprint_template'] == tpl_bytes:
            return jsonify({
                "status": "success",
                "id": r['id'],
                "name": r['name'],
                "has_voted": r['has_voted']
            })

    return jsonify({"status":"error","message":"Fingerprint not recognized"}), 404

# ---------- STATS ----------
@app.route('/stats')
def stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) AS c FROM voters").fetchone()['c']
    voted = conn.execute("SELECT COUNT(*) AS c FROM voters WHERE has_voted=1").fetchone()['c']
    conn.close()
    return render_template('stats.html', total=total, voted=voted)

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
