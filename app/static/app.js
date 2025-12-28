// app/static/js/app.js - SYNTAX ERROR FIXED
class SecurePattaPWA {
  constructor() {
    this.initCSP();
    this.setupXSRF();
    this.initFileSecurity();
  }

  initCSP() {
    const csp = `
      default-src 'self';
      script-src 'self' 'unsafe-inline' https://unpkg.com https://cdnjs.cloudflare.com;
      style-src 'self' 'unsafe-inline' https://unpkg.com https://fonts.googleapis.com https://cdn.tailwindcss.com;
      img-src 'self' data: https: blob: https://*.tile.openstreetmap.org https://*.googleusercontent.com;
      connect-src 'self' https://nominatim.openstreetmap.org https://ipapi.co https://*.googleapis.com;
      form-action 'self';
      frame-ancestors 'none';
    `;
    
    document.addEventListener('securitypolicyviolation', (e) => {
      console.error('🚨 CSP Violation:', {
        blockedURI: e.blockedURI,
        violatedDirective: e.violatedDirective,
        timestamp: new Date().toISOString()
      });
    });
  }

  setupXSRF() {
    this.xsrfToken = document.cookie.split(';')
      .find(row => row.startsWith('csrf_token='))
      ?.split('=')[1] || this.generateToken();
  }

  generateToken() {
    const bytes = new Uint8Array(32);
    crypto.getRandomValues(bytes);
    return btoa(String.fromCharCode(...bytes)).substring(0, 43);
  }

  initFileSecurity() {
    document.addEventListener('dragover', (e) => {
      if (!e.target.closest('.document-field')) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'none';
      }
    });

    document.addEventListener('change', (e) => {
      if (e.target.matches('input[type="file"]')) {
        this.validateFile(e.target);
      }
    }, true);
  }

  validateFile(input) {
    const file = input.files[0];
    if (!file) return;

    if (file.size > 10 * 1024 * 1024) {
      alert('❌ File too large (max 10MB)');
      input.value = '';
      return false;
    }

    const allowedTypes = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png'];
    if (!allowedTypes.includes(file.type)) {
      alert('❌ Only PDF, JPG, PNG allowed');
      input.value = '';
      return false;
    }

    const dangerous = /<(script|iframe|object|embed|svg)/i;
    if (dangerous.test(file.name)) {
      alert('❌ Invalid filename');
      input.value = '';
      return false;
    }

    console.log('✅ File validated:', file.name, `${(file.size/1024/1024).toFixed(1)}MB`);
    return true;
  }

  async secureFileUpload(url, formData, onProgress = null) {
    const required = ['parentDoc', 'saleDeed', 'aadharCard', 'encumbCert', 'layoutScan'];
    for (let key of required) {
      if (!formData.get(key) || formData.get(key).size === 0) {
        throw new Error(`${key.replace(/([A-Z])/g, ' $1')} missing`);
      }
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 120000);

    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
        credentials: 'same-origin',
        headers: {
          'X-Requested-With': 'XMLHttpRequest'
        }
      });

      clearTimeout(timeout);

      if (!response.ok) {
        const error = await response.text();
        throw new Error(`Upload failed: ${response.status} ${error}`);
      }

      return await response.json();
    } catch (error) {
      if (error.name === 'AbortError') {
        throw new Error('Upload timeout (2min)');
      }
      throw error;
    }
  }

  async apiFetch(url, options = {}) {
    const headers = {
      'X-Requested-With': 'XMLHttpRequest',
      ...(options.headers || {})
    };

    if (options.body && !(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(url, { 
      ...options, 
      headers,
      credentials: 'same-origin'
    });

    if (response.status === 403) {
      location.reload();
      throw new Error('Session expired');
    }

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`${response.status}: ${errorText}`);
    }

    return response.json();
  }
}

// 🌐 GLOBAL INSTANCE
window.pattaApp = new SecurePattaPWA();

// 🚀 PATTA SUBMIT HELPER
window.submitPattaSecure = async function() {
  try {
    const formData = new FormData();
    
    const files = ['parentDoc', 'saleDeed', 'aadharCard', 'encumbCert', 'layoutScan'];
    for (let id of files) {
      const input = document.getElementById(id);
      if (!input?.files[0]) {
        throw new Error('All 5 documents required');
      }
      formData.append(id, input.files[0]);
    }

    formData.append('district', document.getElementById('district')?.value || '');
    formData.append('taluk', document.getElementById('taluk')?.value || '');
    formData.append('village', document.getElementById('village')?.value || '');
    formData.append('lat', document.getElementById('lat')?.value || '0');
    formData.append('lng', document.getElementById('lng')?.value || '0');
    formData.append('surveyNo', document.getElementById('surveyNo')?.value || '');
    formData.append('subdivNo', document.getElementById('subdivNo')?.value || '');

    const boundary = [];
    if (typeof drawnItems !== 'undefined') {
      drawnItems.eachLayer(layer => {
        if (layer.getLatLngs) {
          boundary.push(layer.getLatLngs()[0].map(p => [p.lat.toFixed(10), p.lng.toFixed(10)]));
        }
      });
    }
    formData.append('boundary', JSON.stringify(boundary));

    const result = await window.pattaApp.secureFileUpload('/api/patta/apply', formData);
    console.log('✅ Patta submitted:', result);
    return result;

  } catch (error) {
    console.error('❌ Patta upload failed:', error);
    throw error;
  }
};
