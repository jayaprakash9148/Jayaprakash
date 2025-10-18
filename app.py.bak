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

app = Flask(__name__)
app.secret_key = "supersecretkey_change_this"  # Change before production

# -------------------------
# Permanent PostgreSQL Database
# -------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    # Ensure DATABASE_URL is set in environment (Render sets it when you add a Postgres add-on)
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

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"  # Change to a strong password

@app.route("/")
def index():
    admin = session.get("admin", False)
    total = voted = 0
    # provide male/female counts on dashboard only if admin (safe)
    male_total = female_total = male_voted = female_voted = 0
    if admin:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT COUNT(*) AS c FROM voters")
        total = cur.fetchone()["c"] or 0
        cur.execute("SELECT COUNT(*) AS c FROM voters WHERE has_voted=1")
        voted = cur.fetchone()["c"] or 0

        # also compute male/female totals (useful for dashboard if template expects them)
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
    # pass extra gender stats safely; templates that don't use them won't break
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

# -------------------------
# Voter Management
# -------------------------

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

# -------------------------
# Downloads
# -------------------------

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
        ws.append([
            r["id"],
            r["name"],
            r["gender"],
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
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM voters WHERE fingerprint_template = %s", (tpl,))
    r = cur.fetchone()
    if not r:
        cur.close()
        conn.close()
        return jsonify({"status": "error", "message": "Fingerprint not recognized"}), 404

    if r["has_voted"]:
        cur.close()
        conn.close()
        return jsonify({"status": "error", "message": "Already voted"}), 409

    cur.execute("UPDATE voters SET has_voted = 1 WHERE id = %s", (r["id"],))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "success", "id": r["id"], "name": r["name"], "gender": r["gender"], "has_voted": 1})

# -------------------------
# Stats
# -------------------------
@app.route("/stats")
@admin_required
def stats():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # overall
    cur.execute("SELECT COUNT(*) AS c FROM voters")
    total = cur.fetchone()["c"] or 0
    cur.execute("SELECT COUNT(*) AS c FROM voters WHERE has_voted=1")
    voted = cur.fetchone()["c"] or 0
    not_voted = total - voted

    # gender splits
    cur.execute("SELECT COUNT(*) AS c FROM voters WHERE gender = %s", ("Male",))
    male_total = cur.fetchone()["c"] or 0
    cur.execute("SELECT COUNT(*) AS c FROM voters WHERE gender = %s", ("Female",))
    female_total = cur.fetchone()["c"] or 0

    cur.execute("SELECT COUNT(*) AS c FROM voters WHERE gender = %s AND has_voted=1", ("Male",))
    male_voted = cur.fetchone()["c"] or 0
    cur.execute("SELECT COUNT(*) AS c FROM voters WHERE gender = %s AND has_voted=1", ("Female",))
    female_voted = cur.fetchone()["c"] or 0

    # new: male/female not voted
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

# -------------------------
# Run app
# -------------------------
if __name__ == "__main__":
    # On Render the PORT is provided by the environment; for local dev keep 5000
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)