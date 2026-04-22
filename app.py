"""
Traffic Guard TVM — Full Stack Flask Backend
Roles: citizen | officer | admin
"""

import os, sys, json, hashlib, secrets, string, re, math, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, session, send_from_directory, abort

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "database"))
from schema import get_db, hash_password, init_db, DB_PATH

# Initialize database on startup
init_db()

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB upload limit

UPLOAD_FOLDER = os.path.join(app.static_folder, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────


def make_token():
    """Generate a secure random token for authentication"""
    return secrets.token_urlsafe(32)


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates in kilometers"""
    R = 6371  # Earth's radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def create_session(user_id):
    token = make_token()
    expires = (datetime.utcnow() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    db = get_db()
    db.execute(
        "INSERT INTO sessions (user_id, token, expires_at) VALUES (?,?,?)",
        (user_id, token, expires),
    )
    db.commit()
    db.close()
    return token


def get_current_user():
    token = request.headers.get("X-Auth-Token") or request.cookies.get("auth_token")
    if not token:
        return None
    db = get_db()
    row = db.execute(
        """
        SELECT u.*, s.expires_at, o.id as officer_id, o.badge_id, o.rank, o.zone, o.latitude, o.longitude, o.status as officer_status,
               c.id as citizen_id
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        LEFT JOIN officers o ON o.user_id = u.id
        LEFT JOIN citizens c ON c.user_id = u.id
        WHERE s.token=? AND s.expires_at > datetime('now')
    """,
        (token,),
    ).fetchone()
    db.close()
    return dict(row) if row else None


def require_auth(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({"error": "Authentication required"}), 401
            if roles and user["role"] not in roles:
                return jsonify({"error": "Insufficient permissions"}), 403
            request.current_user = user
            return f(*args, **kwargs)

        return wrapper

    return decorator


def log_action(user_id, action, details=""):
    db = get_db()
    db.execute(
        "INSERT INTO audit_log (user_id,action,details,ip_address) VALUES (?,?,?,?)",
        (user_id, action, details, request.remote_addr),
    )
    db.commit()
    db.close()


def gen_challan():
    year = datetime.now().year
    db = get_db()
    count = db.execute("SELECT COUNT(*) FROM violations").fetchone()[0] + 1
    db.close()
    return f"EC{year}{count:04d}"


# ──────────────────────────────────────────────
# SERVE FRONTEND PAGES
# ──────────────────────────────────────────────


@app.route("/")
def index():
    return send_from_directory("templates", "loginpage.html")


@app.route("/<path:filename>")
def serve_template(filename):
    # serve HTML templates
    if filename.endswith(".html") and os.path.exists(
        os.path.join(app.template_folder, filename)
    ):
        return send_from_directory(app.template_folder, filename)
    # static files
    if os.path.exists(os.path.join(app.static_folder, filename)):
        return send_from_directory(app.static_folder, filename)
    abort(404)


# ──────────────────────────────────────────────
# AUTH ENDPOINTS
# ──────────────────────────────────────────────


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    role = (data.get("role") or "citizen").strip()

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    db = get_db()
    # Citizens must log in with email only
    if role == "citizen":
        user = db.execute(
            "SELECT * FROM users WHERE email=? AND role=? AND is_active=1",
            (username, role),
        ).fetchone()
    else:
        user = db.execute(
            "SELECT * FROM users WHERE (username=? OR email=?) AND role=? AND is_active=1",
            (username, username, role),
        ).fetchone()

    if not user or user["password"] != hash_password(password):
        db.close()
        return jsonify({"error": "Invalid credentials"}), 401

    # Get extended profile
    extra = {}
    if role == "officer":
        o = db.execute(
            "SELECT * FROM officers WHERE user_id=?", (user["id"],)
        ).fetchone()
        if o:
            extra = dict(o)
    elif role == "citizen":
        c = db.execute(
            "SELECT * FROM citizens WHERE user_id=?", (user["id"],)
        ).fetchone()
        if c:
            extra = dict(c)
    db.close()

    token = create_session(user["id"])
    log_action(user["id"], "LOGIN", f"Role: {role}")

    resp = jsonify(
        {
            "token": token,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "full_name": user["full_name"],
                "email": user["email"],
                "phone": user["phone"],
                "role": user["role"],
                **{
                    k: extra[k]
                    for k in extra.keys()
                    if k not in ("id", "user_id", "password")
                },
            },
        }
    )
    resp.set_cookie("auth_token", token, httponly=True, max_age=28800)
    return resp


@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json()
    required = ["full_name", "email", "phone", "password"]
    for f in required:
        if not data.get(f):
            return jsonify({"error": f"Missing field: {f}"}), 400

    # Validate aadhaar if provided (must be exactly 12 digits)
    aadhaar = data.get("aadhaar", "").strip()
    if aadhaar and (not aadhaar.isdigit() or len(aadhaar) != 12):
        return jsonify({"error": "Aadhaar number must be exactly 12 digits"}), 400

    username = data["email"].split("@")[0] + "_" + secrets.token_hex(3)
    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (username,password,role,full_name,email,phone) VALUES (?,?,?,?,?,?)",
            (
                username,
                hash_password(data["password"]),
                "citizen",
                data["full_name"],
                data["email"],
                data["phone"],
            ),
        )
        uid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.execute(
            "INSERT INTO citizens (user_id,aadhaar) VALUES (?,?)",
            (uid, aadhaar if aadhaar else None),
        )
        db.commit()
        db.close()
        return (
            jsonify({"message": "Registration successful", "username": username}),
            201,
        )
    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({"error": str(e)}), 400


@app.route("/api/auth/logout", methods=["POST"])
@require_auth()
def logout():
    token = request.headers.get("X-Auth-Token") or request.cookies.get("auth_token")
    db = get_db()
    db.execute("DELETE FROM sessions WHERE token=?", (token,))
    db.commit()
    db.close()
    resp = jsonify({"message": "Logged out"})
    resp.delete_cookie("auth_token")
    return resp


@app.route("/api/auth/me", methods=["GET"])
@require_auth()
def me():
    return jsonify(request.current_user)


# ──────────────────────────────────────────────
# VIOLATIONS CRUD
# ──────────────────────────────────────────────


@app.route("/api/violations", methods=["GET"])
@require_auth()
def get_violations():
    user = request.current_user
    db = get_db()
    params = []

    if user["role"] == "citizen":
        # citizen sees only their own vehicle violations
        query = """
            SELECT v.*, veh.plate_number as vplate, veh.make, veh.model,
                   u.full_name as officer_name, o.badge_id
            FROM violations v
            LEFT JOIN vehicles veh ON veh.id = v.vehicle_id
            LEFT JOIN officers o ON o.id = v.officer_id
            LEFT JOIN users u ON u.id = o.user_id
            WHERE veh.citizen_id = ?
            ORDER BY v.issued_at DESC
        """
        params = [user["citizen_id"]]
    elif user["role"] == "officer":
        query = """
            SELECT v.*, veh.make, veh.model,
                   u.full_name as officer_name, o.badge_id
            FROM violations v
            LEFT JOIN vehicles veh ON veh.id = v.vehicle_id
            LEFT JOIN officers o ON o.id = v.officer_id
            LEFT JOIN users u ON u.id = o.user_id
            WHERE v.officer_id = ?
            ORDER BY v.issued_at DESC
        """
        params = [user["officer_id"]]
    else:  # admin
        status_filter = request.args.get("status")
        query = """
            SELECT v.*, veh.make, veh.model,
                   uo.full_name as officer_name, o.badge_id,
                   uc.full_name as citizen_name
            FROM violations v
            LEFT JOIN vehicles veh ON veh.id = v.vehicle_id
            LEFT JOIN officers o ON o.id = v.officer_id
            LEFT JOIN users uo ON uo.id = o.user_id
            LEFT JOIN citizens c ON c.id = veh.citizen_id
            LEFT JOIN users uc ON uc.id = c.user_id
        """
        if status_filter:
            query += " WHERE v.status=?"
            params = [status_filter]
        query += " ORDER BY v.issued_at DESC"

    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))
    query += f" LIMIT {limit} OFFSET {offset}"

    rows = db.execute(query, params).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/violations", methods=["POST"])
@require_auth("officer", "admin")
def create_violation():
    user = request.current_user
    data = request.get_json()
    required = ["plate_number", "violation_type", "fine_amount"]
    for f in required:
        if not data.get(f):
            return jsonify({"error": f"Missing: {f}"}), 400

    plate = data["plate_number"].upper().replace(" ", "")
    db = get_db()

    # Look up vehicle
    veh = db.execute(
        "SELECT id FROM vehicles WHERE plate_number=?", (plate,)
    ).fetchone()
    veh_id = veh["id"] if veh else None

    challan = gen_challan()
    due_date = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")

    db.execute(
        """
        INSERT INTO violations 
        (challan_number,vehicle_id,officer_id,plate_number,violation_type,fine_amount,
         location,latitude,longitude,description,evidence_path,due_date)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """,
        (
            challan,
            veh_id,
            user.get("officer_id"),
            plate,
            data["violation_type"],
            data["fine_amount"],
            data.get("location", ""),
            data.get("latitude"),
            data.get("longitude"),
            data.get("description", ""),
            data.get("evidence_path", ""),
            due_date,
        ),
    )
    db.commit()
    vid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    row = db.execute("SELECT * FROM violations WHERE id=?", (vid,)).fetchone()
    db.close()
    log_action(user["id"], "VIOLATION_ISSUED", f"Challan: {challan}, Plate: {plate}")
    return jsonify(dict(row)), 201


@app.route("/api/violations/<int:vid>", methods=["GET"])
@require_auth()
def get_violation(vid):
    db = get_db()
    row = db.execute(
        """
        SELECT v.*, veh.make, veh.model, veh.color,
               uo.full_name as officer_name, o.badge_id, o.rank,
               uc.full_name as citizen_name, uc.email as citizen_email, uc.phone as citizen_phone
        FROM violations v
        LEFT JOIN vehicles veh ON veh.id = v.vehicle_id
        LEFT JOIN officers o ON o.id = v.officer_id
        LEFT JOIN users uo ON uo.id = o.user_id
        LEFT JOIN citizens c ON c.id = veh.citizen_id
        LEFT JOIN users uc ON uc.id = c.user_id
        WHERE v.id=?
    """,
        (vid,),
    ).fetchone()
    db.close()
    if not row:
        return jsonify({"error": "Not found"}), 404
    return jsonify(dict(row))


@app.route("/api/violations/<int:vid>/status", methods=["PATCH"])
@require_auth("officer", "admin")
def update_violation_status(vid):
    data = request.get_json()
    status = data.get("status")
    if status not in ("pending", "paid", "contested", "cancelled", "overdue"):
        return jsonify({"error": "Invalid status"}), 400
    db = get_db()
    db.execute("UPDATE violations SET status=? WHERE id=?", (status, vid))
    db.commit()
    db.close()
    return jsonify({"message": "Updated"})


@app.route("/api/violations/<string:challan>/lookup", methods=["GET"])
def lookup_challan(challan):
    """Public challan lookup by number"""
    db = get_db()
    row = db.execute(
        """
        SELECT v.*, veh.make, veh.model, uo.full_name as officer_name
        FROM violations v
        LEFT JOIN vehicles veh ON veh.id = v.vehicle_id
        LEFT JOIN officers o ON o.id = v.officer_id
        LEFT JOIN users uo ON uo.id = o.user_id
        WHERE v.challan_number=?
    """,
        (challan.upper(),),
    ).fetchone()
    db.close()
    if not row:
        return jsonify({"error": "Challan not found"}), 404
    return jsonify(dict(row))


# ──────────────────────────────────────────────
# PAYMENTS
# ──────────────────────────────────────────────


@app.route("/api/payments", methods=["POST"])
@require_auth("citizen", "admin")
def make_payment():
    user = request.current_user
    data = request.get_json()
    vid = data.get("violation_id")
    method = data.get("payment_method", "online")

    db = get_db()
    viol = db.execute("SELECT * FROM violations WHERE id=?", (vid,)).fetchone()
    if not viol:
        db.close()
        return jsonify({"error": "Violation not found"}), 404
    if viol["status"] == "paid":
        db.close()
        return jsonify({"error": "Already paid"}), 400

    txn_id = "TXN" + secrets.token_hex(8).upper()
    paid_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    db.execute(
        """
        INSERT INTO payments (violation_id,citizen_id,amount,payment_method,transaction_id,paid_at)
        VALUES (?,?,?,?,?,?)
    """,
        (vid, user.get("citizen_id"), viol["fine_amount"], method, txn_id, paid_at),
    )
    db.execute(
        "UPDATE violations SET status='paid', paid_at=? WHERE id=?", (paid_at, vid)
    )
    db.commit()
    db.close()
    log_action(
        user["id"], "PAYMENT", f"Challan: {viol['challan_number']}, Txn: {txn_id}"
    )
    return jsonify(
        {
            "message": "Payment successful",
            "transaction_id": txn_id,
            "amount": viol["fine_amount"],
        }
    )


@app.route("/api/payments/history", methods=["GET"])
@require_auth("citizen", "admin")
def payment_history():
    user = request.current_user
    db = get_db()
    if user["role"] == "citizen":
        rows = db.execute(
            """
            SELECT p.*, v.challan_number, v.violation_type, v.plate_number
            FROM payments p JOIN violations v ON v.id=p.violation_id
            WHERE p.citizen_id=?
            ORDER BY p.paid_at DESC
        """,
            (user["citizen_id"],),
        ).fetchall()
    else:
        rows = db.execute(
            """
            SELECT p.*, v.challan_number, v.violation_type, v.plate_number,
                   u.full_name as citizen_name
            FROM payments p 
            JOIN violations v ON v.id=p.violation_id
            LEFT JOIN citizens c ON c.id=p.citizen_id
            LEFT JOIN users u ON u.id=c.user_id
            ORDER BY p.paid_at DESC LIMIT 100
        """
        ).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


# ──────────────────────────────────────────────
# VEHICLES
# ──────────────────────────────────────────────


@app.route("/api/vehicles", methods=["GET"])
@require_auth()
def get_vehicles():
    user = request.current_user
    db = get_db()
    if user["role"] == "citizen":
        rows = db.execute(
            """
            SELECT v.*, 
                   (SELECT COUNT(*) FROM violations viol WHERE viol.vehicle_id=v.id AND viol.status='pending') as pending_count,
                   (SELECT SUM(fine_amount) FROM violations viol WHERE viol.vehicle_id=v.id AND viol.status='pending') as pending_amount
            FROM vehicles v WHERE v.citizen_id=?
        """,
            (user["citizen_id"],),
        ).fetchall()
    else:
        plate = request.args.get("plate", "")
        rows = db.execute(
            """
            SELECT v.*, u.full_name as owner_name, u.phone as owner_phone,
                   (SELECT COUNT(*) FROM violations viol WHERE viol.vehicle_id=v.id AND viol.status='pending') as pending_count
            FROM vehicles v
            LEFT JOIN citizens c ON c.id=v.citizen_id
            LEFT JOIN users u ON u.id=c.user_id
            WHERE v.plate_number LIKE ?
        """,
            (f"%{plate.upper()}%",),
        ).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/vehicles", methods=["POST"])
@require_auth("citizen")
def add_vehicle():
    user = request.current_user
    data = request.get_json()
    if not data.get("plate_number"):
        return jsonify({"error": "Plate number required"}), 400
    db = get_db()
    try:
        db.execute(
            """
            INSERT INTO vehicles (citizen_id,plate_number,make,model,year,color,vehicle_type,insurance_expiry)
            VALUES (?,?,?,?,?,?,?,?)
        """,
            (
                user["citizen_id"],
                data["plate_number"].upper(),
                data.get("make", ""),
                data.get("model", ""),
                data.get("year"),
                data.get("color", ""),
                data.get("vehicle_type", "Car"),
                data.get("insurance_expiry"),
            ),
        )
        # If driving licence provided, update citizen record
        if data.get("dl_number"):
            db.execute(
                "UPDATE citizens SET dl_number=? WHERE id=?",
                (data["dl_number"].strip(), user["citizen_id"]),
            )
        db.commit()
        vid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        row = db.execute("SELECT * FROM vehicles WHERE id=?", (vid,)).fetchone()
        db.close()
        return jsonify(dict(row)), 201
    except Exception as e:
        db.close()
        return jsonify({"error": str(e)}), 400


@app.route("/api/vehicles/<string:plate>/verify", methods=["GET"])
@require_auth("officer", "admin")
def verify_plate(plate):
    """Officer plate lookup"""
    db = get_db()
    row = db.execute(
        """
        SELECT v.*, u.full_name as owner_name, u.phone as owner_phone, u.email as owner_email,
               c.aadhaar, c.dl_number,
               (SELECT COUNT(*) FROM violations viol WHERE viol.vehicle_id=v.id AND viol.status='pending') as pending_violations,
               (SELECT SUM(fine_amount) FROM violations viol WHERE viol.vehicle_id=v.id AND viol.status='pending') as total_due
        FROM vehicles v
        LEFT JOIN citizens c ON c.id=v.citizen_id
        LEFT JOIN users u ON u.id=c.user_id
        WHERE v.plate_number=?
    """,
        (plate.upper(),),
    ).fetchone()
    db.close()
    if not row:
        return jsonify({"error": "Vehicle not found in RTO database"}), 404
    return jsonify(dict(row))


# ──────────────────────────────────────────────
# OFFICERS
# ──────────────────────────────────────────────


@app.route("/api/officers", methods=["GET"])
@require_auth("admin")
def get_officers():
    db = get_db()
    rows = db.execute(
        """
        SELECT o.*, u.full_name, u.email, u.phone, u.is_active,
               (SELECT COUNT(*) FROM violations v WHERE v.officer_id=o.id) as total_citations
        FROM officers o JOIN users u ON u.id=o.user_id
        ORDER BY o.badge_id
    """
    ).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/officers/<int:oid>/location", methods=["PATCH"])
@require_auth("officer")
def update_officer_location(oid):
    user = request.current_user
    if user["officer_id"] != oid:
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json()
    db = get_db()
    db.execute(
        "UPDATE officers SET latitude=?, longitude=?, location_name=?, last_update=? WHERE id=?",
        (
            data["latitude"],
            data["longitude"],
            data.get("location_name", ""),
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            oid,
        ),
    )
    db.commit()
    db.close()
    return jsonify({"message": "Location updated"})


@app.route("/api/officers/<int:oid>/status", methods=["PATCH"])
@require_auth("officer", "admin")
def update_officer_status(oid):
    data = request.get_json()
    status = data.get("status")
    if status not in ("on_duty", "off_duty", "on_break", "emergency"):
        return jsonify({"error": "Invalid status"}), 400
    db = get_db()
    db.execute(
        "UPDATE officers SET status=?, last_update=? WHERE id=?",
        (status, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), oid),
    )
    db.commit()
    db.close()
    return jsonify({"message": "Status updated"})


# ──────────────────────────────────────────────
# SOS / EMERGENCY ALERTS
# ──────────────────────────────────────────────


@app.route("/api/sos", methods=["GET"])
@require_auth()
def get_sos():
    db = get_db()
    if request.current_user["role"] == "officer":
        rows = db.execute(
            """
            SELECT s.*, u.full_name as reporter_name, u.phone as reporter_phone
            FROM sos_alerts s
            LEFT JOIN officers o ON o.id=s.officer_id
            LEFT JOIN users u ON u.id=o.user_id
            WHERE s.officer_id=?
            ORDER BY s.created_at DESC
        """,
            (request.current_user["officer_id"],),
        ).fetchall()
    else:
        rows = db.execute(
            """
            SELECT s.*, u.full_name as reporter_name, o.badge_id
            FROM sos_alerts s
            LEFT JOIN officers o ON o.id=s.officer_id
            LEFT JOIN users u ON u.id=o.user_id
            ORDER BY s.created_at DESC
        """
        ).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/sos", methods=["POST"])
@require_auth("officer")
def create_sos():
    user = request.current_user
    data = request.get_json()
    db = get_db()
    db.execute(
        """
        INSERT INTO sos_alerts (officer_id,alert_type,priority,location,latitude,longitude,description)
        VALUES (?,?,?,?,?,?,?)
    """,
        (
            user["officer_id"],
            data.get("alert_type", "Road Accident"),
            data.get("priority", "high"),
            data.get("location", ""),
            data.get("latitude"),
            data.get("longitude"),
            data.get("description", ""),
        ),
    )
    db.commit()
    sid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    row = db.execute("SELECT * FROM sos_alerts WHERE id=?", (sid,)).fetchone()
    db.close()
    log_action(
        user["id"],
        "SOS_CREATED",
        f"Type: {data.get('alert_type')}, Priority: {data.get('priority')}",
    )
    return jsonify(dict(row)), 201


@app.route("/api/sos/<int:sid>/dispatch", methods=["PATCH"])
@require_auth("admin")
def dispatch_sos(sid):
    data = request.get_json()
    db = get_db()
    sos = db.execute("SELECT * FROM sos_alerts WHERE id=?", (sid,)).fetchone()
    if not sos:
        db.close()
        return jsonify({"error": "Not found"}), 404

    updates = {}
    if data.get("police_unit"):
        updates["police_unit"] = data["police_unit"]
    if data.get("medical_unit"):
        updates["medical_unit"] = data["medical_unit"]
    if data.get("fire_unit"):
        updates["fire_unit"] = data["fire_unit"]
    updates["status"] = "dispatched"

    set_clause = ", ".join(f"{k}=?" for k in updates)
    db.execute(
        f"UPDATE sos_alerts SET {set_clause} WHERE id=?", list(updates.values()) + [sid]
    )
    db.commit()
    row = db.execute("SELECT * FROM sos_alerts WHERE id=?", (sid,)).fetchone()
    db.close()
    return jsonify(dict(row))


@app.route("/api/sos/<int:sid>/resolve", methods=["PATCH"])
@require_auth("admin")
def resolve_sos(sid):
    resolved_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    db = get_db()
    db.execute(
        "UPDATE sos_alerts SET status='resolved', resolved_at=? WHERE id=?",
        (resolved_at, sid),
    )
    db.commit()
    db.close()
    return jsonify({"message": "Resolved"})


# ──────────────────────────────────────────────
# ADMIN: ANALYTICS & STATS
# ──────────────────────────────────────────────


@app.route("/api/admin/stats", methods=["GET"])
@require_auth("admin")
def admin_stats():
    db = get_db()
    stats = {}
    stats["total_violations"] = db.execute(
        "SELECT COUNT(*) FROM violations"
    ).fetchone()[0]
    stats["pending_violations"] = db.execute(
        "SELECT COUNT(*) FROM violations WHERE status='pending'"
    ).fetchone()[0]
    stats["paid_violations"] = db.execute(
        "SELECT COUNT(*) FROM violations WHERE status='paid'"
    ).fetchone()[0]
    stats["total_revenue"] = db.execute(
        "SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='success'"
    ).fetchone()[0]
    stats["total_officers"] = db.execute("SELECT COUNT(*) FROM officers").fetchone()[0]
    stats["on_duty_officers"] = db.execute(
        "SELECT COUNT(*) FROM officers WHERE status='on_duty'"
    ).fetchone()[0]
    stats["total_citizens"] = db.execute("SELECT COUNT(*) FROM citizens").fetchone()[0]
    stats["total_vehicles"] = db.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0]
    stats["active_sos"] = db.execute(
        "SELECT COUNT(*) FROM sos_alerts WHERE status NOT IN ('resolved','cancelled')"
    ).fetchone()[0]

    # Violations by type
    by_type = db.execute(
        """
        SELECT violation_type, COUNT(*) as count, SUM(fine_amount) as revenue
        FROM violations GROUP BY violation_type ORDER BY count DESC LIMIT 10
    """
    ).fetchall()
    stats["violations_by_type"] = [dict(r) for r in by_type]

    # Daily trend (last 7 days)
    daily = db.execute(
        """
        SELECT date(issued_at) as day, COUNT(*) as count
        FROM violations
        WHERE issued_at >= date('now', '-7 days')
        GROUP BY date(issued_at) ORDER BY day
    """
    ).fetchall()
    stats["daily_trend"] = [dict(r) for r in daily]

    db.close()
    return jsonify(stats)


@app.route("/api/admin/users", methods=["GET"])
@require_auth("admin")
def admin_users():
    role = request.args.get("role")
    db = get_db()
    query = (
        "SELECT id,username,role,full_name,email,phone,created_at,is_active FROM users"
    )
    params = []
    if role:
        query += " WHERE role=?"
        params = [role]
    query += " ORDER BY created_at DESC"
    rows = db.execute(query, params).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/admin/users/<int:uid>/toggle", methods=["PATCH"])
@require_auth("admin")
def toggle_user(uid):
    db = get_db()
    user = db.execute("SELECT is_active FROM users WHERE id=?", (uid,)).fetchone()
    if not user:
        db.close()
        return jsonify({"error": "Not found"}), 404
    new_status = 0 if user["is_active"] else 1
    db.execute("UPDATE users SET is_active=? WHERE id=?", (new_status, uid))
    db.commit()
    db.close()
    return jsonify({"is_active": new_status})


# ──────────────────────────────────────────────
# FILE UPLOAD (Evidence)
# ──────────────────────────────────────────────


@app.route("/api/upload/evidence", methods=["POST"])
@require_auth("officer", "admin")
def upload_evidence():
    if "file" not in request.files:
        return jsonify({"error": "No file"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Empty file"}), 400
    ext = f.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "mp4", "mov"):
        return jsonify({"error": "Invalid file type"}), 400
    fname = secrets.token_hex(16) + "." + ext
    f.save(os.path.join(UPLOAD_FOLDER, fname))
    return jsonify({"path": f"/static/uploads/{fname}", "filename": fname})


# ──────────────────────────────────────────────
# CITIZEN PROFILE UPDATE
# ──────────────────────────────────────────────


@app.route("/api/profile", methods=["GET"])
@require_auth()
def get_profile():
    user = request.current_user
    db = get_db()
    u = db.execute(
        "SELECT id,username,full_name,email,phone,role,created_at FROM users WHERE id=?",
        (user["id"],),
    ).fetchone()
    result = dict(u)
    if user["role"] == "citizen":
        c = db.execute(
            "SELECT * FROM citizens WHERE user_id=?", (user["id"],)
        ).fetchone()
        if c:
            result.update({k: c[k] for k in c.keys()})
    elif user["role"] == "officer":
        o = db.execute(
            "SELECT * FROM officers WHERE user_id=?", (user["id"],)
        ).fetchone()
        if o:
            result.update({k: o[k] for k in o.keys()})
    db.close()
    return jsonify(result)


@app.route("/api/profile", methods=["PATCH"])
@require_auth()
def update_profile():
    user = request.current_user
    data = request.get_json()
    db = get_db()
    allowed_user = ["full_name", "phone"]
    updates = {k: v for k, v in data.items() if k in allowed_user}
    if updates:
        set_clause = ", ".join(f"{k}=?" for k in updates)
        db.execute(
            f"UPDATE users SET {set_clause} WHERE id=?",
            list(updates.values()) + [user["id"]],
        )
    # Citizen can also update aadhaar
    if user["role"] == "citizen" and "aadhaar" in data:
        aadhaar = (data["aadhaar"] or "").strip()
        if aadhaar and (not aadhaar.isdigit() or len(aadhaar) != 12):
            db.close()
            return jsonify({"error": "Aadhaar must be exactly 12 digits"}), 400
        db.execute(
            "UPDATE citizens SET aadhaar=? WHERE user_id=?",
            (aadhaar if aadhaar else None, user["id"]),
        )
    db.commit()
    db.close()
    return jsonify({"message": "Profile updated"})


# ──────────────────────────────────────────────
# AUDIT LOG
# ──────────────────────────────────────────────


@app.route("/api/admin/audit", methods=["GET"])
@require_auth("admin")
def get_audit():
    db = get_db()
    rows = db.execute(
        """
        SELECT a.*, u.full_name, u.role
        FROM audit_log a LEFT JOIN users u ON u.id=a.user_id
        ORDER BY a.created_at DESC LIMIT 200
    """
    ).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


# ──────────────────────────────────────────────
# NEARBY OFFICERS & EMERGENCY SERVICES
# ──────────────────────────────────────────────


@app.route("/api/nearby/officers", methods=["GET"])
@require_auth("admin", "officer")
def get_nearby_officers():
    """Get officers within specified radius (default 3 km) of given coordinates"""
    try:
        user_lat = float(request.args.get("latitude"))
        user_lon = float(request.args.get("longitude"))
        radius_km = int(request.args.get("radius", 3))
    except:
        return jsonify({"error": "Invalid coordinates or radius"}), 400

    db = get_db()
    officers = db.execute(
        """
        SELECT o.id, o.badge_id, o.rank, o.zone, o.latitude, o.longitude, o.status,
               u.full_name, u.phone
        FROM officers o
        JOIN users u ON u.id = o.user_id
        WHERE o.latitude IS NOT NULL AND o.longitude IS NOT NULL AND u.is_active = 1
    """
    ).fetchall()
    db.close()

    nearby = []
    for officer in officers:
        dist = haversine_distance(
            user_lat, user_lon, officer["latitude"], officer["longitude"]
        )
        if dist <= radius_km:
            officer_dict = dict(officer)
            officer_dict["distance_km"] = round(dist, 2)
            nearby.append(officer_dict)

    nearby.sort(key=lambda x: x["distance_km"])
    return jsonify(nearby)


@app.route("/api/nearby/emergency-services", methods=["GET"])
@require_auth("admin", "officer")
def get_nearby_emergency_services():
    """Get emergency services (hospitals, fire, police) within specified radius (default 3 km)"""
    try:
        user_lat = float(request.args.get("latitude"))
        user_lon = float(request.args.get("longitude"))
        radius_km = int(request.args.get("radius", 3))
        service_type = request.args.get(
            "type", ""
        )  # Optional: 'hospital', 'fire_station', 'police_post'
    except:
        return jsonify({"error": "Invalid coordinates or radius"}), 400

    db = get_db()
    query = "SELECT * FROM emergency_services WHERE is_active=1"
    params = []

    if service_type:
        query += " AND service_type=?"
        params.append(service_type)

    services = db.execute(query, params).fetchall()
    db.close()

    nearby = []
    for service in services:
        dist = haversine_distance(
            user_lat, user_lon, service["latitude"], service["longitude"]
        )
        if dist <= radius_km:
            service_dict = dict(service)
            service_dict["distance_km"] = round(dist, 2)
            nearby.append(service_dict)

    nearby.sort(key=lambda x: x["distance_km"])
    return jsonify(nearby)


@app.route("/api/emergency-services", methods=["GET"])
@require_auth("admin", "officer")
def get_all_emergency_services():
    """Get all emergency services with optional filtering"""
    service_type = request.args.get("type", "")
    db = get_db()

    query = "SELECT * FROM emergency_services WHERE is_active=1"
    params = []
    if service_type:
        query += " AND service_type=?"
        params.append(service_type)

    query += " ORDER BY name"
    rows = db.execute(query, params).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/reverse-geocode", methods=["GET"])
def reverse_geocode():
    """Get location name and Telugu translation for coordinates (PUBLIC - no auth required for MVP)"""
    try:
        latitude = float(request.args.get("latitude"))
        longitude = float(request.args.get("longitude"))
    except:
        return jsonify({"error": "Invalid coordinates"}), 400

    # For now, return generic location name
    # In production, integrate with Google Maps API for reverse geocoding
    location_name = f"Location ({latitude:.4f}, {longitude:.4f})"
    location_telugu = f"స్థానం ({latitude:.4f}, {longitude:.4f})"

    return jsonify(
        {
            "latitude": latitude,
            "longitude": longitude,
            "location": location_name,
            "location_telugu": location_telugu,
        }
    )


# ──────────────────────────────────────────────
# TRAFFIC NEWS (Live RSS Feed)
# ──────────────────────────────────────────────


_news_cache = {"data": None, "expires": 0}


@app.route("/api/traffic-news", methods=["GET"])
@require_auth()
def get_traffic_news():
    """Fetch live traffic/road safety news from Google News RSS for India/Telangana"""
    import time

    now = time.time()
    # Cache news for 10 minutes to avoid hammering RSS feeds
    if _news_cache["data"] and _news_cache["expires"] > now:
        return jsonify(_news_cache["data"])

    feeds = [
        "https://news.google.com/rss/search?q=road+accident+Telangana+OR+Hyderabad&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=traffic+update+Hyderabad+OR+Telangana&hl=en-IN&gl=IN&ceid=IN:en",
        "https://news.google.com/rss/search?q=road+safety+India&hl=en-IN&gl=IN&ceid=IN:en",
    ]

    articles = []
    seen_titles = set()
    for feed_url in feeds:
        try:
            req = urllib.request.Request(
                feed_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TrafficGuard/1.0"
                },
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                xml_data = resp.read()
            root = ET.fromstring(xml_data)
            for item in root.findall(".//item"):
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                pub_date = item.findtext("pubDate", "")
                source = item.findtext("source", "")
                if not source:
                    # Extract source from title (Google News format: "Title - Source")
                    if " - " in title:
                        parts = title.rsplit(" - ", 1)
                        source = parts[-1].strip()
                        title = parts[0].strip()
                # Deduplicate
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    articles.append(
                        {
                            "title": title,
                            "link": link,
                            "source": source or "News",
                            "published": pub_date,
                        }
                    )
        except Exception as e:
            print(f"[News Feed Error] {feed_url}: {e}")
            continue

    # Limit to 12 articles
    articles = articles[:12]

    # Cache the result
    _news_cache["data"] = articles
    _news_cache["expires"] = now + 600  # 10 min cache

    return jsonify(articles)


# ──────────────────────────────────────────────
# HEALTH CHECK
# ──────────────────────────────────────────────


@app.route("/api/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "time": datetime.utcnow().isoformat(),
            "db": os.path.exists(DB_PATH),
        }
    )


# ──────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("  TRAFFIC GUARD TVM — BACKEND SERVER")
    print("=" * 50)
    init_db()
    print("\n  Default Credentials:")
    print("  Admin:   admin / admin123")
    print("  Officer: officer1 / officer123")
    print("  Citizen: citizen1 / 1234")
    print(f"\n  Running at: http://127.0.0.1:5000")
    print("=" * 50)
    app.run(debug=True, host="0.0.0.0", port=5000)
