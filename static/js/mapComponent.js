/**
 * Traffic Guard TVM — Map Component
 * Leaflet-based interactive map with satellite imagery only
 */

class TrafficGuardMap {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.map = null;
        this.markers = new Map();
        this.locationLabels = new Map();
        this.layers = {
            officers: L.featureGroup(),
            services: L.featureGroup(),
            violations: L.featureGroup(),
            labels: L.featureGroup()
        };
        
        // Default Hyderabad center
        this.defaultCenter = [17.3850, 78.4867];
        this.defaultZoom = options.zoom || 13;
        this.options = options;
        
        this.init();
    }
    
    init() {
        // Initialize map — satellite only, no layer switcher
        this.map = L.map(this.containerId, {
            zoomControl: true,
            attributionControl: false
        }).setView(this.defaultCenter, this.defaultZoom);
        
        // Google Hybrid — satellite imagery with all labels (roads, localities, landmarks)
        L.tileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', {
            maxZoom: 21,
            subdomains: ['mt0','mt1','mt2','mt3']
        }).addTo(this.map);
        
        // Add all layer groups to map
        this.layers.officers.addTo(this.map);
        this.layers.services.addTo(this.map);
        this.layers.violations.addTo(this.map);
        this.layers.labels.addTo(this.map);
    }
    
    setCenter(lat, lon, zoom = 15) {
        this.map.setView([lat, lon], zoom);
    }
    
    addOfficerMarker(officer) {
        const key = `officer-${officer.id}`;
        if (this.markers.has(key)) {
            this.layers.officers.removeLayer(this.markers.get(key));
        }
        
        const locationLabel = officer.location_name || officer.zone || '';
        const icon = L.divIcon({
            html: `<div class="officer-marker" title="${officer.full_name}">
                     👮
                     <div style="font-size:9px;font-weight:700;color:#fff;background:rgba(0,0,0,0.65);border-radius:4px;padding:1px 4px;margin-top:2px;white-space:nowrap;max-width:90px;overflow:hidden;text-overflow:ellipsis;">${officer.full_name.split(' ')[0]}</div>
                   </div>`,
            className: 'marker-officer',
            iconSize: [60, 46],
            popupAnchor: [0, -24]
        });
        
        const marker = L.marker([officer.latitude, officer.longitude], { icon })
            .bindPopup(`
                <div class="marker-popup">
                    <strong>${officer.full_name}</strong><br>
                    Badge: ${officer.badge_id}<br>
                    Rank: ${officer.rank}<br>
                    Zone: ${officer.zone}<br>
                    ${locationLabel ? `Location: <em>${locationLabel}</em><br>` : ''}
                    Status: <span class="status-${officer.status}">${officer.status.replace('_', ' ')}</span><br>
                    📞 ${officer.phone || 'N/A'}
                </div>
            `)
            .addTo(this.layers.officers);
        
        this.markers.set(key, marker);

        // Add location name label on map
        if (locationLabel) {
            this.addLocationLabel(officer.latitude, officer.longitude, locationLabel, `officer-${officer.id}`);
        }

        return marker;
    }
    
    addServiceMarker(service) {
        const key = `service-${service.id}`;
        if (this.markers.has(key)) {
            this.layers.services.removeLayer(this.markers.get(key));
        }
        
        const icons = {
            'hospital': '🏥',
            'fire_station': '🚒',
            'police_post': '🚔'
        };
        
        const labels = {
            'hospital': 'Hospital',
            'fire_station': 'Fire Station',
            'police_post': 'Police Post'
        };
        
        const icon = L.divIcon({
            html: `<div class="service-marker" title="${service.name}">${icons[service.service_type] || '📍'}</div>`,
            className: `marker-service marker-${service.service_type}`,
            iconSize: [32, 32],
            popupAnchor: [0, -16]
        });
        
        const marker = L.marker([service.latitude, service.longitude], { icon })
            .bindPopup(`
                <div class="marker-popup">
                    <strong>${service.name}</strong><br>
                    <em>${service.name_telugu || ''}</em><br>
                    <strong>Type:</strong> ${labels[service.service_type]}<br>
                    <strong>Address:</strong> ${service.address}<br>
                    📞 ${service.phone || 'N/A'}
                </div>
            `)
            .addTo(this.layers.services);
        
        this.markers.set(key, marker);

        // Add label for service
        this.addLocationLabel(service.latitude, service.longitude, service.name, `service-${service.id}`);

        return marker;
    }
    
    addViolationMarker(violation) {
        const key = `violation-${violation.id}`;
        if (this.markers.has(key)) {
            this.layers.violations.removeLayer(this.markers.get(key));
        }
        
        const statusColors = {
            'pending': '#FEF3C7',
            'paid': '#D1FAE5',
            'overdue': '#FEE2E2'
        };
        
        const icon = L.divIcon({
            html: `<div class="violation-marker" style="background-color: ${statusColors[violation.status] || '#F3F4F6'}" title="${violation.violation_type}">⚠️</div>`,
            className: 'marker-violation',
            iconSize: [32, 32],
            popupAnchor: [0, -16]
        });
        
        const marker = L.marker([violation.latitude || 17.3850, violation.longitude || 78.4867], { icon })
            .bindPopup(`
                <div class="marker-popup">
                    <strong>Challan: ${violation.challan_number}</strong><br>
                    <strong>Type:</strong> ${violation.violation_type}<br>
                    <strong>Plate:</strong> ${violation.plate_number}<br>
                    <strong>Fine:</strong> ₹${violation.fine_amount}<br>
                    <strong>Status:</strong> ${violation.status}<br>
                    <strong>Location:</strong> ${violation.location}
                </div>
            `)
            .addTo(this.layers.violations);
        
        this.markers.set(key, marker);
        return marker;
    }
    
    addCurrentLocationMarker(lat, lon) {
        const key = 'current-location';
        if (this.markers.has(key)) {
            this.layers.violations.removeLayer(this.markers.get(key));
        }
        
        const marker = L.circleMarker([lat, lon], {
            radius: 10,
            color: '#007BFF',
            weight: 3,
            opacity: 1,
            fillColor: '#007BFF',
            fillOpacity: 0.3
        })
            .bindPopup('Your Current Location')
            .addTo(this.layers.violations);
        
        this.markers.set(key, marker);
        return marker;
    }

    /**
     * Add a named location label on the map
     */
    addLocationLabel(lat, lng, name, uniqueId = null) {
        const labelKey = uniqueId ? `lbl-${uniqueId}` : `lbl-${lat}-${lng}`;

        // Remove existing label if present
        if (this.locationLabels.has(labelKey)) {
            this.layers.labels.removeLayer(this.locationLabels.get(labelKey));
        }

        const label = L.marker([lat, lng], {
            icon: L.divIcon({
                html: `<div style="
                    background: rgba(255,255,255,0.92);
                    padding: 4px 8px;
                    border-radius: 6px;
                    border: 1.5px solid #0288D1;
                    font-size: 11px;
                    font-weight: 700;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.2);
                    white-space: nowrap;
                    color: #1C1C1E;
                    max-width: 160px;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    pointer-events: none;
                ">${name}</div>`,
                iconSize: [160, 28],
                iconAnchor: [80, -6],
                className: 'location-label-icon'
            }),
            interactive: false
        });

        label.addTo(this.layers.labels);
        this.locationLabels.set(labelKey, label);
        return label;
    }
    
    clearMarkers() {
        this.layers.officers.clearLayers();
        this.layers.services.clearLayers();
        this.layers.violations.clearLayers();
        this.layers.labels.clearLayers();
        this.markers.clear();
        this.locationLabels.clear();
    }
    
    fitBounds(latLngs) {
        if (latLngs.length > 0) {
            const group = new L.featureGroup(latLngs);
            this.map.fitBounds(group.getBounds().pad(0.1));
        }
    }
    
    getCenter() {
        const center = this.map.getCenter();
        return { latitude: center.lat, longitude: center.lng };
    }
}

// Export for use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TrafficGuardMap;
}
