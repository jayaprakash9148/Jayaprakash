from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, send_file, jsonify
)
import sqlite3
import io
from datetime import datetime
from openpyxl import Workbook
import csv
import base64
import os

app = Flask(_name_)
app.secret_key = "supersecretkey_change_this"  # Change before production

DB_FILE = "voters.db"
# Save fingerprint photos inside Flask static so they can be served directly.
IMAGE_DIR = os.path.join("static", "uploads")
os.makedirs(IMAGE_DIR, exist_ok=True)

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "12345"  # Change to a strong password

# -------------------------
# Database helpers
# -------------------------
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create or update voters table (persistent)."""
    conn = get_db_connection()
    conn.execute("""
<<<<<<< HEAD
        CREATE TABLE IF NOT EXISTS voters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            fingerprint_template TEXT NOT NULL,
            has_voted INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_booth TEXT,
            voted_at TEXT
        )
=======
    CREATE TABLE IF NOT EXISTS voters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        fingerprint_template TEXT NOT NULL,
        fingerprint_image TEXT,
        has_voted INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
>>>>>>> d7f6b55ec3d715d826615aab68fbecc25b5387e3
    """)
    # Ensure new columns exist for permanent features
    try:
        conn.execute("ALTER TABLE voters ADD COLUMN last_booth TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE voters ADD COLUMN voted_at TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

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
            # redirect to dashboard/index
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
        file = request.files.get("fingerprint_image")

        if not name or not template:
            flash("Name and fingerprint template are required.", "danger")
            return redirect(url_for("add_voter"))

        # save optional fingerprint image (store filename only so templates can serve via static/uploads)
        filename = None
        if file and file.filename:
            # sanitize filename somewhat (very simple)
            safe_name = "".join(c for c in name if c.isalnum() or c in (" ", "", "-")).strip().replace(" ", "")
            filename = f"{safe_name}_{int(datetime.utcnow().timestamp())}.png"
            image_path = os.path.join(IMAGE_DIR, filename)
            try:
                file.save(image_path)
            except Exception as e:
                flash(f"Failed to save image: {e}", "danger")
                return redirect(url_for("add_voter"))

        conn = get_db_connection()
        try:
            cur = conn.execute(
                "INSERT INTO voters (name, fingerprint_template, fingerprint_image) VALUES (?, ?, ?)",
                (name, template, filename)
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
    # remove image file if present
    row = conn.execute("SELECT fingerprint_image FROM voters WHERE id = ?", (voter_id,)).fetchone()
    if row and row["fingerprint_image"]:
        try:
            path = os.path.join(IMAGE_DIR, row["fingerprint_image"])
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            # non-fatal; continue
            pass

    conn.execute("DELETE FROM voters WHERE id = ?", (voter_id,))
    conn.commit()

    # resequence IDs
    rows = conn.execute(
<<<<<<< HEAD
        "SELECT name, fingerprint_template, has_voted, created_at, last_booth, voted_at FROM voters ORDER BY id"
=======
        "SELECT name, fingerprint_template, fingerprint_image, has_voted, created_at FROM voters ORDER BY id"
>>>>>>> d7f6b55ec3d715d826615aab68fbecc25b5387e3
    ).fetchall()
    conn.execute("DELETE FROM voters")
    conn.commit()
    next_id = 1
    for r in rows:
        conn.execute(
<<<<<<< HEAD
            "INSERT INTO voters (id, name, fingerprint_template, has_voted, created_at, last_booth, voted_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (next_id, r["name"], r["fingerprint_template"], r["has_voted"], r["created_at"], r["last_booth"], r["voted_at"])
=======
            "INSERT INTO voters (id, name, fingerprint_template, fingerprint_image, has_voted, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (next_id, r["name"], r["fingerprint_template"], r["fingerprint_image"], r["has_voted"], r["created_at"])
>>>>>>> d7f6b55ec3d715d826615aab68fbecc25b5387e3
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
    conn.execute("UPDATE voters SET has_voted = 0, last_booth=NULL, voted_at=NULL")
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
<<<<<<< HEAD
        "SELECT id, name, fingerprint_template, has_voted, created_at, last_booth, voted_at FROM voters ORDER BY id"
=======
        "SELECT id, name, fingerprint_template, fingerprint_image, has_voted, created_at FROM voters ORDER BY id"
>>>>>>> d7f6b55ec3d715d826615aab68fbecc25b5387e3
    ).fetchall()
    conn.close()

    wb = Workbook()
    ws = wb.active
    ws.title = "Voters"
<<<<<<< HEAD
    ws.append(["ID", "Name", "Fingerprint Template", "Has Voted", "Created At", "Last Booth", "Voted At"])
=======
    ws.append(["ID", "Name", "Fingerprint Template", "Fingerprint Image Filename", "Has Voted", "Created At"])
>>>>>>> d7f6b55ec3d715d826615aab68fbecc25b5387e3
    for r in rows:
        ws.append([
            r["id"],
            r["name"],
            r["fingerprint_template"],
            r["fingerprint_image"] or "",
            "Yes" if r["has_voted"] else "No",
            r["created_at"],
            r["last_booth"] if r["last_booth"] else "",
            r["voted_at"] if r["voted_at"] else ""
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
<<<<<<< HEAD
        "SELECT id, name, fingerprint_template, has_voted, created_at, last_booth, voted_at FROM voters ORDER BY id"
=======
        "SELECT id, name, fingerprint_template, fingerprint_image, has_voted, created_at FROM voters ORDER BY id"
>>>>>>> d7f6b55ec3d715d826615aab68fbecc25b5387e3
    ).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
<<<<<<< HEAD
    writer.writerow(["ID", "Name", "Fingerprint Template", "Has Voted", "Created At", "Last Booth", "Voted At"])
    for r in rows:
        writer.writerow([r["id"], r["name"], r["fingerprint_template"], r["has_voted"], r["created_at"], r["last_booth"] or "", r["voted_at"] or ""])
=======
    writer.writerow(["ID", "Name", "Fingerprint Template", "Fingerprint Image Filename", "Has Voted", "Created At"])
    for r in rows:
        writer.writerow([r["id"], r["name"], r["fingerprint_template"], r["fingerprint_image"] or "", r["has_voted"], r["created_at"]])
>>>>>>> d7f6b55ec3d715d826615aab68fbecc25b5387e3

    mem = io.BytesIO()
    mem.write(output.getvalue().encode("utf-8"))
    mem.seek(0)
    fname = f"voters-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.csv"
    return send_file(mem, download_name=fname, as_attachment=True, mimetype="text/csv")

# -------------------------
<<<<<<< HEAD
# API for ESP Enrollment & Verification
# -------------------------

@app.route("/api/add_voter", methods=["POST"])
def api_add_voter():
    payload = request.get_json(silent=True)
    if not payload or "fingerprint_template" not in payload or "name" not in payload:
        return jsonify({"status": "error", "message": "Name and fingerprint template required"}), 400

    name = payload["name"].strip()
    tpl = payload["fingerprint_template"].strip()

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO voters (name, fingerprint_template) VALUES (?, ?)",
        (name, tpl)
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": f"Voter {name} added"})
=======
# API for fingerprint enrollment & verification
# -------------------------

@app.route("/api/enroll", methods=["POST"])
def api_enroll():
    """
    ESP sends: { "name": "John", "fingerprint_template": "raw_data_or_hash", "fingerprint_image": "<base64>" }
    """
    payload = request.get_json(silent=True)
    if not payload or "name" not in payload or "fingerprint_template" not in payload:
        return jsonify({"status": "error", "message": "Name and fingerprint required"}), 400

    name = payload["name"].strip()
    tpl = payload["fingerprint_template"].strip()
    img_b64 = payload.get("fingerprint_image")

    if not name or not tpl:
        return jsonify({"status": "error", "message": "Invalid input"}), 400

    filename = None
    if img_b64:
        try:
            img_data = base64.b64decode(img_b64)
            safe_name = "".join(c for c in name if c.isalnum() or c in (" ", "", "-")).strip().replace(" ", "")
            filename = f"{safe_name}_{int(datetime.utcnow().timestamp())}.png"
            image_path = os.path.join(IMAGE_DIR, filename)
            with open(image_path, "wb") as f:
                f.write(img_data)
        except Exception as e:
            return jsonify({"status": "error", "message": f"Image save failed: {e}"}), 500

    conn = get_db_connection()
    try:
        cur = conn.execute(
            "INSERT INTO voters (name, fingerprint_template, fingerprint_image) VALUES (?, ?, ?)",
            (name, tpl, filename)
        )
        conn.commit()
        voter_id = cur.lastrowid
        return jsonify({"status": "success", "id": voter_id, "name": name})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        conn.close()
>>>>>>> d7f6b55ec3d715d826615aab68fbecc25b5387e3

@app.route("/api/verify", methods=["POST"])
def api_verify():
    payload = request.get_json(silent=True)
    if not payload or "fingerprint_template" not in payload:
        return jsonify({"status": "error", "message": "No template provided"}), 400

    tpl = (payload["fingerprint_template"] or "").strip()
    booth = (payload.get("booth") or "Unknown").strip()

    conn = get_db_connection()
    r = conn.execute("SELECT * FROM voters WHERE fingerprint_template = ?", (tpl,)).fetchone()
    if not r:
        conn.close()
        return jsonify({"status": "error", "message": "Fingerprint not recognized"}), 404

    if r["has_voted"]:
        conn.close()
        return jsonify({"status": "error", "message": "Already voted"}), 409

    # Mark as voted with booth + timestamp
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("UPDATE voters SET has_voted=1, last_booth=?, voted_at=? WHERE id=?", (booth, now, r["id"]))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "id": r["id"], "name": r["name"], "has_voted": 1, "booth": booth, "time": now})

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
if _name_ == "_main_":
    app.run(host="0.0.0.0", port=5000, debug=True)