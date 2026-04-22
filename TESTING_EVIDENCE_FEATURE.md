# 🧪 Testing the Evidence Feature

## Quick Test Guide

### Test Credentials
- **Username**: citizen1
- **Password**: 1234

### Test Vehicle
- **Plate**: KA01AB1234
- **Owner**: Rahul Sharma (citizen1)

### Test Violation with Evidence
- **Challan**: EC2024001
- **Type**: Signal Jumping
- **Vehicle**: KA01AB1234
- **Evidence**: ✅ YES - Has test image attached

---

## How to Test

### Step 1: Start the Application
```bash
cd c:\realtime2\po_project_modified
python app.py
```

Navigate to: `http://localhost:5000`

### Step 2: Login as Citizen
1. Click "Citizen Login" or go to `/loginpage.html`
2. Email: `citizen1@example.com`
3. Password: `1234`
4. Click "Sign In"

### Step 3: View Evidence on Overview Page
1. You'll see "Action Required" section
2. Find the **"Signal Jumping"** violation (EC2024001)
3. Look for the **"📸 View Evidence"** button
4. Click it to see the test image

### Step 4: View Evidence on E-Challans Page
1. Click "My E-Challans" in navigation
2. Find **EC2024001** in the list
3. Click **"📸 View Evidence"** button
4. Modal should open with the test image and metadata

---

## Expected Behavior

### Button Should Appear When:
✅ Violation has `evidence_path` populated in database
✅ Citizen owns the vehicle with the violation
✅ Violation status is any status (pending, paid, overdue, etc.)

### Modal Should Show:
✅ Professional header with description
✅ Large image display
✅ Metadata grid showing:
   - 📋 Violation Type: "Signal Jumping"
   - 🚗 Vehicle Plate: "KA01AB1234"
✅ Close button (✕)
✅ Gradient background

### Fallback Should Work:
- Click "↗ Open File in New Tab" for non-image files
- Gets redirected to `/static/uploads/[filename]`

---

## Troubleshooting

### Button doesn't show?
1. ✅ Make sure you're logged in as **citizen1**
2. ✅ Check you're viewing violation **EC2024001**
3. ✅ Verify database has evidence_path set:
   ```bash
   python -c "import sys, os; sys.path.insert(0, 'database'); from schema import get_db; db = get_db(); v = db.execute('SELECT evidence_path FROM violations WHERE id = 1').fetchone(); print(v[0]); db.close()"
   ```

### Image doesn't load?
1. Check browser console (F12) for errors
2. Verify file exists at `/static/uploads/test_evidence_sample.png`
3. Check network tab to see if 404 error

### Modal doesn't open?
1. Check browser console for JavaScript errors
2. Verify `viewEvidence()` function is defined
3. Check if there's a modal element with id "evidenceModal"

---

## Database Query to Check Evidence

```sql
SELECT id, challan_number, violation_type, evidence_path 
FROM violations 
WHERE evidence_path IS NOT NULL;
```

Should return:
```
ID: 1
Challan: EC2024001
Type: Signal Jumping
Evidence: /static/uploads/test_evidence_sample.png
```

---

## Adding More Test Evidence

To add evidence to another violation:
```bash
python -c "
import sys, os
sys.path.insert(0, 'database')
from schema import get_db
db = get_db()
db.execute('UPDATE violations SET evidence_path = ? WHERE id = ?', 
           ('/static/uploads/test_evidence_sample.png', 2))
db.commit()
db.close()
print('Updated violation ID 2 with evidence')
"
```

---

## Real Usage Flow (for production)

1. **Officer** captures photo while issuing violation
2. Photo is uploaded to `/api/upload/evidence`
3. Upload returns path: `/static/uploads/[random_hash].jpg`
4. Officer creates violation with evidence_path included
5. Citizen logs in and views their violations
6. **"📸 View Evidence"** button appears automatically
7. Citizen clicks to view officer-captured photo

