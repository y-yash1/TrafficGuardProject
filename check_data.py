#!/usr/bin/env python3
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "database"))
from schema import get_db

db = get_db()

# Check vehicle ownership
print("Checking vehicle ownership...\n")

vehicles = db.execute(
    """
    SELECT v.id, v.plate_number, c.id as citizen_id, u.username, u.full_name
    FROM vehicles v
    LEFT JOIN citizens c ON c.id = v.citizen_id
    LEFT JOIN users u ON u.id = c.user_id
    LIMIT 5
"""
).fetchall()

for v in vehicles:
    print(f"Vehicle: {v['plate_number']}")
    print(f"  Citizen ID: {v['citizen_id']}")
    print(f"  Username: {v['username']}")
    print(f"  Full Name: {v['full_name']}")
    print()

# Check violations for those vehicles
print("\nChecking violations...\n")

violations = db.execute(
    """
    SELECT v.id, v.challan_number, v.violation_type, v.evidence_path, veh.plate_number
    FROM violations v
    LEFT JOIN vehicles veh ON veh.id = v.vehicle_id
    LIMIT 5
"""
).fetchall()

for v in violations:
    print(f"Challan: {v['challan_number']}")
    print(f"  Violation: {v['violation_type']}")
    print(f"  Vehicle: {v['plate_number']}")
    print(f"  Evidence: {v['evidence_path']}")
    print()

db.close()
