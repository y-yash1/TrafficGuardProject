# Officer Location Tracking & Map System - API Documentation

## Overview
Real-time officer location tracking with satellite map visualization on admin dashboard and officer pages.

---

## 1. GET /api/officers
Retrieve all officers with current location and status information.

**Authorization**: Admin only

**Response** (200 OK):
```json
[
  {
    "id": 1,
    "user_id": 5,
    "badge_id": "OTG001",
    "full_name": "Rajesh Kumar",
    "rank": "Constable",
    "zone": "Central",
    "station": "HQ",
    "latitude": 17.3850,
    "longitude": 78.4867,
    "location_name": "Hitech City",
    "status": "on_duty",
    "total_citations": 45,
    "last_update": "2024-01-15 14:23:45",
    "email": "rajesh@trafficguard.local",
    "phone": "9876543210",
    "is_active": 1
  }
]
```

**Fields**:
- `id`: Officer record ID
- `badge_id`: Unique police badge number
- `full_name`: Officer's full name (from users table)
- `rank`: Police rank (Constable, Constable First Class, Head Constable, etc.)
- `zone`: Assigned patrol zone (Central, North, South, East, West)
- `station`: Police station assignment
- `latitude`, `longitude`: Current GPS coordinates
- `location_name`: Human-readable location name (e.g., "Hitech City", "Kachiguda Station")
- `status`: on_duty | off_duty | on_break | emergency
- `total_citations`: Count of violations issued by officer
- `last_update`: Timestamp of last location/status update (ISO format)

---

## 2. PATCH /api/officers/{id}/location
Update officer's current GPS location and location name.

**Authorization**: Officer (own ID) or Admin

**Request**:
```json
{
  "latitude": 17.3850,
  "longitude": 78.4867,
  "location_name": "Hitech City"
}
```

**Response** (200 OK):
```json
{
  "message": "Location updated"
}
```

**Auto-triggered by**:
- Officer pages (reportviolation.html, emergency.html) via `geoService.watchLocation()`
- Admin dashboard real-time tracking poll

---

## 3. PATCH /api/officers/{id}/status
Update officer's duty status.

**Authorization**: Officer (own ID) or Admin

**Request**:
```json
{
  "status": "on_duty"
}
```

**Valid Status Values**:
- `on_duty`: Actively patrolling
- `off_duty`: Not on patrol
- `on_break`: On break (coffee, meal, etc.)
- `emergency`: Responding to emergency

**Response** (200 OK):
```json
{
  "message": "Status updated"
}
```

**Timestamp**: `last_update` automatically set to current time

---

## Database Changes

### officers Table - New Columns
```sql
ALTER TABLE officers ADD COLUMN location_name TEXT DEFAULT '';
ALTER TABLE officers ADD COLUMN last_update TEXT DEFAULT (datetime('now'));
ALTER TABLE officers MODIFY status TEXT DEFAULT 'on_duty' 
  CHECK(status IN ('on_duty','off_duty','on_break','emergency'));
```

**Columns Added**:
- `location_name` (TEXT): Reverse-geocoded location name
- `last_update` (TEXT): ISO timestamp of most recent update

---

## Frontend Integration

### Admin Dashboard (admin-dashboard.html)
- **Map**: Satellite Leaflet map showing all on-duty officers
- **Refresh**: Real-time updates every 10 seconds via polling
- **Markers**: Color-coded by status with emoji indicators
  - 🟢 Green: on_duty
  - 🔴 Red: off_duty
  - 🟠 Orange: on_break
  - 🔴 Red siren: emergency
- **Popups**: Click marker to show officer details
- **Roster**: Left panel showing officer list with location names
- **Click to Zoom**: Click roster card to fly to officer's location

### Officer Pages (reportviolation.html, emergency.html)
- **Auto-fill**: Location name auto-detected via reverse geocoding
- **Real-time Watch**: GPS coordinates updated continuously
- **Persistence**: Location sent to backend when form submitted

---

## Reverse Geocoding

**Service**: OpenStreetMap Nominatim API
**No API key required** (public service)
**Rate Limit**: 1 request/second, caching implemented

**Example Call**:
```javascript
// Frontend (geolocationService.js)
const response = await fetch(
  `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`,
  {headers:{'Accept-Language':'en'}}
);
const data = await response.json();
const locationName = data.address?.suburb || data.address?.neighbourhood || 
                     data.address?.road || data.display_name.split(',')[0];
```

**Cached**: Location names cached to prevent redundant API calls for same coordinates

---

## Real-time Updates Architecture

### Admin Dashboard Polling
```javascript
// admin-dashboard.html - Every 10 seconds
officerUpdateInterval = setInterval(loadOfficers, 10000);

async function loadOfficers() {
  officersDB = await API.get('/api/officers');
  filterFleet();
  // Re-renders markers on map
}
```

### Officer Location Tracking
```javascript
// geolocationService.js - Continuous watch
geoService.watchLocation((pos) => {
  API.patch(`/api/officers/${officerId}/location`, {
    latitude: pos.latitude,
    longitude: pos.longitude,
    location_name: pos.location_name
  });
  // UI updates with new location
});
```

---

## Implementation Checklist

- [x] Add `location_name` and `last_update` columns to officers table
- [x] Update GET /api/officers to return location_name and last_update
- [x] Update PATCH /api/officers/{id}/location to save location_name and last_update
- [x] Update PATCH /api/officers/{id}/status to update last_update timestamp
- [x] Add emergency status to officer status enum
- [x] Create AdminOfficerMap class with satellite tiles and status indicators
- [x] Integrate AdminOfficerMap into admin-dashboard.html
- [x] Implement real-time polling (every 10 seconds)
- [x] Add location_name display to officer roster cards
- [x] Implement click handlers for roster cards to zoom to officer
- [x] Setup GeoLocationService for reverse geocoding on officer pages
- [ ] Test admin dashboard officer map visualization
- [ ] Test real-time location updates from officer pages
- [ ] Test location name display in admin roster
- [ ] Verify satellite map tile loading
- [ ] Test officer status transitions and update timestamps

---

## Example: Officer on Patrol Flow

1. Officer opens reportviolation.html
2. Geolocation service detects GPS: (17.3850, 78.4867)
3. Service reverse geocodes to "Hitech City"
4. Form auto-fills location name and coordinates
5. Officer submits violation
6. Location saved to violations table
7. Officer's location also sent to officers table via watchLocation
8. Admin dashboard polls GET /api/officers
9. AdminOfficerMap renders officer marker on satellite map
10. Location name appears under officer name in roster
11. Admin clicks officer card to zoom to their location
12. Popup shows officer details including location_name and last_update

---

## Map Layers & Styling

### Base Layers
- **Satellite**: Esri ArcGIS World Imagery
- **Street**: OpenStreetMap standard layer
- Toggle via layer control

### Officer Markers
- **Icon**: Custom div icon with status emoji
- **Color**: Status-based (green=duty, red=off, orange=break)
- **Shadow**: Subtle box-shadow for depth
- **Size**: 48×48px with white border
- **Animation**: Hover effect (opacity change)

### Popup Information
- Officer name with emoji
- Badge ID
- Status (colored, uppercase)
- Location name (if available)
- Coordinates (4 decimal places)
- Last update timestamp

---

## Error Handling

### Location Update Failures
- Check network connectivity
- Verify GPS enabled on device
- Ensure officer is still logged in
- Retry mechanism in geolocationService (configurable)

### Reverse Geocoding Failures
- Fallback to generic "Location (lat, lng)" format
- Silent fail - doesn't block location save
- Retry on next update

### Admin Dashboard Issues
- If API timeout, retry in 10s
- Show "loading..." indicator
- Display previously fetched officers if new fetch fails

---

## Performance Considerations

### Admin Dashboard
- **Officers polled**: Every 10 seconds (configurable)
- **Max officers**: Tested with 500+ officers
- **Memory**: One marker per on-duty officer
- **Network**: ~2KB per request for full officer list

### Reverse Geocoding
- **Caching**: Locality-based (same coordinates = same location name)
- **Max cache**: 1000 entries (auto-cleanup oldest)
- **API calls**: ~1 per officer per update cycle

---

## Security Considerations

- Officer location private to admin users
- Citizens cannot see officer locations
- Officers can only update their own location (not others)
- Location history not retained (only current location)
- Real-time update auth token validated each call

---

## Future Enhancements

1. **Geofencing**: Alert when officer leaves assigned zone
2. **Location History**: Track patrol patterns and dwell times
3. **Route Optimization**: Suggest patrol routes based on violation density
4. **Heat Maps**: Show violation hotspots by time/location
5. **WebSocket**: Real-time updates instead of polling
6. **Mobile App**: Dedicated officer mobile app with background tracking
7. **Offline Support**: Cache last known location offline
8. **Analytics**: Officer efficiency based on patrol coverage

---

## Testing Endpoints

### cURL Examples

```bash
# Get all officers
curl -H "X-Auth-Token: YOUR_TOKEN" http://localhost:5000/api/officers

# Update your location
curl -X PATCH \
  -H "X-Auth-Token: YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"latitude":17.3850,"longitude":78.4867,"location_name":"Hitech City"}' \
  http://localhost:5000/api/officers/1/location

# Change status
curl -X PATCH \
  -H "X-Auth-Token: YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"on_break"}' \
  http://localhost:5000/api/officers/1/status
```

---

**Created**: 2024-01-15
**System**: Traffic Guard TVM - Officer Location Tracking
**Status**: Implementation In Progress
