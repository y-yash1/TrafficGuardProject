#!/usr/bin/env python3
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "database"))
from schema import get_db

db = get_db()

print("=" * 70)
print("CITIZENS IN DATABASE")
print("=" * 70)
citizens = db.execute(
    """
    SELECT u.id, u.username, u.email, u.full_name, COUNT(v.id) as vehicle_count
    FROM users u
    LEFT JOIN citizens c ON c.user_id = u.id
    LEFT JOIN vehicles v ON v.citizen_id = c.id
    WHERE u.role = 'citizen'
    GROUP BY u.id
    ORDER BY u.id
"""
).fetchall()

for c in citizens:
    print(f"\nCitizen ID: {c['id']}")
    print(f"  Username: {c['username']}")
    print(f"  Email: {c['email']}")
    print(f"  Name: {c['full_name']}")
    print(f"  Vehicles: {c['vehicle_count']}")

print("\n" + "=" * 70)
print("VEHICLES & THEIR VIOLATIONS")
print("=" * 70)

vehicles = db.execute(
    """
    SELECT v.id, v.plate_number, u.username, u.full_name, COUNT(vio.id) as violation_count
    FROM vehicles v
    LEFT JOIN citizens c ON c.id = v.citizen_id
    LEFT JOIN users u ON u.id = c.user_id
    LEFT JOIN violations vio ON vio.vehicle_id = v.id
    GROUP BY v.id
    ORDER BY v.plate_number
"""
).fetchall()

for v in vehicles:
    print(f"\nVehicle: {v['plate_number']}")
    print(f"  Owner: {v['full_name']} ({v['username']})")
    print(f"  Violations: {v['violation_count']}")

print("\n" + "=" * 70)
print("VIOLATIONS WITH/WITHOUT EVIDENCE")
print("=" * 70)

violations = db.execute(
    """
    SELECT v.id, v.challan_number, v.violation_type, v.evidence_path,
           veh.plate_number, u.username, u.full_name
    FROM violations v
    LEFT JOIN vehicles veh ON veh.id = v.vehicle_id
    LEFT JOIN citizens c ON c.id = veh.citizen_id
    LEFT JOIN users u ON u.id = c.user_id
    ORDER BY v.id DESC
    LIMIT 15
"""
).fetchall()

print(f"\nTotal violations shown: {len(violations)}\n")
for vio in violations:
    has_evidence = "✅" if vio["evidence_path"] else "❌"
    print(f"{has_evidence} Challan: {vio['challan_number']}")
    print(f"   Violation: {vio['violation_type']}")
    print(f"   Vehicle: {vio['plate_number']}")
    print(f"   Citizen: {vio['full_name']} ({vio['username']})")
    print(f"   Evidence: {vio['evidence_path']}")
    print()

db.close()
