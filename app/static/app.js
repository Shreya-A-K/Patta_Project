// Add to app.js - Client-side security
class SecurePattaPWA {
    constructor() {
        this.initCSP();
        this.setupXSRF();
    }
    
    initCSP() {
        // Enforce CSP violations block execution
        document.addEventListener('securitypolicyviolation', (e) => {
            console.error('CSP Violation:', e);
            document.body.innerHTML = '<h1>Security violation detected</h1>';
        });
    }
    
    // CSRF protection
    setupXSRF() {
        const token = localStorage.getItem('xsrf_token') || this.generateToken();
        localStorage.setItem('xsrf_token', token);
        
        // Attach to all requests
        this.apiFetch = (url, options = {}) => {
            options.headers = {
                ...options.headers,
                'X-XSRF-TOKEN': token,
                'Content-Type': 'application/json'
            };
            return fetch(url, options);
        };
    }
    
    generateToken() {
        return btoa(String.fromCharCode(...crypto.getRandomValues(new Uint8Array(32))));
    }
}
