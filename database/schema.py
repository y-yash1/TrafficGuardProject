import sqlite3
import os
import hashlib
from datetime import datetime, timedelta
import random

DB_PATH = os.path.join(os.path.dirname(__file__), "traffic_guard.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def init_db():
    conn = get_db()
    c = conn.cursor()

    # ── USERS ──
    c.executescript(
        """
    CREATE TABLE IF NOT EXISTS users (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        username    TEXT UNIQUE NOT NULL,
        password    TEXT NOT NULL,
        role        TEXT NOT NULL CHECK(role IN ('citizen','officer','admin')),
        full_name   TEXT,
        email       TEXT UNIQUE,
        phone       TEXT,
        created_at  TEXT DEFAULT (datetime('now')),
        is_active   INTEGER DEFAULT 1
    );

    -- CITIZENS
    CREATE TABLE IF NOT EXISTS citizens (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
        aadhaar     TEXT,
        dl_number   TEXT,
        address     TEXT,
        city        TEXT DEFAULT 'Hyderabad'
    );

    -- OFFICERS
    CREATE TABLE IF NOT EXISTS officers (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
        badge_id    TEXT UNIQUE NOT NULL,
        rank        TEXT DEFAULT 'Constable',
        zone        TEXT DEFAULT 'Central',
        station     TEXT DEFAULT 'HQ',
        latitude    REAL DEFAULT 17.3850,
        longitude   REAL DEFAULT 78.4867,
        location_name TEXT DEFAULT '',
        status      TEXT DEFAULT 'on_duty' CHECK(status IN ('on_duty','off_duty','on_break','emergency')),
        last_update TEXT DEFAULT (datetime('now'))
    );

    -- VEHICLES
    CREATE TABLE IF NOT EXISTS vehicles (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        citizen_id      INTEGER REFERENCES citizens(id) ON DELETE CASCADE,
        plate_number    TEXT UNIQUE NOT NULL,
        make            TEXT,
        model           TEXT,
        year            INTEGER,
        color           TEXT,
        vehicle_type    TEXT DEFAULT 'Car',
        insurance_expiry TEXT,
        rc_number       TEXT,
        is_active       INTEGER DEFAULT 1
    );

    -- VIOLATIONS / CITATIONS
    CREATE TABLE IF NOT EXISTS violations (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        challan_number  TEXT UNIQUE NOT NULL,
        vehicle_id      INTEGER REFERENCES vehicles(id),
        officer_id      INTEGER REFERENCES officers(id),
        plate_number    TEXT NOT NULL,
        violation_type  TEXT NOT NULL,
        fine_amount     REAL NOT NULL,
        location        TEXT,
        latitude        REAL,
        longitude       REAL,
        description     TEXT,
        evidence_path   TEXT,
        status          TEXT DEFAULT 'pending' CHECK(status IN ('pending','paid','contested','cancelled','overdue')),
        issued_at       TEXT DEFAULT (datetime('now')),
        due_date        TEXT,
        paid_at         TEXT
    );

    -- PAYMENTS
    CREATE TABLE IF NOT EXISTS payments (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        violation_id    INTEGER REFERENCES violations(id),
        citizen_id      INTEGER REFERENCES citizens(id),
        amount          REAL NOT NULL,
        payment_method  TEXT DEFAULT 'online',
        transaction_id  TEXT UNIQUE,
        status          TEXT DEFAULT 'success',
        paid_at         TEXT DEFAULT (datetime('now'))
    );

    -- EMERGENCY / SOS ALERTS
    CREATE TABLE IF NOT EXISTS sos_alerts (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        officer_id      INTEGER REFERENCES officers(id),
        alert_type      TEXT NOT NULL,
        priority        TEXT DEFAULT 'high' CHECK(priority IN ('low','medium','high','critical')),
        location        TEXT,
        latitude        REAL,
        longitude       REAL,
        description     TEXT,
        status          TEXT DEFAULT 'pending' CHECK(status IN ('pending','dispatched','enroute','resolved')),
        police_unit     TEXT,
        medical_unit    TEXT,
        fire_unit       TEXT,
        created_at      TEXT DEFAULT (datetime('now')),
        resolved_at     TEXT
    );

    -- EMERGENCY SERVICES (Hospitals, Fire Stations, Police Posts)
    CREATE TABLE IF NOT EXISTS emergency_services (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        service_type    TEXT NOT NULL CHECK(service_type IN ('hospital','fire_station','police_post')),
        name            TEXT NOT NULL,
        name_telugu     TEXT,
        phone           TEXT,
        address         TEXT,
        latitude        REAL NOT NULL,
        longitude       REAL NOT NULL,
        zone            TEXT,
        is_active       INTEGER DEFAULT 1
    );

    -- AUDIT LOG
    CREATE TABLE IF NOT EXISTS audit_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER REFERENCES users(id),
        action      TEXT NOT NULL,
        details     TEXT,
        ip_address  TEXT,
        created_at  TEXT DEFAULT (datetime('now'))
    );

    -- SESSIONS (simple token store)
    CREATE TABLE IF NOT EXISTS sessions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER REFERENCES users(id) ON DELETE CASCADE,
        token       TEXT UNIQUE NOT NULL,
        expires_at  TEXT NOT NULL,
        created_at  TEXT DEFAULT (datetime('now'))
    );
    """
    )

    # ── SEED DATA ──
    # Admin
    c.execute("SELECT id FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute(
            "INSERT INTO users (username,password,role,full_name,email,phone) VALUES (?,?,?,?,?,?)",
            (
                "admin",
                hash_password("admin123"),
                "admin",
                "System Administrator",
                "admin@trafficguard.gov.in",
                "+91-9876543210",
            ),
        )

    # Officers
    officers_data = [
        (
            "officer1",
            "officer123",
            "Const. Venkat Reddy",
            "venkat.reddy@police.hyderabad.gov.in",
            "+91-9876543211",
            "OFF001",
            "Constable",
            "Central",
            17.4375,
            78.4483,
        ),
        (
            "officer2",
            "officer123",
            "SI. Srikanth Rao",
            "srikanth.rao@police.hyderabad.gov.in",
            "+91-9876543212",
            "OFF002",
            "Sub Inspector",
            "North",
            17.4399,
            78.4983,
        ),
        (
            "officer3",
            "officer123",
            "HC. Ramesh Chary",
            "ramesh.chary@police.hyderabad.gov.in",
            "+91-9876543213",
            "OFF003",
            "Head Constable",
            "West",
            17.4435,
            78.3772,
        ),
        (
            "officer4",
            "officer123",
            "SI. Lakshmi Devi",
            "lakshmi.devi@police.hyderabad.gov.in",
            "+91-9876543214",
            "OFF004",
            "Sub Inspector",
            "South",
            17.3616,
            78.4747,
        ),
        (
            "officer5",
            "officer123",
            "Const. Srinivas Goud",
            "srinivas.goud@police.hyderabad.gov.in",
            "+91-9876543215",
            "OFF005",
            "Constable",
            "East",
            17.3950,
            78.5500,
        ),
    ]
    for o in officers_data:
        c.execute("SELECT id FROM users WHERE username=?", (o[0],))
        if not c.fetchone():
            c.execute(
                "INSERT INTO users (username,password,role,full_name,email,phone) VALUES (?,?,?,?,?,?)",
                (o[0], hash_password(o[1]), "officer", o[2], o[3], o[4]),
            )
            uid = c.lastrowid
            c.execute(
                "INSERT INTO officers (user_id,badge_id,rank,zone,latitude,longitude) VALUES (?,?,?,?,?,?)",
                (uid, o[5], o[6], o[7], o[8], o[9]),
            )

    # Citizens
    citizens_data = [
        (
            "citizen1",
            "1234",
            "Rajesh Reddy",
            "rajesh.reddy@example.com",
            "+91-9876543220",
            "XXXX-XXXX-4921",
            "TS-09-1234567",
        ),
        (
            "citizen2",
            "1234",
            "Swathi Kumari",
            "swathi.kumari@example.com",
            "+91-9876543221",
            "XXXX-XXXX-8832",
            "TS-09-9876543",
        ),
        (
            "citizen3",
            "1234",
            "Anil Kumar Goud",
            "anil.goud@example.com",
            "+91-9876543222",
            "XXXX-XXXX-3310",
            "TS-09-5566778",
        ),
    ]
    for ci in citizens_data:
        c.execute("SELECT id FROM users WHERE username=?", (ci[0],))
        if not c.fetchone():
            c.execute(
                "INSERT INTO users (username,password,role,full_name,email,phone) VALUES (?,?,?,?,?,?)",
                (ci[0], hash_password(ci[1]), "citizen", ci[2], ci[3], ci[4]),
            )
            uid = c.lastrowid
            c.execute(
                "INSERT INTO citizens (user_id,aadhaar,dl_number) VALUES (?,?,?)",
                (uid, ci[5], ci[6]),
            )

    # Vehicles — Telangana (TS) registration plates
    vehicles_data = [
        (1, "TS09AB1234", "Honda", "City", 2019, "White", "Car", "2025-12-31"),
        (
            1,
            "TS10CD5678",
            "Royal Enfield",
            "Classic 350",
            2021,
            "Black",
            "Motorcycle",
            "2026-06-30",
        ),
        (2, "TS08EF9012", "Maruti", "Swift", 2020, "Silver", "Car", "2025-09-30"),
        (3, "TS07GH3456", "Hyundai", "i20", 2022, "Blue", "Car", "2026-03-31"),
    ]
    for v in vehicles_data:
        c.execute("SELECT id FROM vehicles WHERE plate_number=?", (v[1],))
        if not c.fetchone():
            c.execute(
                "INSERT INTO vehicles (citizen_id,plate_number,make,model,year,color,vehicle_type,insurance_expiry) VALUES (?,?,?,?,?,?,?,?)",
                v,
            )

    # Violations
    violations_seed = [
        # (challan, vehicle_id, officer_id, plate, type, fine, location, lat, lng, desc, status, issued_at)
        (
            "EC2024001",
            1,
            1,
            "TS09AB1234",
            "Signal Jumping",
            1000,
            "Road No 1, Banjara Hills",
            17.4375,
            78.4483,
            "Crossed red signal at junction",
            "pending",
            "2024-10-24 10:30:00",
        ),
        (
            "EC2024002",
            1,
            2,
            "TS09AB1234",
            "Speeding",
            1000,
            "Begumpet, Secunderabad",
            17.4399,
            78.4983,
            "Recorded at 92 kmph in 60 zone",
            "pending",
            "2024-10-18 08:15:00",
        ),
        (
            "EC2024003",
            3,
            1,
            "TS08EF9012",
            "No Helmet",
            1000,
            "Hitech City, Madhapur",
            17.4484,
            78.3772,
            "Rider without helmet",
            "paid",
            "2024-10-20 14:00:00",
        ),
        (
            "EC2024004",
            4,
            3,
            "TS07GH3456",
            "Using Mobile Phone",
            5000,
            "KPHB Colony",
            17.4833,
            78.3919,
            "Using phone while driving",
            "pending",
            "2024-11-01 09:00:00",
        ),
        (
            "EC2024005",
            2,
            2,
            "TS10CD5678",
            "Triple Riding",
            1000,
            "Secunderabad Junction",
            17.4340,
            78.5020,
            "Three persons on motorcycle",
            "overdue",
            "2024-09-15 16:30:00",
        ),
        (
            "EC2024006",
            1,
            1,
            "TS09AB1234",
            "No Seatbelt",
            1000,
            "Gachibowli",
            17.4400,
            78.3500,
            "Driver without seatbelt",
            "paid",
            "2024-11-05 11:00:00",
        ),
    ]
    for v in violations_seed:
        c.execute("SELECT id FROM violations WHERE challan_number=?", (v[0],))
        if not c.fetchone():
            issued_at = v[11]
            due = (
                datetime.strptime(issued_at, "%Y-%m-%d %H:%M:%S") + timedelta(days=30)
            ).strftime("%Y-%m-%d")
            c.execute(
                """INSERT INTO violations 
                (challan_number,vehicle_id,officer_id,plate_number,violation_type,fine_amount,location,latitude,longitude,description,status,issued_at,due_date)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                v + (due,),
            )

    # SOS Alerts
    sos_seed = [
        (
            1,
            "Road Accident",
            "critical",
            "Road No 1, Banjara Hills",
            17.4250,
            78.4467,
            "3-vehicle collision, injured persons",
            "pending",
        ),
        (
            2,
            "Medical Emergency",
            "high",
            "Hitech City, Madhapur",
            17.4484,
            78.3772,
            "Pedestrian collapsed",
            "enroute",
        ),
        (
            3,
            "Vehicle Fire",
            "critical",
            "Gachibowli",
            17.4400,
            78.3500,
            "Car fire near main gate",
            "resolved",
        ),
    ]
    for s in sos_seed:
        c.execute(
            "INSERT OR IGNORE INTO sos_alerts (officer_id,alert_type,priority,location,latitude,longitude,description,status) VALUES (?,?,?,?,?,?,?,?)",
            s,
        )

    # Emergency Services (Hospitals, Fire Stations, Police Posts) — Hyderabad
    emergency_services_seed = [
        # Hospitals
        (
            "hospital",
            "Apollo Hospitals Jubilee Hills",
            "అపోలో హాస్పిటల్ జూబిలీ హిల్స్",
            "+91-40-23607777",
            "Road No 72, Jubilee Hills, Hyderabad",
            17.4260,
            78.4140,
        ),
        (
            "hospital",
            "CARE Hospitals Banjara Hills",
            "కేర్ హాస్పిటల్ బంజారా హిల్స్",
            "+91-40-67617777",
            "Road No 1, Banjara Hills, Hyderabad",
            17.4230,
            78.4430,
        ),
        (
            "hospital",
            "Yashoda Hospitals Secunderabad",
            "యశోద హాస్పిటల్ సికందరాబాద్",
            "+91-40-44555555",
            "Raj Bhavan Road, Secunderabad",
            17.4390,
            78.4980,
        ),
        (
            "hospital",
            "Continental Hospitals Gachibowli",
            "కాంటినెంటల్ హాస్పిటల్ గచిబౌళీ",
            "+91-40-67001000",
            "IT Park Road, Gachibowli, Hyderabad",
            17.4360,
            78.3630,
        ),
        # Fire Stations
        (
            "fire_station",
            "Fire Station - Abids",
            "ఫైర్ స్టేషన్ - ఆబిడ్స్",
            "+91-40-24555544",
            "Abids Road, Hyderabad",
            17.3930,
            78.4740,
        ),
        (
            "fire_station",
            "Fire Station - Secunderabad",
            "ఫైర్ స్టేషన్ - సికందరాబాద్",
            "+91-40-27619999",
            "SD Road, Secunderabad",
            17.4410,
            78.4990,
        ),
        (
            "fire_station",
            "Fire Station - Kukatpally",
            "ఫైర్ స్టేషన్ - కూకట్‌పల్లి",
            "+91-40-27557777",
            "KPHB Colony, Kukatpally",
            17.4900,
            78.3900,
        ),
        # Police Posts
        (
            "police_post",
            "Banjara Hills Police Station",
            "బంజారా హిల్‌లు పోలీసు స్టేషన్",
            "+91-40-23562200",
            "Road No 12, Banjara Hills, Hyderabad",
            17.4310,
            78.4400,
        ),
        (
            "police_post",
            "Begumpet Police Station",
            "బేగంపేట పోలీసు స్టేషన్",
            "+91-40-27619999",
            "Begumpet, Hyderabad",
            17.4430,
            78.4720,
        ),
        (
            "police_post",
            "Madhapur Police Station",
            "మాధాపూర్ పోలీసు స్టేషన్",
            "+91-40-23555555",
            "Hitech City Road, Madhapur",
            17.4490,
            78.3900,
        ),
        (
            "police_post",
            "Charminar Police Station",
            "చార్మినార్ పోలీసు స్టేషన్",
            "+91-40-24573100",
            "Charminar, Hyderabad",
            17.3616,
            78.4747,
        ),
    ]
    for service in emergency_services_seed:
        c.execute(
            "INSERT OR IGNORE INTO emergency_services (service_type,name,name_telugu,phone,address,latitude,longitude) VALUES (?,?,?,?,?,?,?)",
            service,
        )

    conn.commit()
    conn.close()
    print(f"[DB] Initialized at {DB_PATH}")


if __name__ == "__main__":
    init_db()
