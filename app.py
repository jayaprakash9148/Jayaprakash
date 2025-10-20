from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, send_file, jsonify
)
import psycopg2
import psycopg2.extras
import io
from datetime import datetime
from openpyxl import Workbook
import csv
import os
from functools import wraps

# -------------------------
# App Initialization
# -------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecretkey_change_this")  # Change for production

# -------------------------
# Database Setup
# -------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL environment variable is not set.")
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    return conn

def init_db():
    """Create voters table if missing (persistent)."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS voters (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            gender TEXT NOT NULL,
            fingerprint_template TEXT NOT NULL,
            has_voted INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

# Ensure DB always exists before app runs
init_db()

# -------------------------
# Admin Config
# -------------------------
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "12345")  # Change in production

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# -------------------------
# Routes
# -------------------------
@app.route("/")
def index():
    admin = session.get("admin", False)
    total = voted = 0
    male_total = female_total = male_voted = female_voted = 0
    if admin:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT COUNT(*) AS c FROM voters")
        total = cur.fetchone()["c"] or 0
        cur.execute("SELECT COUNT(*) AS c FROM voters WHERE has_voted=1")
        voted = cur.fetchone()["c"] or 0
        cur.execute("SELECT COUNT(*) AS c FROM voters WHERE gender = %s", ("Male",))
        male_total = cur.fetchone()["c"] or 0
        cur.execute("SELECT COUNT(*) AS c FROM voters WHERE gender = %s", ("Female",))
        female_total = cur.fetchone()["c"] or 0
        cur.execute("SELECT COUNT(*) AS c FROM voters WHERE gender = %s AND has_voted=1", ("Male",))
        male_voted = cur.fetchone()["c"] or 0
        cur.execute("SELECT COUNT(*) AS c FROM voters WHERE gender = %s AND has_voted=1", ("Female",))
        female_voted = cur.fetchone()["c"] or 0
        cur.close()
        conn.close()
    return render_template(
        "index.html",
        admin=admin,
        total=total,
        voted=voted,
        male_total=male_total,
        female_total=female_total,
        male_voted=male_voted,
        female_voted=female_voted
    )

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin"] = True
            flash("✅ Logged in as admin.", "success")
            return redirect(url_for("index"))
        else:
            error = "Invalid username or password"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.pop("admin", None)
    flash("Logged out.", "info")
    return redirect(url_for("login"))

@app.route("/stats")
@admin_required
def stats():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT COUNT(*) AS c FROM voters")
    total = cur.fetchone()["c"] or 0
    cur.execute("SELECT COUNT(*) AS c FROM voters WHERE has_voted=1")
    voted = cur.fetchone()["c"] or 0
    not_voted = total - voted
    cur.execute("SELECT COUNT(*) AS c FROM voters WHERE gender = %s", ("Male",))
    male_total = cur.fetchone()["c"] or 0
    cur.execute("SELECT COUNT(*) AS c FROM voters WHERE gender = %s", ("Female",))
    female_total = cur.fetchone()["c"] or 0
    cur.execute("SELECT COUNT(*) AS c FROM voters WHERE gender = %s AND has_voted=1", ("Male",))
    male_voted = cur.fetchone()["c"] or 0
    cur.execute("SELECT COUNT(*) AS c FROM voters WHERE gender = %s AND has_voted=1", ("Female",))
    female_voted = cur.fetchone()["c"] or 0
    male_not_voted = male_total - male_voted
    female_not_voted = female_total - female_voted
    cur.close()
    conn.close()
    return render_template(
        "stats.html",
        total=total,
        voted=voted,
        not_voted=not_voted,
        male_total=male_total,
        female_total=female_total,
        male_voted=male_voted,
        female_voted=female_voted,
        male_not_voted=male_not_voted,
        female_not_voted=female_not_voted
    )

@app.route("/voters")
@admin_required
def voters():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM voters ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("voters.html", voters=rows)

@app.route("/add-voter", methods=["GET", "POST"])
@admin_required
def add_voter():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        gender = (request.form.get("gender") or "").strip()
        template = (request.form.get("fingerprint_template") or "").strip()
        if not name or not gender or not template:
            flash("Name, gender and fingerprint template are required.", "danger")
            return redirect(url_for("add_voter"))
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO voters (name, gender, fingerprint_template) VALUES (%s, %s, %s)",
                (name, gender, template)
            )
            conn.commit()
            flash("✅ Voter added successfully.", "success")
        except Exception as e:
            flash(f"Error adding voter: {e}", "danger")
        finally:
            cur.close()
            conn.close()
        return redirect(url_for("voters"))
    return render_template("add_voter.html")

@app.route("/delete-voter/<int:voter_id>", methods=["POST"])
@admin_required
def delete_voter(voter_id):
    password = request.form.get("admin_password", "")
    if password != ADMIN_PASSWORD:
        flash("❌ Wrong admin password. Voter not deleted.", "danger")
        return redirect(url_for("voters"))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM voters WHERE id = %s", (voter_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("✅ Voter deleted.", "success")
    return redirect(url_for("voters"))

@app.route("/reset-votes", methods=["POST"])
@admin_required
def reset_votes():
    password = request.form.get("admin_password", "")
    if password != ADMIN_PASSWORD:
        flash("❌ Wrong admin password. Votes not reset.", "danger")
        return redirect(url_for("voters"))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE voters SET has_voted = 0")
    conn.commit()
    cur.close()
    conn.close()
    flash("✅ All votes reset.", "success")
    return redirect(url_for("voters"))

@app.route("/download-excel")
@admin_required
def download_excel():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT id, name, gender, fingerprint_template, has_voted, created_at FROM voters ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    wb = Workbook()
    ws = wb.active
    ws.title = "Voters"
    ws.append(["ID", "Name", "Gender", "Fingerprint Template", "Has Voted", "Created At"])
    for r in rows:
        ws.append([r["id"], r["name"], r["gender"], r["fingerprint_template"], "Yes" if r["has_voted"] else "No", r["created_at"]])

    virtual_wb = io.BytesIO()
    wb.save(virtual_wb)
    virtual_wb.seek(0)
    fname = f"voters-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.xlsx"
    return send_file(virtual_wb, download_name=fname, as_attachment=True, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.route("/download-csv")
@admin_required
def download_csv():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT id, name, gender, fingerprint_template, has_voted, created_at FROM voters ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "Gender", "Fingerprint Template", "Has Voted", "Created At"])
    for r in rows:
        writer.writerow([r["id"], r["name"], r["gender"], r["fingerprint_template"], r["has_voted"], r["created_at"]])

    mem = io.BytesIO()
    mem.write(output.getvalue().encode("utf-8"))
    mem.seek(0)
    fname = f"voters-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.csv"
    return send_file(mem, download_name=fname, as_attachment=True, mimetype="text/csv")

# -------------------------
# Fingerprint API (Updated to Store in DB)
# -------------------------
@app.route("/api/enroll", methods=["POST"])
def api_enroll():
    payload = request.get_json(force=True)
    name = (payload.get("name") or "").strip()
    gender = (payload.get("gender") or "").strip()
    template = (payload.get("fingerprint_template") or "").strip()

    if not name or not gender or not template:
        return jsonify({"status":"error","message":"Name, gender, and fingerprint_template are required"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO voters (name, gender, fingerprint_template) VALUES (%s, %s, %s)",
            (name, gender, template)
        )
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "status": "success",
            "message": f"Voter enrolled successfully: {name} ({gender})",
            "template": template
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/verify", methods=["POST"])
def api_verify():
    payload = request.get_json(force=True)
    template = (payload.get("fingerprint_template") or "").strip()

    if not template:
        return jsonify({"status":"error","message":"Fingerprint template required"}), 400

    # Dummy response (you can later connect actual matching)
    return jsonify({
        "status": "success",
        "message": f"Verify received for template {template}",
        "match": True
    }), 200

# -------------------------
# 🔹 Mark Voted API (Added for ESP32)
# -------------------------
@app.route("/api/mark_voted", methods=["POST"])
def api_mark_voted():
    payload = request.get_json(force=True)
    template = (payload.get("fingerprint_template") or "").strip()

    if not template:
        return jsonify({"status": "error", "message": "Missing fingerprint_template"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE voters SET has_voted = 1 WHERE fingerprint_template = %s", (template,))
        if cur.rowcount == 0:
            conn.commit()
            cur.close()
            conn.close()
            return jsonify({"status": "error", "message": "Voter not found"}), 404
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"status": "success", "message": f"Voter with template {template} marked as voted."}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# -------------------------
# Vote API (Actual DB)
# -------------------------
@app.route("/api/vote", methods=["POST"])
def api_vote():
    payload = request.get_json(force=True)
    template = (payload.get("fingerprint_template") or "").strip()
    if not template:
        return jsonify({"status":"error","message":"Fingerprint template required"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM voters WHERE fingerprint_template = %s", (template,))
        voter = cur.fetchone()
        if not voter:
            cur.close()
            conn.close()
            return jsonify({"status":"error","message":"Voter not found"}), 404

        if voter["has_voted"]:
            cur.close()
            conn.close()
            return jsonify({"status":"error","message":"Already voted"}), 403

        cur.execute("UPDATE voters SET has_voted = 1 WHERE id = %s", (voter["id"],))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"status":"success","message":"Vote recorded"}), 200
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500

@app.route("/api/stats", methods=["GET"])
def api_stats():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT COUNT(*) AS total FROM voters")
        total = cur.fetchone()["total"] or 0
        cur.execute("SELECT COUNT(*) AS voted FROM voters WHERE has_voted=1")
        voted = cur.fetchone()["voted"] or 0
        cur.close()
        conn.close()
        return jsonify({
            "total_voters": total,
            "voted": voted,
            "not_voted": total - voted
        }), 200
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
