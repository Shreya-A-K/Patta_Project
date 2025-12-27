// app/static/js/app.js
class SecurePattaPWA {
  constructor() {
    this.initCSP();
    this.setupXSRF();
  }

  initCSP() {
    document.addEventListener('securitypolicyviolation', (e) => {
      console.error('CSP Violation:', e);
    });
  }

  setupXSRF() {
    const existing = localStorage.getItem('xsrf_token');
    const token = existing || this.generateToken();
    localStorage.setItem('xsrf_token', token);
    this.xsrfToken = token;
  }

  generateToken() {
    const bytes = new Uint8Array(32);
    crypto.getRandomValues(bytes);
    return btoa(String.fromCharCode(...bytes));
  }

  async apiFetch(url, options = {}) {
    const headers = {
      'X-XSRF-TOKEN': this.xsrfToken,
      ...(options.headers || {})
    };

    // Only set JSON content type if caller didn’t specify anything
    if (options.body && !(options.body instanceof FormData)) {
      headers['Content-Type'] = headers['Content-Type'] || 'application/json';
    }

    return fetch(url, { ...options, headers });
  }
}

window.pattaApp = new SecurePattaPWA();
