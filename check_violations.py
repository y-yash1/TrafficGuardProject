#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "database"))
from schema import get_db

db = get_db()

# Check if there are any violations
violations = db.execute(
    "SELECT id, challan_number, violation_type, plate_number, evidence_path FROM violations ORDER BY issued_at DESC LIMIT 5"
).fetchall()

if not violations:
    print("❌ No violations found in database")
else:
    print(f"✅ Found {len(violations)} violations:\n")
    for v in violations:
        print(f"  ID: {v['id']}")
        print(f"  Challan: {v['challan_number']}")
        print(f"  Type: {v['violation_type']}")
        print(f"  Plate: {v['plate_number']}")
        print(f"  Evidence Path: {v['evidence_path']}")
        print(f"  Has Evidence: {'✅ YES' if v['evidence_path'] else '❌ NO'}")
        print()

db.close()
