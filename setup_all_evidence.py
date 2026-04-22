#!/usr/bin/env python3
"""Add evidence to remaining violations for testing"""
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "database"))
from schema import get_db

db = get_db()

# Update all violations without evidence to have the test evidence
result = db.execute(
    """
    UPDATE violations 
    SET evidence_path = '/static/uploads/test_evidence_sample.png'
    WHERE evidence_path IS NULL OR evidence_path = ''
"""
)

db.commit()

affected_rows = result.rowcount

print("=" * 70)
print("✅ EVIDENCE ADDED TO ALL VIOLATIONS")
print("=" * 70)
print(f"\nUpdated {affected_rows} violations with evidence path")
print("\nAll citizens can now test the evidence viewing feature!")
print("\nCitizens with violations ready to test:")
print("-" * 70)

citizens = db.execute(
    """
    SELECT DISTINCT u.full_name, u.email, COUNT(v.id) as violation_count
    FROM users u
    JOIN citizens c ON c.user_id = u.id
    LEFT JOIN vehicles veh ON veh.citizen_id = c.id
    LEFT JOIN violations v ON v.vehicle_id = veh.id
    WHERE v.id IS NOT NULL
    GROUP BY u.id
    ORDER BY u.full_name
"""
).fetchall()

for i, c in enumerate(citizens, 1):
    print(f"\n{i}. {c['full_name']}")
    print(f"   Email: {c['email']}")
    print(f"   Violations with evidence: {c['violation_count']}")

db.close()

print("\n" + "=" * 70)
print("READY TO TEST!")
print("=" * 70)
print(
    """
Each citizen can now:
1. Login to the system
2. Go to 'My E-Challans' page
3. See their violations with '📸 View Evidence' buttons
4. Click to see the evidence photos in a modal

For NEW violations created by officers moving forward:
- Officers upload evidence photos when creating violations
- Evidence automatically saves to database
- Citizens automatically see the 'View Evidence' button
"""
)
