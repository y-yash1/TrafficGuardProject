/**
 * Traffic Guard TVM — Geolocation & Localization
 * Handles GPS, location reversal, and Telugu/English translation
 */

class GeoLocation {
    constructor() {
        this.currentPosition = null;
        this.translationCache = {};
        this.locationCache = {};
    }
    
    /**
     * Get current device location using browser Geolocation API
     */
    async getCurrentLocation() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Geolocation not supported'));
                return;
            }
            
            const options = {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0
            };
            
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    this.currentPosition = {
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude,
                        accuracy: position.coords.accuracy,
                        timestamp: new Date()
                    };
                    resolve(this.currentPosition);
                },
                (error) => {
                    reject(new Error(`Geolocation error: ${error.message}`));
                },
                options
            );
        });
    }
    
    /**
     * Watch device location for continuous tracking
     */
    watchLocation(callback, options = {}) {
        if (!navigator.geolocation) {
            callback({ error: 'Geolocation not supported' });
            return null;
        }
        
        const geoOptions = {
            enableHighAccuracy: true,
            timeout: 5000,
            maximumAge: 0,
            ...options
        };
        
        return navigator.geolocation.watchPosition(
            (position) => {
                this.currentPosition = {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    accuracy: position.coords.accuracy,
                    timestamp: new Date()
                };
                callback(this.currentPosition);
            },
            (error) => {
                callback({ error: `Watch error: ${error.message}` });
            },
            geoOptions
        );
    }
    
    /**
     * Stop watching location
     */
    stopWatchLocation(watchId) {
        if (navigator.geolocation && watchId) {
            navigator.geolocation.clearWatch(watchId);
        }
    }
    
    /**
     * Get location name and Telugu translation via reverse geocoding
     */
    async getLocationName(latitude, longitude) {
        const cacheKey = `${latitude.toFixed(5)},${longitude.toFixed(5)}`;
        
        if (this.locationCache[cacheKey]) {
            return this.locationCache[cacheKey];
        }
        
        try {
            // Use zoom=18 and addressdetails=1 for maximum precision
            const response = await fetch(
                `https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}&zoom=18&addressdetails=1`,
                { headers: { 'Accept': 'application/json', 'Accept-Language': 'en' } }
            );
            
            if (!response.ok) throw new Error('Reverse geocoding failed');
            
            const data = await response.json();
            const a = data.address || {};
            
            // Build accurate human-readable location name
            let parts = [];
            
            // Specific place name
            const placeName = a.amenity || a.building || a.shop || a.tourism || '';
            if (placeName) parts.push(placeName);
            
            // Road / street
            if (a.road) parts.push(a.road);
            
            // Neighbourhood or suburb for context
            const area = a.neighbourhood || a.residential || a.hamlet || '';
            const suburb = a.suburb || a.quarter || a.city_district || '';
            if (area && !parts.includes(area)) parts.push(area);
            else if (suburb && !parts.includes(suburb)) parts.push(suburb);
            
            // Fallback to village/town/city
            if (parts.length === 0) {
                if (a.village) parts.push(a.village);
                else if (a.town) parts.push(a.town);
                else if (a.city) parts.push(a.city);
            }
            
            // Append city if not already present
            if (parts.length > 0 && parts.length <= 2) {
                const city = a.city || a.town || a.county || '';
                if (city && !parts.includes(city)) parts.push(city);
            }
            
            let locationName = parts.slice(0, 3).join(', ');
            
            if (!locationName) {
                locationName = data.display_name 
                    ? data.display_name.split(',').slice(0, 3).join(',').trim()
                    : `Location (${latitude.toFixed(4)}, ${longitude.toFixed(4)})`;
            }
            
            // Get Telugu translation
            const locationTelugu = await this.translateToTelugu(locationName);
            
            const result = {
                latitude,
                longitude,
                location: locationName,
                location_telugu: locationTelugu,
                address: a
            };
            
            this.locationCache[cacheKey] = result;
            return result;
        } catch (error) {
            console.error('Reverse geocoding error:', error);
            // Fallback to generic location
            return {
                latitude,
                longitude,
                location: `Location (${latitude.toFixed(4)}, ${longitude.toFixed(4)})`,
                location_telugu: `స్థానం (${latitude.toFixed(4)}, ${longitude.toFixed(4)})`,
                address: {}
            };
        }
    }
    
    /**
     * Translate location name to Telugu using Google Translate API
     * Note: In production, store translations in database to avoid repeated API calls
     */
    async translateToTelugu(text) {
        const cacheKey = `te_${text.toLowerCase()}`;
        
        if (this.translationCache[cacheKey]) {
            return this.translationCache[cacheKey];
        }
        
        // Use local Hyderabad location name translations (no external API needed)
        const locations = this.getHyderabadLocationNames();
        
        // Try direct match first
        if (locations[text]) {
            this.translationCache[cacheKey] = locations[text];
            return locations[text];
        }
        
        // Try partial match — check if any known location name appears in the text
        for (const [eng, tel] of Object.entries(locations)) {
            if (text.toLowerCase().includes(eng.toLowerCase())) {
                const translated = text.replace(new RegExp(eng, 'gi'), tel);
                this.translationCache[cacheKey] = translated;
                return translated;
            }
        }
        
        // Fallback: return with Telugu prefix
        const fallback = `స్థానం: ${text}`;
        this.translationCache[cacheKey] = fallback;
        return fallback;
    }
    
    /**
     * Specific location translations for Hyderabad
     */
    getHyderabadLocationNames() {
        return {
            'Banjara Hills': 'బంజారా హిల్‌లు',
            'Jubilee Hills': 'జూబిలీ హిల్‌లు',
            'Hitech City': 'హైటెక్ సిటీ',
            'Madhapur': 'మాధపూర్',
            'Secunderabad': 'సికందరాబాద్',
            'KPHB Colony': 'కెపీహెచ్‌బీ కాలనీ',
            'Gachibowli': 'గచిబౌళీ',
            'Innerring Road': 'ఇనర్‌రింగ్ రోడ్',
            'Road No 1': 'రోడ్ నం 1',
            'Road No 72': 'రోడ్ నం 72',
            'Kachiguda': 'కాచిగూడా'
        };
    }
    
    /**
     * Get location name with Telugu translation for specific Hyderabad locations
     */
    getHyderabadLocation(locationEnglish) {
        const locations = this.getHyderabadLocationNames();
        return {
            english: locationEnglish,
            telugu: locations[locationEnglish] || locationEnglish
        };
    }
    
    /**
     * Calculate distance between two points
     */
    calculateDistance(lat1, lon1, lat2, lon2) {
        const R = 6371; // Earth's radius in km
        const dLat = this.toRad(lat2 - lat1);
        const dLon = this.toRad(lon2 - lon1);
        const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                  Math.cos(this.toRad(lat1)) * Math.cos(this.toRad(lat2)) *
                  Math.sin(dLon / 2) * Math.sin(dLon / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    }
    
    toRad(deg) {
        return deg * (Math.PI / 180);
    }
}

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GeoLocation;
}
