/* =========================================================
   AGRI ONE-OS / K2P
   Backend JWT authentication
   ========================================================= */

/*
  Same-origin is used by default.

  If the HTML dashboard is hosted on another domain during
  development, define this BEFORE auth.js:

  window.LIMS_API_BASE = 'http://127.0.0.1:8000';
*/
const API_BASE = (window.LIMS_API_BASE || '').replace(/\/$/, '');

const SESSION_KEY = 'agrione_k2p_backend_session';

function normalizeRole(role) {
  return String(role || '')
    .trim()
    .toLowerCase();
}

function getSession() {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);

    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}

function setSession(data) {
  const session = {
    access: data.access,
    refresh: data.refresh,
    user_id: data.user_id,
    role: normalizeRole(data.user_role),
    roleLabel: data.user_role || '',
    name: data.user_name || data.user_role || 'User',
    ts: Date.now(),
  };

  try {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
  } catch (e) {}

  return session;
}

function updateSession(session) {
  try {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
  } catch (e) {}
}

function clearSession() {
  try {
    sessionStorage.removeItem(SESSION_KEY);
  } catch (e) {}
}

async function tryLogin(username, password) {
  const response = await fetch(API_BASE + '/api/project-dashboard/login/', {
    method: 'POST',

    headers: {
      'Content-Type': 'application/json',
    },

    body: JSON.stringify({
      username: username,
      password: password,
    }),
  });

  if (!response.ok) {
    return null;
  }

  const data = await response.json();

  return setSession(data);
}

async function refreshAccessToken() {
  const session = getSession();

  if (!session || !session.refresh) {
    return null;
  }

  const response = await fetch(API_BASE + '/api/token/refresh/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      refresh: session.refresh,
    }),
  });

  if (!response.ok) {
    clearSession();
    return null;
  }

  const data = await response.json();

  session.access = data.access;

  if (data.refresh) {
    session.refresh = data.refresh;
  }

  updateSession(session);

  return session.access;
}

async function apiFetch(path, options) {
  options = options || {};

  let session = getSession();

  if (!session) {
    throw new Error('Authentication required.');
  }

  const headers = new Headers(options.headers || {});

  headers.set('Authorization', 'Bearer ' + session.access);

  let response = await fetch(API_BASE + path, {
    ...options,
    headers,
  });

  if (response.status !== 401) {
    return response;
  }

  const newAccess = await refreshAccessToken();

  if (!newAccess) {
    clearSession();
    location.reload();

    return response;
  }

  headers.set('Authorization', 'Bearer ' + newAccess);

  response = await fetch(API_BASE + path, {
    ...options,
    headers,
  });

  return response;
}

/* =========================================================
   LOGIN UI
   ========================================================= */

function injectAuthStyles() {
  if (document.getElementById('auth-styles')) {
    return;
  }

  const style = document.createElement('style');

  style.id = 'auth-styles';

  style.textContent = `
    #authOverlay{
      position:fixed;
      inset:0;
      background:
        linear-gradient(
          135deg,
          #14561A,
          #1F3864
        );
      display:flex;
      align-items:center;
      justify-content:center;
      z-index:99999;
      font-family:
        'Inter',
        -apple-system,
        'Segoe UI',
        Roboto,
        sans-serif;
      padding:16px;
    }

    #authOverlay .box{
      background:#fff;
      border-radius:14px;
      padding:34px 30px;
      width:100%;
      max-width:360px;
      box-shadow:
        0 20px 60px
        rgba(0,0,0,.35);
    }

    #authOverlay h2{
      font-family:
        'Barlow Condensed',
        sans-serif;
      font-size:26px;
      color:#1F3864;
      margin-bottom:4px;
      text-align:center;
    }

    #authOverlay p.sub{
      font-size:12.5px;
      color:#6B7280;
      text-align:center;
      margin-bottom:22px;
    }

    #authOverlay label{
      display:block;
      font-size:11px;
      font-weight:700;
      color:#6B7280;
      text-transform:uppercase;
      margin:14px 0 5px;
    }

    #authOverlay input{
      width:100%;
      padding:10px 12px;
      border:
        1.5px solid #E3E6EA;
      border-radius:8px;
      font-size:14px;
      box-sizing:border-box;
    }

    #authOverlay input:focus{
      outline:
        2px solid #A5D6A7;
      border-color:#2E9E33;
    }

    #authOverlay button{
      width:100%;
      margin-top:20px;
      padding:11px;
      border:0;
      border-radius:8px;
      background:#1B5E20;
      color:#fff;
      font-weight:700;
      font-size:14px;
      cursor:pointer;
    }

    #authOverlay .err{
      color:#D32F2F;
      font-size:12.5px;
      margin-top:10px;
      text-align:center;
      min-height:16px;
    }
  `;

  document.head.appendChild(style);
}

function showLoginGate(opts) {
  opts = opts || {};

  injectAuthStyles();

  if (document.getElementById('authOverlay')) {
    return;
  }

  const overlay = document.createElement('div');

  overlay.id = 'authOverlay';

  overlay.innerHTML = `
    <div class="box">
      <h2>AgriOne-OS (K2P)</h2>

      <p class="sub">
        ${opts.subtitle || 'Sign in to continue'}
      </p>

      <form id="loginForm">

        <label>
  Username
</label>

<input
  type="text"
  id="loginUsername"
  autocomplete="username"
  placeholder="admin / ceo / guest"
  required
>

        <label>
          Password
        </label>

        <input
          type="password"
          id="loginPass"
          autocomplete="current-password"
          required
        >

        <button
          type="submit"
          id="loginButton"
        >
          Sign In
        </button>

        <div
          class="err"
          id="loginErr"
        ></div>

      </form>
    </div>
  `;

  document.body.appendChild(overlay);

  document
    .getElementById('loginForm')
    .addEventListener('submit', async function (e) {
      e.preventDefault();

      const button = document.getElementById('loginButton');

      const error = document.getElementById('loginErr');

      button.disabled = true;

      button.textContent = 'Signing in...';

      error.textContent = '';

      try {
        const session = await tryLogin(
          document.getElementById('loginUsername').value.trim(),

          document.getElementById('loginPass').value,
        );

        if (session) {
          location.reload();
          return;
        }

        error.textContent = 'Invalid mobile number or password.';
      } catch (err) {
        error.textContent = 'Unable to connect to the backend.';
      } finally {
        button.disabled = false;

        button.textContent = 'Sign In';
      }
    });
}

function requireAuth(opts) {
  opts = opts || {};

  const session = getSession();

  if (!session) {
    showLoginGate(opts);
    return null;
  }

  if (opts.allowRoles) {
    const allowed = opts.allowRoles.map(normalizeRole);

    if (!allowed.includes(normalizeRole(session.role))) {
      if (opts.deniedMessage) {
        alert(opts.deniedMessage);
      }

      location.href = opts.redirectTo || 'dashboard.html';

      return null;
    }
  }

  return session;
}

function renderUserBar(container, session, buttonClass) {
  if (!container || !session) {
    return;
  }

  const bar = document.createElement('span');

  bar.style.cssText =
    'margin-left:auto;' +
    'display:flex;' +
    'align-items:center;' +
    'gap:10px;' +
    'color:#fff;' +
    'font-size:12.5px;' +
    'font-weight:600;';

  const who = document.createElement('span');

  who.textContent =
    session.name + ' · ' + (session.roleLabel || session.role).toUpperCase();

  const button = document.createElement('button');

  button.type = 'button';

  button.textContent = 'Logout';

  button.className = buttonClass || 'btn ghost';

  button.onclick = function () {
    clearSession();
    location.reload();
  };

  bar.appendChild(who);

  bar.appendChild(button);

  container.appendChild(bar);
}
