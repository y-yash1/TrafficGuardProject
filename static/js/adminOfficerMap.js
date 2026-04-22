/**
 * Traffic Guard TVM — Admin Officer Tracking Map
 * Shows all officers on satellite map with real-time location updates
 */

class AdminOfficerMap {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.map = null;
        this.officerMarkers = new Map();
        this.locationLabels = new Map();
        this.officerLayer = L.featureGroup();
        this.labelLayer = L.featureGroup();
        this.defaultCenter = [17.3850, 78.4867];
        this.defaultZoom = options.zoom || 12;
        this.init();
    }
    
    init() {
        // Initialize map with satellite view only
        this.map = L.map(this.containerId, {
            attributionControl: false,
            zoomControl: true
        }).setView(this.defaultCenter, this.defaultZoom);
        
        // Google Hybrid — satellite imagery with all labels (roads, localities, landmarks)
        L.tileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', {
            maxZoom: 21,
            subdomains: ['mt0','mt1','mt2','mt3']
        }).addTo(this.map);
        
        // Add officer and label layers
        this.officerLayer.addTo(this.map);
        this.labelLayer.addTo(this.map);
    }
    
    /**
     * Add or update officer marker on map
     */
    addOfficerMarker(officer) {
        const key = `officer-${officer.id}`;
        
        // Remove existing marker if present
        if (this.officerMarkers.has(key)) {
            this.officerLayer.removeLayer(this.officerMarkers.get(key));
        }
        
        // Determine icon color based on status
        const statusColors = {
            'on_duty': '#22C55E',
            'off_duty': '#EF4444',
            'on_break': '#F59E0B',
            'emergency': '#FF1744'
        };
        
        const statusEmojis = {
            'on_duty': '👮',
            'off_duty': '🚫',
            'on_break': '☕',
            'emergency': '🚨'
        };
        
        const color = statusColors[officer.status] || '#007BFF';
        const emoji = statusEmojis[officer.status] || '👮';
        
        // Create custom icon
        const icon = L.divIcon({
            html: `
                <div style="
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    width: 48px;
                    height: 48px;
                    background: ${color};
                    border-radius: 50%;
                    border: 3px solid white;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                    font-size: 24px;
                    cursor: pointer;
                    transition: all 0.2s;
                ">
                    ${emoji}
                </div>
            `,
            iconSize: [48, 48],
            popupAnchor: [0, -24]
        });
        
        // Create marker
        const marker = L.marker(
            [officer.latitude, officer.longitude],
            { icon: icon }
        );
        
        // Add popup with officer details
        marker.bindPopup(`
            <div style="font-size: 14px; width: 200px;">
                <div style="font-weight: 700; margin-bottom: 8px; color: #1C1C1E;">
                    ${emoji} ${officer.name}
                </div>
                <div style="font-size: 12px; color: #6B7280;">
                    <div><strong>Badge ID:</strong> ${officer.badge_id || '—'}</div>
                    <div><strong>Status:</strong> <span style="color: ${color}; font-weight: 600;">${officer.status.toUpperCase().replace('_', ' ')}</span></div>
                    <div><strong>Location:</strong> ${officer.location_name || '—'}</div>
                    <div><strong>Coordinates:</strong> ${officer.latitude.toFixed(4)}, ${officer.longitude.toFixed(4)}</div>
                    <div><strong>Last Update:</strong> ${new Date(officer.last_update || new Date()).toLocaleTimeString()}</div>
                </div>
            </div>
        `);
        
        // Add click event to highlight officer
        marker.on('click', () => {
            this.map.flyTo([officer.latitude, officer.longitude], 16);
            if (window.highlightOfficer) window.highlightOfficer(officer.id);
        });
        
        marker.addTo(this.officerLayer);
        this.officerMarkers.set(key, marker);
        
        // Add location name label if available
        if (officer.location_name) {
            this.addLocationLabel(officer.latitude, officer.longitude, officer.location_name, officer.id);
        }
    }
    
    /**
     * Remove officer marker
     */
    removeOfficerMarker(officerId) {
        const key = `officer-${officerId}`;
        if (this.officerMarkers.has(key)) {
            this.officerLayer.removeLayer(this.officerMarkers.get(key));
            this.officerMarkers.delete(key);
        }
        const labelKey = `label-${officerId}`;
        if (this.locationLabels.has(labelKey)) {
            this.labelLayer.removeLayer(this.locationLabels.get(labelKey));
            this.locationLabels.delete(labelKey);
        }
    }
    
    /**
     * Update officer location (for real-time tracking)
     */
    updateOfficerLocation(officerId, latitude, longitude, locationName, status) {
        this.removeOfficerMarker(officerId);
        this.addOfficerMarker({
            id: officerId,
            name: document.querySelector(`[data-officer-id="${officerId}"]`)?.textContent || `Officer ${officerId}`,
            latitude: latitude,
            longitude: longitude,
            location_name: locationName,
            status: status || 'on_duty',
            badge_id: document.querySelector(`[data-badge-id="${officerId}"]`)?.textContent || '',
            last_update: new Date().toISOString()
        });
    }
    
    /**
     * Fit map to show all officers
     */
    fitAllOfficers() {
        if (this.officerMarkers.size === 0) return;
        
        const bounds = L.latLngBounds();
        this.officerMarkers.forEach(marker => {
            bounds.extend(marker.getLatLng());
        });
        
        this.map.fitBounds(bounds, { padding: [50, 50] });
    }
    
    /**
     * Set map center
     */
    setCenter(lat, lng, zoom = 14) {
        this.map.setView([lat, lng], zoom);
    }
    
    /**
     * Add location name label on map
     */
    addLocationLabel(lat, lng, name, uniqueId = null) {
        const labelKey = uniqueId ? `label-${uniqueId}` : `label-${lat}-${lng}`;
        
        // Remove existing label if present
        if (this.locationLabels.has(labelKey)) {
            this.labelLayer.removeLayer(this.locationLabels.get(labelKey));
        }
        
        const label = L.marker([lat, lng], {
            icon: L.divIcon({
                html: `<div style="
                    background: rgba(255, 255, 255, 0.95);
                    padding: 6px 10px;
                    border-radius: 8px;
                    border: 2px solid #0288D1;
                    font-size: 12px;
                    font-weight: 700;
                    box-shadow: 0 3px 10px rgba(0,0,0,0.25);
                    white-space: nowrap;
                    color: #1C1C1E;
                    max-width: 180px;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    pointer-events: none;
                ">${name}</div>`,
                iconSize: [180, 36],
                iconAnchor: [90, -8],
                className: 'location-label-icon'
            })
        });
        
        label.addTo(this.labelLayer);
        this.locationLabels.set(labelKey, label);
    }
    
    /**
     * Draw zone boundary (polygon)
     */
    addZoneBoundary(coordinates, zoneName, color = '#007BFF') {
        const polygon = L.polygon(coordinates, {
            color: color,
            weight: 2,
            opacity: 0.7,
            fillColor: color,
            fillOpacity: 0.1
        }).addTo(this.map);
        
        polygon.bindPopup(`<strong>${zoneName}</strong>`);
        return polygon;
    }
    
    /**
     * Clear all markers and labels
     */
    clear() {
        this.officerMarkers.forEach((marker) => {
            this.officerLayer.removeLayer(marker);
        });
        this.officerMarkers.clear();
        
        this.locationLabels.forEach((label) => {
            this.labelLayer.removeLayer(label);
        });
        this.locationLabels.clear();
    }
}
