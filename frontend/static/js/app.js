const app = {
  currentUser: null,
  currentView: 'daily-log',
  theme: null,
  inactivityTimer: null,
  inactivityTimeout: 15 * 60 * 1000, // 15 minutes in milliseconds
  lastActivityTime: 0,

  icons: {
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

  icon(name) {
    return this.icons[name] || '';
  },

  async init() {
    await this.loadTheme();
    await this.checkAuth();
    this.setupInactivityListeners();
  },

  async loadTheme() {
    try {
      const res = await fetch('/assets/branding/theme.json');
      if (res.ok) {
        this.theme = await res.json();
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

  async checkAuth() {
    try {
      const res = await fetch('/api/auth/me');
      if (res.ok) {
        this.currentUser = await res.json();
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

  showLogin() {
    this.currentUser = null;
    this.stopInactivityTimer();
    this.cleanseDOM();
    document.getElementById('app-nav').style.display = 'none';
    document.getElementById('user-nav').innerHTML = '';
    document.getElementById('login-modal').style.display = 'flex';
    this.showLoginForm();
  },

  async handleLogin(event) {
    event.preventDefault();
    const u = document.getElementById('login-username').value;
    const p = document.getElementById('login-password').value;
    const errDiv = document.getElementById('login-error');
    errDiv.style.display = 'none';

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: u, password: p })
      });

      if (res.ok) {
        const data = await res.json();
        this.currentUser = data.user;
        document.getElementById('login-modal').style.display = 'none';
        document.getElementById('app-nav').style.display = 'flex';
        this.renderUserNav();
        this.startInactivityTimer();

        if (data.status === 'reset_required' || (data.user && data.user.password_reset_required)) {
          this.showResetPasswordModal();
        } else {
          this.navigate('daily-log');
        }
      } else {
        const err = await res.json();
        errDiv.textContent = err.detail || 'Login failed';
        errDiv.style.display = 'block';
      }
    } catch (e) {
      errDiv.textContent = 'Connection error. Please try again.';
      errDiv.style.display = 'block';
    }
  },

  async handleLogout() {
    this.stopInactivityTimer();
    await fetch('/api/auth/logout', { method: 'POST' });
    this.showLogin();
  },

  showResetPasswordModal() {
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

  async handleChangePassword(event) {
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
      const res = await fetch('/api/auth/change-password', {
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
        this.showToast('Password changed successfully!', 'success');
        this.navigate('daily-log');
      } else {
        const err = await res.json();
        errDiv.textContent = err.detail || 'Failed to change password.';
        errDiv.style.display = 'block';
      }
    } catch (e) {
      errDiv.textContent = 'Connection error. Please try again.';
      errDiv.style.display = 'block';
    }
  },

  showRegisterForm(event) {
    if (event) event.preventDefault();
    document.getElementById('login-form-container').style.display = 'none';
    document.getElementById('register-form-container').style.display = 'block';
    document.getElementById('register-error').style.display = 'none';
    document.getElementById('register-success').style.display = 'none';
  },

  showLoginForm(event) {
    if (event) event.preventDefault();
    document.getElementById('register-form-container').style.display = 'none';
    document.getElementById('login-form-container').style.display = 'block';
    document.getElementById('login-error').style.display = 'none';
  },

  async handleRegister(event) {
    event.preventDefault();
    const fullname = document.getElementById('register-fullname').value;
    const username = document.getElementById('register-username').value;
    const password = document.getElementById('register-password').value;
    const errDiv = document.getElementById('register-error');
    const successDiv = document.getElementById('register-success');
    
    errDiv.style.display = 'none';
    successDiv.style.display = 'none';

    try {
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ full_name: fullname, username: username, password: password })
      });

      if (res.ok) {
        const data = await res.json();
        if (data.is_active) {
          successDiv.textContent = 'Super Administrator account registered successfully! Redirecting...';
        } else {
          successDiv.textContent = 'Registration submitted! Access is pending administrator approval.';
        }
        successDiv.style.display = 'block';
        document.getElementById('register-form').reset();
        setTimeout(() => {
          this.showLoginForm();
        }, 3000);
      } else {
        const err = await res.json();
        errDiv.textContent = err.detail || 'Registration failed';
        errDiv.style.display = 'block';
      }
    } catch (e) {
      errDiv.textContent = 'Connection error. Please try again.';
      errDiv.style.display = 'block';
    }
  },

  setupInactivityListeners() {
    const reset = () => this.resetInactivityTimer();
    window.addEventListener('mousemove', reset);
    window.addEventListener('keydown', reset);
    window.addEventListener('click', reset);
    window.addEventListener('scroll', reset);
  },

  startInactivityTimer() {
    this.resetInactivityTimer();
  },

  resetInactivityTimer() {
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
        this.showToast("Logged out automatically due to inactivity.", "error");
      }, this.inactivityTimeout);
    }
  },

  stopInactivityTimer() {
    if (this.inactivityTimer) {
      clearTimeout(this.inactivityTimer);
      this.inactivityTimer = null;
    }
  },

  togglePasswordVisibility(inputId) {
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

  cleanseDOM() {
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

  renderUserNav() {
    const nav = document.getElementById('user-nav');
    if (!this.currentUser) return;

    const isPrivileged = this.currentUser.role === 'admin' || this.currentUser.role === 'superadmin';
    const adminTabs = document.querySelectorAll('.admin-only');
    adminTabs.forEach(tab => {
      tab.style.display = isPrivileged ? 'inline-block' : 'none';
    });

    const roleLabel = this.currentUser.role === 'superadmin' ? 'Super Administrator'
      : (this.currentUser.role === 'admin' ? 'Administrator'
      : (this.currentUser.role === 'technologist' || this.currentUser.role === 'Laboratory Technologist' ? 'Laboratory Technologist'
      : 'Technician'));

    nav.innerHTML = `
      <div class="user-badge">
        ${this.icon('user')} <strong>${this.escape(this.currentUser.full_name)}</strong> (${this.escape(roleLabel)})
      </div>
      <button class="btn btn-secondary" style="padding: 4px 12px; font-size: 0.8rem;" onclick="app.handleLogout()">${this.icon('log-out')} Logout</button>
    `;
  },

  navigate(viewName) {
    if (this.currentUser && this.currentUser.password_reset_required) {
      this.showResetPasswordModal();
      return;
    }
    this.currentView = viewName;
    document.querySelectorAll('.nav-tab').forEach(tab => {
      tab.classList.remove('active');
    });

    const activeBtn = Array.from(document.querySelectorAll('.nav-tab')).find(b => b.textContent.toLowerCase().includes(viewName.replace('-', '')));
    if (activeBtn) activeBtn.classList.add('active');

    const container = document.getElementById('view-container');
    if (viewName === 'daily-log') this.renderDailyLog(container);
    else if (viewName === 'reports') this.renderReports(container);
    else if (viewName === 'trends') this.renderTrends(container);
    else if (viewName === 'clients') this.renderClients(container);
    else if (viewName === 'config') this.renderConfig(container);
    else if (viewName === 'audit') this.renderAuditLog(container);
  },

  showToast(message, type = 'success', duration = 3500) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <span>${this.escape(message)}</span>
      <span style="cursor:pointer; opacity:0.8; font-weight:700;" onclick="this.parentElement.remove()">&times;</span>
    `;

    container.appendChild(toast);
    setTimeout(() => {
      if (toast.parentElement) toast.remove();
    }, duration);
  },

  shiftLogDate(offsetDays) {
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
  async renderDailyLog(container) {
    const today = new Date().toISOString().split('T')[0];
    container.innerHTML = `
      <div class="card">
        <div class="card-header">
          <span class="card-title">${this.icon('clipboard-list')} Daily Laboratory Entry Log</span>
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
            <button class="btn btn-success" onclick="app.saveDailyLogData()">${this.icon('save')} Save Entries</button>
          </div>
        </div>

        <div class="audit-check-panel">
          <div class="check-item">
            <span class="label">System Total (Derived from Orders):</span>
            <span class="val" id="sys-total-done">0</span>
          </div>
          <div class="check-item">
            <label for="paper-register-input" style="font-weight:600; color:var(--text-muted);">Paper Register Total:</label>
            <input type="number" id="paper-register-input" placeholder="Type register total" style="width: 140px; font-weight:700;" oninput="app.updateAuditCheck()">
          </div>
          <div class="check-item">
            <span class="label">Register Check:</span>
            <span class="val" id="audit-check-status">&mdash;</span>
          </div>
          <button class="btn btn-primary" onclick="app.submitShiftAudit()">${this.icon('save')} Verify Shift Audit</button>
        </div>

        <div id="daily-sections-container">
          <p style="color: var(--text-muted);">Loading daily log...</p>
        </div>
      </div>
    `;
    await this.loadDailyLogData(today);
  },

  async loadDailyLogData(dateStr) {
    try {
      const res = await fetch(`/api/daily-log?date=${dateStr}`);
      if (!res.ok) return;
      const data = await res.json();

      const secContainer = document.getElementById('daily-sections-container');
      secContainer.innerHTML = '';

      data.sections.forEach(sec => {
        let rowsHtml = '';
        sec.tests.forEach(t => {
          const posCell = t.is_tracked 
            ? `<input type="number" class="test-pos-input" data-test-id="${t.test_id}" min="0" value="${t.positive !== null ? t.positive : ''}" oninput="app.updateAuditCheck()">`
            : `<span class="tag-na">N/A</span>`;

          rowsHtml += `
            <tr>
              <td><strong>${this.escape(t.test_name)}</strong></td>
              <td>${t.is_tracked ? '<span class="tag-positive">Tracked</span>' : '<span style="color:#94A3B8;">Standard</span>'}</td>
              <td style="text-align: right;">
                <input type="number" class="test-done-input" data-test-id="${t.test_id}" min="0" value="${t.done || ''}" oninput="app.updateAuditCheck()">
              </td>
              <td style="text-align: center;">${posCell}</td>
            </tr>
          `;
        });

        secContainer.innerHTML += `
          <div style="margin-bottom: 24px;">
            <h3 style="color: var(--primary-color); margin-bottom: 8px; font-size: 1rem; border-bottom: 2px solid var(--border-color); padding-bottom: 4px;">
              Section: ${this.escape(sec.section_name)}
            </h3>
            <table class="data-table" data-section-id="${sec.section_id}">
              <thead>
                <tr>
                  <th>Test Name</th>
                  <th style="width: 120px;">Surveillance</th>
                  <th style="width: 140px; text-align: right;">Done Count</th>
                  <th style="width: 140px; text-align: center;">Positive Count</th>
                </tr>
              </thead>
              <tbody>
                ${rowsHtml}
              </tbody>
              <tfoot>
                <tr style="background-color: #F8FAFC; font-weight: 700;">
                  <td colspan="2">Subtotal &mdash; ${this.escape(sec.section_name)}</td>
                  <td style="text-align: right;" id="sec-subtotal-done-${sec.section_id}">0</td>
                  <td style="text-align: center;" id="sec-subtotal-pos-${sec.section_id}">0</td>
                </tr>
              </tfoot>
            </table>
          </div>
        `;
      });

      this.updateAuditCheck();
      this.setupKeyboardNavigation();
    } catch (e) {
      console.error('Error loading daily log:', e);
    }
  },

  setupKeyboardNavigation() {
    const inputs = Array.from(document.querySelectorAll('.test-done-input, .test-pos-input'));
    inputs.forEach(input => {
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === 'ArrowDown') {
          e.preventDefault();
          const isPos = input.classList.contains('test-pos-input');
          const selector = isPos ? '.test-pos-input' : '.test-done-input';
          const colInputs = Array.from(document.querySelectorAll(selector));
          const idx = colInputs.indexOf(input);
          if (idx >= 0 && idx < colInputs.length - 1) {
            colInputs[idx + 1].focus();
            colInputs[idx + 1].select();
          }
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          const isPos = input.classList.contains('test-pos-input');
          const selector = isPos ? '.test-pos-input' : '.test-done-input';
          const colInputs = Array.from(document.querySelectorAll(selector));
          const idx = colInputs.indexOf(input);
          if (idx > 0) {
            colInputs[idx - 1].focus();
            colInputs[idx - 1].select();
          }
        }
      });
    });
  },

  updateAuditCheck() {
    let sysDone = 0;

    // Calculate overall system total and per-section subtotals
    document.querySelectorAll('table.data-table[data-section-id]').forEach(table => {
      const secId = table.getAttribute('data-section-id');
      let secDone = 0;
      let secPos = 0;

      table.querySelectorAll('.test-done-input').forEach(inp => {
        const v = parseInt(inp.value, 10);
        if (!isNaN(v) && v > 0) {
          secDone += v;
          sysDone += v;
        }
      });

      table.querySelectorAll('.test-pos-input').forEach(inp => {
        const v = parseInt(inp.value, 10);
        if (!isNaN(v) && v > 0) secPos += v;
      });

      const secDoneEl = document.getElementById(`sec-subtotal-done-${secId}`);
      const secPosEl = document.getElementById(`sec-subtotal-pos-${secId}`);
      if (secDoneEl) secDoneEl.textContent = secDone;
      if (secPosEl) secPosEl.textContent = secPos;
    });

    const sysTotalEl = document.getElementById('sys-total-done');
    if (sysTotalEl) sysTotalEl.textContent = sysDone;

    const paperVal = parseInt(document.getElementById('paper-register-input').value, 10);
    const statusSpan = document.getElementById('audit-check-status');

    if (statusSpan) {
      if (isNaN(paperVal) || paperVal <= 0) {
        statusSpan.textContent = '—';
        statusSpan.className = 'val';
      } else if (paperVal === sysDone) {
        statusSpan.textContent = 'Match';
        statusSpan.className = 'val status-match';
      } else {
        statusSpan.textContent = 'Mismatch';
        statusSpan.className = 'val status-mismatch';
      }
    }
  },

  async saveDailyLogData() {
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
      const res = await fetch('/api/daily-log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entry_date: dateStr, entries: entries })
      });

      if (res.ok) {
        this.showToast('Daily log entries saved successfully!', 'success');
        this.loadDailyLogData(dateStr);
      } else {
        this.showToast('Failed to save entries.', 'error');
      }
    } catch (e) {
      this.showToast('Error connecting to server.', 'error');
    }
  },

  // Reports View
  async renderReports(container) {
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
    await this.loadReportData();
  },

  exportReportCSV() {
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
    this.showToast('Report CSV exported successfully!', 'success');
  },

  async loadReportData() {
    const pType = document.getElementById('report-period-type').value;
    const rDate = document.getElementById('report-ref-date').value;

    try {
      const res = await fetch(`/api/reports?period_type=${pType}&reference_date=${rDate}`);
      if (!res.ok) return;
      const data = await res.json();

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
              <td style="text-align: center;">${t.is_tracked ? (t.positive !== null ? t.positive : 0) : '<span class="tag-na">N/A</span>'}</td>
              <td style="text-align: right;">${t.positivity_rate !== null ? t.positivity_rate + '%' : '—'}</td>
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
  async renderTrends(container) {
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
    await this.loadTrendsData();
  },

  exportTrendsCSV() {
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
    this.showToast('Trends CSV exported successfully!', 'success');
  },

  async loadTrendsData() {
    const fy = document.getElementById('trend-from-year').value;
    const ty = document.getElementById('trend-to-year').value;

    try {
      const res = await fetch(`/api/trends?from_year=${fy}&to_year=${ty}`);
      if (!res.ok) return;
      const data = await res.json();

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
  async renderClients(container) {
    container.innerHTML = `
      <div class="card">
        <div class="card-header">
          <span class="card-title">${this.icon('file-text')} Test Reports & Diagnostic Test Entry</span>
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
    await this.searchClients('');
  },

  async searchClients(q) {
    try {
      const res = await fetch(`/api/clients?query=${encodeURIComponent(q || '')}`);
      if (!res.ok) return;
      const clients = await res.json();

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

  async selectClient(pid, pnum, pname, psex) {
    const box = document.getElementById('client-detail-box');
    box.innerHTML = `
      <div class="client-report-paper">
        <!-- Official Hospital Header Banner -->
        <div class="official-header-banner">
          <img src="/assets/branding/logo.png" alt="Hospital Crest" style="height: 72px; width: auto; object-fit: contain;">
          <div class="official-header-titles">
            <h2>AHMADIYYA MUSLIM HOSPITAL</h2>
            <p class="contact-line">P.O. BOX 982, MBALE, UGANDA &bull; TEL: +256 (0) 454 433 111</p>
            <p class="dept-line">DEPARTMENT OF MEDICAL LABORATORY SCIENCES</p>
          </div>
          <img src="/assets/branding/header_banner.png" alt="AMH Banner" style="height: 72px; width: auto; object-fit: contain; max-width: 200px;" onerror="this.style.display='none'">
        </div>

        <div class="report-document-title">
          <span>CLIENT DIAGNOSTIC LABORATORY REPORT</span>
        </div>

        <div class="report-watermark">AMH MBALE LAB</div>

        <!-- Client Info Card -->
        <div class="client-info-grid">
          <div class="client-info-item"><span class="label">Client Full Name:</span> <span class="val">${pname}</span></div>
          <div class="client-info-item"><span class="label">Hospital Client ID:</span> <span class="val">${pnum}</span></div>
          <div class="client-info-item"><span class="label">Gender / Sex:</span> <span class="val">${psex}</span></div>
          <div class="client-info-item"><span class="label">Date of Report:</span> <span class="val">${new Date().toLocaleDateString()}</span></div>
        </div>

        <!-- Result Entry Form -->
        <div class="no-print" style="margin-bottom: 20px; background: #EFF6FF; padding: 16px; border-radius: 6px; border: 1px solid #BFDBFE;">
          <h4 style="font-size: 0.95rem; color: var(--primary-color); margin-bottom: 12px;">Order & Log Diagnostic Result</h4>
          
          <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-bottom: 12px;">
            <div class="form-group">
              <label>Select Test / Panel:</label>
              <select id="order-test-select" onchange="app.onTestSelectChange(this.value)">
                <option value="">Loading test catalog...</option>
              </select>
            </div>
            <div class="form-group">
              <label>Sample / Tube ID (Optional):</label>
              <input type="text" id="order-sample-id" placeholder="e.g. LAB-1042">
            </div>
            <div class="form-group" id="single-status-group">
              <label>Surveillance Status:</label>
              <select id="order-result-pos">
                <option value="false">Normal / Negative</option>
                <option value="true">Positive / Abnormal</option>
              </select>
            </div>
          </div>

          <div class="form-group" id="single-result-group" style="margin-bottom: 12px;">
            <label>Observed Result Value:</label>
            <input type="text" id="order-result-value" placeholder="e.g. 13.5 g/dL or Positive">
          </div>

          <!-- Dynamic Panel Parameters Container -->
          <div id="test-parameters-container" style="display: none; margin-bottom: 12px; background: #FFFFFF; padding: 12px; border-radius: 6px; border: 1px solid #BFDBFE;">
          </div>

          <button class="btn btn-success" style="width: 100%; padding: 10px;" onclick="app.submitTestResult(${pid})">${this.icon('save')} Submit Result & Add to Report</button>
        </div>

        <!-- Dynamic Results Table -->
        <div id="client-orders-table-container">
          <p style="color: var(--text-muted); padding: 12px;">Loading test results...</p>
        </div>

        <!-- Footer -->
        <div class="report-footer-banner" style="margin-top: 32px;">
          <div>
            <p>Accredited Quality Laboratory Services</p>
            <p>Report Generated: ${new Date().toLocaleString()}</p>
          </div>
          <div class="signature-block">
            Medical Laboratory Analyst
          </div>
        </div>

        <div style="margin-top: 20px; text-align: right;" class="no-print">
          <button class="btn btn-primary" onclick="window.print()">${this.icon('printer')} Print Official Report</button>
        </div>
      </div>
    `;

    await this.loadTestOptions();
    await this.loadClientOrders(pid);
  },

  async loadTestOptions() {
    try {
      const res = await fetch('/api/config/tests');
      if (!res.ok) return;
      const tests = await res.json();

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

  async onTestSelectChange(testId) {
    if (!testId) return;
    try {
      const res = await fetch(`/api/config/tests/${testId}/parameters`);
      if (!res.ok) return;
      const params = await res.json();

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

  async submitShiftAudit() {
    const dateStr = document.getElementById('log-date') ? document.getElementById('log-date').value : new Date().toISOString().split('T')[0];
    const sysTotal = parseInt(document.getElementById('sys-total-done').textContent, 10) || 0;
    const paperVal = parseInt(document.getElementById('paper-register-input').value, 10);

    if (isNaN(paperVal) || paperVal <= 0) {
      this.showToast('Please type a valid Paper Register Total before submitting audit.', 'error');
      return;
    }

    try {
      const res = await fetch('/api/daily-log/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          entry_date: dateStr,
          paper_register_tally: paperVal,
          system_total: sysTotal
        })
      });

      if (res.ok) {
        const data = await res.json();
        this.showToast(`Shift audit recorded: ${data.match} (System: ${sysTotal}, Register: ${paperVal})`, data.match === 'MATCH' ? 'success' : 'error');
      } else {
        this.showToast('Failed to record shift audit.', 'error');
      }
    } catch (e) {
      this.showToast('Error recording shift audit.', 'error');
    }
  },

  async submitTestResult(pid) {
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
        this.showToast('Please enter at least one parameter result for this panel.', 'error');
        return;
      }
    } else {
      mainResultValue = document.getElementById('order-result-value').value;
      if (!mainResultValue) {
        this.showToast('Please enter a result value.', 'error');
        return;
      }
    }

    try {
      // 1. Create order
      const ordRes = await fetch('/api/clients/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_id: pid, test_id: tid, sample_id: sampleId })
      });

      if (!ordRes.ok) throw new Error('Order creation failed');
      const ordData = await ordRes.json();

      // 2. Submit result
      const resRes = await fetch('/api/clients/results', {
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
        this.showToast('Result recorded successfully! Daily Log auto-incremented.', 'success');
        await this.loadClientOrders(pid);
        window.print();
      } else {
        this.showToast('Failed to record result.', 'error');
      }
    } catch (e) {
      this.showToast('Error submitting result.', 'error');
    }
  },

  async loadClientOrders(pid) {
    try {
      const res = await fetch(`/api/clients/${pid}/orders`);
      if (!res.ok) return;
      const orders = await res.json();

      const container = document.getElementById('client-orders-table-container');
      if (!container) return;

      if (orders.length === 0) {
        container.innerHTML = `
          <p style="padding: 16px; color: var(--text-muted); background: #F8FAFC; border-radius: 6px; text-align: center;">
            No laboratory test results recorded yet for this client. Use the form above to log a diagnostic result.
          </p>
        `;
        return;
      }

      let rows = '';
      orders.forEach(o => {
        if (o.results && o.results.length > 0) {
          o.results.forEach((r, idx) => {
            const isPos = r.is_positive;
            const statusBadge = isPos 
              ? `<span style="color: var(--danger-color); font-weight:700;">Positive / Abnormal</span>`
              : `<span style="color: var(--accent-color); font-weight:700;">Normal / Negative</span>`;
            
            const testLabel = idx === 0 
              ? `<strong>${this.escape(o.test_name)}</strong> ${o.sample_id ? `<br><small style="color:var(--text-muted);">Sample ID: ${this.escape(o.sample_id)}</small>` : ''}`
              : '';

            const paramName = r.parameter_name ? `↳ ${this.escape(r.parameter_name)}` : this.escape(o.test_name);
            const refInterval = r.ref_range ? `${this.escape(r.ref_range)} ${this.escape(r.unit || '')}` : 'Standard';

            rows += `
              <tr>
                <td>${testLabel}</td>
                <td>${paramName}</td>
                <td><strong>${this.escape(r.result_value || '')}</strong> ${r.unit ? this.escape(r.unit) : ''}</td>
                <td>${refInterval}</td>
                <td>${statusBadge}</td>
              </tr>
            `;
          });
        }
      });

      container.innerHTML = `
        <table class="report-results-table">
          <thead>
            <tr>
              <th>Investigation Panel</th>
              <th>Parameter / Test</th>
              <th>Observed Result</th>
              <th>Reference Interval</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
      `;
    } catch (e) {
      console.error('Error loading client orders:', e);
    }
  },

  async showNewClientModal() {
    const pnum = 'AMH-C' + Math.floor(1000 + Math.random() * 9000);
    const pname = prompt('Enter Client Full Name:');
    if (!pname) return;
    const psex = prompt('Enter Client Gender (Male/Female):', 'Male') || 'Male';
    const pphone = prompt('Enter Phone Number (Optional):', '') || '';

    try {
      const res = await fetch('/api/clients', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_number: pnum,
          full_name: pname,
          sex: psex,
          phone: pphone
        })
      });

      if (res.ok) {
        this.showToast(`Client registered successfully! Assigned ID: ${pnum}`, 'success');
        this.searchClients('');
      } else {
        this.showToast('Error registering client.', 'error');
      }
    } catch (e) {
      this.showToast('Connection error.', 'error');
    }
  },

  // Configuration View
  async renderConfig(container) {
    const isSuperAdmin = this.currentUser && this.currentUser.role === 'superadmin';

    container.innerHTML = `
      <div class="card" style="margin-bottom: 24px;">
        <div class="card-header">
          <span class="card-title">${this.icon('settings')} Test Catalog & Section Configuration</span>
          <button class="btn btn-primary" onclick="app.showAddTestModal()">${this.icon('plus')} Add New Test</button>
        </div>
        <div id="config-table-container">
          <p style="color: var(--text-muted);">Loading configuration...</p>
        </div>
      </div>

      ${isSuperAdmin ? `
      <div class="card" id="pending-users-card" style="margin-bottom: 24px;">
        <div class="card-header">
          <span class="card-title">${this.icon('user-plus')} Pending Registration Requests</span>
        </div>
        <div id="pending-users-container">
          <p style="color: var(--text-muted);">Loading pending requests...</p>
        </div>
      </div>

      <div class="card" id="active-users-card">
        <div class="card-header">
          <span class="card-title">${this.icon('users')} Active Lab Staff Accounts</span>
        </div>
        <div id="active-users-container">
          <p style="color: var(--text-muted);">Loading accounts...</p>
        </div>
      </div>
      ` : ''}
    `;
    await this.loadConfigData();
  },

  async loadConfigData() {
    try {
      // 1. Load test catalog
      const res = await fetch('/api/config/tests');
      if (res.ok) {
        const tests = await res.json();
        let rows = '';
        tests.forEach(t => {
          rows += `
            <tr>
              <td><strong>${this.escape(t.name)}</strong></td>
              <td>Section ${t.section_id}</td>
              <td>${t.is_tracked ? '<span class="tag-positive">Tracked (Positive Checked)</span>' : '<span class="tag-na">Standard (Done Only)</span>'}</td>
              <td>
                <button class="btn btn-secondary" style="padding: 2px 8px; font-size: 0.8rem;" onclick="app.deleteTest(${t.id})">Delete</button>
              </td>
            </tr>
          `;
        });
        const catalogContainer = document.getElementById('config-table-container');
        if (catalogContainer) {
          catalogContainer.innerHTML = `
            <table class="data-table">
              <thead>
                <tr>
                  <th>Test Name</th>
                  <th>Section ID</th>
                  <th>Surveillance Tracking</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                ${rows}
              </tbody>
            </table>
          `;
        }
      }

      // 2. Load user management for superadmin
      if (this.currentUser && this.currentUser.role === 'superadmin') {
        const userRes = await fetch('/api/auth/users');
        if (userRes.ok) {
          const users = await userRes.json();

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
                const formattedDate = u.created_at ? u.created_at.replace('T', ' ').substring(0, 19) : '—';
                pendingRows += `
                  <tr>
                    <td><strong>${this.escape(u.full_name)}</strong></td>
                    <td><code>${this.escape(u.username)}</code></td>
                    <td>${this.escape(formattedDate)}</td>
                    <td>
                      <div style="display: flex; gap: 8px; align-items: center;">
                        <button class="btn btn-success" style="padding: 4px 10px; font-size: 0.8rem;" onclick="app.approveUser(${u.id}, '${this.escape(u.role)}')">Approve</button>
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
                const statusBadge = u.password_reset_required
                  ? '<span class="tag-na" style="background: var(--warning-color); color: white;">Temporary (Reset Required)</span>'
                  : '<span class="tag-positive">Active</span>';

                const roleSelect = `
                  <select onchange="app.changeUserRole(${u.id}, this.value, true)" ${isSelf ? 'disabled' : ''} style="padding: 4px 8px; border-radius: 4px; border: 1px solid var(--border-color); font-size: 0.85rem;">
                    <option value="technician" ${u.role === 'technician' ? 'selected' : ''}>Technician</option>
                    <option value="Laboratory Technologist" ${u.role === 'Laboratory Technologist' ? 'selected' : ''}>Laboratory Technologist</option>
                    <option value="admin" ${u.role === 'admin' ? 'selected' : ''}>Administrator</option>
                    <option value="superadmin" ${u.role === 'superadmin' ? 'selected' : ''}>Super Administrator</option>
                  </select>
                `;

                const deactivateBtn = !isSelf
                  ? `<button class="btn btn-secondary" style="padding: 4px 8px; font-size: 0.8rem; color: var(--danger-color); border-color: var(--danger-color);" onclick="app.deactivateUser(${u.id}, '${this.escape(u.role)}')">Deactivate</button>`
                  : '';

                activeRows += `
                  <tr>
                    <td><strong>${this.escape(u.full_name)}</strong> ${isSelf ? '<small style="color: var(--primary-color); font-weight: 600;">(You)</small>' : ''}</td>
                    <td><code>${this.escape(u.username)}</code></td>
                    <td>${roleSelect}</td>
                    <td>${statusBadge}</td>
                    <td>
                      <div style="display: flex; gap: 6px; align-items: center;">
                        <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 0.8rem;" onclick="app.promptResetPassword(${u.id}, '${this.escape(u.username)}', '${this.escape(u.role)}')">Reset Password</button>
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

  async approveUser(userId, role) {
    await this.saveUserUpdate(userId, { role: role || 'technician', is_active: true });
    this.showToast('User registration approved successfully!', 'success');
  },

  async rejectUser(userId, username) {
    if (!confirm(`Are you sure you want to reject and delete the registration for '${username}'?`)) return;
    try {
      const res = await fetch(`/api/auth/users/${userId}`, { method: 'DELETE' });
      if (res.ok) {
        this.showToast(`Registration for '${username}' rejected and removed.`, 'success');
        await this.loadConfigData();
      } else {
        const err = await res.json();
        this.showToast(err.detail || 'Failed to reject registration.', 'error');
      }
    } catch (e) {
      this.showToast('Connection error rejecting registration.', 'error');
    }
  },

  async deactivateUser(userId, role) {
    if (!confirm('Are you sure you want to deactivate this account?')) return;
    await this.saveUserUpdate(userId, { role: role, is_active: false });
    this.showToast('User account deactivated.', 'success');
  },

  async changeUserRole(userId, newRole, isActive) {
    await this.saveUserUpdate(userId, { role: newRole, is_active: isActive });
    this.showToast('Role updated successfully.', 'success');
  },

  async promptResetPassword(userId, username, role) {
    const tempPw = prompt(`Enter a new temporary password for user '${username}' (minimum 4 characters):`);
    if (tempPw === null) return; // user clicked Cancel
    if (tempPw.trim().length < 4) {
      this.showToast('Password must be at least 4 characters long.', 'error');
      return;
    }
    await this.saveUserUpdate(userId, { role: role, is_active: true, password: tempPw.trim() });
    this.showToast(`Password reset for '${username}'. User will be required to change it on next login.`, 'success');
  },

  async saveUserUpdate(userId, updateBody) {
    try {
      const res = await fetch(`/api/auth/users/${userId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updateBody)
      });
      if (res.ok) {
        if (userId === this.currentUser.id) {
          await this.checkAuth();
        } else {
          await this.loadConfigData();
        }
      } else {
        const err = await res.json();
        this.showToast(err.detail || 'Failed to update user account.', 'error');
      }
    } catch (e) {
      this.showToast('Connection error updating account.', 'error');
    }
  },

  async showAddTestModal() {
    const name = prompt('Enter Test Name:');
    if (!name) return;
    const secStr = prompt('Enter Section ID (1-8):', '1');
    if (!secStr) return;
    const isTracked = confirm('Enable Surveillance Tracking (Positives) for this test?');

    try {
      const res = await fetch('/api/config/tests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          section_id: parseInt(secStr, 10),
          is_tracked: isTracked,
          sort_order: 0
        })
      });
      if (res.ok) {
        this.showToast('Test added successfully!', 'success');
        this.loadConfigData();
      } else {
        const err = await res.json();
        this.showToast(err.detail || 'Failed to add test.', 'error');
      }
    } catch (e) {
      this.showToast('Connection error.', 'error');
    }
  },

  async deleteTest(testId) {
    if (!confirm('Are you sure you want to deactivate/delete this test from the catalog?')) return;
    try {
      const res = await fetch(`/api/config/tests/${testId}`, { method: 'DELETE' });
      if (res.ok) {
        this.showToast('Test removed from catalog.', 'success');
        this.loadConfigData();
      } else {
        this.showToast('Failed to delete test.', 'error');
      }
    } catch (e) {
      this.showToast('Connection error.', 'error');
    }
  },

  // Audit Log View
  async renderAuditLog(container) {
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
      const res = await fetch('/api/audit-log');
      if (!res.ok) return;
      const logs = await res.json();

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

  escape(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
};

window.addEventListener('DOMContentLoaded', () => {
  app.init();
});
