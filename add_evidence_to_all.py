#!/usr/bin/env python3
"""Add evidence to test violations for all citizens"""
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "database"))
from schema import get_db

db = get_db()

# Get all violations without evidence
violations = db.execute(
    """
    SELECT v.id, v.challan_number, v.violation_type, 
           veh.plate_number, u.username
    FROM violations v
    LEFT JOIN vehicles veh ON veh.id = v.vehicle_id
    LEFT JOIN citizens c ON c.id = veh.citizen_id
    LEFT JOIN users u ON u.id = c.user_id
    WHERE v.evidence_path IS NULL AND veh.citizen_id IS NOT NULL
    ORDER BY v.id
    LIMIT 5
"""
).fetchall()

print("=" * 70)
print("ADDING EVIDENCE TO VIOLATIONS")
print("=" * 70)

# Add evidence to these violations
for vio in violations:
    db.execute(
        "UPDATE violations SET evidence_path = ? WHERE id = ?",
        ("/static/uploads/test_evidence_sample.png", vio["id"]),
    )
    print(f"\n✅ Added evidence to violation ID {vio['id']}")
    print(f"   Challan: {vio['challan_number']}")
    print(f"   Type: {vio['violation_type']}")
    print(f"   Vehicle: {vio['plate_number']}")
    print(f"   Citizen: {vio['username']}")

db.commit()
db.close()

print("\n" + "=" * 70)
print("✅ DONE! Evidence added to violations.")
print("=" * 70)
print("\nNow when citizens log in, they will see 'View Evidence' buttons")
print("for their violations.\n")
