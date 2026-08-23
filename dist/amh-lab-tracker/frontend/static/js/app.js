// ============================================================================
// Legacy Browser Polyfills & Coroutine Runner (Edge 12-18, IE11+, WebViews)
// ============================================================================

// Native ES6 Generator-to-Promise Coroutine (replaces ES2017 async/await)
function __async(generatorFunc) {
  return function() {
    var self = this;
    var args = arguments;
    return new Promise(function(resolve, reject) {
      var gen = generatorFunc.apply(self, args);
      function step(key, arg) {
        var info;
        try {
          info = gen[key](arg);
        } catch (error) {
          return reject(error);
        }
        if (info.done) {
          return resolve(info.value);
        }
        Promise.resolve(info.value).then(
          function(val) { step('next', val); },
          function(err) { step('throw', err); }
        );
      }
      step('next');
    });
  };
}

// Array.prototype.includes (ES2016 polyfill for Edge 12-13)
if (!Array.prototype.includes) {
  Array.prototype.includes = function(searchElement, fromIndex) {
    var O = Object(this);
    var len = parseInt(O.length, 10) || 0;
    if (len === 0) return false;
    var n = parseInt(fromIndex, 10) || 0;
    var k = n >= 0 ? n : Math.max(0, len + n);
    while (k < len) {
      if (searchElement === O[k] || (searchElement !== searchElement && O[k] !== O[k])) {
        return true;
      }
      k++;
    }
    return false;
  };
}

// String.prototype.includes (ES6 polyfill)
if (!String.prototype.includes) {
  String.prototype.includes = function(search, start) {
    if (typeof start !== 'number') start = 0;
    if (start + search.length > this.length) return false;
    return this.indexOf(search, start) !== -1;
  };
}

// Object.values (ES2017 polyfill for Edge 12-13)
if (!Object.values) {
  Object.values = function(obj) {
    var vals = [];
    for (var key in obj) {
      if (Object.prototype.hasOwnProperty.call(obj, key)) {
        vals.push(obj[key]);
      }
    }
    return vals;
  };
}

// Object.entries (ES2017 polyfill for Edge 12-13)
if (!Object.entries) {
  Object.entries = function(obj) {
    var entries = [];
    for (var key in obj) {
      if (Object.prototype.hasOwnProperty.call(obj, key)) {
        entries.push([key, obj[key]]);
      }
    }
    return entries;
  };
}

// Array.prototype.find (ES6 polyfill)
if (!Array.prototype.find) {
  Array.prototype.find = function(predicate) {
    if (this == null) throw new TypeError('Array.prototype.find called on null or undefined');
    if (typeof predicate !== 'function') throw new TypeError('predicate must be a function');
    var list = Object(this);
    var length = list.length >>> 0;
    var thisArg = arguments[1];
    for (var i = 0; i < length; i++) {
      var value = list[i];
      if (predicate.call(thisArg, value, i, list)) return value;
    }
    return undefined;
  };
}


const app = {
  currentUser: null,
  currentView: 'clients',
  theme: null,
  inactivityTimer: null,
  inactivityTimeout: 15 * 60 * 1000, // 15 minutes in milliseconds
  lastActivityTime: 0,

  icons: {
      'building': `<svg class="lucide" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="16" height="20" x="4" y="2" rx="2" ry="2"/><path d="M9 22v-4h6v4"/><path d="M8 6h.01"/><path d="M16 6h.01"/><path d="M12 6h.01"/><path d="M12 10h.01"/><path d="M12 14h.01"/><path d="M16 10h.01"/><path d="M16 14h.01"/><path d="M8 10h.01"/><path d="M8 14h.01"/></svg>`,
      'stethoscope': `<svg class="lucide" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 2v2"/><path d="M5 2v2"/><path d="M5 3H4a2 2 0 0 0-2 2v4a6 6 0 0 0 12 0V5a2 2 0 0 0-2-2h-1"/><path d="M8 15a6 6 0 0 0 12 0v-3"/><circle cx="20" cy="10" r="2"/></svg>`,

    'clipboard-list': `<svg class="lucide" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="8" height="4" x="8" y="2" rx="1" ry="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="M12 11h4"/><path d="M12 16h4"/><path d="M8 11h.01"/><path d="M8 16h.01"/></svg>`,
    'bar-chart-2': `<svg class="lucide" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" x2="18" y1="20" y2="10"/><line x1="12" x2="12" y1="20" y2="4"/><line x1="6" x2="6" y1="20" y2="14"/></svg>`,
    'trending-up': `<svg class="lucide" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>`,
    'file-text': `<svg class="lucide" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><polyline points="14 2 14 8 20 8"/><line x1="16" x2="8" y1="13" y2="13"/><line x1="16" x2="8" y1="17" y2="17"/><line x1="10" x2="8" y1="9" y2="9"/></svg>`,
    'settings': `<svg class="lucide" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.38a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>`,
    'shield-check': `<svg class="lucide" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/></svg>`,
    'save': `<svg class="lucide" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>`,
    'printer': `<svg class="lucide" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect width="12" height="8" x="6" y="14"/></svg>`,
    'download': `<svg class="lucide" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>`,
    'user': `<svg class="lucide" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`,
    'users': `<svg class="lucide" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
    'user-plus': `<svg class="lucide" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" x2="19" y1="8" y2="14"/><line x1="16" x2="22" y1="11" y2="11"/></svg>`,
    'plus': `<svg class="lucide" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" x2="12" y1="5" y2="19"/><line x1="5" x2="19" y1="12" y2="12"/></svg>`,
    'chevron-left': `<svg class="lucide" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>`,
    'chevron-right': `<svg class="lucide" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>`,
    'check-circle': `<svg class="lucide" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
    'alert-triangle': `<svg class="lucide" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" x2="12" y1="9" y2="13"/><line x1="12" x2="12.01" y1="17" y2="17"/></svg>`,
    'log-out': `<svg class="lucide" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/></svg>`
  },

  icon: function(name) {
    return this.icons[name] || '';
  },

  init: __async(function*() {
    yield this.loadTheme();
    yield this.checkAuth();
    this.setupInactivityListeners();
    
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const el = document.activeElement;
        if (el && el.type === 'checkbox') {
          e.preventDefault();
          el.click();
        }
      }
    });
  },

  loadTheme: __async(function*() {
    try {
      const res = yield fetch('/assets/branding/theme.json');
      if (res.ok) {
        this.theme = yield res.json();
        document.getElementById('app-title').textContent = this.theme.app_title || 'AMH Lab Tracker';
        document.getElementById('facility-name').textContent = this.theme.facility_name || '';
        document.getElementById('footer-text').textContent = this.theme.footer_text || '';
        if (this.theme.logo_path) {
          document.getElementById('header-logo').src = this.theme.logo_path;
        }
      }
    } catch (e) {
      console.warn('Theme loading warning:', e);
    }
  },

  checkAuth: __async(function*() {
    try {
      const res = yield fetch('/api/auth/me');
      if (res.ok) {
        this.currentUser = yield res.json();
        this.renderUserNav();
        document.getElementById('login-modal').style.display = 'none';
        document.getElementById('app-nav').style.display = 'flex';
        this.startInactivityTimer();

        if (this.currentUser.password_reset_required) {
          this.showResetPasswordModal();
        } else {
          this.navigate(this.currentView);
        }
      } else {
        this.showLogin();
      }
    } catch (e) {
      this.showLogin();
    }
  },

  showLogin: function() {
    this.currentUser = null;
    this.stopInactivityTimer();
    this.cleanseDOM();
    document.getElementById('app-nav').style.display = 'none';
    document.getElementById('user-nav').innerHTML = '';
    document.getElementById('login-modal').style.display = 'flex';
    this.showLoginForm();
  },

  handleLogin: __async(function*(event) {
    event.preventDefault();
    const u = document.getElementById('login-username').value;
    const p = document.getElementById('login-password').value;
    const errDiv = document.getElementById('login-error');
    errDiv.style.display = 'none';

    try {
      const res = yield fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: u, password: p })
      });

      if (res.ok) {
        const data = yield res.json();
        this.currentUser = data.user;
        document.getElementById('login-modal').style.display = 'none';
        document.getElementById('app-nav').style.display = 'flex';
        this.renderUserNav();
        this.startInactivityTimer();

        if (data.status === 'reset_required' || (data.user && data.user.password_reset_required)) {
          this.showResetPasswordModal();
        } else {
          this.navigate('clients');
        }
      } else {
        const err = yield res.json();
        errDiv.textContent = err.detail || 'Login failed';
        errDiv.style.display = 'block';
      }
    } catch (e) {
      errDiv.textContent = 'Connection error. Please try again.';
      errDiv.style.display = 'block';
    }
  },

  handleLogout: __async(function*() {
    this.stopInactivityTimer();
    yield fetch('/api/auth/logout', { method: 'POST' });
    this.showLogin();
  },

  showResetPasswordModal: function() {
    const modal = document.getElementById('reset-password-modal');
    if (modal) {
      modal.style.display = 'flex';
      const err = document.getElementById('reset-password-error');
      if (err) {
        err.textContent = '';
        err.style.display = 'none';
      }
      const form = document.getElementById('reset-password-form');
      if (form) form.reset();
      const oldPw = document.getElementById('reset-old-password');
      if (oldPw) oldPw.focus();
    }
  },

  handleChangePassword: __async(function*(event) {
    event.preventDefault();
    const oldPassword = document.getElementById('reset-old-password').value;
    const newPassword = document.getElementById('reset-new-password').value;
    const confirmPassword = document.getElementById('reset-confirm-password').value;
    const errDiv = document.getElementById('reset-password-error');

    errDiv.style.display = 'none';

    if (!newPassword || newPassword.trim().length < 4) {
      errDiv.textContent = 'New password must be at least 4 characters.';
      errDiv.style.display = 'block';
      return;
    }

    if (newPassword !== confirmPassword) {
      errDiv.textContent = 'New password and confirmation do not match.';
      errDiv.style.display = 'block';
      return;
    }

    try {
      const res = yield fetch('/api/auth/change-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          old_password: oldPassword,
          new_password: newPassword
        })
      });

      if (res.ok) {
        if (this.currentUser) {
          this.currentUser.password_reset_required = false;
        }
        document.getElementById('reset-password-modal').style.display = 'none';
        document.getElementById('reset-password-form').reset();
        this.showNotificationModal("Success", 'Password changed successfully!', false);
        this.navigate('clients');
      } else {
        const err = yield res.json();
        errDiv.textContent = err.detail || 'Failed to change password.';
        errDiv.style.display = 'block';
      }
    } catch (e) {
      errDiv.textContent = 'Connection error. Please try again.';
      errDiv.style.display = 'block';
    }
  },

  showRegisterForm: function(event) {
    if (event) event.preventDefault();
    document.getElementById('login-form-container').style.display = 'none';
    document.getElementById('register-form-container').style.display = 'block';
    document.getElementById('register-error').style.display = 'none';
    document.getElementById('register-success').style.display = 'none';
  },

  showLoginForm: function(event) {
    if (event) event.preventDefault();
    document.getElementById('register-form-container').style.display = 'none';
    document.getElementById('login-form-container').style.display = 'block';
    document.getElementById('login-error').style.display = 'none';
  },

  handleRegister: __async(function*(event) {
    event.preventDefault();
    const fullname = document.getElementById('register-fullname').value;
    const username = document.getElementById('register-username').value;
    const password = document.getElementById('register-password').value;
    const cadre = document.getElementById('register-cadre').value;
    const errDiv = document.getElementById('register-error');
    const successDiv = document.getElementById('register-success');
    
    errDiv.style.display = 'none';
    successDiv.style.display = 'none';

    try {
      const res = yield fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ full_name: fullname, username: username, password: password, cadre: cadre })
      });

      if (res.ok) {
        const data = yield res.json();
        if (data.is_active) {
          successDiv.textContent = 'Super Admin account registered successfully! Redirecting...';
        } else {
          successDiv.textContent = 'Registration submitted! Access is pending Admin approval.';
        }
        successDiv.style.display = 'block';
        document.getElementById('register-form').reset();
        setTimeout(() => {
          this.showLoginForm();
        }, 3000);
      } else {
        const err = yield res.json();
        errDiv.textContent = err.detail || 'Registration failed';
        errDiv.style.display = 'block';
      }
    } catch (e) {
      errDiv.textContent = 'Connection error. Please try again.';
      errDiv.style.display = 'block';
    }
  },

  setupInactivityListeners: function() {
    const reset = () => this.resetInactivityTimer();
    window.addEventListener('mousemove', reset);
    window.addEventListener('keydown', reset);
    window.addEventListener('click', reset);
    window.addEventListener('scroll', reset);
  },

  startInactivityTimer: function() {
    this.resetInactivityTimer();
  },

  resetInactivityTimer: function() {
    const now = Date.now();
    if (now - this.lastActivityTime < 5000) {
      return;
    }
    this.lastActivityTime = now;

    if (this.inactivityTimer) {
      clearTimeout(this.inactivityTimer);
    }
    
    if (this.currentUser) {
      this.inactivityTimer = setTimeout(() => {
        console.log("Inactivity timeout reached. Logging out...");
        this.handleLogout();
        this.showNotificationModal("Notice", "Logged out automatically due to inactivity.", true);
      }, this.inactivityTimeout);
    }
  },

  stopInactivityTimer: function() {
    if (this.inactivityTimer) {
      clearTimeout(this.inactivityTimer);
      this.inactivityTimer = null;
    }
  },

  togglePasswordVisibility: function(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const type = input.getAttribute('type') === 'password' ? 'text' : 'password';
    input.setAttribute('type', type);
    
    const btn = input.nextElementSibling;
    if (btn) {
      if (type === 'text') {
        btn.innerHTML = `<svg class="lucide" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.52 13.52 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/><line x1="2" x2="22" y1="2" y2="22"/></svg>`;
      } else {
        btn.innerHTML = `<svg class="lucide" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0z"/><circle cx="12" cy="12" r="3"/></svg>`;
      }
    }
  },

  cleanseDOM: function() {
    // Reset all password input types back to password
    ['login-password', 'register-password', 'reset-old-password', 'reset-new-password', 'reset-confirm-password'].forEach(id => {
      const input = document.getElementById(id);
      if (input) {
        input.setAttribute('type', 'password');
        const btn = input.nextElementSibling;
        if (btn) {
          btn.innerHTML = `<svg class="lucide" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0z"/><circle cx="12" cy="12" r="3"/></svg>`;
        }
      }
    });

    // Reset all forms in modal/app
    document.querySelectorAll('form').forEach(form => form.reset());

    // Hide reset password modal
    const resetModal = document.getElementById('reset-password-modal');
    if (resetModal) resetModal.style.display = 'none';

    // Reset dynamic view container content to default placeholder
    const container = document.getElementById('view-container');
    if (container) {
      container.innerHTML = '<p class="text-muted" style="text-align: center; padding: 40px;">Session inactive. Please sign in.</p>';
    }

    // Reset state caches to prevent data leakage between technician shifts
    this.currentClient = null;
    this.currentOrder = null;
  },

  renderUserNav: function() {
    const nav = document.getElementById('user-nav');
    if (!this.currentUser) return;

    const isPrivileged = this.currentUser.role === 'admin' || this.currentUser.role === 'superadmin';
    const isSuper = this.currentUser.role === 'superadmin';
    
    const adminTabs = document.querySelectorAll('.admin-only');
    adminTabs.forEach(tab => {
      tab.style.display = isPrivileged ? 'inline-block' : 'none';
    });
    
    const superAdminTabs = document.querySelectorAll('.superadmin-only');
    superAdminTabs.forEach(tab => {
      tab.style.display = isSuper ? 'inline-block' : 'none';
    });

    const roleLabel = this.currentUser.role === 'superadmin' ? 'Super Admin'
      : (this.currentUser.role === 'admin' ? 'Admin' : 'Staff');

    nav.innerHTML = `
      <div class="user-badge">
        ${this.icon('user')} <strong>${this.escape(this.currentUser.full_name)}</strong> (${this.escape(roleLabel)}${this.currentUser.cadre ? ' - ' + this.escape(this.currentUser.cadre) : ''})
      </div>
      <button class="btn btn-secondary" style="padding: 4px 12px; font-size: 0.8rem;" onclick="app.handleLogout()">${this.icon('log-out')} Logout</button>
    `;
  },

  navigate: function(viewName) {
    if (this.currentUser && this.currentUser.password_reset_required) {
      this.showResetPasswordModal();
      return;
    }
    this.currentView = viewName;
    document.querySelectorAll('.nav-tab').forEach(tab => {
      tab.classList.remove('active');
    });

    const activeBtn = Array.from(document.querySelectorAll('.nav-tab')).find(b => b.getAttribute('onclick').includes(viewName));
    if (activeBtn) activeBtn.classList.add('active');

    const container = document.getElementById('view-container');
    if (viewName === 'daily-log') this.renderDailyLog(container);
    else if (viewName === 'reports') this.renderReports(container);
    else if (viewName === 'trends') this.renderTrends(container);
    else if (viewName === 'clients') this.renderClients(container);
    else if (viewName === 'config') this.renderConfig(container);
    else if (viewName === 'audit') this.renderAuditLog(container);
  },

  showNotificationModal: function(title, message, isError = false) {
    const modal = document.getElementById('notification-modal');
    if (!modal) return;
    document.getElementById('notif-title').textContent = title;
    document.getElementById('notif-title').style.color = isError ? 'var(--danger-color)' : 'var(--primary-color)';
    document.getElementById('notif-message').textContent = message;
    modal.style.display = 'flex';
  },

  confirmAction: function(title, message, callback) {
    const modal = document.getElementById('confirm-modal');
    if (!modal) {
      if (confirm(message)) callback();
      return;
    }
    document.getElementById('confirm-title').textContent = title;
    document.getElementById('confirm-message').textContent = message;
    
    const cancelBtn = document.getElementById('confirm-cancel-btn');
    const okBtn = document.getElementById('confirm-ok-btn');
    
    // Remove old listeners
    const newCancel = cancelBtn.cloneNode(true);
    const newOk = okBtn.cloneNode(true);
    cancelBtn.parentNode.replaceChild(newCancel, cancelBtn);
    okBtn.parentNode.replaceChild(newOk, okBtn);
    
    newCancel.addEventListener('click', () => {
      modal.style.display = 'none';
    });
    
    newOk.addEventListener('click', () => {
      modal.style.display = 'none';
      callback();
    });
    
    modal.style.display = 'flex';
  },

  shiftLogDate: function(offsetDays) {
    const dateInput = document.getElementById('log-date');
    if (!dateInput) return;

    let current = new Date(dateInput.value || new Date());
    if (isNaN(current.getTime())) current = new Date();
    
    if (offsetDays === 0) {
      current = new Date();
    } else {
      current.setDate(current.getDate() + offsetDays);
    }

    const newDateStr = current.toISOString().split('T')[0];
    dateInput.value = newDateStr;
    this.loadDailyLogData(newDateStr);
  },

  // Daily Log View
  renderDailyLog: __async(function*(container) {
    const today = new Date().toISOString().split('T')[0];
    container.innerHTML = `
      <div class="card">
        <div class="card-header">
          <span class="card-title">${this.icon('clipboard-list')} Daily Laboratory Tests Log</span>
          <div class="controls-row">
            <div class="form-group" style="flex-direction: row; align-items: center; gap: 8px;">
              <label for="log-date">Entry Date:</label>
              <input type="date" id="log-date" value="${today}" onchange="app.loadDailyLogData(this.value)">
              <div class="btn-group" style="display: flex; gap: 4px;">
                <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 0.8rem;" onclick="app.shiftLogDate(0)">Today</button>
                <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 0.8rem;" onclick="app.shiftLogDate(-1)">Yesterday</button>
                <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 0.8rem;" onclick="app.shiftLogDate(-1)">${this.icon('chevron-left')} Prev</button>
                <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 0.8rem;" onclick="app.shiftLogDate(1)">Next ${this.icon('chevron-right')}</button>
              </div>
            </div>
          </div>
        </div>

        <div id="daily-summary-container" style="background: var(--bg-color); padding: 12px; margin-bottom: 20px; border-radius: 6px; display: flex; gap: 32px; border: 1px solid var(--border-color);">
          <div><strong>Tests Done:</strong> <span id="summary-done">0</span></div>
          <div><strong>Tracked Findings:</strong> <span id="summary-pos">0</span></div>
          <div><strong>Pending Orders:</strong> <span id="summary-pending">0</span></div>
          <div><strong>Completed Orders:</strong> <span id="summary-completed">0</span></div>
        </div>

        <div id="daily-sections-container">
          <p style="color: var(--text-muted);">Loading daily log...</p>
        </div>
      </div>
    `;
    yield this.loadDailyLogData(today);
  },

  loadDailyLogData: __async(function*(dateStr) {
    try {
      const res = yield fetch(`/api/daily-log?date=${dateStr}`);
      if (!res.ok) throw new Error('API returned ' + res.status);
      const data = yield res.json();
      
      if (data.today_check) {
        const doneEl = document.getElementById('summary-done');
        const posEl = document.getElementById('summary-pos');
        if (doneEl) doneEl.textContent = data.today_check.total_done;
        if (posEl) posEl.textContent = data.today_check.total_positive;
      }

      if (data.order_summary) {
        const pendEl = document.getElementById('summary-pending');
        const compEl = document.getElementById('summary-completed');
        if (pendEl) pendEl.textContent = data.order_summary.pending;
        if (compEl) compEl.textContent = data.order_summary.completed;
      }

      const secContainer = document.getElementById('daily-sections-container');
      secContainer.innerHTML = '';

      data.sections.forEach(sec => {
        let rowsHtml = '';
        let secDone = 0;
        let secPos = 0;

        sec.tests.forEach(t => {
          const done = t.done || 0;
          const pos = (t.positive !== null && t.positive !== undefined) ? t.positive : null;
          
          secDone += done;
          if (pos !== null) {
            secPos += pos;
          }

          let rateStr = '-';
          if (t.is_tracked && done > 0 && pos !== null) {
            rateStr = ((pos / done) * 100).toFixed(1) + '%';
          }

          const posDisplay = t.is_tracked 
            ? (pos !== null ? pos : 0)
            : 'N/A';

          rowsHtml += `
            <tr>
              <td><strong>${this.escape(t.test_name)}</strong></td>
              <td>${t.is_tracked ? 'Tracked' : 'Standard'}</td>
              <td style="text-align: right; font-weight: 500;">${done}</td>
              <td style="text-align: center; font-weight: 500;">${posDisplay}</td>
              <td style="text-align: right; color: var(--text-muted);">${rateStr}</td>
            </tr>
          `;
        });

        let secRateStr = '-';
        if (secDone > 0 && secPos > 0) {
          secRateStr = ((secPos / secDone) * 100).toFixed(1) + '%';
        }

        secContainer.innerHTML += `
          <div style="margin-bottom: 24px;">
            <h3 style="color: var(--primary-color); margin-bottom: 8px; font-size: 1rem; border-bottom: 2px solid var(--border-color); padding-bottom: 4px;">
              Section: ${this.escape(sec.section_name)}
            </h3>
            <table class="data-table" data-section-id="${sec.section_id}">
              <thead>
                <tr>
                  <th>Test Name</th>
                  <th style="width: 110px;">Surveillance</th>
                  <th style="width: 120px; text-align: right;">Done Count</th>
                  <th style="width: 160px; text-align: center;">Tracked Findings</th>
                  <th style="width: 130px; text-align: right;">Incidence Rate</th>
                </tr>
              </thead>
              <tbody>
                ${rowsHtml}
              </tbody>
              <tfoot>
                <tr style="background-color: #F8FAFC; font-weight: 700;">
                  <td colspan="2">Subtotal &mdash; ${this.escape(sec.section_name)}</td>
                  <td style="text-align: right;">${secDone}</td>
                  <td style="text-align: center;">${secPos}</td>
                  <td style="text-align: right;">${secRateStr}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        `;
      });
    } catch (e) {
      console.error('Error loading daily log:', e);
    }
  },

  saveDailyLogData: __async(function*() {
    const dateStr = document.getElementById('log-date').value;
    const entries = [];

    document.querySelectorAll('.test-done-input').forEach(inp => {
      const tid = parseInt(inp.getAttribute('data-test-id'), 10);
      const doneVal = parseInt(inp.value, 10) || 0;

      const posInp = document.querySelector(`.test-pos-input[data-test-id="${tid}"]`);
      const posVal = posInp ? (parseInt(posInp.value, 10) || 0) : null;

      if (doneVal > 0 || (posVal !== null && posVal > 0)) {
        entries.push({ test_id: tid, done: doneVal, positive: posVal });
      }
    });

    try {
      const res = yield fetch('/api/daily-log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entry_date: dateStr, entries: entries })
      });

      if (res.ok) {
        this.showNotificationModal("Success", 'Daily log entries saved successfully!', false);
        this.loadDailyLogData(dateStr);
      } else {
        this.showNotificationModal("Error", 'Failed to save entries.', true);
      }
    } catch (e) {
      this.showNotificationModal("Error", 'Error connecting to server.', true);
    }
  },

  // Reports View
  renderReports: __async(function*(container) {
    const today = new Date().toISOString().split('T')[0];
    container.innerHTML = `
      <div class="card">
        <div class="card-header">
          <span class="card-title">${this.icon('bar-chart-2')} Laboratory Aggregated Performance Report</span>
          <div class="controls-row">
            <div class="form-group">
              <label>Period Type:</label>
              <select id="report-period-type" onchange="app.loadReportData()">
                <option value="Day">Day</option>
                <option value="Week">Week</option>
                <option value="Month" selected>Month</option>
                <option value="Quarter">Quarter</option>
                <option value="Half-Year">Half-Year</option>
                <option value="Financial Year">Financial Year (July-June)</option>
                <option value="Calendar Year">Calendar Year</option>
              </select>
            </div>
            <div class="form-group">
              <label>Reference Date:</label>
              <input type="date" id="report-ref-date" value="${today}" onchange="app.loadReportData()">
            </div>
            <button class="btn btn-primary" onclick="app.exportReportCSV()">${this.icon('download')} Export CSV</button>
          </div>
        </div>

        <div id="report-content-container">
          <p>Loading report data...</p>
        </div>
      </div>
    `;
    yield this.loadReportData();
  },

  exportReportCSV: function() {
    const pType = document.getElementById('report-period-type').value;
    const rDate = document.getElementById('report-ref-date').value;
    
    let csvContent = `AMH Laboratory Performance Report\n`;
    csvContent += `Period Type,${pType}\n`;
    csvContent += `Reference Date,${rDate}\n\n`;
    csvContent += `Section,Test Name,Done Count,Positive Count,Positivity Rate (%)\n`;

    document.querySelectorAll('#report-content-container table.data-table').forEach(table => {
      const secHeader = table.closest('div').querySelector('h3');
      const secTitle = secHeader ? secHeader.textContent.replace('Section: ', '').trim() : '';
      table.querySelectorAll('tbody tr').forEach(tr => {
        const tds = tr.querySelectorAll('td');
        if (tds.length >= 4) {
          const testName = tds[0].textContent.trim();
          const done = tds[1].textContent.trim();
          const pos = tds[2].textContent.trim();
          const rate = tds[3].textContent.trim();
          csvContent += `"${secTitle}","${testName}",${done},${pos},${rate}\n`;
        }
      });
    });

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.setAttribute('download', `AMH_Lab_Report_${pType}_${rDate}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    this.showNotificationModal("Success", 'Report CSV exported successfully!', false);
  },

  loadReportData: __async(function*() {
    const pType = document.getElementById('report-period-type').value;
    const rDate = document.getElementById('report-ref-date').value;

    try {
      const res = yield fetch(`/api/reports?period_type=${pType}&reference_date=${rDate}`);
      if (!res.ok) throw new Error('API returned ' + res.status);
      const data = yield res.json();

      const rContainer = document.getElementById('report-content-container');
      let html = `
        <div style="background: #F8FAFC; padding: 12px; border-radius: 6px; margin-bottom: 20px; display: flex; gap: 32px;">
          <div><strong>Report Period:</strong> ${data.period_type} (${data.start_date} to ${data.end_date})</div>
          <div><strong>Grand Total Done:</strong> ${data.grand_total_done}</div>
          <div><strong>Grand Total Positive:</strong> ${data.grand_total_positive}</div>
        </div>
      `;

      data.sections.forEach(sec => {
        let rows = '';
        sec.tests.forEach(t => {
          rows += `
            <tr>
              <td><strong>${this.escape(t.test_name)}</strong></td>
              <td style="text-align: right;">${t.done}</td>
              <td style="text-align: center;">${t.is_tracked ? (t.positive !== null ? t.positive : 0) : 'N/A'}</td>
              <td style="text-align: right;">${t.positivity_rate !== null ? t.positivity_rate + '%' : 'â€”'}</td>
            </tr>
          `;
        });

        html += `
          <div style="margin-bottom: 24px;">
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid var(--border-color); padding-bottom: 4px; margin-bottom: 8px;">
              <h3 style="color: var(--primary-color); font-size: 1rem;">Section: ${this.escape(sec.section_name)}</h3>
              <span style="font-size: 0.85rem; font-weight: 700;">Subtotal Done: ${sec.section_total_done} | Positive: ${sec.section_total_positive}</span>
            </div>
            <table class="data-table">
              <thead>
                <tr>
                  <th>Test Name</th>
                  <th style="width: 140px; text-align: right;">Tests Done</th>
                  <th style="width: 140px; text-align: center;">Positives</th>
                  <th style="width: 140px; text-align: right;">Positivity Rate</th>
                </tr>
              </thead>
              <tbody>
                ${rows}
              </tbody>
            </table>
          </div>
        `;
      });

      rContainer.innerHTML = html;
    } catch (e) {
      console.error('Report error:', e);
    }
  },

  // Trends View
  renderTrends: __async(function*(container) {
    container.innerHTML = `
      <div class="card">
        <div class="card-header">
          <span class="card-title">${this.icon('trending-up')} Longitudinal Monthly Trends</span>
          <div class="controls-row">
            <div class="form-group">
              <label>From Year:</label>
              <select id="trend-from-year" onchange="app.loadTrendsData()">
                <option value="2026">2026</option>
                <option value="2025">2025</option>
              </select>
            </div>
            <div class="form-group">
              <label>To Year:</label>
              <select id="trend-to-year" onchange="app.loadTrendsData()">
                <option value="2027" selected>2027</option>
                <option value="2026">2026</option>
              </select>
            </div>
            <button class="btn btn-primary" onclick="app.exportTrendsCSV()">${this.icon('download')} Export CSV</button>
          </div>
        </div>

        <div id="trends-table-container">
          <p>Loading trends...</p>
        </div>
      </div>
    `;
    yield this.loadTrendsData();
  },

  exportTrendsCSV: function() {
    const fy = document.getElementById('trend-from-year').value;
    const ty = document.getElementById('trend-to-year').value;
    
    const table = document.querySelector('#trends-table-container table');
    if (!table) return;

    let csvContent = `AMH Laboratory Monthly Trends (${fy} to ${ty})\n\n`;

    table.querySelectorAll('tr').forEach(tr => {
      const cells = Array.from(tr.querySelectorAll('th, td')).map(c => `"${c.textContent.trim()}"`);
      csvContent += cells.join(',') + '\n';
    });

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.setAttribute('download', `AMH_Lab_Trends_${fy}_${ty}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    this.showNotificationModal("Success", 'Trends CSV exported successfully!', false);
  },

  loadTrendsData: __async(function*() {
    const fy = document.getElementById('trend-from-year').value;
    const ty = document.getElementById('trend-to-year').value;

    try {
      const res = yield fetch(`/api/trends?from_year=${fy}&to_year=${ty}`);
      if (!res.ok) throw new Error('API returned ' + res.status);
      const data = yield res.json();

      let headers = '<th>Month</th>';
      data.sections.forEach(s => { headers += `<th style="text-align: right;">${this.escape(s)}</th>`; });
      headers += '<th style="text-align: right;">Monthly Total</th>';

      let rows = '';
      data.trends.forEach(r => {
        let secCols = '';
        data.sections.forEach(s => { secCols += `<td style="text-align: right;">${r[s] || 0}</td>`; });
        rows += `
          <tr>
            <td><strong>${r.month}</strong></td>
            ${secCols}
            <td style="text-align: right; font-weight: 700;">${r.Total}</td>
          </tr>
        `;
      });

      document.getElementById('trends-table-container').innerHTML = `
        <table class="data-table">
          <thead>
            <tr>${headers}</tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
      `;
    } catch (e) {
      console.error('Trends error:', e);
    }
  },

  // Test Reports View
  renderClients: __async(function*(container) {
    container.innerHTML = `
      <div class="card">
        <div class="card-header">
          <span class="card-title">${this.icon('file-text')} Lab Reports and Client Details</span>
          <div class="controls-row">
            <button class="btn btn-primary" onclick="app.showNewClientModal()">${this.icon('user-plus')} Register New Client</button>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 20px;">
          <!-- Client List -->
          <div>
            <h3 style="font-size: 0.95rem; color: var(--primary-color); margin-bottom: 10px;">Registered Clients</h3>
            <div class="form-group" style="margin-bottom: 12px;">
              <input type="text" id="client-search-input" placeholder="Search client name/ID..." oninput="app.searchClients(this.value)">
            </div>
            <div id="client-list-box" style="background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 6px; max-height: 500px; overflow-y: auto;">
              <p style="padding: 12px; color: var(--text-muted);">Loading client directory...</p>
            </div>
          </div>

          <!-- Client Detail & Official Report Paper -->
          <div id="client-detail-box">
            <div style="padding: 32px; background: #F8FAFC; border-radius: 8px; border: 2px dashed var(--border-color); text-align: center; color: var(--text-muted);">
              Select a client from the list on the left to log diagnostic test results or view their official letterhead report.
            </div>
          </div>
        </div>
      </div>
    `;
    yield this.searchClients('');
  },

  searchClients: __async(function*(q) {
    try {
      const res = yield fetch(`/api/clients?query=${encodeURIComponent(q || '')}`);
      if (!res.ok) throw new Error('API returned ' + res.status);
      const clients = yield res.json();

      const box = document.getElementById('client-list-box');
      if (clients.length === 0) {
        box.innerHTML = '<p style="padding: 12px; color: var(--text-muted);">No clients found.</p>';
        return;
      }

      let html = '';
      clients.forEach(p => {
        html += `
          <div style="padding: 10px 14px; border-bottom: 1px solid var(--border-color); cursor: pointer; transition: background 0.2s;" 
               onclick="app.selectClient(${p.id}, '${this.escape(p.client_number)}', '${this.escape(p.full_name)}', '${p.sex}')"
               onmouseover="this.style.background='#F1F5F9'" onmouseout="this.style.background='transparent'">
            <div style="font-weight: 700; color: var(--primary-color);">${this.escape(p.full_name)}</div>
            <div style="font-size: 0.8rem; color: var(--text-muted);">ID: ${this.escape(p.client_number)} | Sex: ${p.sex}</div>
          </div>
        `;
      });
      box.innerHTML = html;
    } catch (e) {
      console.error('Client search error:', e);
    }
  },

  selectClient: __async(function*(pid, pnum, pname, psex) {
    this.currentClientId = pid;
    this.currentClientData = { id: pid, client_number: pnum, full_name: pname, sex: psex };
    const box = document.getElementById('client-detail-box');
    box.innerHTML = `
      <div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3 style="color: var(--primary-color);">Client: <span id="client-header-name">${pname}</span> (${pnum})</h3>
          <button class="btn btn-secondary btn-sm" onclick="app.openEditClientModal(${pid})">Edit Client Details</button>
        </div>

        <!-- Section A: Create Visit -->
        <div class="no-print" style="margin-bottom: 20px; background: #EFF6FF; padding: 16px; border-radius: 6px; border: 1px solid #BFDBFE;">
          <h4 style="font-size: 0.95rem; color: var(--primary-color); margin-bottom: 12px;">Create Visit & Order Tests</h4>
          <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 12px; margin-bottom: 12px;">
            <div class="form-group">
              <label>Ward of Origin:</label>
              <select id="visit-ward">
                <option value="">Loading wards...</option>
              </select>
            </div>
            <div class="form-group">
              <label>Requested By (Clinician):</label>
              <select id="visit-clinician">
                <option value="">Loading...</option>
              </select>
            </div>
            <div class="form-group">
              <label>Test Category:</label>
              <select id="visit-order-category" style="width: 100%; padding: 8px;">
                <option value="in-house" selected>In-house</option>
                <option value="referral">Referral</option>
                <option value="outreach">Outreach</option>
              </select>
            </div>
            <div class="form-group">
              <label>Lab Section:</label>
              <select id="visit-test-section" onchange="app.filterVisitTests()" style="width: 100%; padding: 8px;">
                <option value="all">All Sections</option>
              </select>
            </div>
          </div>
          <div class="form-group" style="margin-bottom: 12px;">
            <label>Select Test(s):</label>
            <input type="text" id="visit-test-search" placeholder="Search tests..." onkeyup="app.filterVisitTests()" style="width: 100%; padding: 8px; margin-bottom: 8px; box-sizing: border-box;">
            <div id="visit-tests-container">Loading tests...</div>
          </div>
          </div>
          <button class="btn btn-success" style="width: 100%; padding: 10px;" onclick="app.createVisit(${pid})">${this.icon('plus')} Create Visit & Orders</button>
        </div>

        <!-- Section B: Pending Tests -->
        <div class="no-print" style="margin-bottom: 20px;">
          <h4 style="font-size: 0.95rem; color: var(--primary-color); margin-bottom: 12px;">Pending Tests</h4>
          <div id="pending-tests-container" style="background: #fff; border: 1px solid var(--border-color); border-radius: 4px; padding: 12px;">
            Loading pending tests...
          </div>
        </div>

        <!-- Section C: Historical Reports -->
        <div class="no-print" style="margin-bottom: 20px;">
          <h4 style="font-size: 0.95rem; color: var(--primary-color); margin-bottom: 12px;">Historical Reports</h4>
          <div id="historical-visits-container" style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px;">
            Loading visits...
          </div>
        </div>

        <!-- Official PDF Report Iframe -->
        <iframe id="report-frame" src="" width="100%" height="800px" style="border: none; display: none;"></iframe>
      </div>
    `;

    yield this.loadWards();
    yield this.loadClinicians();
    yield this.loadTestOptionsMulti();
    yield this.loadPendingTests(pid);
    yield this.loadHistoricalVisits(pid);
  },

  loadTestOptions: __async(function*() {
    try {
      const res = yield fetch('/api/config/tests');
      if (!res.ok) throw new Error('API returned ' + res.status);
      const tests = yield res.json();

      const selectEl = document.getElementById('order-test-select');
      if (!selectEl) return;

      selectEl.innerHTML = '';
      tests.forEach(t => {
        selectEl.innerHTML += `<option value="${t.id}">${this.escape(t.name)}</option>`;
      });

      if (tests.length > 0) {
        this.onTestSelectChange(tests[0].id);
      }
    } catch (e) {
      console.error('Error loading test catalog options:', e);
    }
  },

  onTestSelectChange: __async(function*(testId) {
    if (!testId) return;
    try {
      const res = yield fetch(`/api/config/tests/${testId}/parameters`);
      if (!res.ok) throw new Error('API returned ' + res.status);
      const params = yield res.json();

      const container = document.getElementById('test-parameters-container');
      const singleGroup = document.getElementById('single-result-group');

      if (params && params.length > 0) {
        singleGroup.style.display = 'none';
        container.style.display = 'block';

        let html = '<h5 style="color: var(--primary-color); margin-bottom: 8px; font-size: 0.85rem;">Panel Parameters:</h5>';
        params.forEach(p => {
          html += `
            <div style="display: grid; grid-template-columns: 2fr 1.5fr 1fr 1fr; gap: 8px; align-items: center; margin-bottom: 6px;" class="panel-param-row" data-param-id="${p.id}">
              <div><strong style="font-size: 0.85rem;">${this.escape(p.parameter_name)}</strong></div>
              <div><input type="text" class="param-val-input" placeholder="Result" style="padding: 4px 8px; font-size: 0.85rem;"></div>
              <div style="font-size: 0.8rem; color: var(--text-muted);">${p.ref_range ? `${this.escape(p.ref_range)} ${this.escape(p.unit || '')}` : ''}</div>
              <div><label style="font-size: 0.75rem; cursor:pointer;"><input type="checkbox" class="param-pos-check"> Abnormal</label></div>
            </div>
          `;
        });
        container.innerHTML = html;
      } else {
        container.style.display = 'none';
        container.innerHTML = '';
        singleGroup.style.display = 'block';
      }
    } catch (e) {
      console.error('Error loading test parameters:', e);
    }
  },

  submitShiftAudit: __async(function*() {
    const dateStr = document.getElementById('log-date') ? document.getElementById('log-date').value : new Date().toISOString().split('T')[0];
    const sysTotal = parseInt(document.getElementById('sys-total-done').textContent, 10) || 0;
    const paperVal = parseInt(document.getElementById('paper-register-input').value, 10);

    if (isNaN(paperVal) || paperVal <= 0) {
      this.showNotificationModal("Error", 'Please type a valid Paper Register Total before submitting audit.', true);
      return;
    }

    try {
      const res = yield fetch('/api/daily-log/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          entry_date: dateStr,
          paper_register_tally: paperVal,
          system_total: sysTotal
        })
      });

      if (res.ok) {
        const data = yield res.json();
        this.showNotificationModal('Audit Recorded', `Shift audit recorded: ${data.match} (System: ${sysTotal}, Register: ${paperVal})`, data.match !== 'MATCH');
      } else {
        this.showNotificationModal("Error", 'Failed to record shift audit.', true);
      }
    } catch (e) {
      this.showNotificationModal("Error", 'Error recording shift audit.', true);
    }
  },

  loadWards: __async(function*() {
    try {
      const res = yield fetch('/api/config/wards?active_only=true');
      if (!res.ok) throw new Error('API returned ' + res.status);
      const wards = yield res.json();
      const sel = document.getElementById('visit-ward');
      if (!sel) return;
      sel.innerHTML = '';
      if (wards.length === 0) {
        sel.innerHTML = '<option value="OPD">OPD</option>';
      } else {
        wards.forEach(w => {
          sel.innerHTML += `<option value="${this.escape(w.name)}">${this.escape(w.name)}</option>`;
        });
      }
    } catch (e) {
      console.error('Error loading wards', e);
    }
  },

  loadClinicians: __async(function*() {
    try {
      const res = yield fetch('/api/config/clinicians');
      if (!res.ok) throw new Error('API returned ' + res.status);
      const clinicians = yield res.json();
      const sel = document.getElementById('visit-clinician');
      if (!sel) return;
      sel.innerHTML = '<option value="">(None)</option>';
      clinicians.forEach(c => {
        sel.innerHTML += `<option value="${c.id}">${this.escape(c.name)}</option>`;
      });
    } catch (e) {
      console.error('Error loading clinicians', e);
    }
  },


  loadTestOptionsMulti: __async(function*() {
    try {
      if (!this.sections) {
         try {
           const sres = yield fetch('/api/config/sections');
           if (sres.ok) this.sections = yield sres.json();
         } catch(e) { this.sections = []; }
      }
      const res = yield fetch('/api/config/tests');
      if (!res.ok) throw new Error('API returned ' + res.status);
      const tests = yield res.json();
      
      this.testCatalog = tests;
      
      const container = document.getElementById('visit-tests-container');
      if (!container) return;
      
      let html = '<div style="max-height: 150px; overflow-y: auto; border: 1px solid var(--border-color); border-radius: 4px; padding: 8px; background: #fff;">';
      
      const catSelect = document.getElementById('visit-test-section');
      if (catSelect && this.sections) {
        let catHtml = '<option value="all">All Sections</option>';
        this.sections.forEach(s => {
          catHtml += `<option value="${s.id}">${this.escape(s.name)}</option>`;
        });
        catSelect.innerHTML = catHtml;
      }
      
      tests.forEach(t => {
        if (!t.parent_rollup_id) {
          html += `
            <label class="visit-test-row" data-name="${this.escape(t.name).toLowerCase()}" data-category="${t.section_id}" style="display: block; margin-bottom: 4px; cursor: pointer;">
              <input type="checkbox" name="visit-test-cb" value="${t.id}">
              ${this.escape(t.name)}
            </label>
          `;
        }
      });
      html += '</div>';

      container.innerHTML = html;
    } catch (e) {
      console.error('Error loading tests', e);
    }
  },

  filterVisitTests: function() {
    const query = document.getElementById('visit-test-search').value.toLowerCase();
    const cat = document.getElementById('visit-test-section') ? document.getElementById('visit-test-section').value : 'all';
    const rows = document.querySelectorAll('.visit-test-row');
    rows.forEach(row => {
      const nameMatch = row.getAttribute('data-name').includes(query);
      const catMatch = (cat === 'all' || row.getAttribute('data-category') === cat);
      if (nameMatch && catMatch) {
        row.style.display = 'block';
      } else {
        row.style.display = 'none';
      }
    });
  },
  createVisit: __async(function*(pid) {
    const ward = document.getElementById('visit-ward').value;
    const clinician = document.getElementById('visit-clinician').value;
    const orderCat = document.getElementById('visit-order-category') ? document.getElementById('visit-order-category').value : 'in-house';
    const checkboxes = document.querySelectorAll('input[name="visit-test-cb"]:checked');
    const selectedTests = Array.from(checkboxes).map(cb => parseInt(cb.value, 10));
    
    if (selectedTests.length === 0) {
      this.showNotificationModal("Error", 'Select at least one test.', true);
      return;
    }
    
    try {
      const payload = {
        client_id: pid,
        ward_of_origin: ward,
        test_ids: selectedTests,
        order_category: orderCat
      };
      if (clinician) payload.clinician_id = parseInt(clinician, 10);
      
      const res = yield fetch('/api/visits', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        this.showNotificationModal("Success", 'Visit and orders created successfully!', false);
        // Uncheck all
        document.querySelectorAll('input[name="visit-test-cb"]').forEach(cb => cb.checked = false);
        yield this.loadPendingTests(pid);
        yield this.loadHistoricalVisits(pid);
      } else {
        this.showNotificationModal("Error", 'Failed to create visit.', true);
      }
    } catch(e) {
      this.showNotificationModal("Error", 'Error creating visit.', true);
    }
  },
  loadPendingTests: __async(function*(pid) {
    const container = document.getElementById('pending-tests-container');
    if (!container) return;
    try {
      const res = yield fetch(`/api/clients/${pid}/orders`);
      if (!res.ok) throw new Error('API returned ' + res.status);
      const orders = yield res.json();
      const pending = orders.filter(o => o.status === 'pending');
      
      if (pending.length === 0) {
        container.innerHTML = '<div style="color:var(--text-muted);">No pending tests.</div>';
        return;
      }
      
      let html = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <span style="font-size: 0.85rem; color: var(--text-muted);">${pending.length} pending test(s)</span>
          <button id="btn-bulk-delete-orders" class="btn btn-danger btn-sm" style="display: none;" onclick="app.bulkDeleteOrders()">
            Remove Selected (<span id="selected-orders-count">0</span>)
          </button>
        </div>
        <table style="width:100%; border-collapse:collapse; font-size:0.9rem;">
          <thead>
            <tr style="background: #f8fafc;">
              <th style="width:36px; text-align:center; padding:8px; border-bottom:1px solid #ddd;">
                <input type="checkbox" id="select-all-pending-tests" onchange="app.toggleSelectAllPendingOrders(this.checked)">
              </th>
              <th style="text-align:left; padding:8px; border-bottom:1px solid #ddd;">Test</th>
              <th style="text-align:left; padding:8px; border-bottom:1px solid #ddd;">Ordered At</th>
              <th style="text-align:right; padding:8px; border-bottom:1px solid #ddd;">Action</th>
            </tr>
          </thead>
          <tbody>
      `;
      pending.forEach(o => {
        html += `
          <tr>
            <td style="text-align:center; padding:8px; border-bottom:1px solid #ddd;">
              <input type="checkbox" class="pending-order-checkbox" value="${o.order_id}" onchange="app.onPendingOrderSelectionChange()">
            </td>
            <td style="padding:8px; border-bottom:1px solid #ddd;"><strong>${this.escape(o.test_name)}</strong><br><small style="color:var(--text-muted);">Order ID: ${o.order_id}</small></td>
            <td style="padding:8px; border-bottom:1px solid #ddd;">${o.ordered_at}</td>
            <td style="padding:8px; border-bottom:1px solid #ddd; text-align:right;">
              <button class="btn btn-primary btn-sm" onclick="app.showEnterResultModal(${o.order_id}, ${o.test_id}, '${this.escape(o.test_name)}', ${o.results && o.results.length > 0 ? `'${this.escape(o.results[0].result_value || '')}'` : 'null'}, ${o.results && o.results.length > 0 && o.results[0].result_unit ? `'${this.escape(o.results[0].result_unit)}'` : 'null'}, ${o.visit_id || 'null'})">
                ${o.results && o.results.length > 0 ? 'Edit Result' : 'Enter Result'}
              </button>
              <button class="btn btn-danger btn-sm" onclick="app.removeOrder(${o.order_id})">Remove</button>
            </td>
          </tr>
        `;
      });
      html += '</tbody></table>';
      container.innerHTML = html;
    } catch (e) {
      console.error(e);
      container.innerHTML = 'Error loading pending tests.';
    }
  },

  toggleSelectAllPendingOrders: function(checked) {
    const checkboxes = document.querySelectorAll('.pending-order-checkbox');
    checkboxes.forEach(cb => cb.checked = checked);
    this.onPendingOrderSelectionChange();
  },

  onPendingOrderSelectionChange: function() {
    const selected = document.querySelectorAll('.pending-order-checkbox:checked');
    const all = document.querySelectorAll('.pending-order-checkbox');
    const selectAllCb = document.getElementById('select-all-pending-tests');
    if (selectAllCb) {
      selectAllCb.checked = all.length > 0 && selected.length === all.length;
    }
    const btn = document.getElementById('btn-bulk-delete-orders');
    const countSpan = document.getElementById('selected-orders-count');
    if (btn && countSpan) {
      countSpan.textContent = selected.length;
      btn.style.display = selected.length > 0 ? 'inline-block' : 'none';
    }
  },

  bulkDeleteOrders: __async(function*() {
    const selected = Array.from(document.querySelectorAll('.pending-order-checkbox:checked')).map(cb => parseInt(cb.value, 10));
    if (selected.length === 0) return;

    this.confirmAction(
      "Remove Pending Tests",
      `Are you sure you want to remove ${selected.length} selected pending test order(s)?`,
      __async(function*() {
        try {
          const res = yield fetch('/api/orders/bulk', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ order_ids: selected })
          });
          if (res.ok) {
            const data = yield res.json();
            this.showNotificationModal("Success", `Removed ${data.deleted_order_ids.length} test order(s).`, false);
            if (this.currentClientId) {
              yield this.loadPendingTests(this.currentClientId);
            }
          } else {
            const err = yield res.json();
            this.showNotificationModal("Error", err.detail || "Failed to remove test orders.", true);
          }
        } catch(e) {
          console.error(e);
          this.showNotificationModal("Error", "Server error.", true);
        }
      }
    );
  },

  loadHistoricalVisits: __async(function*(pid) {
    const container = document.getElementById('historical-visits-container');
    if (!container) return;
    try {
      const res = yield fetch(`/api/clients/${pid}/visits`);
      if (!res.ok) throw new Error('API returned ' + res.status);
      const visits = yield res.json();
      if (visits.length === 0) {
        container.innerHTML = '<div style="color:var(--text-muted);">No historical visits found.</div>';
        return;
      }
      
      const isAdmin = this.currentUser && (this.currentUser.role === 'admin' || this.currentUser.role === 'superadmin');
      let html = '';
      if (isAdmin) {
        html += `
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; width: 100%; max-width: 800px;">
            <label style="display: flex; align-items: center; gap: 6px; font-size: 0.85rem; cursor: pointer; font-weight: 600;">
              <input type="checkbox" id="select-all-visits" onchange="app.toggleSelectAllVisits(this.checked)"> Select All Visits
            </label>
            <button id="btn-bulk-delete-visits" class="btn btn-danger btn-sm" style="display: none;" onclick="app.bulkDeleteVisits()">
              Delete Selected (<span id="selected-visits-count">0</span>)
            </button>
          </div>
        `;
      }
      visits.forEach(v => {
        const labNumStr = v.lab_number ? `(${this.escape(v.lab_number)})` : '(Pending Lab No)';
        if (isAdmin) {
          html += `<div style="display: grid; grid-template-columns: 36px 4fr 1fr 1fr 1fr; gap: 8px; align-items: center; margin-bottom: 8px; width: 100%; max-width: 800px;">
                    <div style="text-align: center;">
                      <input type="checkbox" class="visit-checkbox" value="${v.visit_id}" onchange="app.onVisitSelectionChange()">
                    </div>
                    <button class="btn btn-secondary btn-sm" style="text-align: left;" onclick="app.viewReport(${v.visit_id})">Visit ${v.visit_id} ${labNumStr} - ${v.created_at.split(' ')[0]}</button>
                    <button class="btn btn-secondary btn-sm" onclick="app.openEditVisitModal(${v.visit_id})">Edit</button>
                    <button class="btn btn-primary btn-sm" onclick="app.showAddTestModal(${v.visit_id})">Add Tests</button>
                    <button class="btn btn-danger btn-sm" onclick="app.deleteVisit(${v.visit_id})">Delete</button>
                   </div>`;
        } else {
          html += `<div style="display: grid; grid-template-columns: 4fr 1fr 1fr; gap: 8px; margin-bottom: 8px; width: 100%; max-width: 800px;">
                    <button class="btn btn-secondary btn-sm" style="text-align: left;" onclick="app.viewReport(${v.visit_id})">Visit ${v.visit_id} ${labNumStr} - ${v.created_at.split(' ')[0]}</button>
                    <button class="btn btn-secondary btn-sm" onclick="app.openEditVisitModal(${v.visit_id})">Edit</button>
                    <button class="btn btn-primary btn-sm" onclick="app.showAddTestModal(${v.visit_id})">Add Tests</button>
                   </div>`;
        }
      });
      container.innerHTML = html;
    } catch(e) {
      console.error(e);
      container.innerHTML = 'Error loading visits.';
    }
  },

  toggleSelectAllVisits: function(checked) {
    const checkboxes = document.querySelectorAll('.visit-checkbox');
    checkboxes.forEach(cb => cb.checked = checked);
    this.onVisitSelectionChange();
  },

  onVisitSelectionChange: function() {
    const selected = document.querySelectorAll('.visit-checkbox:checked');
    const all = document.querySelectorAll('.visit-checkbox');
    const selectAllCb = document.getElementById('select-all-visits');
    if (selectAllCb) {
      selectAllCb.checked = all.length > 0 && selected.length === all.length;
    }
    const btn = document.getElementById('btn-bulk-delete-visits');
    const countSpan = document.getElementById('selected-visits-count');
    if (btn && countSpan) {
      countSpan.textContent = selected.length;
      btn.style.display = selected.length > 0 ? 'inline-block' : 'none';
    }
  },

  bulkDeleteVisits: __async(function*() {
    const selected = Array.from(document.querySelectorAll('.visit-checkbox:checked')).map(cb => parseInt(cb.value, 10));
    if (selected.length === 0) return;

    this.confirmAction(
      "Delete Selected Visits",
      `Are you sure you want to delete ${selected.length} selected visit(s)? All associated test orders and results will be removed. This action cannot be undone.`,
      __async(function*() {
        try {
          const res = yield fetch('/api/visits/bulk', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ visit_ids: selected })
          });
          if (res.ok) {
            const data = yield res.json();
            this.showNotificationModal("Success", `Deleted ${data.deleted_visit_ids.length} visit(s).`, false);
            if (this.currentClientId) {
              yield this.loadHistoricalVisits(this.currentClientId);
              yield this.loadPendingTests(this.currentClientId);
            }
          } else {
            const err = yield res.json();
            this.showNotificationModal("Error", err.detail || "Failed to delete visits.", true);
          }
        } catch(e) {
          console.error(e);
          this.showNotificationModal("Error", "Server error.", true);
        }
      }
    );
  },

  deleteVisit: function(visitId) {
    this.confirmAction(
      "Delete Visit",
      `Are you sure you want to delete this visit? All associated test orders and results will be removed. This action cannot be undone.`,
      __async(function*() {
        try {
          const res = yield fetch(`/api/visits/${visitId}`, { method: 'DELETE' });
          if (res.ok) {
            this.showNotificationModal("Success", "Visit deleted successfully.", false);
            if (this.currentClientId) {
              yield this.loadHistoricalVisits(this.currentClientId);
              yield this.loadPendingTests(this.currentClientId);
            }
          } else {
            const err = yield res.json();
            this.showNotificationModal("Error", err.detail || "Failed to delete visit.", true);
          }
        } catch(e) {
          console.error(e);
          this.showNotificationModal("Error", "Server error.", true);
        }
      }
    );
  },
  viewReport: function(visitId) {
    const frame = document.getElementById('report-frame');
    if (frame) {
      frame.style.display = 'block';
      frame.src = `/api/reports/visit/${visitId}/pdf`;
    }
  },

  updateEditAgePlaceholder: function() {
    const cat = document.getElementById('edit-client-category').value;
    const ageInput = document.getElementById('edit-client-age');
    if (!ageInput) return;
    if (cat === 'Neonate') ageInput.placeholder = "e.g. 14d or 14/365";
    else if (cat === 'Infant') ageInput.placeholder = "e.g. 6m or 11/12";
    else if (cat === 'Toddler') ageInput.placeholder = "e.g. 2y or 1 6/12";
    else if (cat === 'Child') ageInput.placeholder = "e.g. 8, 8y";
    else ageInput.placeholder = "e.g. 25, 25y";
  },

  openEditClientModal: __async(function*(clientId) {
    try {
      const res = yield fetch(`/api/clients/${clientId}`);
      if (!res.ok) throw new Error("Failed to fetch client");
      const data = yield res.json();

      document.getElementById('edit-client-id').value = clientId;
      document.getElementById('edit-client-name').value = data.full_name || '';
      document.getElementById('edit-client-sex').value = data.sex || 'Male';
      document.getElementById('edit-client-age').value = data.age_display || '';
      document.getElementById('edit-client-phone').value = data.phone || '';

      const cat = data.age_category || 'Adult';
      const catSel = document.getElementById('edit-client-category');
      catSel.value = cat;
      this.updateEditAgePlaceholder();

      document.getElementById('edit-client-modal').style.display = 'flex';
    } catch(e) {
      console.error(e);
      this.showNotificationModal("Error", "Could not open edit form.", true);
    }
  },

  submitEditClient: __async(function*(event) {
    event.preventDefault();
    const clientId = document.getElementById('edit-client-id').value;
    const full_name = document.getElementById('edit-client-name').value.trim();
    const age_string = document.getElementById('edit-client-age').value.trim();
    const age_category = document.getElementById('edit-client-category').value;
    const sex = document.getElementById('edit-client-sex').value;
    const phone = document.getElementById('edit-client-phone').value.trim();

    const payload = { full_name, sex, phone, age_category };
    if (age_string) payload.age_string = age_string;

    try {
      const res = yield fetch(`/api/clients/${clientId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const updated = yield res.json();
        document.getElementById('edit-client-modal').style.display = 'none';
        // Update header name live
        const nameSpan = document.getElementById('client-header-name');
        if (nameSpan) nameSpan.textContent = updated.full_name || full_name;
        // Update cached data
        if (this.currentClientData) {
          this.currentClientData.full_name = updated.full_name || full_name;
          this.currentClientData.sex = updated.sex || sex;
          this.currentClientData.phone = updated.phone || phone;
          this.currentClientData.age_category = updated.age_category || age_category;
        }
        // Refresh client list so search shows updated name
        yield this.searchClients('');
        this.showNotificationModal("Success", "Client details updated successfully.", false);
      } else {
        const err = yield res.json();
        this.showNotificationModal("Error", err.detail || "Failed to update client.", true);
      }
    } catch(e) {
      this.showNotificationModal("Error", "Connection error.", true);
    }
  },

  openEditVisitModal: __async(function*(visitId) {
    try {
      const res = yield fetch(`/api/visits/${visitId}`);
      if (!res.ok) throw new Error('Failed to load visit details');
      const data = yield res.json();
      
      document.getElementById('edit-visit-id').value = visitId;
      
      // Populate ward dropdown
      const wardSelect = document.getElementById('edit-visit-ward');
      wardSelect.innerHTML = '';
      try {
        const wRes = yield fetch('/api/config/wards?active_only=true');
        const wards = yield wRes.json();
        wards.forEach(w => {
          const opt = document.createElement('option');
          opt.value = w.name;
          opt.textContent = w.name;
          wardSelect.appendChild(opt);
        });
      } catch(e) {}
      wardSelect.value = data.ward_of_origin || '';
      
      // Populate clinician dropdown
      const clinSelect = document.getElementById('edit-visit-clinician');
      clinSelect.innerHTML = '<option value="">-- None --</option>';
      try {
        const cRes = yield fetch('/api/config/clinicians');
        const clins = yield cRes.json();
        clins.forEach(cl => {
          const opt = document.createElement('option');
          opt.value = cl.id;
          opt.textContent = cl.name;
          clinSelect.appendChild(opt);
        });
      } catch(e) {}
      clinSelect.value = data.clinician_id || '';
      
      // Set order category — use first order's category as current value
      const catSelect = document.getElementById('edit-visit-order-category');
      if (data.orders && data.orders.length > 0 && data.orders[0].order_category) {
        catSelect.value = data.orders[0].order_category;
      } else {
        catSelect.value = 'in-house';
      }

      // Render tests in this visit with current results and Edit Result action
      const ordersList = document.getElementById('edit-visit-orders-list');
      if (ordersList) {
        if (!data.orders || data.orders.length === 0) {
          ordersList.innerHTML = '<div style="color:var(--text-muted); font-size:0.85rem;">No tests attached to this visit.</div>';
        } else {
          const isAdmin = this.currentUser && (this.currentUser.role === 'admin' || this.currentUser.role === 'superadmin');
          let oHtml = '<table style="width:100%; border-collapse:collapse; font-size:0.875rem;">';
          oHtml += '<thead><tr style="border-bottom:2px solid #e2e8f0; color:var(--text-muted); text-align:left; background:#f8fafc;"><th style="padding:8px 12px;">Test Name</th><th style="padding:8px 12px;">Section</th><th style="padding:8px 12px;">Category</th><th style="padding:8px 12px;">Current Result</th><th style="padding:8px 12px; text-align:right;">Action</th></tr></thead><tbody>';
          data.orders.forEach(o => {
            const hasResult = o.results && o.results.length > 0;
            const resVal = hasResult ? (o.results[0].result_value || 'Completed') : '<span style="color:var(--text-muted); font-style:italic;">Pending Entry</span>';
            const resUnit = hasResult && o.results[0].result_unit ? ` ${this.escape(o.results[0].result_unit)}` : '';
            const catText = this.escape(o.order_category || 'in-house');
            oHtml += `
              <tr style="border-bottom:1px solid #f1f5f9;">
                <td style="padding:10px 12px;"><strong>${this.escape(o.test_name)}</strong></td>
                <td style="padding:10px 12px; color:var(--text-muted); font-size:0.85rem;">${this.escape(o.section_name || '—')}</td>
                <td style="padding:10px 12px; text-transform:capitalize; font-size:0.85rem;">${catText}</td>
                <td style="padding:10px 12px;"><strong>${resVal}</strong>${resUnit}</td>
                <td style="padding:10px 12px; text-align:right;">
                  ${isAdmin ? `<button type="button" class="btn btn-secondary btn-sm" style="padding:4px 12px;" onclick="app.showEnterResultModal(${o.order_id}, ${o.test_id}, '${this.escape(o.test_name)}', '${hasResult ? this.escape(o.results[0].result_value || '') : ''}', '${hasResult && o.results[0].result_unit ? this.escape(o.results[0].result_unit) : ''}', ${visitId})">${hasResult ? 'Edit Result' : 'Enter Result'}</button>` : ''}
                </td>
              </tr>
            `;
          });
          oHtml += '</tbody></table>';
          ordersList.innerHTML = oHtml;
        }
      }
      
      document.getElementById('edit-visit-modal').style.display = 'flex';
    } catch(e) {
      console.error(e);
      this.showNotificationModal("Error", "Could not load visit details.", true);
    }
  },

  submitEditVisit: __async(function*(e) {
    e.preventDefault();
    const visitId = document.getElementById('edit-visit-id').value;
    const ward = document.getElementById('edit-visit-ward').value;
    const clinicianId = document.getElementById('edit-visit-clinician').value;
    const orderCat = document.getElementById('edit-visit-order-category').value;

    try {
      const res = yield fetch(`/api/visits/${visitId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ward_of_origin: ward,
          clinician_id: clinicianId ? parseInt(clinicianId, 10) : null,
          order_category: orderCat
        })
      });
      if (res.ok) {
        this.showNotificationModal("Success", "Visit details updated successfully.", false);
        document.getElementById('edit-visit-modal').style.display = 'none';
        if (this.currentClientId) {
          yield this.loadHistoricalVisits(this.currentClientId);
        }
      } else {
        const err = yield res.json();
        this.showNotificationModal("Error", err.detail || "Failed to update visit.", true);
      }
    } catch(err) {
      this.showNotificationModal("Error", "Connection error.", true);
    }
  },

  showAddTestModal: __async(function*(visitId) {
    document.getElementById('add-test-visit-id').value = visitId;
    document.getElementById('add-test-search').value = '';
    const container = document.getElementById('add-tests-container');
    container.innerHTML = 'Loading...';
    document.getElementById('add-test-modal').style.display = 'flex';

    if (!this.sections || this.sections.length === 0) {
      try {
        const sres = yield fetch('/api/config/sections');
        if (sres.ok) this.sections = yield sres.json();
      } catch(e) { this.sections = []; }
    }

    const secSelect = document.getElementById('add-test-section');
    if (secSelect && this.sections) {
      let secHtml = '<option value="all">All Sections</option>';
      this.sections.forEach(s => {
        secHtml += `<option value="${s.id}">${this.escape(s.name)}</option>`;
      });
      secSelect.innerHTML = secHtml;
      secSelect.value = 'all';
    }

    if (!this.testCatalog || this.testCatalog.length === 0) {
      try {
        const res = yield fetch('/api/config/tests');
        if (res.ok) this.testCatalog = yield res.json();
      } catch(e) {}
    }
    
    if (this.testCatalog) {
      let html = '';
      this.testCatalog.forEach(t => {
        if (!t.parent_rollup_id) {
          html += `
            <label class="add-test-row" data-name="${this.escape(t.name).toLowerCase()}" data-category="${t.section_id}" style="display: block; margin-bottom: 4px; cursor: pointer;">
              <input type="checkbox" name="add-test-cb" value="${t.id}">
              ${this.escape(t.name)}
            </label>
          `;
        }
      });
      container.innerHTML = html;
    }
  },

  filterAddTests: function() {
    const query = document.getElementById('add-test-search').value.toLowerCase();
    const cat = document.getElementById('add-test-section') ? document.getElementById('add-test-section').value : 'all';
    const rows = document.querySelectorAll('.add-test-row');
    rows.forEach(row => {
      const nameMatch = row.getAttribute('data-name').includes(query);
      const catMatch = (cat === 'all' || row.getAttribute('data-category') === cat);
      if (nameMatch && catMatch) {
        row.style.display = 'block';
      } else {
        row.style.display = 'none';
      }
    });
  },

  submitAddTests: __async(function*() {
    const visitId = document.getElementById('add-test-visit-id').value;
    const orderCat = document.getElementById('add-test-order-category').value;
    const checkboxes = document.querySelectorAll('input[name="add-test-cb"]:checked');
    const selectedTests = Array.from(checkboxes).map(cb => parseInt(cb.value, 10));
    
    if (selectedTests.length === 0) {
      this.showNotificationModal("Notice", "Select at least one test to add.", false);
      return;
    }
    
    try {
      const res = yield fetch(`/api/visits/${visitId}/orders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ test_ids: selectedTests, order_category: orderCat })
      });
      if (res.ok) {
        this.showNotificationModal("Success", "Tests added to visit successfully.", false);
        document.getElementById('add-test-modal').style.display = 'none';
        if (this.currentClientId) {
           yield this.loadPendingTests(this.currentClientId);
        }
      } else {
        const err = yield res.json();
        this.showNotificationModal("Error", err.detail || "Failed to add tests.", true);
      }
    } catch(e) {
      this.showNotificationModal("Error", "Connection error.", true);
    }
  },


  removeOrder: __async(function*(orderId) {
    app.confirmAction("Confirm Removal", "Are you sure you want to remove this pending test?", __async(function*() {
      try {
        const res = yield fetch(`/api/orders/${orderId}`, { method: 'DELETE' });
        if (res.ok) {
          app.showNotificationModal("Success", "Test order removed.", false);
          if (app.currentClientId) {
            yield app.loadPendingTests(app.currentClientId);
          }
        } else {
          const err = yield res.json();
          app.showNotificationModal("Error", err.detail || "Failed to remove test order.", true);
        }
      } catch(e) {
        app.showNotificationModal("Error", "Connection error.", true);
      }
    });
  },


  toggleAnalyzerPaste: function(show = null) {
    const container = document.getElementById('analyzer-paste-container');
    if (!container) return;
    if (show === null) {
      container.style.display = container.style.display === 'none' ? 'block' : 'none';
    } else {
      container.style.display = show ? 'block' : 'none';
    }
    if (container.style.display === 'block') {
      const input = document.getElementById('analyzer-raw-input');
      if (input) input.focus();
    }
  },

  parseAndPopulateAnalyzerData: __async(function*() {
    const rawText = document.getElementById('analyzer-raw-input').value.trim();
    const statusSpan = document.getElementById('analyzer-parse-status');
    if (!rawText) {
      this.showNotificationModal("Error", "Please paste raw output from the analyzer first.", true);
      return;
    }

    try {
      const res = yield fetch('/api/integrations/parse-analyzer-output', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ analyzer_type: 'nihon_kohden', raw_text: rawText })
      });

      if (!res.ok) {
        const err = yield res.json();
        this.showNotificationModal("Parsing Failed", err.detail || "Failed to parse analyzer output.", true);
        return;
      }

      const data = yield res.json();
      if (data.status !== 'success' || !data.parameters) {
        this.showNotificationModal("Error", "No parameters extracted from output.", true);
        return;
      }

      // Populate each parameter input row by matching name
      let populatedCount = 0;
      const paramRows = document.querySelectorAll('.modal-param-row');
      data.parameters.forEach(p => {
        paramRows.forEach(row => {
          const nameEl = row.querySelector('strong');
          if (nameEl && nameEl.textContent.trim().toLowerCase() === p.name.trim().toLowerCase()) {
            const input = row.querySelector('.modal-param-val');
            if (input) {
              input.value = p.value;
              // store device flag if present
              if (p.flag) {
                row.setAttribute('data-device-flag', p.flag);
              }
              populatedCount++;
            }
          }
        });
      });

      if (statusSpan) {
        statusSpan.textContent = `Captured: ${populatedCount} parameters (Sample: ${data.sample_id || 'N/A'})`;
      }
      this.showNotificationModal("Success", `Captured ${populatedCount} CBC parameters from ${data.device_model || 'Analyzer'}. Review values and save.`, false);
      this.toggleAnalyzerPaste(false);
    } catch(err) {
      console.error(err);
      this.showNotificationModal("Error", "Failed to connect to parser service.", true);
    }
  },

  showEnterResultModal: __async(function*(orderId, testId, testName, existingVal = null, existingUnit = null, visitId = null) {
    document.getElementById('result-entry-order-id').value = orderId;
    document.getElementById('result-entry-test-id').value = testId;
    document.getElementById('result-entry-visit-id').value = visitId || '';
    document.getElementById('result-entry-test-name').textContent = testName;

    const isEdit = existingVal !== null && existingVal !== undefined && existingVal !== '';
    document.getElementById('result-entry-is-edit').value = isEdit ? '1' : '0';
    
    const titleElem = document.getElementById('result-entry-modal-title');
    if (titleElem) titleElem.textContent = isEdit ? 'Edit Result' : 'Enter Result';

    const reasonGroup = document.getElementById('result-entry-reason-group');
    const reasonInput = document.getElementById('result-entry-reason');
    if (reasonGroup) {
      reasonGroup.style.display = isEdit ? 'block' : 'none';
      if (reasonInput) reasonInput.value = '';
    }

    const analyzerSection = document.getElementById('result-entry-analyzer-section');
    const isCBC = testName.toLowerCase().includes('cbc') || testName.toLowerCase().includes('complete blood count');
    if (analyzerSection) {
      analyzerSection.style.display = isCBC ? 'block' : 'none';
      this.toggleAnalyzerPaste(false);
      const rawInput = document.getElementById('analyzer-raw-input');
      if (rawInput) rawInput.value = '';
      const statusSpan = document.getElementById('analyzer-parse-status');
      if (statusSpan) statusSpan.textContent = '';
    }
    
    // Ensure testCatalog is loaded
    if (!this.testCatalog || this.testCatalog.length === 0) {
      try {
        const res = yield fetch('/api/config/tests');
        if (res.ok) this.testCatalog = yield res.json();
      } catch(e) {}
    }
    
    const singleContainer = document.getElementById('result-entry-single-container');
    const paramsContainer = document.getElementById('result-entry-params-container');
    const trackGroup = document.getElementById('result-entry-tracked-group');
    if (trackGroup) trackGroup.style.display = 'none';
    
    paramsContainer.style.display = 'none';
    singleContainer.style.display = 'block';
    
    const nameLower = testName.toLowerCase();
    const test = (this.testCatalog || []).find(t => t.id === testId) || {};
    
    // Tailored Forms
    if (nameLower.includes('urinalysis')) {
       // URINALYSIS FULL MODAL — 3-section panel via API sub-parameters
       singleContainer.style.display = 'none';
       paramsContainer.style.display = 'block';
       // Fetch sub-parameters from the API (same endpoint as CBC uses via children/tests)
       var uaParamRes = yield fetch('/api/config/tests/' + testId + '/children');
       var uaParams = [];
       if (uaParamRes.ok) {
         uaParams = yield uaParamRes.json();
       }
       // Sort by sort_order
       uaParams.sort(function(a, b) { return (a.sort_order || 0) - (b.sort_order || 0); });

       // Section groupings by sort_order
       // Macroscopy: 1-2, Microscopy: 3-7, Dipstick: 8-17
       var UA_SECTIONS = [
         { label: 'Macroscopy', min: 1, max: 2 },
         { label: 'Microscopy', min: 3, max: 7 },
         { label: 'Dry Chemistry Dipstick', min: 8, max: 17 }
       ];

       var uaHtml = '';
       UA_SECTIONS.forEach(function(sec) {
         var secParams = uaParams.filter(function(p) {
           var so = p.sort_order || 0;
           return so >= sec.min && so <= sec.max;
         });
         if (!secParams.length) return;
         uaHtml += '<div style="margin-bottom: 18px;">';
         uaHtml += '<h5 style="margin: 0 0 10px 0; padding-bottom: 4px; border-bottom: 1px solid var(--border-color); color: var(--primary-color);">' + sec.label + '</h5>';
         uaHtml += '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px 18px;">';
         secParams.forEach(function(p) {
           var opts = [];
           try { if (p.options) opts = JSON.parse(p.options); } catch(e) {}
           var inputHtml = '';
           if (opts && opts.length > 0) {
             var optsHtml = opts.map(function(o) {
               return '<option value="' + o.replace(/"/g, '&quot;') + '">' + o + '</option>';
             }).join('');
             inputHtml = '<select class="modal-param-val" style="width:100%; padding:6px 8px; border:1px solid var(--border-color); border-radius:4px; font-size:0.85rem;">' + optsHtml + '</select>';
           } else {
             inputHtml = '<input type="text" class="modal-param-val" placeholder="Value" style="width:100%; padding:6px 8px; border:1px solid var(--border-color); border-radius:4px; font-size:0.85rem;">';
           }
           uaHtml += '<div class="modal-param-row" data-param-id="' + p.id + '" style="display:flex; flex-direction:column; gap:3px;">';
           uaHtml += '<label style="font-size:0.8rem; font-weight:600; color:var(--text-dark);">' + p.name + '</label>';
           uaHtml += inputHtml;
           uaHtml += '</div>';
         });
         uaHtml += '</div></div>';
       });
       paramsContainer.innerHTML = uaHtml;
    } else if (nameLower.includes('widal')) {
       singleContainer.innerHTML = `
         <label>Result:</label>
         <select id="widal-res" onchange="document.getElementById('widal-titers').style.display = this.value==='Positive' ? 'block' : 'none'" style="width:100%; padding:8px; margin-bottom:8px;">
           <option>Negative</option><option>Positive</option>
         </select>
         <div id="widal-titers" style="display:none;">
           <label>Titers (if Positive):</label>
           <input type="text" id="widal-tit-val" placeholder="e.g. TO 1:160, TH 1:80" style="width:100%; padding:8px;">
         </div>
       `;
    } else {
        // Use the new dynamic system
        let options = [];
        try {
            if (test.options) options = JSON.parse(test.options);
        } catch (e) {}

        if (test.result_type === 'qualitative' || test.result_type === 'semi_quantitative') {
            if (options && options.length > 0) {
                let optsHtml = options.map(o => `<option value="${this.escape(o)}">${this.escape(o)}</option>`).join('');
                singleContainer.innerHTML = `
                  <label>Result:</label>
                  <select id="qual-res" style="width:100%; padding:8px;">
                    ${optsHtml}
                  </select>
                `;
            } else {
                singleContainer.innerHTML = `
                  <label>Result:</label>
                  <input type="text" id="result-entry-value" placeholder="Enter text result" style="width:100%; padding:8px;">
                `;
            }
        } else {
            // quantitative
            let unitHtml = '';
            if (test.default_unit && test.secondary_unit) {
                unitHtml = `<select id="result-entry-unit" style="padding: 8px; border: 1px solid var(--border-color); border-radius: 4px;">
                    <option value="${this.escape(test.default_unit)}">${this.escape(test.default_unit)}</option>
                    <option value="${this.escape(test.secondary_unit)}">${this.escape(test.secondary_unit)}</option>
                </select>`;
            } else if (test.default_unit) {
                unitHtml = `<span style="padding: 8px; background: var(--bg-color); border: 1px solid var(--border-color); border-radius: 4px;">${this.escape(test.default_unit)}</span>`;
            }
            singleContainer.innerHTML = `
              <div class="form-group" style="margin-bottom: 16px;">
                <label>Result Value:</label>
                <div style="display: flex; gap: 8px;">
                    <input type="number" step="any" id="result-entry-value" value="${isEdit ? this.escape(existingVal) : ''}" placeholder="Enter Value${test.ref_range ? '. Ref: ' + this.escape(test.ref_range) : ''}" style="flex: 1; padding: 8px;">
                    ${unitHtml}
                </div>
              </div>
            `;
            if (isEdit && existingUnit && document.getElementById('result-entry-unit')) {
              document.getElementById('result-entry-unit').value = existingUnit;
            }
        }
        // Check for test parameters from test_parameters table
        try {
          const paramRes = yield fetch(`/api/config/tests/${testId}/parameters`);
          let paramsList = [];
          if (paramRes.ok) {
            paramsList = yield paramRes.json();
          }

          if (paramsList && paramsList.length > 0) {
            singleContainer.style.display = 'none';
            paramsContainer.style.display = 'block';
            let html = '<h5 style="color: var(--primary-color); margin-bottom: 8px;">Panel Parameters:</h5>';
            paramsList.forEach(p => {
              let unitDisplay = '';
              if (p.unit && p.secondary_unit) {
                unitDisplay = `<select class="modal-param-unit" style="padding: 2px 4px; font-size: 0.8rem; border: 1px solid var(--border-color); border-radius: 4px;">
                  <option value="${this.escape(p.unit)}">${this.escape(p.unit)}</option>
                  <option value="${this.escape(p.secondary_unit)}">${this.escape(p.secondary_unit)}</option>
                </select>`;
              } else if (p.unit) {
                unitDisplay = `<span class="modal-param-unit" data-unit="${this.escape(p.unit)}" style="font-size: 0.8rem; color: var(--text-muted);">${this.escape(p.unit)}</span>`;
              }
              html += `
                 <div style="display: grid; grid-template-columns: 1.8fr 1.1fr 1.1fr; gap: 8px; align-items: center; padding: 6px 0; border-bottom: 1px solid #edf2f7;" class="modal-param-row" data-param-id="${p.id}">
                   <div><strong style="font-size: 0.85rem; color: var(--text-dark);">${this.escape(p.parameter_name)}</strong></div>
                   <div><input type="text" class="modal-param-val" placeholder="Value" style="width: 100%; padding: 6px 8px; border: 1px solid var(--border-color); border-radius: 4px; box-sizing: border-box; font-size: 0.85rem;"></div>
                   <div style="display: flex; gap: 4px; align-items: center;">
                     ${unitDisplay}
                     ${p.ref_range ? `<span style="font-size: 0.75rem; color: var(--text-muted); white-space: nowrap;">(${this.escape(p.ref_range)})</span>` : ''}
                   </div>
                 </div>
               `;
            });
            paramsContainer.innerHTML = html;
          }
        } catch(e) { console.error(e); }
    }
    document.getElementById('result-entry-modal').style.display = 'flex';
    
    // Add keyboard navigation
    const form = document.getElementById('result-entry-form');
    const inputs = Array.from(form.querySelectorAll('input:not([type="hidden"]), select'));
    inputs.forEach((input, index) => {
        input.onkeydown = (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const nextInput = inputs[index + 1];
                if (nextInput) {
                    nextInput.focus();
                } else {
                    form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
                }
            }
        };
    });
    
    form.onsubmit = __async(function*(e) {
       e.preventDefault();
       
       let finalVal = null;
       let paramResults = null;
       
       if (paramsContainer.style.display === 'block') {
         paramResults = [];
         const rows = paramsContainer.querySelectorAll('.modal-param-row');
         rows.forEach(r => {
            const pid = parseInt(r.getAttribute('data-param-id'), 10);
            const pval = r.querySelector('.modal-param-val').value.trim();
            const uElem = r.querySelector('.modal-param-unit');
            let punit = null;
            if (uElem) {
              punit = uElem.tagName === 'SELECT' ? uElem.value : (uElem.getAttribute('data-unit') || uElem.textContent.trim());
            }
            if (pval) {
              paramResults.push({ parameter_id: pid, result_value: pval });
            }
         });
        } else if (nameLower.includes('widal')) {
         const res = document.getElementById('widal-res').value;
         const tit = document.getElementById('widal-tit-val').value;
         finalVal = res === 'Positive' && tit ? `${res} (${tit})` : res;
       } else if (document.getElementById('qual-res')) {
         finalVal = document.getElementById('qual-res').value;
       } else {
         finalVal = document.getElementById('result-entry-value').value.trim();
       }
       
       if ((!paramResults || paramResults.length === 0) && !finalVal) {
           app.showNotificationModal("Error", "Result cannot be empty.", true);
           return;
       }
       
       try {
         if (paramResults && paramResults.length > 0) {
           const isEditMode = document.getElementById('result-entry-is-edit') ? document.getElementById('result-entry-is-edit').value === '1' : false;
           const editReason = document.getElementById('result-entry-reason') ? document.getElementById('result-entry-reason').value.trim() : '';

           const res = yield fetch('/api/clients/results', {
             method: 'POST',
             headers: { 'Content-Type': 'application/json' },
             body: JSON.stringify({
               order_id: orderId,
               result_value: "Completed",
               parameter_results: paramResults,
               edit_reason: isEditMode ? editReason : null
             })
           });
           if (!res.ok) {
             const err = yield res.json();
             app.showNotificationModal("Error", err.detail || "Failed to save results.", true);
             return;
           }
         } else {
            // Single order
            const unitElem = document.getElementById('result-entry-unit');
            const selectedUnit = unitElem ? (unitElem.tagName === 'SELECT' ? unitElem.value : unitElem.textContent.trim()) : null;
            const isEditMode = document.getElementById('result-entry-is-edit') ? document.getElementById('result-entry-is-edit').value === '1' : false;
            const editReason = document.getElementById('result-entry-reason') ? document.getElementById('result-entry-reason').value.trim() : '';

            if (isEditMode) {
              const isAdmin = this.currentUser && (this.currentUser.role === 'admin' || this.currentUser.role === 'superadmin');
              if (!isAdmin) {
                this.showNotificationModal("Error", "Only administrators can edit saved results.", true);
                return;
              }
              if (!editReason) {
                this.showNotificationModal("Error", "Reason for edit is required.", true);
                return;
              }
            }

            const payload = {
              order_id: orderId,
              result_value: finalVal,
              result_unit: selectedUnit,
              edit_reason: isEditMode ? editReason : null
            };
            const res = yield fetch('/api/clients/results', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(payload)
            });
            if (!res.ok) {
              const err = yield res.json();
              this.showNotificationModal("Error", err.detail || "Failed to save result.", true);
              return;
            }
         }
         
         this.showNotificationModal("Success", "Result saved successfully!", false);
         document.getElementById('result-entry-modal').style.display = 'none';
         if (this.currentClientId) {
            yield this.loadPendingTests(this.currentClientId);
            yield this.loadHistoricalVisits(this.currentClientId);
         }
         // Also refresh the edit visit modal tests list if it's currently open
         const editVisitId = (document.getElementById('edit-visit-id') ? document.getElementById('edit-visit-id').value : null);
         if (editVisitId && (document.getElementById('edit-visit-modal') ? document.getElementById('edit-visit-modal').style.display : null) !== 'none') {
           yield this.openEditVisitModal(parseInt(editVisitId, 10));
         }
       } catch(err) {
         this.showNotificationModal("Error", "Connection error saving result.", true);
       }
    };
  },




  submitTestResult: __async(function*(pid) {
    const tid = parseInt(document.getElementById('order-test-select').value, 10);
    const sampleId = document.getElementById('order-sample-id').value;
    const isPos = document.getElementById('order-result-pos').value === 'true';

    const paramRows = document.querySelectorAll('.panel-param-row');
    let paramResults = null;
    let mainResultValue = null;

    if (paramRows.length > 0) {
      paramResults = [];
      paramRows.forEach(row => {
        const paramId = parseInt(row.getAttribute('data-param-id'), 10);
        const val = row.querySelector('.param-val-input').value;
        const pos = row.querySelector('.param-pos-check').checked;
        if (val) {
          paramResults.push({ parameter_id: paramId, result_value: val, is_positive: pos });
        }
      });
      if (paramResults.length === 0) {
        this.showNotificationModal("Error", 'Please enter at least one parameter result for this panel.', true);
        return;
      }
    } else {
      mainResultValue = document.getElementById('order-result-value').value;
      if (!mainResultValue) {
        this.showNotificationModal("Error", 'Please enter a result value.', true);
        return;
      }
    }

    try {
      // 1. Create order
      const ordRes = yield fetch('/api/clients/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_id: pid, test_id: tid, sample_id: sampleId })
      });

      if (!ordRes.ok) throw new Error('Order creation failed');
      const ordData = yield ordRes.json();

      // 2. Submit result
      const resRes = yield fetch('/api/clients/results', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          order_id: ordData.order_id,
          result_value: mainResultValue,
          is_positive: isPos,
          parameter_results: paramResults
        })
      });

      if (resRes.ok) {
        this.showNotificationModal("Success", 'Result recorded successfully! Daily Log auto-incremented.', false);
        yield this.loadClientOrders(pid);
        // Print removed to avoid race conditions
      } else {
        this.showNotificationModal("Error", 'Failed to record result.', true);
      }
    } catch (e) {
      this.showNotificationModal("Error", 'Error submitting result.', true);
    }
  },

  loadClientOrders: __async(function*(pid) {
    const frame = document.getElementById('report-frame');
    if (frame) {
      frame.src = `/api/reports/client/${pid}/pdf`;
    }
  },

  showNewClientModal: function() {
    document.getElementById('new-client-form').reset();
    document.getElementById('new-client-modal').style.display = 'flex';
    document.getElementById('client-name').focus();
  },

  closeNewClientModal: function() {
    document.getElementById('new-client-modal').style.display = 'none';
  },

  updateAgePlaceholder: function() {
    const cat = document.getElementById('client-category').value;
    const ageInput = document.getElementById('client-age');
    if (!ageInput) return;
    if (cat === 'Neonate') ageInput.placeholder = "e.g. 14/365 or 14d";
    else if (cat === 'Infant') ageInput.placeholder = "e.g. 11/12 or 11m";
    else if (cat === 'Toddler') ageInput.placeholder = "e.g. 1 3/12 or 2y";
    else ageInput.placeholder = "e.g. 25, 25y";
  },

  handleRegisterClientSubmit: __async(function*(e) {
    e.preventDefault();
    const pname = document.getElementById('client-name').value.trim();
    const psex = document.getElementById('client-sex').value;
    const pcategory = document.getElementById('client-category').value;
    const pageStr = document.getElementById('client-age').value.trim();
    const pphone = document.getElementById('client-phone').value.trim();
    
    if (!pname || !pageStr) return;
    
    // Strict Age Validation
    let ageYrs = 0;
    const lowerAge = pageStr.toLowerCase().replace(/ /g, '');
    if (lowerAge.includes('d') || lowerAge.includes('/365')) {
       ageYrs = parseInt(lowerAge) / 365.25;
    } else if (lowerAge.includes('m') || lowerAge.includes('/12')) {
       // Support '1 3/12' format by checking if there's a space? We stripped spaces.
       // It's safer to just parse the first number if it's '11m'.
       const parts = pageStr.split(' ');
       if (parts.length > 1 && parts[1].includes('/12')) {
          ageYrs = parseInt(parts[0]) + (parseInt(parts[1]) / 12);
       } else {
          ageYrs = parseInt(lowerAge) / 12;
       }
    } else {
       ageYrs = parseFloat(lowerAge);
    }
    
    if (isNaN(ageYrs)) {
        app.showNotificationModal("Error", "Invalid age format.", true);
        return;
    }
    
    let isValid = true;
    if (pcategory === 'Neonate' && ageYrs > 0.0768) isValid = false;
    else if (pcategory === 'Infant' && (ageYrs <= 0.0768 || ageYrs > 1)) isValid = false;
    else if (pcategory === 'Toddler' && (ageYrs <= 1 || ageYrs > 3)) isValid = false;
    else if (pcategory === 'Child' && (ageYrs <= 3 || ageYrs > 14)) isValid = false;
    else if (pcategory === 'Adult' && ageYrs < 15) isValid = false;

    if (!isValid) {
      app.showNotificationModal("Error", "Age does not match selected category.", true);
      return;
    }
    
    try {
      const res = yield fetch('/api/clients', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          full_name: pname,
          sex: psex,
          age_category: pcategory,
          age_string: pageStr,
          phone: pphone
        })
      });

      if (res.ok) {
        const data = yield res.json();
        app.showNotificationModal("Success", `Client registered successfully! Assigned ID: ${data.client_number}`, false);
        app.closeNewClientModal();
        app.searchClients('');
      } else {
        this.showNotificationModal("Error", 'Error registering client.', true);
      }
    } catch (error) {
      this.showNotificationModal("Error", 'Connection error.', true);
    }
  },

  // Configuration View

  renderConfig: __async(function*(container) {
    const isSuperAdmin = this.currentUser && this.currentUser.role === 'superadmin';

    container.innerHTML = `
      <details class="card" style="margin-bottom: 16px;" open>
        <summary class="card-header" style="cursor: pointer; list-style: none;">
          <span class="card-title">${this.icon('settings')} Test Catalog & Section Configuration</span>
        </summary>
        <div style="padding: 16px;">
          <button class="btn btn-primary" onclick="app.openTestConfigModal()" style="margin-bottom: 12px;">${this.icon('plus')} Add New Test</button>
          <div id="config-table-container">
            <p style="color: var(--text-muted);">Loading configuration...</p>
          </div>
        </div>
      </details>

      <details class="card" style="margin-bottom: 16px;">
        <summary class="card-header" style="cursor: pointer; list-style: none;">
          <span class="card-title">${this.icon('building')} Wards Configuration</span>
        </summary>
        <div style="padding: 16px;">
          <button class="btn btn-primary" onclick="app.showAddWardModal()" style="margin-bottom: 12px;">${this.icon('plus')} Add Ward</button>
          <div id="wards-table-container">
            <p style="color: var(--text-muted);">Loading wards...</p>
          </div>
        </div>
      </details>
      
      <details class="card" style="margin-bottom: 16px;">
        <summary class="card-header" style="cursor: pointer; list-style: none;">
          <span class="card-title">${this.icon('stethoscope')} Clinicians Configuration</span>
        </summary>
        <div style="padding: 16px;">
          <button class="btn btn-primary" onclick="app.showAddClinicianModal()" style="margin-bottom: 12px;">${this.icon('plus')} Add Clinician</button>
          <div id="clinicians-table-container">
            <p style="color: var(--text-muted);">Loading clinicians...</p>
          </div>
        </div>
      </details>

      ${isSuperAdmin ? `
      <details class="card" style="margin-bottom: 16px;">
        <summary class="card-header" style="cursor: pointer; list-style: none;">
          <span class="card-title">${this.icon('user-plus')} Pending Registration Requests</span>
        </summary>
        <div id="pending-users-container" style="padding: 16px;">
          <p style="color: var(--text-muted);">Loading pending requests...</p>
        </div>
      </details>

      <details class="card" style="margin-bottom: 16px;">
        <summary class="card-header" style="cursor: pointer; list-style: none;">
          <span class="card-title">${this.icon('users')} Active Lab Staff Accounts</span>
        </summary>
        <div id="active-users-container" style="padding: 16px;">
          <p style="color: var(--text-muted);">Loading accounts...</p>
        </div>
      </details>
      ` : ''}
    `;
    yield this.loadConfigData();
    yield this.loadWardsConfig();
    yield this.loadCliniciansConfig();
  },


  
  loadWardsConfig: __async(function*() {
    try {
      const res = yield fetch('/api/config/wards');
      if (!res.ok) throw new Error('API returned ' + res.status);
      const wards = yield res.json();
      let rows = '';
      wards.forEach(w => {
        rows += `
          <tr>
            <td><strong>${this.escape(w.name)}</strong></td>
            <td>${w.is_active ? '<span style="color:green;">Active</span>' : '<span style="color:red;">Inactive</span>'}</td>
            <td>
              <button class="btn btn-secondary" style="padding: 2px 8px; font-size: 0.8rem;" onclick="app.editWard(${w.id}, '${this.escape(w.name)}', ${w.is_active})">Edit</button>
              ${w.is_active
                ? `<button class="btn btn-secondary" style="padding: 2px 8px; font-size: 0.8rem; color: var(--danger-color);" onclick="app.deleteWard(${w.id})">Deactivate</button>`
                : `<button class="btn btn-secondary" style="padding: 2px 8px; font-size: 0.8rem; color: green;" onclick="app.reactivateWard(${w.id})">Reactivate</button>`
              }
            </td>
          </tr>
        `;
      });
      document.getElementById('wards-table-container').innerHTML = `
        <table class="data-table">
          <thead><tr><th>Ward Name</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      `;
    } catch(e) { console.error(e); }
  },

  showAddWardModal: __async(function*() {
    document.getElementById('ward-modal-title').textContent = 'Add Ward';
    document.getElementById('ward-modal-id').value = '';
    document.getElementById('ward-modal-active').value = '1';
    document.getElementById('ward-modal-name').value = '';
    document.getElementById('ward-modal').style.display = 'flex';
    document.getElementById('ward-modal-name').focus();
  },

  editWard: __async(function*(id, oldName, isActive) {
    document.getElementById('ward-modal-title').textContent = 'Edit Ward';
    document.getElementById('ward-modal-id').value = id;
    document.getElementById('ward-modal-active').value = isActive ? '1' : '0';
    document.getElementById('ward-modal-name').value = oldName;
    document.getElementById('ward-modal').style.display = 'flex';
    document.getElementById('ward-modal-name').focus();
  },

  submitWardModal: __async(function*(e) {
    e.preventDefault();
    const id = document.getElementById('ward-modal-id').value;
    const name = document.getElementById('ward-modal-name').value.trim();
    const isActive = document.getElementById('ward-modal-active').value === '1';
    if (!name) return;
    try {
      let res;
      if (id) {
        res = yield fetch(`/api/config/wards/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, is_active: isActive })
        });
      } else {
        res = yield fetch('/api/config/wards', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name })
        });
      }
      if (res.ok) {
        document.getElementById('ward-modal').style.display = 'none';
        this.loadWardsConfig();
      } else {
        const err = yield res.json();
        this.showNotificationModal("Error", err.detail || "Failed to save ward.", true);
      }
    } catch(e) { console.error(e); }
  },

  deleteWard: __async(function*(id) {
    app.confirmAction("Confirm Deactivation", "Are you sure you want to deactivate this ward?", __async(function*() {
      try {
        yield fetch(`/api/config/wards/${id}`, { method: 'DELETE' });
        app.loadWardsConfig();
      } catch(e) { console.error(e); }
    });
  },

  reactivateWard: __async(function*(id) {
    try {
      const res = yield fetch(`/api/config/wards/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: true })
      });
      if (res.ok) {
        this.loadWardsConfig();
      } else {
        const err = yield res.json();
        this.showNotificationModal("Error", err.detail || "Failed to reactivate ward.", true);
      }
    } catch(e) { console.error(e); }
  },

  loadCliniciansConfig: __async(function*() {
    try {
      const res = yield fetch('/api/config/clinicians');
      if (!res.ok) throw new Error('API returned ' + res.status);
      const clinicians = yield res.json();
      let rows = '';
      clinicians.forEach(c => {
        rows += `
          <tr>
            <td><strong>${this.escape(c.name)}</strong></td>
            <td>Active</td>
          </tr>
        `;
      });
      document.getElementById('clinicians-table-container').innerHTML = `
        <table class="data-table">
          <thead><tr><th>Clinician Name</th><th>Status</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      `;
    } catch(e) { console.error(e); }
  },
  
  showAddClinicianModal: function() {
    document.getElementById('clinician-modal-name').value = '';
    document.getElementById('clinician-modal').style.display = 'flex';
  },

  submitClinicianModal: __async(function*(event) {
    event.preventDefault();
    const name = document.getElementById('clinician-modal-name').value;
    try {
      const res = yield fetch('/api/config/clinicians', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name, is_active: true })
      });
      if (res.ok) {
        document.getElementById('clinician-modal').style.display = 'none';
        app.loadCliniciansConfig();
      } else {
        const err = yield res.json();
        app.showNotificationModal("Error", err.detail || "Failed to add clinician.", true);
      }
    } catch(e) { console.error(e); }
  },

  loadConfigData: __async(function*() {
    try {
      // 1. Load sections first so we can display names
      if (!this.sections) {
        try {
          const secRes = yield fetch('/api/config/sections');
          if (secRes.ok) this.sections = yield secRes.json();
          else this.sections = [];
        } catch(e) { this.sections = []; }
      }
      const sectionMap = {};
      (this.sections || []).forEach(s => { sectionMap[s.id] = s.name; });

      // 2. Load test catalog
      const res = yield fetch('/api/config/tests');
      if (res.ok) {
        const tests = yield res.json();
        this.testCatalog = tests;

        // Build section name lookup
        const sectionMap = {};
        (this.sections || []).forEach(s => { sectionMap[s.id] = s.name; });

        // Identify panel parents: result_type === 'panel' and no parent_rollup_id
        const parentIds = new Set(
          tests.filter(t => t.result_type === 'panel' && !t.parent_rollup_id).map(t => t.id)
        );

        // Group all tests by section name, in section order
        const bySection = {};
        const sectionOrder = (this.sections || []).map(s => s.name);
        tests.forEach(t => {
          const secName = sectionMap[t.section_id] || `Section ${t.section_id}`;
          if (!bySection[secName]) bySection[secName] = [];
          bySection[secName].push(t);
        });

        let tableHtml = `
          <table class="data-table" style="table-layout: auto; width: 100%;">
            <thead>
              <tr>
                <th>Test Name</th>
                <th style="white-space: nowrap;">Surveillance Tracking</th>
                <th style="white-space: nowrap;">Actions</th>
              </tr>
            </thead>
            <tbody>
        `;

        // Render in section order, then any extra sections
        const orderedSections = sectionOrder.filter(n => bySection[n]);
        Object.keys(bySection).forEach(n => { if (!orderedSections.includes(n)) orderedSections.push(n); });

        orderedSections.forEach(secName => {
          const secTests = bySection[secName];

          // Section header row
          tableHtml += `
            <tr style="background-color: var(--primary-color); color: white;">
              <td colspan="3" style="font-weight: 700; padding: 6px 12px; font-size: 0.82rem; letter-spacing: 0.06em;">
                ${this.escape(secName.toUpperCase())}
              </td>
            </tr>
          `;

          const panelsInSec = secTests.filter(t => parentIds.has(t.id));
          const childrenMap = {};
          secTests.filter(t => t.parent_rollup_id && parentIds.has(t.parent_rollup_id)).forEach(t => {
            if (!childrenMap[t.parent_rollup_id]) childrenMap[t.parent_rollup_id] = [];
            childrenMap[t.parent_rollup_id].push(t);
          });
          const standalones = secTests.filter(t => !parentIds.has(t.id) && !t.parent_rollup_id);

          // Panel parent rows (collapsed by default)
          panelsInSec.forEach(parent => {
            const children = childrenMap[parent.id] || [];
            const count = children.length;
            tableHtml += `
              <tr style="background-color: #EEF2FF; font-weight: 600;">
                <td style="padding-left: 12px;">
                  <button
                    id="toggle-btn-${parent.id}"
                    class="btn btn-secondary"
                    style="padding: 1px 7px; font-size: 0.75rem; margin-right: 8px; min-width: 22px;"
                    onclick="app.togglePanelGroup(${parent.id})"
                  >+</button>${this.escape(parent.name)}<span style="font-size: 0.78rem; color: var(--text-muted); font-weight: 400; margin-left: 10px;">${count} parameter${count !== 1 ? 's' : ''}</span>
                </td>
                <td>${parent.is_tracked ? 'Tracked (Positives / Findings)' : 'Standard (Done Only)'}</td>
                <td style="color: var(--text-muted); font-size: 0.8rem;">System panel</td>
              </tr>
            `;
            // Child rows hidden by default
            children.forEach(child => {
              tableHtml += `
                <tr data-parent-id="${parent.id}" style="display: none; background-color: #FAFAFA;">
                  <td style="padding-left: 40px; font-size: 0.9rem;">${this.escape(child.name)}</td>
                  <td style="font-size: 0.85rem;">${child.is_tracked ? 'Tracked (Positives / Findings)' : 'Standard (Done Only)'}</td>
                  <td>
                    <button class="btn btn-secondary" style="padding: 2px 8px; font-size: 0.8rem;" onclick="app.openTestConfigModal(${child.id})">Edit</button>
                    <button class="btn btn-secondary" style="padding: 2px 8px; font-size: 0.8rem; color: var(--danger-color);" onclick="app.deleteTest(${child.id})">Delete</button>
                  </td>
                </tr>
              `;
            });
          });

          // Standalone tests (flat rows with Edit + Delete)
          standalones.forEach(t => {
            tableHtml += `
              <tr>
                <td style="padding-left: 12px;"><strong>${this.escape(t.name)}</strong></td>
                <td>${t.is_tracked ? 'Tracked (Positives / Findings)' : 'Standard (Done Only)'}</td>
                <td>
                  <button class="btn btn-secondary" style="padding: 2px 8px; font-size: 0.8rem;" onclick="app.openTestConfigModal(${t.id})">Edit</button>
                  <button class="btn btn-secondary" style="padding: 2px 8px; font-size: 0.8rem; color: var(--danger-color);" onclick="app.deleteTest(${t.id})">Delete</button>
                </td>
              </tr>
            `;
          });
        });

        tableHtml += `</tbody></table>`;

        const catalogContainer = document.getElementById('config-table-container');
        if (catalogContainer) catalogContainer.innerHTML = tableHtml;
      }

      // 3. Load clinicians config
      yield this.loadCliniciansConfig();

      // 4. Load wards config
      yield this.loadWardsConfig();

      // 5. Load user management for admin/superadmin
      if (this.currentUser && (this.currentUser.role === 'admin' || this.currentUser.role === 'superadmin')) {
        const userRes = yield fetch('/api/auth/users');
        if (userRes.ok) {
          const users = yield userRes.json();

          // Split into pending and active
          const pendingUsers = users.filter(u => !u.is_active);
          const activeUsers = users.filter(u => u.is_active);

          // 2a. Render Pending Registrations
          const pendingContainer = document.getElementById('pending-users-container');
          if (pendingContainer) {
            if (pendingUsers.length === 0) {
              pendingContainer.innerHTML = '<p style="padding: 12px; color: var(--text-muted);">No pending registration requests.</p>';
            } else {
              let pendingRows = '';
              pendingUsers.forEach(u => {
                const formattedDate = u.created_at ? u.created_at.replace('T', ' ').substring(0, 19) : 'â€”';
                pendingRows += `
                  <tr>
                    <td><strong>${this.escape(u.full_name)}</strong></td>
                    <td><code>${this.escape(u.username)}</code></td>
                    <td>${this.escape(u.cadre || 'None')}</td>
                    <td>${this.escape(formattedDate)}</td>
                    <td>
                      <div style="display: flex; gap: 8px; align-items: center;">
                        <button class="btn btn-success" style="padding: 4px 10px; font-size: 0.8rem;" onclick="app.approveUser(${u.id}, '${this.escape(u.role)}', '${this.escape(u.cadre || '')}')">Approve</button>
                        <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 0.8rem; background: var(--danger-color); color: white; border: none;" onclick="app.rejectUser(${u.id}, '${this.escape(u.username)}')">Reject</button>
                      </div>
                    </td>
                  </tr>
                `;
              });

              pendingContainer.innerHTML = `
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>Full Name</th>
                      <th>Username</th>
                      <th>Cadre</th>
                      <th>Registered On</th>
                      <th style="width: 180px;">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${pendingRows}
                  </tbody>
                </table>
              `;
            }
          }

          // 2b. Render Active Staff
          const activeContainer = document.getElementById('active-users-container');
          if (activeContainer) {
            if (activeUsers.length === 0) {
              activeContainer.innerHTML = '<p style="padding: 12px; color: var(--text-muted);">No active staff accounts found.</p>';
            } else {
              let activeRows = '';
              activeUsers.forEach(u => {
                const isSelf = u.id === this.currentUser.id;
                const canEdit = !isSelf && !(this.currentUser.role === 'admin' && u.role === 'superadmin');
                const statusBadge = u.password_reset_required
                  ? 'Temporary (Reset Required)'
                  : 'Active';

                const superAdminOption = u.role === 'superadmin' ? `<option value="superadmin" selected>Super Admin</option>` : '';

                const roleSelect = `
                  <select id="role-select-${u.id}" onchange="app.changeUserFields(${u.id}, true)" ${!canEdit ? 'disabled' : ''} style="padding: 4px 8px; border-radius: 4px; border: 1px solid var(--border-color); font-size: 0.85rem;">
                    <option value="staff" ${u.role === 'staff' ? 'selected' : ''}>Staff</option>
                    <option value="admin" ${u.role === 'admin' ? 'selected' : ''}>Admin</option>
                    ${superAdminOption}
                  </select>
                `;
                
                const cadreSelect = `
                  <select id="cadre-select-${u.id}" onchange="app.changeUserFields(${u.id}, true)" ${!canEdit ? 'disabled' : ''} style="padding: 4px 8px; border-radius: 4px; border: 1px solid var(--border-color); font-size: 0.85rem; max-width: 200px;">
                    <option value="">None</option>
                    <option value="Medical Laboratory Assistant" ${u.cadre === 'Medical Laboratory Assistant' ? 'selected' : ''}>Medical Laboratory Assistant</option>
                    <option value="Medical Laboratory Technician" ${u.cadre === 'Medical Laboratory Technician' ? 'selected' : ''}>Medical Laboratory Technician</option>
                    <option value="Senior Medical Laboratory Technician" ${u.cadre === 'Senior Medical Laboratory Technician' ? 'selected' : ''}>Senior Medical Laboratory Technician</option>
                    <option value="Principal Medical Laboratory Technician" ${u.cadre === 'Principal Medical Laboratory Technician' ? 'selected' : ''}>Principal Medical Laboratory Technician</option>
                    <option value="Medical Laboratory Technologist / Scientist" ${u.cadre === 'Medical Laboratory Technologist / Scientist' ? 'selected' : ''}>Medical Laboratory Technologist / Scientist</option>
                    <option value="Senior Medical Laboratory Technologist" ${u.cadre === 'Senior Medical Laboratory Technologist' ? 'selected' : ''}>Senior Medical Laboratory Technologist</option>
                    <option value="Principal Medical Laboratory Technologist" ${u.cadre === 'Principal Medical Laboratory Technologist' ? 'selected' : ''}>Principal Medical Laboratory Technologist</option>
                  </select>
                `;

                const deactivateBtn = canEdit
                  ? `<button class="btn btn-secondary" style="padding: 4px 8px; font-size: 0.8rem; color: var(--danger-color); border-color: var(--danger-color);" onclick="app.deactivateUser(${u.id}, '${this.escape(u.role)}', '${this.escape(u.cadre || '')}')">Deactivate</button>`
                  : '';

                activeRows += `
                  <tr>
                    <td><strong>${this.escape(u.full_name)}</strong> ${isSelf ? '<small style="color: var(--primary-color); font-weight: 600;">(You)</small>' : ''}</td>
                    <td><code>${this.escape(u.username)}</code></td>
                    <td>${roleSelect}</td>
                    <td>${cadreSelect}</td>
                    <td>${statusBadge}</td>
                    <td>
                      <div style="display: flex; gap: 6px; align-items: center;">
                        <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 0.8rem;" onclick="app.promptResetPassword(${u.id}, '${this.escape(u.username)}', '${this.escape(u.role)}', '${this.escape(u.cadre || '')}')" ${!canEdit ? 'disabled' : ''}>Reset Password</button>
                        ${deactivateBtn}
                      </div>
                    </td>
                  </tr>
                `;
              });

              activeContainer.innerHTML = `
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>Full Name</th>
                      <th>Username</th>
                      <th>Role</th>
                      <th>Cadre</th>
                      <th>Status</th>
                      <th style="width: 220px;">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${activeRows}
                  </tbody>
                </table>
              `;
            }
          }
        }
      }
    } catch (e) {
      console.error('Config loading error:', e);
    }
  },

  approveUser: __async(function*(userId, role, cadre) {
    yield this.saveUserUpdate(userId, { role: role || 'staff', cadre: cadre || null, is_active: true });
    this.showNotificationModal("Success", 'User registration approved successfully!', false);
  },

  rejectUser: __async(function*(userId, username) {
    app.confirmAction("Reject User", `Are you sure you want to reject and delete the registration for '${username}'?`, __async(function*() {
      try {
        const res = yield fetch(`/api/auth/users/${userId}`, { method: 'DELETE' });
        if (res.ok) {
          app.showNotificationModal("Success", `Registration for '${username}' rejected and removed.`, false);
          yield app.loadConfigData();
        } else {
          const err = yield res.json();
          app.showNotificationModal("Error", err.detail || 'Failed to reject registration.', true);
        }
      } catch (e) {
        app.showNotificationModal("Error", 'Connection error rejecting registration.', true);
      }
    });
  },

  deactivateUser: __async(function*(userId, role, cadre) {
    app.confirmAction("Deactivate User", "Are you sure you want to deactivate this account?", __async(function*() {
      yield app.saveUserUpdate(userId, { role: role, cadre: cadre || null, is_active: false });
      app.showNotificationModal("Success", 'User account deactivated.', false);
    });
  },

  changeUserFields: __async(function*(userId, isActive) {
    const roleEl = document.getElementById(`role-select-${userId}`);
    const cadreEl = document.getElementById(`cadre-select-${userId}`);
    if (!roleEl || !cadreEl) return;
    
    yield this.saveUserUpdate(userId, { role: roleEl.value, cadre: cadreEl.value || null, is_active: isActive });
    this.showNotificationModal("Success", 'User details updated successfully.', false);
  },

  promptAction: function(title, message, callback) {
    const modal = document.getElementById('prompt-modal');
    if (!modal) {
      const result = prompt(message);
      if (result !== null) callback(result);
      return;
    }
    document.getElementById('prompt-title').textContent = title;
    document.getElementById('prompt-message').textContent = message;
    const input = document.getElementById('prompt-input');
    input.value = '';
    
    const cancelBtn = document.getElementById('prompt-cancel-btn');
    const okBtn = document.getElementById('prompt-ok-btn');
    
    const newCancel = cancelBtn.cloneNode(true);
    const newOk = okBtn.cloneNode(true);
    cancelBtn.parentNode.replaceChild(newCancel, cancelBtn);
    okBtn.parentNode.replaceChild(newOk, okBtn);
    
    newCancel.addEventListener('click', () => {
      modal.style.display = 'none';
    });
    
    newOk.addEventListener('click', () => {
      modal.style.display = 'none';
      callback(input.value);
    });
    
    modal.style.display = 'flex';
    input.focus();
  },

  promptResetPassword: __async(function*(userId, username, role, cadre) {
    app.promptAction("Reset Password", `Enter a new temporary password for user '${username}' (minimum 4 characters):`, __async(function*(tempPw) {
      if (tempPw.trim().length < 4) {
        app.showNotificationModal("Error", 'Password must be at least 4 characters long.', true);
        return;
      }
      yield app.saveUserUpdate(userId, { role: role, cadre: cadre || null, is_active: true, password: tempPw.trim() });
      app.showNotificationModal("Success", `Password reset for '${username}'. User will be required to change it on next login.`, false);
    });
  },

  saveUserUpdate: __async(function*(userId, updateBody) {
    try {
      const res = yield fetch(`/api/auth/users/${userId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updateBody)
      });
      if (res.ok) {
        if (userId === this.currentUser.id) {
          yield this.checkAuth();
        } else {
          yield this.loadConfigData();
        }
      } else {
        const err = yield res.json();
        this.showNotificationModal("Error", err.detail || 'Failed to update user account.', true);
      }
    } catch (e) {
      this.showNotificationModal("Error", 'Connection error updating account.', true);
    }
  },

  togglePanelGroup: function(panelId) {
    const rows = document.querySelectorAll(`tr[data-parent-id="${panelId}"]`);
    const btn = document.getElementById(`toggle-btn-${panelId}`);
    if (!rows || rows.length === 0) return;
    const isHidden = rows[0].style.display === 'none' || getComputedStyle(rows[0]).display === 'none';
    rows.forEach(row => { row.style.display = isHidden ? 'table-row' : 'none'; });
    if (btn) btn.textContent = isHidden ? '-' : '+';
  },

  openTestConfigModal: __async(function*(testId = null) {
    // If editing, look up the test object from testCatalog (already loaded) or fetch it
    let test = null;
    if (testId !== null) {
      if (this.testCatalog && this.testCatalog.length > 0) {
        test = this.testCatalog.find(t => t.id === testId) || null;
      }
      if (!test) {
        try {
          const res = yield fetch('/api/config/tests');
          if (res.ok) {
            this.testCatalog = yield res.json();
            test = this.testCatalog.find(t => t.id === testId) || null;
          }
        } catch(e) {}
      }
    }
    
    // Load sections if not loaded
    if (!this.sections) {
      try {
        const res = yield fetch('/api/config/sections');
        if (res.ok) this.sections = yield res.json();
        else this.sections = [];
      } catch(e) { this.sections = []; }
    }

    const modal = document.getElementById('test-config-modal');
    const form = document.getElementById('test-config-form');
    form.reset();
    
    const secSelect = document.getElementById('test-config-section');
    secSelect.innerHTML = '<option value="">-- Select Section --</option>';
    this.sections.forEach(s => {
      secSelect.innerHTML += `<option value="${s.id}">${this.escape(s.name)}</option>`;
    });

    // Populate parent panel selector
    const parentSelect = document.getElementById('test-config-parent');
    if (parentSelect) {
      parentSelect.innerHTML = '<option value="">None (standalone test)</option>';
      const panels = (this.testCatalog || []).filter(t => t.result_type === 'panel' && t.is_active !== 0);
      panels.forEach(p => {
        parentSelect.innerHTML += `<option value="${p.id}">${this.escape(p.name)}</option>`;
      });
      parentSelect.value = (test && test.parent_rollup_id) ? test.parent_rollup_id : '';
    }

    if (test) {
      document.getElementById('test-config-title').textContent = 'Edit Test';
      document.getElementById('test-config-id').value = test.id;
      document.getElementById('test-config-name').value = test.name;
      document.getElementById('test-config-section').value = test.section_id;
      document.getElementById('test-config-result-type').value = test.result_type || 'qualitative';
      document.getElementById('test-config-unit').value = test.default_unit || '';
      try {
        document.getElementById('test-config-options').value = test.options ? JSON.parse(test.options).join(', ') : '';
      } catch(e) {
        document.getElementById('test-config-options').value = '';
      }
      document.getElementById('test-config-tracked').checked = !!test.is_tracked;
    } else {
      document.getElementById('test-config-title').textContent = 'Add New Test';
      document.getElementById('test-config-id').value = '';
      document.getElementById('test-config-result-type').value = 'qualitative';
      document.getElementById('test-config-unit').value = '';
      document.getElementById('test-config-options').value = '';
      document.getElementById('test-config-tracked').checked = true;
    }
    this.handleTestResultTypeChange();
    modal.style.display = 'flex';
    
    form.onsubmit = __async(function*(e) {
      e.preventDefault();
      yield this.saveTestConfig();
    };
  },

  handleTestResultTypeChange: function() {
    const rType = document.getElementById('test-config-result-type').value;
    const unitGroup = document.getElementById('test-config-unit-group');
    const unitInput = document.getElementById('test-config-unit');
    const unitLabel = document.getElementById('test-config-unit-label');
    const optionsGroup = document.getElementById('test-config-options-group');
    const trackedCheckbox = document.getElementById('test-config-tracked');
    const isNew = !document.getElementById('test-config-id').value;
    
    if (rType === 'quantitative') {
      unitGroup.style.display = 'block';
      if (unitLabel) unitLabel.textContent = 'Reporting Unit (Required):';
      if (unitInput) unitInput.required = true;
      optionsGroup.style.display = 'none';
      document.getElementById('test-config-options').value = '';
      if (isNew) {
        trackedCheckbox.checked = false;
      }
    } else if (rType === 'semi_quantitative') {
      unitGroup.style.display = 'block';
      if (unitLabel) unitLabel.textContent = 'Reporting Unit (Optional):';
      if (unitInput) unitInput.required = false;
      optionsGroup.style.display = 'block';
      if (isNew) {
        trackedCheckbox.checked = true;
      }
    } else {
      // qualitative / options
      unitGroup.style.display = 'none';
      if (unitInput) {
        unitInput.required = false;
        unitInput.value = '';
      }
      optionsGroup.style.display = 'block';
      if (isNew) {
        trackedCheckbox.checked = true;
      }
    }
  },

  saveTestConfig: __async(function*() {
    const id = document.getElementById('test-config-id').value;
    const name = document.getElementById('test-config-name').value.trim();
    const section_id = parseInt(document.getElementById('test-config-section').value, 10);
    const result_type = document.getElementById('test-config-result-type').value;
    const default_unit = document.getElementById('test-config-unit').value.trim() || null;
    const optionsRaw = document.getElementById('test-config-options').value;
    const is_tracked = document.getElementById('test-config-tracked').checked;
    const parentRaw = document.getElementById('test-config-parent') ? document.getElementById('test-config-parent').value : '';
    const parent_rollup_id = parentRaw ? parseInt(parentRaw, 10) : null;

    if (result_type === 'quantitative' && !default_unit) {
      this.showNotificationModal("Validation Error", "Reporting unit is required for quantitative tests.", true);
      return;
    }
    
    let options = null;
    if (optionsRaw.trim() && (result_type === 'qualitative' || result_type === 'semi_quantitative')) {
      options = JSON.stringify(optionsRaw.split(',').map(s => s.trim()).filter(s => s));
    }

    const payload = { name, section_id, is_tracked, result_type, default_unit, options, sort_order: 0, parent_rollup_id };
    
    try {
      let res;
      if (id) {
        res = yield fetch(`/api/config/tests/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      } else {
        res = yield fetch(`/api/config/tests`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      }
      
      if (res.ok) {
        document.getElementById('test-config-modal').style.display = 'none';
        this.showNotificationModal("Success", `Test ${id ? 'updated' : 'added'} successfully.`);
        yield this.loadConfigData();
      } else {
        const err = yield res.json();
        this.showNotificationModal("Error", err.detail || 'Failed to save test.', true);
      }
    } catch (e) {
      this.showNotificationModal("Error", 'Connection error.', true);
    }
  },

  deleteTest: __async(function*(testId) {
    // Guard: block deletion of panel parent that still has children
    const hasChildren = (this.testCatalog || []).some(t => t.parent_rollup_id === testId);
    if (hasChildren) {
      this.showNotificationModal(
        "Cannot Delete Panel",
        "This panel still has parameters configured under it. Remove or reassign all parameters before deleting the panel.",
        true
      );
      return;
    }

    app.confirmAction("Confirm Deletion", "Are you sure you want to deactivate this test from the catalog?", __async(function*() {
      try {
        const res = yield fetch(`/api/config/tests/${testId}`, { method: 'DELETE' });
        if (res.ok) {
          app.loadConfigData();
        } else {
          app.showNotificationModal("Error", 'Failed to delete test.', true);
        }
      } catch (e) {
        app.showNotificationModal("Error", 'Connection error.', true);
      }
    });
   },


  renderAuditLog: __async(function*(container) {
    container.innerHTML = `
      <div class="card">
        <div class="card-header">
          <span class="card-title">${this.icon('shield-check')} System Audit Trail</span>
        </div>
        <div id="audit-table-container">
          <p>Loading audit log...</p>
        </div>
      </div>
    `;
    try {
      const res = yield fetch('/api/audit-log');
      if (!res.ok) throw new Error('API returned ' + res.status);
      const logs = yield res.json();

      let rows = '';
      logs.forEach(l => {
        rows += `
          <tr>
            <td>${l.timestamp ? l.timestamp.replace('T', ' ').substring(0, 19) : ''}</td>
            <td><strong>${this.escape(l.username)}</strong></td>
            <td><code>${this.escape(l.action)}</code></td>
            <td>${this.escape(l.detail || '')}</td>
          </tr>
        `;
      });

      document.getElementById('audit-table-container').innerHTML = `
        <table class="data-table">
          <thead>
            <tr>
              <th style="width: 180px;">Timestamp</th>
              <th style="width: 140px;">User</th>
              <th style="width: 160px;">Action</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
      `;
    } catch (e) {
      console.error('Audit log error:', e);
    }
  },

  escape: function(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
};



window.onload = () => {
  app.init();
};
