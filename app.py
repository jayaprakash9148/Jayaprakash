from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, send_file, jsonify
)
import sqlite3
import os
import io
from openpyxl import Workbook
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey_change_this"

DB_FILE = "voters.db"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# -------------------------
# DB helpers
# -------------------------
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
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

init_db()

# -------------------------
# Pages
# -------------------------
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
            return redirect(url_for("voters"))
        else:
            error = "Invalid username or password"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.pop("admin", None)
    flash("Logged out.", "info")
    return redirect(url_for("index"))

# -------------------------
# Voters management
# -------------------------
@app.route("/voters")
def voters():
    if not session.get("admin"):
        return redirect(url_for("login"))
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM voters ORDER BY id").fetchall()
    conn.close()
    return render_template("voters.html", voters=rows)

@app.route("/add-voter", methods=["GET", "POST"])
def add_voter():
    if not session.get("admin"):
        return redirect(url_for("login"))
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        template = (request.form.get("fingerprint_template") or "").strip()
        if not name or not template:
            flash("Name and fingerprint template are required.", "danger")
            return redirect(url_for("add_voter"))
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO voters (name, fingerprint_template) VALUES (?, ?)",
            (name, template)
        )
        conn.commit()
        conn.close()
        flash("✅ Voter added.", "success")
        return redirect(url_for("voters"))
    return render_template("add_voter.html")

@app.route("/delete-voter/<int:voter_id>", methods=["POST"])
def delete_voter(voter_id):
    if not session.get("admin"):
        return redirect(url_for("login"))
    password = request.form.get("admin_password", "")
    if password != ADMIN_PASSWORD:
        flash("❌ Wrong admin password. Voter not deleted.", "danger")
        return redirect(url_for("voters"))

    conn = get_db_connection()
    conn.execute("DELETE FROM voters WHERE id = ?", (voter_id,))
    conn.commit()
    conn.close()
    flash("✅ Voter deleted.", "success")
    return redirect(url_for("voters"))

@app.route("/reset-votes", methods=["POST"])
def reset_votes():
    if not session.get("admin"):
        return redirect(url_for("login"))
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

@app.route("/download-excel")
def download_excel():
    if not session.get("admin"):
        return redirect(url_for("login"))
    conn = get_db_connection()
    rows = conn.execute("SELECT id, name, fingerprint_template, has_voted, created_at FROM voters ORDER BY id").fetchall()
    conn.close()
    wb = Workbook()
    ws = wb.active
    ws.title = "Voters"
    ws.append(["ID", "Name", "Fingerprint Template", "Has Voted", "Created At"])
    for r in rows:
        ws.append([r["id"], r["name"], r["fingerprint_template"], "Yes" if r["has_voted"] else "No", r["created_at"]])
    virtual_wb = io.BytesIO()
    wb.save(virtual_wb)
    virtual_wb.seek(0)
    fname = f"voters-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.xlsx"
    return send_file(virtual_wb, download_name=fname, as_attachment=True, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.route("/stats")
def stats():
    conn = get_db_connection()
    total = conn.execute("SELECT COUNT(*) AS c FROM voters").fetchone()["c"]
    voted = conn.execute("SELECT COUNT(*) AS c FROM voters WHERE has_voted=1").fetchone()["c"]
    not_voted = total - voted
    conn.close()
    return render_template("stats.html", total=total, voted=voted, not_voted=not_voted)

# -------------------------
# Run
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
