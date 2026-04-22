/**
 * Traffic Guard TVM — Enhanced Geolocation Service
 * GPS detection + Reverse geocoding with accurate location names
 */

class GeoLocationService {
    constructor() {
        this.currentPosition = null;
        this.locationCache = {};
        this.watcherId = null;
    }
    
    /**
     * Get current device location with name
     */
    async getCurrentLocation() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Geolocation not supported'));
                return;
            }
            
            navigator.geolocation.getCurrentPosition(
                async (position) => {
                    const lat = position.coords.latitude;
                    const lon = position.coords.longitude;
                    
                    this.currentPosition = {
                        latitude: lat,
                        longitude: lon,
                        accuracy: position.coords.accuracy,
                        timestamp: new Date()
                    };
                    
                    // Get location name via reverse geocoding
                    try {
                        const locationName = await this.reverseGeocode(lat, lon);
                        this.currentPosition.location_name = locationName;
                    } catch(err) {
                        this.currentPosition.location_name = `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
                    }
                    
                    resolve(this.currentPosition);
                },
                (error) => {
                    reject(new Error(`GPS Error: ${error.message}`));
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 0
                }
            );
        });
    }
    
    /**
     * Reverse geocode coordinates to get accurate location name
     * Uses OpenStreetMap Nominatim API with high zoom for precision
     */
    async reverseGeocode(lat, lon) {
        const cacheKey = `${lat.toFixed(5)},${lon.toFixed(5)}`;
        
        // Check cache first
        if (this.locationCache[cacheKey]) {
            return this.locationCache[cacheKey];
        }
        
        try {
            const response = await fetch(
                `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&zoom=18&addressdetails=1`,
                { headers: { 'Accept': 'application/json', 'Accept-Language': 'en' } }
            );
            
            if (!response.ok) throw new Error('Geocoding failed');
            
            const data = await response.json();
            const a = data.address || {};
            
            // Build the most accurate, human-readable location name
            // Priority: specific place > road+area > neighbourhood > suburb > town/city
            let parts = [];
            
            // 1. Specific named place (building, amenity, shop etc.)
            const placeName = a.amenity || a.building || a.shop || a.tourism || a.leisure || a.office || '';
            if (placeName) parts.push(placeName);
            
            // 2. Road / street name (most important for accuracy)
            if (a.road) parts.push(a.road);
            
            // 3. Area context — neighbourhood, suburb, or locality
            const area = a.neighbourhood || a.residential || a.hamlet || '';
            const suburb = a.suburb || a.quarter || a.city_district || '';
            
            if (area && !parts.includes(area)) parts.push(area);
            else if (suburb && !parts.includes(suburb)) parts.push(suburb);
            
            // 4. If we still have nothing, try village/town/city
            if (parts.length === 0) {
                if (a.village) parts.push(a.village);
                else if (a.town) parts.push(a.town);
                else if (a.city) parts.push(a.city);
            }
            
            // 5. Append city/town if not already there and we have a road
            if (parts.length > 0 && parts.length <= 2) {
                const city = a.city || a.town || a.county || '';
                if (city && !parts.includes(city)) {
                    parts.push(city);
                }
            }
            
            // Assemble final name, limit to 3 parts for readability
            let locationName = parts.slice(0, 3).join(', ');
            
            // Ultimate fallback
            if (!locationName) {
                locationName = data.display_name 
                    ? data.display_name.split(',').slice(0, 3).join(',').trim()
                    : `Location (${lat.toFixed(4)}, ${lon.toFixed(4)})`;
            }
            
            // Cache it
            this.locationCache[cacheKey] = locationName;
            return locationName;
            
        } catch(err) {
            console.warn('Reverse geocoding failed:', err);
            return `Location (${lat.toFixed(4)}, ${lon.toFixed(4)})`;
        }
    }
    
    /**
     * Get location name for given coordinates (standalone call)
     */
    async getLocationName(lat, lon) {
        return await this.reverseGeocode(lat, lon);
    }
    
    /**
     * Watch continuous location updates
     */
    watchLocation(callback, onError = null) {
        if (!navigator.geolocation) {
            if (onError) onError('Geolocation not supported');
            return;
        }
        
        this.watcherId = navigator.geolocation.watchPosition(
            async (position) => {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                
                try {
                    const locationName = await this.reverseGeocode(lat, lon);
                    callback({
                        latitude: lat,
                        longitude: lon,
                        location_name: locationName,
                        accuracy: position.coords.accuracy,
                        timestamp: new Date()
                    });
                } catch(err) {
                    callback({
                        latitude: lat,
                        longitude: lon,
                        location_name: `${lat.toFixed(4)}, ${lon.toFixed(4)}`,
                        accuracy: position.coords.accuracy,
                        timestamp: new Date()
                    });
                }
            },
            (error) => {
                if (onError) onError(`Watch error: ${error.message}`);
            },
            {
                enableHighAccuracy: true,
                timeout: 5000,
                maximumAge: 1000
            }
        );
    }
    
    /**
     * Stop watching location
     */
    stopWatchingLocation() {
        if (this.watcherId !== null) {
            navigator.geolocation.clearWatch(this.watcherId);
            this.watcherId = null;
        }
    }
    
    /**
     * Get current position (if available)
     */
    getPosition() {
        return this.currentPosition;
    }
}

// Initialize global instance
const geoService = new GeoLocationService();
