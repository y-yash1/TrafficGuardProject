#!/usr/bin/env python3
import sys
import os
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "database"))
from schema import get_db
from datetime import datetime, timedelta

# Create a simple test PNG image (1x1 pixel) in uploads folder
UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Minimal PNG header for a 1x1 transparent pixel
png_data = bytes(
    [
        0x89,
        0x50,
        0x4E,
        0x47,
        0x0D,
        0x0A,
        0x1A,
        0x0A,  # PNG signature
        0x00,
        0x00,
        0x00,
        0x0D,
        0x49,
        0x48,
        0x44,
        0x52,  # IHDR chunk
        0x00,
        0x00,
        0x00,
        0x01,
        0x00,
        0x00,
        0x00,
        0x01,  # 1x1 dimensions
        0x08,
        0x06,
        0x00,
        0x00,
        0x00,
        0x1F,
        0x15,
        0xC4,  # bit depth, color type
        0x89,
        0x00,
        0x00,
        0x00,
        0x0A,
        0x49,
        0x44,
        0x41,  # IDAT chunk
        0x54,
        0x78,
        0x9C,
        0x63,
        0xF8,
        0xCF,
        0xC0,
        0x00,  # compressed data
        0x00,
        0x00,
        0x03,
        0x00,
        0x01,
        0x6D,
        0x5D,
        0xD6,  # more data
        0xDD,
        0x00,
        0x00,
        0x00,
        0x00,
        0x49,
        0x45,
        0x4E,  # IEND chunk
        0x44,
        0xAE,
        0x42,
        0x60,  # PNG end
    ]
)

# Save test image
test_image_path = os.path.join(UPLOAD_FOLDER, "test_evidence_sample.png")
with open(test_image_path, "wb") as f:
    f.write(png_data)

print(f"✅ Created test image: {test_image_path}")

# Update one existing violation with evidence path
db = get_db()

# Get vehicle_id and officer_id for the first violation
violation = db.execute(
    "SELECT id, vehicle_id, officer_id FROM violations LIMIT 1"
).fetchone()

if violation:
    violation_id = violation["id"]
    print(f"\n✅ Updating violation ID {violation_id} with evidence...")

    db.execute(
        "UPDATE violations SET evidence_path = ? WHERE id = ?",
        ("/static/uploads/test_evidence_sample.png", violation_id),
    )
    db.commit()

    # Verify update
    updated = db.execute(
        "SELECT id, challan_number, violation_type, evidence_path FROM violations WHERE id = ?",
        (violation_id,),
    ).fetchone()

    print(f"  Challan: {updated['challan_number']}")
    print(f"  Type: {updated['violation_type']}")
    print(f"  Evidence: {updated['evidence_path']}")
    print(
        f"\n✅ Test violation created! Citizens should now see the 'View Evidence' button."
    )
else:
    print("❌ No violations found to update")

db.close()
