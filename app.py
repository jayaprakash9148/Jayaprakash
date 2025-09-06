from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, send_file, jsonify
)
import sqlite3
import io
from datetime import datetime
from openpyxl import Workbook
import csv
import os

app = Flask(__name__)
app.secret_key = "supersecretkey_change_this"  # Change before production

# -------------------------
# Permanent Database File
# -------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_FILE = os.path.join(BASE_DIR, "voters.db")

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"  # Change to a strong password

# -------------------------
# Database helpers
# -------------------------
def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create voters table if missing (persistent)."""
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS voters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            fingerprint_template TEXT NOT NULL,
            has_voted INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# Ensure DB always exists before app runs
init_db()

# -------------------------
# Routes
# -------------------------

# Login required decorator
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

@app.route("/")
def index():
    admin = session.get("admin", False)
    total = voted = 0
    if admin:
        conn = get_db_connection()
        total = conn.execute("SELECT COUNT(*) AS c FROM voters").fetchone()["c"]
        voted = conn.execute("SELECT COUNT(*) AS c FROM voters WHERE has_voted=1").fetchone()["c"]
        conn.close()
    return render_template("index.html", admin=admin, total=total, voted=voted)

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

# -------------------------
# Voter Management
# -------------------------

@app.route("/voters")
@admin_required
def voters():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM voters ORDER BY id").fetchall()
    conn.close()
    return render_template("voters.html", voters=rows)

@app.route("/add-voter", methods=["GET", "POST"])
@admin_required
def add_voter():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        template = (request.form.get("fingerprint_template") or "").strip()
        if not name or not template:
            flash("Name and fingerprint template are required.", "danger")
            return redirect(url_for("add_voter"))
        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO voters (name, fingerprint_template) VALUES (?, ?)",
                (name, template)
            )
            conn.commit()
            flash("✅ Voter added successfully.", "success")
        except Exception as e:
            flash(f"Error adding voter: {e}", "danger")
        finally:
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
    conn.execute("DELETE FROM voters WHERE id = ?", (voter_id,))
    conn.commit()

    # resequence IDs
    rows = conn.execute(
        "SELECT name, fingerprint_template, has_voted, created_at FROM voters ORDER BY id"
    ).fetchall()
    conn.execute("DELETE FROM voters")
    conn.commit()
    next_id = 1
    for r in rows:
        conn.execute(
            "INSERT INTO voters (id, name, fingerprint_template, has_voted, created_at) VALUES (?, ?, ?, ?, ?)",
            (next_id, r["name"], r["fingerprint_template"], r["has_voted"], r["created_at"])
        )
        next_id += 1
    conn.commit()
    conn.close()
    flash("✅ Voter deleted and IDs resequenced.", "success")
    return redirect(url_for("voters"))

@app.route("/reset-votes", methods=["POST"])
@admin_required
def reset_votes():
    password = request.form.get("admin_password", "")
    if password != ADMIN_PASSWORD:
        flash("❌ Wrong admin password. Votes not reset.", "danger")
        return redirect(url_for("voters"))
    conn = get_db_connection()
    conn.execute("UPDATE voters SET has_voted = 0")
    conn.commit()
    conn.close()
    flash("✅ All votes reset.", "success")
    return redirect(url_for("voters"))

# -------------------------
# Downloads
# -------------------------

@app.route("/download-excel")
@admin_required
def download_excel():
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT id, name, fingerprint_template, has_voted, created_at FROM voters ORDER BY id"
    ).fetchall()
    conn.close()

    wb = Workbook()
    ws = wb.active
    ws.title = "Voters"
    ws.append(["ID", "Name", "Fingerprint Template", "Has Voted", "Created At"])
    for r in rows:
        ws.append([
            r["id"],
            r["name"],
            r["fingerprint_template"],
            "Yes" if r["has_voted"] else "No",
            r["created_at"]
        ])

    virtual_wb = io.BytesIO()
    wb.save(virtual_wb)
    virtual_wb.seek(0)
    fname = f"voters-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.xlsx"
    return send_file(
        virtual_wb,
        download_name=fname,
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.route("/download-csv")
@admin_required
def download_csv():
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT id, name, fingerprint_template, has_voted, created_at FROM voters ORDER BY id"
    ).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "Fingerprint Template", "Has Voted", "Created At"])
    for r in rows:
        writer.writerow([r["id"], r["name"], r["fingerprint_template"], r["has_voted"], r["created_at"]])

    mem = io.BytesIO()
    mem.write(output.getvalue().encode("utf-8"))
    mem.seek(0)
    fname = f"voters-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.csv"
    return send_file(mem, download_name=fname, as_attachment=True, mimetype="text/csv")

# -------------------------
# API for fingerprint verification
# -------------------------
@app.route("/api/verify", methods=["POST"])
def api_verify():
    payload = request.get_json(silent=True)
    if not payload or "fingerprint_template" not in payload:
        return jsonify({"status": "error", "message": "No template provided"}), 400

    tpl = (payload["fingerprint_template"] or "").strip()
    if not tpl:
        return jsonify({"status": "error", "message": "Empty template"}), 400

    conn = get_db_connection()
    r = conn.execute("SELECT * FROM voters WHERE fingerprint_template = ?", (tpl,)).fetchone()
    if not r:
        conn.close()
        return jsonify({"status": "error", "message": "Fingerprint not recognized"}), 404

    if r["has_voted"]:
        conn.close()
        return jsonify({"status": "error", "message": "Already voted"}), 409

    conn.execute("UPDATE voters SET has_voted = 1 WHERE id = ?", (r["id"],))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "id": r["id"], "name": r["name"], "has_voted": 1})

# -------------------------
# Stats
# -------------------------
@app.route("/stats")
@admin_required
def stats():
    conn = get_db_connection()
    total = conn.execute("SELECT COUNT(*) AS c FROM voters").fetchone()["c"]
    voted = conn.execute("SELECT COUNT(*) AS c FROM voters WHERE has_voted=1").fetchone()["c"]
    not_voted = total - voted
    conn.close()
    return render_template("stats.html", total=total, voted=voted, not_voted=not_voted)

# -------------------------
# Run app
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
