/**
 * Traffic Guard TVM — Shared API Client
 * Handles auth tokens and all API calls
 */

const API = {
    getToken() { return localStorage.getItem('tg_token'); },
    getUser()  { try { return JSON.parse(localStorage.getItem('tg_user')); } catch { return null; } },

    async req(method, url, body = null, isForm = false) {
        const opts = {
            method,
            headers: { 'X-Auth-Token': this.getToken() }
        };
        if (body && !isForm) {
            opts.headers['Content-Type'] = 'application/json';
            opts.body = JSON.stringify(body);
        } else if (body && isForm) {
            opts.body = body; // FormData
        }
        const resp = await fetch(url, opts);
        if (resp.status === 401) {
            localStorage.clear();
            window.location.href = '/loginpage.html';
            return;
        }
        const data = await resp.json().catch(() => ({}));
        if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);
        return data;
    },

    get(url)          { return this.req('GET', url); },
    post(url, body)   { return this.req('POST', url, body); },
    patch(url, body)  { return this.req('PATCH', url, body); },
    delete(url)       { return this.req('DELETE', url); },
    upload(url, form) { return this.req('POST', url, form, true); },

    logout() {
        this.req('POST', '/api/auth/logout').finally(() => {
            localStorage.clear();
            window.location.href = '/loginpage.html';
        });
    },

    requireRole(...roles) {
        const user = this.getUser();
        if (!user || !this.getToken()) { window.location.href = '/loginpage.html'; return false; }
        if (roles.length && !roles.includes(user.role)) { window.location.href = '/loginpage.html'; return false; }
        return true;
    },
    
    // Geolocation & Proximity APIs
    async getNearbyOfficers(latitude, longitude, radius = 3) {
        return this.get(`/api/nearby/officers?latitude=${latitude}&longitude=${longitude}&radius=${radius}`);
    },
    
    async getNearbyEmergencyServices(latitude, longitude, radius = 3, serviceType = '') {
        const url = `/api/nearby/emergency-services?latitude=${latitude}&longitude=${longitude}&radius=${radius}${serviceType ? `&type=${serviceType}` : ''}`;
        return this.get(url);
    },
    
    async getAllEmergencyServices(serviceType = '') {
        const url = serviceType ? `/api/emergency-services?type=${serviceType}` : '/api/emergency-services';
        return this.get(url);
    },
    
    async reverseGeocode(latitude, longitude) {
        return this.get(`/api/reverse-geocode?latitude=${latitude}&longitude=${longitude}`);
    }
};

// Format currency in INR
function fmtINR(amount) {
    return '₹' + Number(amount || 0).toLocaleString('en-IN');
}

// Format date
function fmtDate(str) {
    if (!str) return '—';
    return new Date(str).toLocaleDateString('en-IN', {day:'2-digit', month:'short', year:'numeric'});
}

function fmtDateTime(str) {
    if (!str) return '—';
    return new Date(str).toLocaleString('en-IN', {day:'2-digit', month:'short', year:'numeric', hour:'2-digit', minute:'2-digit'});
}

function statusBadge(status) {
    const map = {
        pending: ['#FEF3C7','#92400E','Pending'],
        paid: ['#D1FAE5','#065F46','Paid'],
        overdue: ['#FEE2E2','#991B1B','Overdue'],
        contested: ['#DBEAFE','#1E40AF','Contested'],
        cancelled: ['#F3F4F6','#374151','Cancelled']
    };
    const [bg,fg,label] = map[status] || ['#F3F4F6','#374151', status];
    return `<span style="background:${bg};color:${fg};padding:3px 10px;border-radius:20px;font-size:12px;font-weight:700;">${label}</span>`;
}

function sosBadge(status) {
    const map = {
        pending: ['#FEE2E2','#991B1B','Pending'],
        dispatched: ['#FEF3C7','#92400E','Dispatched'],
        enroute: ['#DBEAFE','#1E40AF','En Route'],
        resolved: ['#D1FAE5','#065F46','Resolved']
    };
    const [bg,fg,label] = map[status] || ['#F3F4F6','#374151', status];
    return `<span style="background:${bg};color:${fg};padding:3px 10px;border-radius:20px;font-size:12px;font-weight:700;">${label}</span>`;
}

function showToast(msg, type='success') {
    let toast = document.getElementById('_tg_toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = '_tg_toast';
        toast.style.cssText = 'position:fixed;bottom:30px;left:50%;transform:translateX(-50%);padding:14px 24px;border-radius:12px;font-size:14px;font-weight:600;z-index:99999;opacity:0;transition:opacity 0.3s;';
        document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.style.background = type === 'error' ? '#FF3B30' : '#34C759';
    toast.style.color = 'white';
    toast.style.opacity = '1';
    clearTimeout(toast._t);
    toast._t = setTimeout(() => toast.style.opacity = '0', 3000);
}
