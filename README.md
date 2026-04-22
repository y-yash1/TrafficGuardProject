# 🚦 Traffic Guard TVM — Full Stack Application

A complete traffic enforcement and management system for Thiruvananthapuram (TVM), India.

---

## 📁 Project Structure

```
traffic-guard-app/
├── run.py                          ← Start the server (run this)
├── app.py                          ← Flask backend with all API endpoints
├── requirements.txt                ← Python dependencies
├── database/
│   ├── schema.py                   ← SQLite schema + seed data
│   └── traffic_guard.db            ← Auto-created on first run
├── static/
│   ├── css/
│   │   ├── loginstyle.css          ← Login page styles
│   │   ├── dashboardstyle.css      ← Officer dashboard styles
│   │   └── citizendash.css         ← Citizen portal styles
│   ├── js/
│   │   └── api.js                  ← Shared API client utility
│   ├── images/                     ← All icons and images
│   └── uploads/                    ← Evidence file uploads
└── templates/
    ├── loginpage.html              ← Unified login (Citizen/Officer/Admin)
    ├── dashboard.html              ← Officer main dashboard
    ├── reportviolation.html        ← Issue e-challan form
    ├── emergency.html              ← SOS emergency dispatch
    ├── citizen-dashboard.html      ← Citizen home/overview
    ├── citizen-violations.html     ← Citizen's challan history + payment
    ├── citizen-profile.html        ← Vehicle management + profile
    └── admin-dashboard.html        ← Admin: Analytics, Data, SOS, Audit
```

---

## 🚀 Quick Start

### 1. Install Python (3.8+)
Download from https://python.org

### 2. Install Dependencies
```bash
pip install flask
```
or
```bash
pip install -r requirements.txt
```

### 3. Run the Application
```bash
python3 run.py
```
Open your browser at: **http://127.0.0.1:5000**

---

## 🔑 Default Login Credentials

| Role     | Username   | Password     | Redirects To             |
|----------|------------|--------------|--------------------------|
| Citizen  | `citizen1` | `1234`       | Citizen Portal           |
| Citizen  | `citizen2` | `1234`       | Citizen Portal           |
| Officer  | `officer1` | `officer123` | Officer Dashboard        |
| Officer  | `officer2` | `officer123` | Officer Dashboard        |
| Admin    | `admin`    | `admin123`   | Admin Command Center     |

---

## 🗄️ Database Tables

| Table         | Description                                      |
|---------------|--------------------------------------------------|
| `users`       | All users (citizen / officer / admin)            |
| `citizens`    | Citizen profiles (Aadhaar, DL number, address)   |
| `officers`    | Badge ID, rank, zone, GPS location, duty status  |
| `vehicles`    | Plate number, make/model/year, insurance expiry  |
| `violations`  | E-challans: challan#, type, fine, location       |
| `payments`    | Payment records with transaction IDs             |
| `sos_alerts`  | Emergency dispatch with multi-agency support     |
| `sessions`    | Auth token store (8h expiry)                     |
| `audit_log`   | All user actions with timestamps                 |

---

## 🔌 API Endpoints

### Auth
| Method | Endpoint            | Description           |
|--------|---------------------|-----------------------|
| POST   | `/api/auth/login`   | Login all roles       |
| POST   | `/api/auth/register`| Register new citizen  |
| POST   | `/api/auth/logout`  | End session           |
| GET    | `/api/auth/me`      | Get current user      |
| GET    | `/api/profile`      | Get full profile      |
| PATCH  | `/api/profile`      | Update profile        |

### Violations
| Method | Endpoint                        | Description           |
|--------|---------------------------------|-----------------------|
| GET    | `/api/violations`               | List violations       |
| POST   | `/api/violations`               | Issue new citation    |
| GET    | `/api/violations/<id>`          | Get single violation  |
| PATCH  | `/api/violations/<id>/status`   | Update status         |
| GET    | `/api/violations/<challan>/lookup` | Public lookup      |

### Payments
| Method | Endpoint               | Description         |
|--------|------------------------|---------------------|
| POST   | `/api/payments`        | Pay a fine          |
| GET    | `/api/payments/history`| Payment history     |

### Vehicles
| Method | Endpoint                         | Description        |
|--------|----------------------------------|--------------------|
| GET    | `/api/vehicles`                  | List vehicles      |
| POST   | `/api/vehicles`                  | Add vehicle        |
| GET    | `/api/vehicles/<plate>/verify`   | RTO plate lookup   |

### Officers
| Method | Endpoint                         | Description        |
|--------|----------------------------------|--------------------|
| GET    | `/api/officers`                  | All officers       |
| PATCH  | `/api/officers/<id>/location`    | Update GPS         |
| PATCH  | `/api/officers/<id>/status`      | Toggle duty status |

### SOS / Emergency
| Method | Endpoint                | Description          |
|--------|-------------------------|----------------------|
| GET    | `/api/sos`              | List alerts          |
| POST   | `/api/sos`              | Create SOS alert     |
| PATCH  | `/api/sos/<id>/dispatch`| Dispatch units       |
| PATCH  | `/api/sos/<id>/resolve` | Resolve alert        |

### Admin
| Method | Endpoint                  | Description          |
|--------|---------------------------|----------------------|
| GET    | `/api/admin/stats`        | Dashboard analytics  |
| GET    | `/api/admin/users`        | All users by role    |
| PATCH  | `/api/admin/users/<id>/toggle` | Enable/disable   |
| GET    | `/api/admin/audit`        | Audit log            |

### Misc
| Method | Endpoint               | Description            |
|--------|------------------------|------------------------|
| POST   | `/api/upload/evidence` | Upload violation photo |
| GET    | `/api/health`          | Health check           |

---

## 🛡️ Security Features
- Session tokens (48-byte URL-safe random)
- Password hashing (SHA-256)
- Role-based access control on all endpoints
- HttpOnly cookie + header token support
- Session expiry (8 hours)
- Audit logging for all actions
- File upload validation

---

## 🗺️ Map Integration
- Uses **Leaflet.js** with **OpenStreetMap** / CartoDB tiles
- Officer GPS tracking (browser Geolocation API)
- Reverse geocoding via **Nominatim**
- SOS dispatch routing with Polyline overlays

---

## 🏗️ Tech Stack

| Layer    | Technology                     |
|----------|--------------------------------|
| Backend  | Python 3 + Flask               |
| Database | SQLite (via sqlite3 stdlib)     |
| Frontend | Vanilla HTML5 + CSS3 + JS (ES6)|
| Maps     | Leaflet.js + OpenStreetMap      |
| Charts   | Chart.js                        |
| Auth     | Custom token sessions           |

---

## 📝 Notes
- SQLite database is created automatically at first run
- All seed data (officers, citizens, violations) is inserted on first run
- Evidence uploads go to `static/uploads/`
- The app is designed for the TVM (Thiruvananthapuram) traffic enforcement context
- Coordinates default to Thiruvananthapuram, Kerala (8.5241°N, 76.9366°E)
