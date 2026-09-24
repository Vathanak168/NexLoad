/* ========================================
   NEXLOAD — app.js  v5.0 Commercial
   Real Download via local Python + yt-dlp
   ======================================== */

const API = (window.location.protocol.startsWith('http'))
  ? `${window.location.origin}/api`
  : 'http://localhost:5000/api';

function readStoredJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    localStorage.removeItem(key);
    return fallback;
  }
}

const defaultSettings = {
  concurrent: 3, autoPaste: true, notifications: true,
  speedLimit: '', subtitles: false, subLang: 'en', theme: 'light', autoDetectBar: false,
};

// ============================================================
// STATE
// ============================================================
const state = {
  currentPage: 'home',
  serverOnline: false,
  language: localStorage.getItem('nexload_lang') || 'en',
  history: readStoredJson('nexload_history', []),
  favorites: readStoredJson('nexload_favorites', []),
  settings: { ...defaultSettings, ...readStoredJson('nexload_settings', {}) },
  licenseKey: localStorage.getItem('nexload_license') || null,
  licenseEmail: localStorage.getItem('nexload_email') || null,
  licenseInfo: null,
  queue: [],   // active downloads queue
  queuePanelOpen: false,
  preferredMode: null,
};

function authHeaders(extra = {}) {
  const headers = { ...extra };
  if (state.licenseKey) headers['X-License-Key'] = state.licenseKey;
  if (state.licenseEmail) headers['X-License-Email'] = state.licenseEmail;
  return headers;
}

async function readApiJson(res) {
  const text = await res.text();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    const snippet = text.replace(/\s+/g, ' ').slice(0, 180);
    return { error: `Server returned non-JSON response (${res.status}): ${snippet}` };
  }
}

// ============================================================
// I18N
// ============================================================
const i18n = {
  en: {
    analyze: 'Analyze', download: 'Download', paste: 'Paste',
    analyzing: 'Analyzing...', error: 'Please enter a valid URL',
    history: 'Download History', clear: 'Clear All',
    serverOff: '⚠️ Server Offline — Run start_server.bat first',
    serverOn: '🟢 Server Ready',
    homeTitle1: 'Download Anything,<br/>',
    homeTitle2: 'Anywhere.',
    homeSub: 'Ultra HD quality, lightning fast. Choose your platform and paste the link.',
    searchPlaceholder: 'https://www.youtube.com/watch?v=...',
    recent: 'Recent Downloads',
    emptyRecent: 'No downloads yet. Start by choosing a platform above.',
    statsTitle: '📊 Statistics Dashboard',
    statsSub: 'Your download activity overview',
    settingsTitle: '⚙️ Settings',
    settingsSub: 'Configure your download preferences',
    dlFolder: 'Download Folder',
    dlSpeed: 'Download Speed',
    unlimited: 'Unlimited',
    subtitles: 'Subtitles',
    dlSubtitles: 'Download subtitles',
    concurrent: 'Concurrent Downloads',
    themeStr: '🎨 Theme',
    langStr: 'Language'
  },
  kh: {
    analyze: 'វិភាគ', download: 'ទាញយក', paste: 'បិទភ្ជាប់',
    analyzing: 'កំពុងវិភាគ...', error: 'សូមបញ្ចូល URL ត្រឹមត្រូវ',
    history: 'ប្រវត្តិទាញយក', clear: 'លុបទាំងអស់',
    serverOff: '⚠️ Server មិន Online — Run start_server.bat ជាមុន',
    serverOn: '🟢 Server Ready',
    homeTitle1: 'ទាញយកគ្រប់យ៉ាង,<br/>',
    homeTitle2: 'គ្រប់ទីកន្លែង។',
    homeSub: 'កម្រិតច្បាស់ខ្ពស់បំផុត និងលឿនរហ័ស។ ជ្រើសរើសមជ្ឈមណ្ឌល ហើយចំណាំ Link បញ្ចូល។',
    searchPlaceholder: 'https://www.youtube.com/watch?v=...',
    recent: 'ទាញយកថ្មីៗ',
    emptyRecent: 'មិនទាន់មានអ្វីទាញយកទេ។ សូមជ្រើសរើសផ្ទាំងខាងលើ។',
    statsTitle: '📊 ស្ថិតិការទាញយក',
    statsSub: 'ទិន្នន័យនៃការទាញយករបស់អ្នក',
    settingsTitle: '⚙️ ការកំណត់ (Settings)',
    settingsSub: 'កំណត់រចនាសម្ព័ន្ធកម្មវិធី',
    dlFolder: 'តំបន់រក្សាទុក (Folder)',
    dlSpeed: 'កំណត់ល្បឿន',
    unlimited: 'គ្មានកំណត់',
    subtitles: 'អក្សររត់ (Subtitles)',
    dlSubtitles: 'ទាញយកចំណងជើងរង',
    concurrent: 'ទាញយកព្រមគ្នា',
    themeStr: '🎨 ពណ៌កម្មវិធី',
    langStr: 'ភាសា (Language)'
  },
};
function t(key) { return (i18n[state.language] || i18n.en)[key] || key; }

function applyTranslations() {
  // Common buttons
  document.querySelectorAll('.analyze-btn').forEach(b => {
    if(!b.disabled && !b.innerHTML.includes('...')) b.innerHTML = b.innerHTML.replace(/(Analyze|វិភាគ)/g, t('analyze'));
  });
  document.querySelectorAll('.paste-btn').forEach(b => {
    b.innerHTML = b.innerHTML.replace(/(Paste|បិទភ្ជាប់)/g, t('paste'));
  });
  
  // Home Text
  const titleGroup = document.querySelector('.page-title-group h1');
  if(titleGroup) titleGroup.innerHTML = t('homeTitle1') + '<span class="gradient-text">' + t('homeTitle2') + '</span>';
  const heroSub = document.querySelector('.hero-subtitle');
  if(heroSub) heroSub.textContent = t('homeSub');
  
  const recTit = document.querySelector('#page-home .section-title');
  if(recTit) recTit.textContent = t('recent');
  
  const empP = document.querySelector('#emptyHistory p');
  if(empP) empP.textContent = t('emptyRecent');
  
  // Stats
  const statH = document.querySelector('#page-stats .platform-page-title');
  if(statH) statH.textContent = t('statsTitle');
  const statSub = document.querySelector('#page-stats .platform-page-sub');
  if(statSub) statSub.textContent = t('statsSub');
  
  // Settings
  const setH = document.querySelector('#page-settings .platform-page-title');
  if(setH) setH.textContent = t('settingsTitle');
  const setSub = document.querySelector('#page-settings .platform-page-sub');
  if(setSub) setSub.textContent = t('settingsSub');
  
  // Settings Cards (Update text nodes while preserving SVGs)
  document.querySelectorAll('.settings-card-title').forEach(el => {
    const textNode = Array.from(el.childNodes).find(n => n.nodeType === 3 && n.textContent.trim().length > 0);
    if (!textNode) return;
    const txt = textNode.textContent.trim();
    if (txt.includes('Download Folder') || txt.includes('តំបន់រក្សាទុក')) textNode.textContent = ' ' + t('dlFolder');
    else if (txt.includes('Download Speed') || txt.includes('កំណត់ល្បឿន')) textNode.textContent = ' ' + t('dlSpeed');
    else if (txt.includes('Subtitles') || txt.includes('អក្សររត់')) textNode.textContent = ' ' + t('subtitles');
    else if (txt.includes('Concurrent Downloads') || txt.includes('ទាញយកព្រមគ្នា')) textNode.textContent = ' ' + t('concurrent');
    else if (txt.includes('Theme') || txt.includes('ពណ៌កម្មវិធី')) textNode.textContent = ' ' + t('themeStr');
    else if (txt.includes('Language') || txt.includes('ភាសា')) textNode.textContent = ' ' + t('langStr');
  });
}

// ============================================================
// PLATFORM CONFIG
// ============================================================
const platformMap = {
  youtube: { urlId: 'yt-url', btnId: 'yt-analyze-btn', resultId: 'yt-result', chipGroupId: 'yt-quality-chips' },
  tiktok: { urlId: 'tt-url', btnId: 'tt-analyze-btn', resultId: 'tt-result', chipGroupId: 'tt-quality-chips' },
  facebook: { urlId: 'fb-url', btnId: 'fb-analyze-btn', resultId: 'fb-result', chipGroupId: 'fb-quality-chips' },
  instagram: { urlId: 'ig-url', btnId: 'ig-analyze-btn', resultId: 'ig-result', chipGroupId: 'ig-quality-chips' },
  pinterest: { urlId: 'pi-url', btnId: 'pi-analyze-btn', resultId: 'pi-result', chipGroupId: 'pi-quality-chips' },
  pexels: { urlId: 'px-url', btnId: 'px-analyze-btn', resultId: 'px-result', chipGroupId: 'px-quality-chips' },
  universal: { urlId: 'uni-url', btnId: 'uni-analyze-btn', resultId: 'uni-result', chipGroupId: 'uni-quality-chips' },
};
const platformEmoji = { youtube: '📺', tiktok: '🎵', facebook: '📘', instagram: '📸', pinterest: '📌', pexels: '📸' };
const platformColors = { youtube: '#ff0033', tiktok: '#00f0ea', facebook: '#1877f2', instagram: '#e1306c', pinterest: '#e60023', pexels: '#05a081' };

// ============================================================
// SERVER STATUS CHECK
// ============================================================
let googleSdkInitialized = false;
async function checkServer() {
  try {
    const res = await fetch(`${API}/ping`, { signal: AbortSignal.timeout(10000) });
    const d = await readApiJson(res);
    setServerStatus(d.ok === true);
    if (d.dir) state.downloadDir = d.dir;
    const versionEl = document.getElementById('settings-version');
    if (versionEl && d.version) versionEl.textContent = `Backend v${d.version}`;
    initGoogleSignIn(d.google_client_id);
  } catch {
    setServerStatus(false);
    initGoogleSignIn();
  }
}

function initGoogleSignIn(clientId) {
  const cid = clientId || '923992084689-7vatdvl000adfn4l3h0opvbvg8s24ml8.apps.googleusercontent.com';
  if (googleSdkInitialized) return;
  if (!window.google || !google.accounts || !google.accounts.id) {
    setTimeout(() => initGoogleSignIn(cid), 500);
    return;
  }
  googleSdkInitialized = true;
  google.accounts.id.initialize({
    client_id: cid,
    callback: handleGoogleCredentialResponse
  });
  const container = document.getElementById('googleSignInDiv');
  if (container) {
    google.accounts.id.renderButton(container, { theme: 'outline', size: 'large', width: 260 });
  }
}

async function handleGoogleCredentialResponse(response) {
  if (!response || !response.credential) return;
  await processSSOLogin({ token: response.credential });
}

async function continueWithEmail() {
  const emailInput = document.getElementById('loginEmailInput');
  const errorEl = document.getElementById('loginError1');
  const btn = document.getElementById('ssoNextBtn');
  const email = (emailInput?.value || '').trim();
  if (!email || !email.includes('@')) {
    if (errorEl) errorEl.textContent = 'Please enter a valid Google email address.';
    return;
  }
  if (btn) { btn.disabled = true; btn.textContent = 'Verifying...'; }
  if (errorEl) errorEl.textContent = '';
  await processSSOLogin({ email });
  if (btn) { btn.disabled = false; btn.textContent = 'Next →'; }
}

async function processSSOLogin(payload) {
  const errorEl = document.getElementById('loginError1');
  try {
    const res = await fetch(`${API}/auth/google`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await readApiJson(res);
    if (data.valid && data.auto_login) {
      localStorage.setItem('nexload_license', data.key);
      localStorage.setItem('nexload_email', data.bound_email);
      state.licenseKey = data.key;
      state.licenseEmail = data.bound_email;
      state.licenseInfo = data;
      hideLicenseOverlay();
      showToast(`✅ Automatic SSO Login: Welcome, ${data.user}!`, 'success');
      updateLicenseInfoBox(data);
    } else if (data.needs_key) {
      window.verifiedSSOEmail = data.email;
      window.verifiedSSOToken = data.email_token || '';
      document.getElementById('step1Google').style.display = 'none';
      document.getElementById('step2Key').style.display = 'block';
      const badge = document.getElementById('verifiedEmailBadge');
      if (badge) badge.textContent = data.email;
    } else {
      if (errorEl) errorEl.textContent = '❌ ' + (data.reason || 'Authentication failed');
    }
  } catch (err) {
    if (errorEl) errorEl.textContent = '❌ Server error during SSO check.';
  }
}

function backToStep1() {
  document.getElementById('step2Key').style.display = 'none';
  document.getElementById('step1Google').style.display = 'block';
}

function setServerStatus(online) {
  state.serverOnline = online;
  const badge = document.getElementById('serverBadge');
  if (badge) {
    badge.textContent = online ? t('serverOn') : t('serverOff');
    badge.className = `server-badge ${online ? 'server-online' : 'server-offline'}`;
  }
  const settingsBadge = document.getElementById('settings-server-status');
  if (settingsBadge) {
    settingsBadge.textContent = online ? t('serverOn') : t('serverOff');
    settingsBadge.className = `server-badge ${online ? 'server-online' : 'server-offline'}`;
  }
}

// Poll server status every 5 seconds
setInterval(checkServer, 5000);

// ============================================================
// LICENSE / LOGIN SYSTEM
// ============================================================
async function submitLicense() {
  const input = document.getElementById('licenseKeyInput');
  const emailInput = document.getElementById('loginEmailInput');
  const errorEl = document.getElementById('loginError');
  const btn = document.getElementById('loginBtn');
  const key = (input?.value || '').trim().toUpperCase();
  const email = (window.verifiedSSOEmail || emailInput?.value || state.licenseEmail || '').trim().toLowerCase();

  if (!key || key.length < 8) {
    if (errorEl) errorEl.textContent = 'Please enter a valid license key.';
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Validating...';
  if (errorEl) errorEl.textContent = '';

  try {
    const res = await fetch(`${API}/auth/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key, email, email_token: window.verifiedSSOToken || '' }),
    });
    const data = await readApiJson(res);

    if (data.valid) {
      localStorage.setItem('nexload_license', key);
      const savedEmail = email || data.bound_email || '';
      if (savedEmail) localStorage.setItem('nexload_email', savedEmail);
      state.licenseKey = key;
      state.licenseEmail = savedEmail;
      state.licenseInfo = data;
      document.documentElement.classList.add('has-license');
      hideLicenseOverlay();
      showToast(`✅ Welcome, ${data.user}! License activated.`, 'success');
      updateLicenseInfoBox(data);
    } else {
      if (errorEl) errorEl.textContent = '❌ ' + (data.reason || 'Invalid key');
      input.style.borderColor = 'rgba(239,68,68,0.6)';
    }
  } catch (err) {
    if (errorEl) errorEl.textContent = '❌ Server error. Make sure server is running.';
  }

  btn.disabled = false;
  btn.textContent = 'Activate & Continue →';
}

function hideLicenseOverlay() {
  document.documentElement.classList.add('has-license');
  const overlay = document.getElementById('loginOverlay');
  if (overlay) {
    overlay.style.opacity = '0';
    overlay.style.transition = 'opacity 0.4s ease';
    setTimeout(() => overlay.classList.add('hidden'), 400);
  }
}

async function checkCachedLicense() {
  const key = state.licenseKey;
  const email = state.licenseEmail;
  if (!key) {
    document.documentElement.classList.remove('has-license');
    const overlay = document.getElementById('loginOverlay');
    if (overlay) {
      overlay.classList.remove('hidden');
      overlay.style.opacity = '1';
    }
    return false;
  }

  // License exists: keep overlay hidden immediately
  hideLicenseOverlay();

  try {
    const res = await fetch(`${API}/auth/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key, email }),
    });
    const data = await readApiJson(res);
    if (data.valid) {
      state.licenseInfo = data;
      if (data.bound_email && !state.licenseEmail) {
        state.licenseEmail = data.bound_email;
        localStorage.setItem('nexload_email', data.bound_email);
      }
      updateLicenseInfoBox(data);
      return true;
    }
    
    // Only logout if explicitly revoked or expired
    if (data.reason && (data.reason.includes('revoked') || data.reason.includes('expired') || data.reason.includes('banned'))) {
      localStorage.removeItem('nexload_license');
      localStorage.removeItem('nexload_email');
      state.licenseKey = null;
      state.licenseEmail = null;
      document.documentElement.classList.remove('has-license');
      const errEl = document.getElementById('loginError1') || document.getElementById('loginError');
      if (errEl) errEl.textContent = '❌ ' + data.reason;

      const overlay = document.getElementById('loginOverlay');
      if (overlay) {
        overlay.classList.remove('hidden');
        overlay.style.opacity = '1';
      }
      return false;
    }
    return true;
  } catch {
    // Offline or server starting up: retain session
    return true;
  }
}

function updateLicenseInfoBox(info) {
  const box = document.getElementById('licenseInfoBox');
  if (!box) return;
  if (!info) {
    box.innerHTML = '<div class="license-info-badge license-invalid">❌ No license activated</div>';
    return;
  }
  box.innerHTML = `
    <div class="license-info-badge license-valid">✅ ${info.tier_label} License Active</div>
    <div style="margin-top:12px;display:grid;gap:6px;font-size:0.85rem">
      <div><span style="color:var(--text-muted)">User: </span>${escapeHtml(info.user || '—')}</div>
      <div><span style="color:var(--text-muted)">Expires: </span>${(info.expires || '').slice(0,10)}</div>
      <div><span style="color:var(--text-muted)">Days Left: </span>${info.days_left}</div>
      <div><span style="color:var(--text-muted)">Speed Limit: </span>${info.daily_limit ? info.daily_limit + '/day' : 'Unlimited'}</div>
      <div><span style="color:var(--text-muted)">Batch Mode: </span>${info.batch ? '✅ Yes' : '❌ No'}</div>
    </div>
    <button onclick="logout()" style="margin-top:14px;padding:8px 16px;border-radius:8px;border:1px solid rgba(239,68,68,0.3);background:rgba(239,68,68,0.08);color:#ef4444;cursor:pointer;font-family:Outfit,sans-serif;font-size:0.82rem">
      🔒 Log Out
    </button>
  `;
}

function logout() {
  localStorage.removeItem('nexload_license');
  localStorage.removeItem('nexload_email');
  state.licenseKey = null;
  state.licenseEmail = null;
  state.licenseInfo = null;
  window.verifiedSSOEmail = '';
  window.verifiedSSOToken = '';
  document.documentElement.classList.remove('has-license');
  try { fetch(`${API}/auth/logout`, { method: 'POST' }); } catch {}
  const keyInput = document.getElementById('licenseKeyInput');
  if (keyInput) keyInput.value = '';
  const loginError = document.getElementById('loginError');
  if (loginError) loginError.textContent = '';
  const step2 = document.getElementById('step2Key');
  if (step2) step2.style.display = 'none';
  const step1 = document.getElementById('step1Google');
  if (step1) step1.style.display = 'block';
  const overlay = document.getElementById('loginOverlay');
  if (overlay) {
    overlay.classList.remove('hidden');
    overlay.style.opacity = '1';
  }
  showToast('Logged out. Please enter your license key.', 'info');
}

// Ensure HWID is fetched when app opens if there's no cached license
setTimeout(async () => {
  if (state.licenseKey) {
    await checkCachedLicense();
  } else {
    const restored = await checkLocalServerLicense();
    if (!restored) {
      document.documentElement.classList.remove('has-license');
      const overlay = document.getElementById('loginOverlay');
      if (overlay) {
        overlay.classList.remove('hidden');
        overlay.style.opacity = '1';
      }
    }
  }
}, 400);

// Enter key on license input
document.getElementById('licenseKeyInput')?.addEventListener('keydown', e => {
  if (e.key === 'Enter') submitLicense();
});

// ============================================================
// NAVIGATION
// ============================================================
function navigateTo(pageId) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  const target = document.getElementById('page-' + pageId);
  if (target) {
    target.classList.add('active');
    // Logic for subpage back bar is removed to match Figma UI
  }
  document.querySelectorAll('.nav-tab').forEach(tab =>
    tab.classList.toggle('active', tab.dataset.page === pageId)
  );
  document.querySelectorAll('.sidebar-item[data-page]').forEach(item =>
    item.classList.toggle('active', item.dataset.page === pageId)
  );
  const navBackBtn = document.getElementById('navBackBtn');
  if (navBackBtn) navBackBtn.style.display = (pageId === 'home') ? 'none' : 'inline-flex';
  state.currentPage = pageId;
  if (pageId === 'home') state.preferredMode = null;
  const scroller = document.querySelector('.main-content');
  if (scroller) scroller.scrollTo({ top: 0, behavior: 'smooth' });
  if (pageId === 'stats' && typeof loadStats === 'function') loadStats();
  if (pageId === 'settings' && typeof refreshFolderDisplay === 'function') refreshFolderDisplay();
  if (pageId === 'favorites' && typeof renderFavorites === 'function') renderFavorites();
}

document.querySelectorAll('.nav-tab').forEach(tab =>
  tab.addEventListener('click', () => navigateTo(tab.dataset.page))
);
document.querySelectorAll('.platform-card').forEach(card =>
  card.addEventListener('click', () => { if (card.dataset.target) navigateTo(card.dataset.target); })
);
// Quality chips removed — quality selected dynamically after Analyze

// ============================================================
// HELPERS
// ============================================================
function isValidUrl(str) {
  try { const u = new URL(str); return u.protocol === 'http:' || u.protocol === 'https:'; }
  catch { return false; }
}
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ============================================================
// PASTE
// ============================================================
async function pasteUrl(inputId) {
  try {
    const text = await navigator.clipboard.readText();
    const el = document.getElementById(inputId);
    if (el) el.value = text;
    showToast('URL pasted from clipboard', 'info');
  } catch {
    showToast('Clipboard denied — paste manually (Ctrl+V)', 'error');
  }
}

// ============================================================
// ANALYZE  → call /api/info → show real metadata + format list
// ============================================================
// URL patterns for each platform validation
const platformUrlPatterns = {
  youtube: [/youtube\.com/, /youtu\.be/],
  tiktok: [/tiktok\.com/],
  facebook: [/facebook\.com/, /fb\.watch/, /fb\.com/],
  instagram: [/instagram\.com/],
  pinterest: [/pinterest\.com/, /pin\.it/],
  pexels: [/pexels\.com/],
  universal: [/.*/],
};

function validatePlatformUrl(platform, url) {
  const patterns = platformUrlPatterns[platform];
  if (!patterns) return true; // Default to allow if platform not defined in list
  const normalizedUrl = String(url || '').toLowerCase();
  return patterns.some(p => p.test(normalizedUrl));
}

async function analyzeUrl(platform) {
  const map = platformMap[platform];
  if (!map) return;

  const urlEl = document.getElementById(map.urlId);
  const btn = document.getElementById(map.btnId);
  const result = document.getElementById(map.resultId);
  const url = urlEl ? urlEl.value.trim() : '';

  if (!url || !isValidUrl(url)) {
    showToast(t('error'), 'error');
    urlEl && urlEl.focus();
    return;
  }

  // Cross-platform validation
  if (!validatePlatformUrl(platform, url)) {
    const pName = platform.charAt(0).toUpperCase() + platform.slice(1);
    showToast(`⚠️ This URL is not from ${pName}. Please use the correct tab.`, 'error');
    urlEl.style.borderColor = 'rgba(239,68,68,0.6)';
    urlEl.style.background = 'rgba(239,68,68,0.06)';
    return;
  } else {
    urlEl.style.borderColor = '';
    urlEl.style.background = '';
  }

  if (!state.serverOnline) {
    showToast(t('serverOff'), 'error');
    return;
  }

  if ((platform === 'youtube' || url.includes('youtube.com') || url.includes('youtu.be')) &&
      window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1' && window.location.protocol.startsWith('http')) {
    const ws = document.querySelector('.workspace');
    if (ws) ws.setAttribute('data-state', 'result');
    result.innerHTML = `
      <div class="native-engine-card">
        <div class="native-engine-title">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
          ✦ Native Engine Required
        </div>
        <div class="native-engine-copy">
          YouTube extraction is handled by Vordex Desktop for protected-platform compatibility, local processing, and maximum download speed. Included with your license!
        </div>
        <div style="display:flex; gap:12px; margin-top:4px; flex-wrap:wrap;">
          <a href="nexload://open?url=${encodeURIComponent(url)}" class="btn-primary-sm" style="text-decoration:none;">⚡ Open Desktop App</a>
          <a href="https://github.com/Vathanak168/NexLoad/releases/latest/download/NexLoad.exe" class="btn-secondary-sm" style="text-decoration:none;">📥 Download Installer (.exe)</a>
        </div>
      </div>
    `;
    return;
  }

  // Show skeleton + disable button
  const ws = document.querySelector('.workspace');
  if (ws) ws.setAttribute('data-state', 'result');
  btn.textContent = t('analyzing');
  btn.classList.add('loading');
  result.innerHTML = buildSkeleton();

  // Platforms that support image downloading
  const imageSupportedPlatforms = ['instagram', 'pinterest', 'tiktok', 'facebook', 'pexels', 'universal'];

  try {
    const res = await fetch(`${API}/info?url=${encodeURIComponent(url)}`, { headers: authHeaders() });
    const data = await readApiJson(res);

    if (!res.ok || data.error) {
      if (data.is_redirect && data.download_url) {
        if (ws) ws.setAttribute('data-state', 'result');
        result.innerHTML = `
          <div class="native-engine-card">
            <div class="native-engine-title">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
              ✦ Native Engine Required
            </div>
            <div class="native-engine-copy">
              ${data.error || 'Protected platform extraction requires Vordex Desktop.'}
            </div>
            <div style="display:flex; gap:12px; margin-top:4px; flex-wrap:wrap;">
              <a href="${data.download_url}" target="_blank" class="btn-primary-sm" style="text-decoration:none;">📥 Download Desktop App</a>
            </div>
          </div>
        `;
        btn.textContent = t('analyze');
        btn.classList.remove('loading');
        return;
      }
      throw new Error(data.error || `HTTP ${res.status}`);
    }

    // 🆕 Auto-detect image posts:
    // Triggers when: (a) no video formats returned, OR (b) backend flagged isImageCandidate
    // This handles TikTok /photo/ URLs that yt-dlp marks as "Unsupported URL"
    const noFormats = !data.formats || data.formats.length === 0;
    const isCandidate = !!data.isImageCandidate;

    if ((noFormats || isCandidate) && imageSupportedPlatforms.includes(platform)) {
      try {
        const imgRes = await fetch(`${API}/image-info?url=${encodeURIComponent(url)}`, { headers: authHeaders() });
        const imgData = await readApiJson(imgRes);
        if (imgRes.ok && !imgData.error) {
          data.isImagePost = true;
          data.imageInfo = imgData;
          // Use image title/thumbnail if video info missed them
          if ((!data.title || data.title === 'Unknown') && imgData.title) data.title = imgData.title;
          if (!data.thumbnail && imgData.thumbnail) data.thumbnail = imgData.thumbnail;
        } else if (isCandidate) {
          // Even if image-info fails, still show image card for TikTok slideshow candidates
          data.isImagePost = true;
          if (!data.title || data.title === 'Unknown') data.title = 'TikTok Photo / Slideshow';
        }
      } catch { /* fall through — show card anyway */ }
    }

    result.innerHTML = buildResultCard(platform, url, data);
    if (data.isImagePost) {
      const count = data.imageInfo?.count;
      const type  = data.imageInfo?.type;
      if (type === 'slideshow' && count > 0) {
        showToast(`📷 TikTok Slideshow — ${count} images ready to download!`, 'success');
      } else {
        showToast('📷 Image post detected! Click Download to save image.', 'success');
      }
    } else if (data.is_playlist) {
      showToast(`📋 Playlist / Profile Selected: ${data.playlist_count} items ready.`, 'success');
    } else {
      showToast('✅ Video info loaded!', 'success');
    }

  } catch (err) {
    result.innerHTML = buildErrorCard(err.message, url);
    showToast('Failed: ' + err.message, 'error');
  }

  // Restore button
  btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg> ${t('analyze')}`;
  btn.classList.remove('loading');
}

// ============================================================
// RESULT CARD
// ============================================================
function buildResultCard(platform, url, info) {
  const color = platformColors[platform] || '#a855f7';
  const emoji = platformEmoji[platform] || '🎬';
  const ts = Date.now();
  const progId = `prog-${ts}`;
  const doneId = `done-${ts}`;
  const cardId = `card-${ts}`;

  const imageCapablePlatforms = ['instagram', 'pinterest', 'tiktok', 'facebook', 'pexels', 'universal'];
  const supportsImage = imageCapablePlatforms.includes(platform);
  const isImagePost = !!(info?.isImagePost);
  const isPlaylist = !!(info?.is_playlist);
  const playCount = info?.playlist_count || 0;

  // ── Quality setup ──────────────────────────────────────────────
  const fmts = info?.formats || [];
  const maxHeight = info?.max_height || (fmts[0]?.height) || 0;
  const defaultMode = isImagePost ? 'image' : (state.preferredMode === 'audio' && fmts.length ? 'audio' : 'video');
  const defaultH    = isImagePost ? 'image' : (fmts.length ? String(fmts[0].height) : '1080');

  // Helper: map height → short display label for badge & button
  function qShortLabel(h) {
    if (!h || h === 'image' || h === 'audio') return String(h);
    const n = parseInt(h);
    if (n >= 4320) return '8K';
    if (n >= 2160) return '4K';
    if (n >= 1440) return '2K';
    return n + 'p';
  }

  const maxLabel = qShortLabel(maxHeight);
  const maxBadge = maxHeight
    ? `<span class="nrc-max-badge">⭐ MAX QUALITY: ${maxLabel}</span>`
    : '';

  // Quality buttons — auto-select first (highest)
  const firstQualityLabel = fmts.length ? qShortLabel(fmts[0].height) : '1080p';
  const qualBtns = [
    ...fmts.map((f, i) =>
      `<div class="nrc-q-box${defaultMode === 'video' && i === 0 ? ' active' : ''}" data-h="${f.height}" data-short="${qShortLabel(f.height)}" onclick="selectQuality(this,'${cardId}')">
         <div class="nrc-q-main">${qShortLabel(f.height)}</div>
         <div class="nrc-q-sub">${f.label}</div>
         ${i === 0 ? '<div class="nrc-q-best-badge">⭐ Best Quality</div>' : ''}
       </div>`
    ),
    `<div class="nrc-q-box nrc-audio-box${defaultMode === 'audio' ? ' active' : ''}" data-h="audio" data-short="Audio" onclick="selectQuality(this,'${cardId}')">
       <div class="nrc-q-main">&#127925; MP3</div>
       <div class="nrc-q-sub">Audio Only</div>
     </div>`,
    supportsImage
      ? `<div class="nrc-q-box nrc-image-box${isImagePost ? ' active' : ''}" data-h="image" data-short="Image" onclick="selectQuality(this,'${cardId}')">
           <div class="nrc-q-main">&#128247; Thumbnail</div>
           <div class="nrc-q-sub">Image</div>
         </div>`
      : ''
  ].join('');

  // Image/Playlist notice banner
  let imageNoticeBanner = '';
  if (isPlaylist) {
    imageNoticeBanner = `<div class="image-post-notice" style="background:rgba(56,189,248,0.1);color:#38bdf8;border:1px solid rgba(56,189,248,0.2)">
      📋 <strong>Playlist / Account Profile Detected</strong> &mdash; <strong>${playCount} items</strong> will be downloaded. This might take a while!
    </div>`;
  } else if (isImagePost) {
    const imgInfo = info?.imageInfo;
    const slideCount = imgInfo?.count;
    const isSlideshow = imgInfo?.type === 'slideshow' && slideCount > 0;
    imageNoticeBanner = isSlideshow
      ? `<div class="image-post-notice">&#128247; TikTok Slideshow &mdash; <strong>${slideCount} images</strong> will be downloaded to Downloads/Vordex/</div>`
      : `<div class="image-post-notice">&#128247; Image post detected &mdash; quality bar not applicable. Click <strong>Download Image</strong> below.</div>`;
  }

  // Use slideshow cover or fallback thumbnail
  const thumbUrl = info?.imageInfo?.thumbnail || info?.thumbnail;
  const thumb = thumbUrl
    ? `<img src="${escapeHtml(thumbUrl)}" alt="thumb" class="nrc-thumb" />`
    : `<div class="nrc-thumb" style="background:linear-gradient(135deg,${color}22,${color}11);display:flex;align-items:center;justify-content:center;font-size:3rem">${emoji}</div>`;

  const durTag = info?.duration ? escapeHtml(info.duration) : '';
  const viewsTag = info?.views ? escapeHtml(info.views) : '-';
  const reactTag = info?.likes || info?.reactions ? escapeHtml(info.likes || info.reactions) : '-';

  // Initial download button label
  let initDlLabel = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="8 17 12 21 16 17"/><line x1="12" y1="21" x2="12" y2="9"/><path d="M20.88 18.09A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.29"/></svg> Download ${firstQualityLabel}`;
  if (isPlaylist) {
    initDlLabel = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/><line x1="19" y1="5" x2="19" y2="19"/></svg> Download All (${playCount})`;
  } else if (isImagePost) {
    initDlLabel = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg> Download Image`;
  }

  return `
    <div class="new-result-card result-card" id="${cardId}"
      data-url="${escapeHtml(url)}"
      data-platform="${platform}"
      data-quality="${defaultH}"
      data-mode="${defaultMode}">

      ${imageNoticeBanner}

      <!-- Slideshow Grid -->
      ${(() => {
        const imgs = info?.imageInfo?.images;
        const isSlideshow = info?.imageInfo?.type === 'slideshow' && imgs && imgs.length > 0;
        if (!isSlideshow) return '';
        const slideItems = imgs.map((img, i) => {
          const imgUrl = typeof img === 'string' ? img : (img.url || img.thumb || '');
          const safe = escapeHtml(imgUrl);
          return `<div class="slide-item selected" data-url="${safe}" data-idx="${i}" onclick="toggleSlide(this,'${cardId}')">
                     <img src="${safe}" class="slide-thumb" loading="lazy">
                     <button class="slide-preview-btn" onclick="event.stopPropagation();openPreview('${safe}','image')" title="Preview">&#128269;</button>
                     <div class="slide-check">&#10003;</div>
                     <div class="slide-num">${i + 1}</div>
                  </div>`;
        }).join('');
        return `
          <div class="slideshow-controls">
            <span class="slide-count-label">&#128247; Select slides: <strong id="sel-count-${cardId}">${imgs.length}/${imgs.length}</strong></span>
            <div class="slide-ctrl-btns">
              <button class="slide-ctrl-btn" onclick="selectAllSlides('${cardId}')">&#9745; All</button>
              <button class="slide-ctrl-btn" onclick="deselectAllSlides('${cardId}')">&#9744; None</button>
            </div>
          </div>
          <div class="slideshow-grid" id="grid-${cardId}">${slideItems}</div>`;
      })()}

      <div class="nrc-top">
        <div class="nrc-thumb-wrapper">
          ${thumb}
          <div class="nrc-play-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="white" stroke="white" stroke-width="2" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg></div>
          ${durTag ? `<div class="nrc-duration-badge">${durTag}</div>` : ''}
        </div>

        <div class="nrc-info">
          <div class="nrc-title-row">
            <h3 class="nrc-title result-title">${escapeHtml(info?.title?.substring(0, 60) || 'Video Download')}</h3>
            ${maxBadge}
          </div>
          <div class="nrc-subtitle">
            ${viewsTag !== '-' ? `${viewsTag} views • ` : ''}${reactTag !== '-' ? `${reactTag} reactions • ` : ''}Just now
          </div>

          <div class="nrc-stats-grid">
            <div class="nrc-stat-box">
              <div class="nrc-stat-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg></div>
              <div>
                <div class="nrc-stat-val">${viewsTag}</div>
                <div class="nrc-stat-label">Views</div>
              </div>
            </div>
            <div class="nrc-stat-box">
              <div class="nrc-stat-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/></svg></div>
              <div>
                <div class="nrc-stat-val">${reactTag}</div>
                <div class="nrc-stat-label">Reactions</div>
              </div>
            </div>
            <div class="nrc-stat-box">
              <div class="nrc-stat-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg></div>
              <div>
                <div class="nrc-stat-val">${durTag || '0:00'}</div>
                <div class="nrc-stat-label">Duration</div>
              </div>
            </div>
            <div class="nrc-stat-box">
              <div class="nrc-stat-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg></div>
              <div>
                <div class="nrc-stat-val" id="size-val-${cardId}">-- MB</div>
                <div class="nrc-stat-label">Size (DL)</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="nrc-quality-section">
        <div class="nrc-quality-title">DOWNLOAD QUALITY</div>
        <div class="nrc-q-grid">
          ${qualBtns}
        </div>
      </div>

      <div style="display:flex; justify-content:center; align-items:center; margin-top: -8px;">
         <button class="nrc-btn primary download-btn" id="dlbtn-${ts}" onclick="startDownloadFromCard('${cardId}','dlbtn-${ts}','${progId}','${doneId}')" style="width: 100%; justify-content: center; padding: 14px; font-size: 1rem;">
            ${initDlLabel}
         </button>
      </div>
      <div id="${progId}" style="display:none; width: 100%; margin-top: 8px;">
          <div style="display:flex; justify-content:space-between; font-size:0.8rem; font-weight:bold; color:#64748b; margin-bottom:4px;">
              <span id="${progId}-label">Downloading...</span>
              <span id="${progId}-pct" style="color:#6366f1">0%</span>
          </div>
          <div style="width:100%; background:#e2e8f0; border-radius:4px; height:6px; overflow:hidden;">
              <div id="${progId}-fill" style="width:0%; height:100%; background:linear-gradient(90deg, #6366f1, #8b5cf6); transition: width 0.3s;"></div>
          </div>
      </div>

      <div class="nrc-success-banner" id="${doneId}" style="display:none">
        <div class="nrc-success-left">
          <div class="nrc-success-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg></div>
          <div>
            <div class="nrc-success-title">Download Complete!</div>
            <div class="nrc-success-sub">${escapeHtml(info?.title?.substring(0,35) || 'Video')}.mp4 • <span id="${doneId}-size">-- MB</span></div>
          </div>
        </div>
        <div class="nrc-success-actions">
          <button class="nrc-btn primary" onclick="openFolder()">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg> Open File
          </button>
          <button class="nrc-btn" onclick="openFolder()">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg> Open Folder
          </button>
          <button class="nrc-btn" onclick="openFolder()">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg> Share
          </button>
          <button class="nrc-btn" style="padding: 10px;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="1"/><circle cx="12" cy="5" r="1"/><circle cx="12" cy="19" r="1"/></svg>
          </button>
        </div>
      </div>

      <div class="footer-text">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
        We do not store any videos on our servers. All downloads are temporary.
      </div>
    </div>`;
}

// Select quality inside result card
function selectQuality(btn, cardId) {
  const card = document.getElementById(cardId);
  if (!card) return;
  card.querySelectorAll('.nrc-q-box').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  card.dataset.quality = btn.dataset.h;
  const shortLabel = btn.dataset.short || btn.dataset.h;  // e.g. "4K", "1080p", "Audio", "Image"

  // Determine mode: 'audio' | 'image' | 'video'
  if (btn.dataset.h === 'audio') {
    card.dataset.mode = 'audio';
  } else if (btn.dataset.h === 'image') {
    card.dataset.mode = 'image';
  } else {
    card.dataset.mode = 'video';
  }

  // Update download button label
  const dlBtn = card.querySelector('.download-btn');
  if (dlBtn && !dlBtn.disabled) {
    const dlSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="8 17 12 21 16 17"/><line x1="12" y1="21" x2="12" y2="9"/><path d="M20.88 18.09A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.29"/></svg>`;
    const imgSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>`;
    const audSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>`;

    if (card.dataset.mode === 'image') {
      dlBtn.innerHTML = `${imgSvg} Download Image`;
    } else if (card.dataset.mode === 'audio') {
      dlBtn.innerHTML = `${audSvg} Download Audio`;
    } else {
      if (shortLabel.includes('Download All')) {
        dlBtn.innerHTML = `${dlSvg} ${shortLabel}`;
      } else {
        dlBtn.innerHTML = `${dlSvg} Download ${shortLabel}`;
      }
    }
  }
}


// Trigger download from card data attributes
function startDownloadFromCard(cardId, btnId, progId, doneId) {
  const card = document.getElementById(cardId);
  if (!card) return;

  // Collect selected slides for slideshow selective download
  const selectedSlides = [...card.querySelectorAll('.slide-item.selected')]
    .map(el => el.dataset.url).filter(Boolean);

  startDownload(
    card.dataset.url,
    card.dataset.quality || '1080',
    card.dataset.mode || 'video',
    btnId, progId, doneId, cardId,
    card.dataset.platform,
    selectedSlides.length > 0 ? selectedSlides : null,
    card.querySelector('.result-title')?.textContent || ''
  );
}

// ── Slideshow selection helpers ────────────────────────────────
function toggleSlide(el, cardId) {
  el.classList.toggle('selected');
  updateSlideSelection(cardId);
}

function selectAllSlides(cardId) {
  document.querySelectorAll(`#grid-${cardId} .slide-item`)
    .forEach(el => el.classList.add('selected'));
  updateSlideSelection(cardId);
}

function deselectAllSlides(cardId) {
  document.querySelectorAll(`#grid-${cardId} .slide-item`)
    .forEach(el => el.classList.remove('selected'));
  updateSlideSelection(cardId);
}

function updateSlideSelection(cardId) {
  const grid  = document.getElementById(`grid-${cardId}`);
  if (!grid) return;
  const total    = grid.querySelectorAll('.slide-item').length;
  const selected = grid.querySelectorAll('.slide-item.selected').length;
  const countEl  = document.getElementById(`sel-count-${cardId}`);
  const dlCount  = document.getElementById(`dl-count-${cardId}`);
  if (countEl) countEl.textContent = `${selected}/${total}`;
  if (dlCount) dlCount.textContent = selected;
  // Dim download button if nothing selected
  const dlBtn = document.getElementById(`dlbtn-${cardId.replace('card-', 'dlbtn-')}`) ||
                document.querySelector(`#${cardId} .download-btn`);
  if (dlBtn) dlBtn.disabled = selected === 0;
}

// ── Preview Modal ──────────────────────────────────────────────
function openPreview(src, type) {
  // Remove existing modal if any
  const old = document.getElementById('nexload-preview-modal');
  if (old) old.remove();

  const modal = document.createElement('div');
  modal.id = 'nexload-preview-modal';
  modal.className = 'preview-modal';
  modal.onclick = e => { if (e.target === modal) closePreview(); };

  let inner = '';
  if (type === 'image') {
    inner = `<img src="${src}" class="preview-img" alt="Preview" />`;
  } else {
    inner = `<video src="${src}" class="preview-video" controls autoplay></video>`;
  }

  modal.innerHTML = `
    <div class="preview-box">
      <button class="preview-close" onclick="closePreview()">&#10005;</button>
      ${inner}
    </div>`;

  document.body.appendChild(modal);
  requestAnimationFrame(() => modal.classList.add('open'));
}

function closePreview() {
  const modal = document.getElementById('nexload-preview-modal');
  if (!modal) return;
  modal.classList.remove('open');
  setTimeout(() => modal.remove(), 250);
}

// ============================================================
// ERROR CARD
// ============================================================
function buildErrorCard(msg, url) {
  return `
    <div class="inline-error" style="animation:pageIn .3s ease;border-radius:16px;padding:20px 22px">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
      <div>
        <div style="font-weight:700;margin-bottom:4px">Analysis Failed</div>
        <div style="font-size:0.82rem;opacity:.8">${escapeHtml(msg)}</div>
      </div>
    </div>`;
}

// ============================================================
// START DOWNLOAD  → POST /api/download → SSE progress
// ============================================================
async function startDownload(url, quality, mode, btnId, progId, doneId, cardId, platform, directUrls, dlTitle) {
  if (!state.serverOnline) {
    showToast(t('serverOff'), 'error');
    return;
  }

  const btn = document.getElementById(btnId);
  const progWrap = document.getElementById(progId);
  const doneLine = document.getElementById(doneId);
  const fill = document.getElementById(progId + '-fill');
  const label = document.getElementById(progId + '-label');
  const pct = document.getElementById(progId + '-pct');
  const meta = document.getElementById(progId + '-meta');
  if (!btn) return;

  // Lock UI
  btn.disabled = true;
  btn.innerHTML = `<span style="opacity:.7">Downloading...</span>`;
  if (progWrap) progWrap.classList.add('visible');
  setProgress(fill, label, pct, 0, 'Connecting...');

  try {
    // POST to backend → start task
    const dlBody = { url, quality, mode };
    if (directUrls && directUrls.length > 0) {
      dlBody.direct_urls = directUrls;
      dlBody.title = dlTitle || '';
    }
    const res = await fetch(`${API}/download`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({
        ...dlBody,
        subtitles:   state.settings.subtitles || false,
        sub_lang:    state.settings.subLang   || 'en',
        speed_limit: state.settings.speedLimit || '',
      }),
    });
    const data = await readApiJson(res);
    if (!res.ok || data.error) throw new Error(data.error || `HTTP ${res.status}`);

    const task_id = data.task_id;
    state.taskTokens = state.taskTokens || {};
    if (data.task_token) state.taskTokens[task_id] = data.task_token;
    const tokenParam = data.task_token ? (`?token=` + encodeURIComponent(data.task_token)) : '';

    // Add to queue panel
    addToQueue(task_id, dlTitle || url.slice(0,60), url);

    // Listen to SSE progress
    const evtSrc = new EventSource(`${API}/progress/${task_id}${tokenParam}`);

    evtSrc.onmessage = (e) => {
      const task = JSON.parse(e.data);

      if (task.status === 'downloading') {
        setProgress(fill, label, pct, task.progress, `Downloading... ${task.filename || ''}`);
        if (meta) {
          meta.textContent = [
            task.speed ? `⚡ ${task.speed}` : '',
            task.eta ? `⏱ ETA: ${task.eta}` : '',
            task.size ? `💾 ${task.size}` : '',
          ].filter(Boolean).join('   ');
        }

      } else if (task.status === 'processing') {
        setProgress(fill, label, pct, 99, 'Processing & merging...');
        if (meta) meta.textContent = '🔧 Finalizing file...';

      } else if (task.status === 'done') {
        evtSrc.close();
        setProgress(fill, label, pct, 100, 'Complete!');
        if (meta) meta.textContent = '';
        setTimeout(() => {
          if (progWrap) progWrap.classList.remove('visible');
          if (doneLine) {
            doneLine.style.display = 'flex';
            const fn = escapeHtml(task.filename || 'video.mp4');
            const tToken = (state.taskTokens && state.taskTokens[task_id]) ? ('?token=' + encodeURIComponent(state.taskTokens[task_id])) : '';
            doneLine.innerHTML = `
              <div class="nrc-success-left">
                <div class="nrc-success-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg></div>
                <div>
                  <div class="nrc-success-title">Download Complete!</div>
                  <div class="nrc-success-sub">${fn} • <span>${task.size || '-- MB'}</span></div>
                </div>
              </div>
              <div class="nrc-success-actions">
                <a href="${API}/file/${task_id}${tToken}" download class="nrc-btn primary" style="text-decoration:none;">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg> Open File
                </a>
                <button class="nrc-btn" onclick="openFolder()">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg> Open Folder
                </button>
                <button class="nrc-btn" onclick="shareOrSaveToPhotos('${API}/file/${task_id}${tToken}', '${fn}')" title="Share">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg> Share
                </button>
                <button class="nrc-btn" style="padding: 10px;">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="1"/><circle cx="12" cy="5" r="1"/><circle cx="12" cy="19" r="1"/></svg>
                </button>
              </div>
            `;
          }
        }, 600);
        addToHistory({
          url,
          platform: detectPlatform(url),
          title: task.filename || 'Video',
          quality: mode === 'audio' ? 'MP3 Audio' : mode === 'image' ? 'Image' : quality + 'p',
          emoji: mode === 'audio' ? '🎵' : mode === 'image' ? '📷' : '📺',
          date: new Date().toISOString(),
        });
        showToast('✅ Download complete! Click Download or Save to Photos below.', 'success');
        updateQueueItem(task_id, 100, 'done');

      } else if (task.status === 'error') {
        evtSrc.close();
        if (progWrap) progWrap.classList.remove('visible');
        btn.disabled = false;
        btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="8 17 12 21 16 17"/><line x1="12" y1="21" x2="12" y2="9"/><path d="M20.88 18.09A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.29"/></svg> Retry`;
        const errMsg = task.error || 'Unknown error';
        showToast('Error: ' + errMsg, 'error');
        const card = document.getElementById(cardId);
        if (card) {
          const el = document.createElement('div');
          el.className = 'inline-error';
          el.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg> ${escapeHtml(errMsg)}`;
          card.appendChild(el);
        }
      }
    };

    evtSrc.onerror = () => {
      evtSrc.close();
      // Server might have finished or connection lost
      setTimeout(() => {
        if (btn.disabled) {
          if (progWrap) progWrap.classList.remove('visible');
          btn.disabled = false;
          btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="8 17 12 21 16 17"/><line x1="12" y1="21" x2="12" y2="9"/><path d="M20.88 18.09A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.29"/></svg> Retry`;
          showToast('Connection lost. Please retry.', 'error');
        }
      }, 3000);
    };

  } catch (err) {
    if (progWrap) progWrap.classList.remove('visible');
    btn.disabled = false;
    btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="8 17 12 21 16 17"/><line x1="12" y1="21" x2="12" y2="9"/><path d="M20.88 18.09A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.29"/></svg> Retry`;
    showToast('Error: ' + err.message, 'error');
  }
}

// ============================================================
// OPEN FOLDER
// ============================================================
async function openFolder() {
  try {
    const res = await fetch(`${API}/open-folder`, { method: 'POST', headers: authHeaders() });
    const data = await readApiJson(res);
    if (!res.ok || data.error) throw new Error(data.error || `HTTP ${res.status}`);
    showToast('📂 Download folder opened', 'success');
  } catch {
    showToast('Could not open folder. Navigate to Downloads/NexLoad/ manually.', 'info');
  }
}

// ============================================================
// SAVE TO PHOTOS / MOBILE GALLERY HELPER (Web Share API)
// ============================================================
async function shareOrSaveToPhotos(fileUrl, filename) {
  try {
    showToast('⏳ Preparing file for Photos / Gallery...', 'info');
    const res = await fetch(fileUrl);
    const blob = await res.blob();
    const file = new File([blob], filename, { type: blob.type || 'video/mp4' });
    if (navigator.canShare && navigator.canShare({ files: [file] })) {
      await navigator.share({
        files: [file],
        title: filename,
        text: 'Save to Photos / Gallery'
      });
      showToast('✅ Saved via Device Share!', 'success');
    } else {
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = filename;
      a.click();
      showToast('💡 File downloaded! On iPhone: Open Files app -> Share -> Save Video.', 'info');
    }
  } catch (err) {
    if (err.name !== 'AbortError') {
      showToast('❌ Could not save: ' + err.message, 'error');
    }
  }
}

// ============================================================
// PROGRESS HELPER
// ============================================================
function setProgress(fill, label, pct, value, text) {
  if (fill) fill.style.width = value + '%';
  if (label) label.textContent = text;
  if (pct) pct.textContent = value + '%';
}

// ============================================================
// DETECT PLATFORM FROM URL
// ============================================================
function detectPlatform(url) {
  const value = String(url || '').toLowerCase();
  if (value.includes('youtube') || value.includes('youtu.be')) return 'youtube';
  if (value.includes('tiktok')) return 'tiktok';
  if (value.includes('facebook') || value.includes('fb.watch')) return 'facebook';
  if (value.includes('instagram')) return 'instagram';
  if (value.includes('pinterest')) return 'pinterest';
  if (value.includes('pexels')) return 'pexels';
  return 'universal';
}

// ============================================================
// SKELETON LOADER
// ============================================================
function buildSkeleton() {
  return `
    <div class="skeleton-card">
      <div style="display:flex;gap:16px;margin-bottom:18px">
        <div class="skeleton-thumb"></div>
        <div style="flex:1;display:flex;flex-direction:column;gap:10px;padding-top:4px">
          <div class="skeleton-row w-80"></div>
          <div class="skeleton-row w-60"></div>
          <div class="skeleton-row w-40"></div>
          <div class="skeleton-row w-40" style="width:50%"></div>
        </div>
      </div>
      <div class="skeleton-row" style="height:52px;border-radius:12px"></div>
    </div>`;
}

// ============================================================
// HISTORY
// ============================================================
function addToHistory(item) {
  state.history.unshift(item);
  if (state.history.length > 50) state.history = state.history.slice(0, 50);
  localStorage.setItem('nexload_history', JSON.stringify(state.history));
  renderHistory();
  updateHistoryCount();
}

function favoriteKey(item) {
  return item?.url || `${item?.title || ''}|${item?.date || ''}`;
}

function isFavorite(item) {
  const key = favoriteKey(item);
  return state.favorites.some(item => favoriteKey(item) === key);
}

function toggleFavorite(historyIndex) {
  const item = state.history[historyIndex];
  if (!item) return;
  const key = favoriteKey(item);
  if (isFavorite(item)) {
    state.favorites = state.favorites.filter(saved => favoriteKey(saved) !== key);
    showToast('Removed from Favorites', 'info');
  } else {
    state.favorites.unshift({ ...item });
    showToast('⭐ Added to Favorites', 'success');
  }
  localStorage.setItem('nexload_favorites', JSON.stringify(state.favorites));
  renderHistory();
  renderFavorites();
}

function renderFavorites() {
  const list = document.getElementById('favoritesList');
  const count = document.getElementById('favoritesCount');
  if (count) count.textContent = state.favorites.length;
  if (!list) return;
  if (!state.favorites.length) {
    list.innerHTML = `<div class="empty-state"><div class="empty-icon">⭐</div><p>No favorites yet. Star a download from Recent Downloads.</p><button class="empty-action" onclick="navigateTo('home')">Browse downloads</button></div>`;
    return;
  }
  list.innerHTML = state.favorites.map((item, index) => `<div class="recent-item favorite-item">
    <div class="recent-item-icon" style="background:${platformColors[item.platform] || '#8b5cf6'}18;border:1px solid ${platformColors[item.platform] || '#8b5cf6'}33;font-size:1.2rem">${item.emoji || '🎬'}</div>
    <div class="recent-item-info"><div class="recent-item-title">${escapeHtml(item.title || 'Saved download')}</div><div class="recent-item-meta">${escapeHtml(item.platform || 'Universal')} • ${escapeHtml(item.quality || 'Best')} • ${formatDate(item.date)}</div></div>
    <button class="recent-favorite active" onclick="removeFavorite(${index})" aria-label="Remove from favorites">★</button>
  </div>`).join('');
}

function removeFavorite(index) {
  state.favorites.splice(index, 1);
  localStorage.setItem('nexload_favorites', JSON.stringify(state.favorites));
  renderFavorites();
  renderHistory();
  showToast('Removed from Favorites', 'info');
}

function renderHistory() {
  const list = document.getElementById('recentList');
  const drawerList = document.getElementById('drawerHistoryList');
  const totalDl = document.getElementById('totalDlCount');
  if (totalDl) totalDl.textContent = state.history.length;

  if (state.history.length === 0) {
    const emp = `<div class="empty-state" id="emptyHistory"><div class="empty-icon"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></div><p>No downloads yet.</p></div>`;
    if (list) list.innerHTML = emp;
    if (drawerList) drawerList.innerHTML = '<div class="empty-state">No downloads yet.</div>';
    return;
  }

  const html = state.history.slice(0, 10).map((item, index) => `
    <div class="recent-item">
      <div class="recent-item-icon" style="background:${platformColors[item.platform] || '#a855f7'}22;border:1px solid ${platformColors[item.platform] || '#a855f7'}33;font-size:1.2rem">${item.emoji}</div>
      <div class="recent-item-info">
        <div class="recent-item-title">${escapeHtml(item.title)}</div>
        <div class="recent-item-meta">${item.platform.charAt(0).toUpperCase() + item.platform.slice(1)} • ${item.quality} • ${formatDate(item.date)}</div>
      </div>
      <button class="recent-favorite${isFavorite(item) ? ' active' : ''}" onclick="toggleFavorite(${index})" aria-label="${isFavorite(item) ? 'Remove from favorites' : 'Add to favorites'}">${isFavorite(item) ? '★' : '☆'}</button>
      <div class="recent-item-size">✅</div>
    </div>`).join('');

  if (list) list.innerHTML = html;
  if (drawerList) drawerList.innerHTML = html;
}

function updateHistoryCount() {
  const el = document.getElementById('historyCount');
  if (el) el.textContent = state.history.length;
}

function formatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

document.getElementById('clearHistoryBtn')?.addEventListener('click', () => {
  state.history = [];
  localStorage.removeItem('nexload_history');
  renderHistory();
  updateHistoryCount();
  showToast('History cleared', 'info');
});

// ============================================================
// HISTORY DRAWER
// ============================================================
function toggleHistory() {
  const drawer = document.getElementById('historyDrawer');
  if (!drawer) return;
  const open = !drawer.classList.contains('open');
  drawer.classList.toggle('open', open);
  drawer.setAttribute('aria-hidden', String(!open));
  if (open) drawer.querySelector('.drawer-close')?.focus();
}
document.getElementById('historyBtn')?.addEventListener('click', toggleHistory);
document.addEventListener('keydown', event => {
  if (event.key !== 'Escape') return;
  const drawer = document.getElementById('historyDrawer');
  if (drawer?.classList.contains('open')) toggleHistory();
  const queue = document.getElementById('queuePanel');
  if (queue?.classList.contains('open')) toggleQueuePanel();
});

// ============================================================
// SETTINGS
// ============================================================
function updateSliderVal(el) {
  const val = el.value;
  const display = document.getElementById('sliderVal');
  if (display) display.textContent = val;
  state.settings.concurrent = parseInt(val);
  saveSettings();
}

function setLanguage(lang) {
  state.language = lang;
  localStorage.setItem('nexload_lang', lang);
  document.querySelectorAll('.lang-btn').forEach(b => b.classList.toggle('active', b.id === 'lang-' + lang));
  showToast(lang === 'kh' ? 'ប្ដូរភាសាជោគជ័យ 🇰🇭' : 'Language set to English 🇬🇧', 'success');
  setServerStatus(state.serverOnline);
  applyTranslations();
}

function saveSettings() {
  const el = id => document.getElementById(id);
  if (el('subtitleToggle')) state.settings.subtitles = el('subtitleToggle').checked;
  if (el('subLangSelect'))  state.settings.subLang   = el('subLangSelect').value;
  if (el('concurrentSlider')) state.settings.concurrent = parseInt(el('concurrentSlider').value);
  if (el('autoPasteToggle'))  state.settings.autoPaste  = el('autoPasteToggle').checked;
  if (el('notifToggle'))      state.settings.notifications = el('notifToggle').checked;
  localStorage.setItem('nexload_settings', JSON.stringify(state.settings));
}

document.getElementById('autoPasteToggle')?.addEventListener('change', function () {
  state.settings.autoPaste = this.checked; saveSettings();
});
document.getElementById('notifToggle')?.addEventListener('change', function () {
  state.settings.notifications = this.checked; saveSettings();
});

async function autoPasteInto(input) {
  if (!state.settings.autoPaste || input.value.trim() || input.dataset.autoPasteUsed === 'true') return;
  input.dataset.autoPasteUsed = 'true';
  try {
    const text = (await navigator.clipboard.readText()).trim();
    if (isValidUrl(text)) {
      input.value = text;
      input.dispatchEvent(new Event('input', { bubbles: true }));
      showToast('🔗 URL pasted from clipboard', 'info');
    }
  } catch { /* Clipboard permissions are optional; manual paste still works. */ }
}

document.querySelectorAll('.url-input').forEach(input => {
  input.addEventListener('focus', () => autoPasteInto(input));
  input.addEventListener('blur', () => { input.dataset.autoPasteUsed = 'false'; });
});

(function initSettings() {
  const s = state.settings;
  const se = id => document.getElementById(id);
  if (se('concurrentSlider')) se('concurrentSlider').value = s.concurrent;
  if (se('sliderVal')) se('sliderVal').textContent = s.concurrent;
  if (se('autoPasteToggle')) se('autoPasteToggle').checked = s.autoPaste;
  if (se('notifToggle')) se('notifToggle').checked = s.notifications;
  if (se('subtitleToggle')) se('subtitleToggle').checked = s.subtitles || false;
  if (se('subLangSelect')) se('subLangSelect').value = s.subLang || 'en';
  // Speed buttons
  document.querySelectorAll('.speed-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.speed === (s.speedLimit || ''))
  );
  // Language
  document.querySelectorAll('.lang-btn').forEach(b =>
    b.classList.toggle('active', b.id === 'lang-' + state.language)
  );
  // Theme
  if (s.theme === 'light') applyTheme('light', true);
  // Auto-detect bar
  if (s.autoDetectBar) toggleAutoDetectBar(true, true);
  // Download folder
  refreshFolderDisplay();
  applyTranslations(); // apply initial language
})();

// ============================================================
// THEME
// ============================================================
function toggleTheme() {
  const newTheme = document.body.classList.contains('light-theme') ? 'dark' : 'light';
  applyTheme(newTheme);
}

function applyTheme(theme, silent = false) {
  const isLight = theme === 'light';
  document.body.classList.toggle('light-theme', isLight);
  const icon = document.getElementById('themeIcon');
  if (icon) icon.textContent = isLight ? '🌙' : '☀️';
  // Update theme buttons in settings
  document.getElementById('theme-dark')?.classList.toggle('active', !isLight);
  document.getElementById('theme-light')?.classList.toggle('active', isLight);
  state.settings.theme = theme;
  localStorage.setItem('nexload_settings', JSON.stringify(state.settings));
  if (!silent) showToast(isLight ? '☀️ Light theme applied' : '🌙 Dark theme applied', 'success');
}

// ============================================================
// QUEUE PANEL
// ============================================================
function toggleQueuePanel() {
  const panel = document.getElementById('queuePanel');
  if (!panel) return;
  state.queuePanelOpen = !state.queuePanelOpen;
  panel.classList.toggle('open', state.queuePanelOpen);
}

function addToQueue(taskId, title, url) {
  state.queue.push({ taskId, title, url, progress: 0, status: 'downloading' });
  renderQueue();
}

function updateQueueItem(taskId, progress, status) {
  const item = state.queue.find(q => q.taskId === taskId);
  if (item) {
    item.progress = progress;
    item.status = status;
    if (status === 'done' || status === 'error') {
      setTimeout(() => {
        state.queue = state.queue.filter(q => q.taskId !== taskId);
        renderQueue();
      }, 3000);
    }
  }
  renderQueue();
}

function renderQueue() {
  const list = document.getElementById('queueList');
  const badge = document.getElementById('queueBadge');
  const navBadge = document.getElementById('navQueueBadge');
  const active = state.queue.filter(q => q.status === 'downloading').length;
  if (badge) badge.textContent = state.queue.length;
  if (navBadge) navBadge.textContent = active;

  if (!list) return;
  if (state.queue.length === 0) {
    list.innerHTML = '<div class="queue-empty">No active downloads</div>';
    return;
  }
  list.innerHTML = state.queue.map(q => `
    <div class="queue-item">
      <div class="queue-item-title">${escapeHtml(q.title || q.url)}</div>
      <div class="queue-item-status">
        <span>${q.status === 'done' ? '✅' : q.status === 'error' ? '❌' : '⏳'}</span>
        <div class="queue-item-progress">
          <div class="queue-item-progress-fill" style="width:${q.progress}%"></div>
        </div>
        <span>${q.progress}%</span>
      </div>
    </div>
  `).join('');
}

// ============================================================
// AUTO-DETECT PLATFORM BAR
// ============================================================
function toggleAutoDetectBar(show, silent = false) {
  const bar = document.getElementById('autoDetectBar');
  if (bar) bar.style.display = show ? 'flex' : 'none';
  state.settings.autoDetectBar = show;
  localStorage.setItem('nexload_settings', JSON.stringify(state.settings));
  const toggle = document.getElementById('autoDetectToggle');
  if (toggle) toggle.checked = show;
}

function autoDetectPlatform(url) {
  if (!url || !isValidUrl(url)) return;
  const platform = detectPlatform(url);
  const goBtn = document.getElementById('autoDetectGo');
  if (goBtn) goBtn.textContent = `Go to ${platform.charAt(0).toUpperCase() + platform.slice(1)} ➜`;
}

function goAutoDetect() {
  const url = document.getElementById('autoDetectInput')?.value.trim();
  if (!url || !isValidUrl(url)) return;
  const platform = detectPlatform(url);
  navigateTo(platform === 'universal' ? 'universal' : platform);
  // Paste URL into platform input
  const map = platformMap[platform];
  if (map) {
    const inp = document.getElementById(map.urlId);
    if (inp) { inp.value = url; inp.dispatchEvent(new Event('input')); }
  }
  document.getElementById('autoDetectInput').value = '';
  const goBtn = document.getElementById('autoDetectGo');
  if (goBtn) goBtn.textContent = 'Go ➜';
  showToast(`🔗 URL detected as ${platform} — switched tab!`, 'success');
}

function openTool(mode) {
  state.preferredMode = mode === 'audio' || mode === 'image' ? mode : null;
  navigateTo('universal');
  const input = document.getElementById('uni-url');
  if (input) {
    input.focus();
    showToast(mode === 'audio' ? '🎵 MP3 mode ready — paste a video URL.' : '🖼️ Image mode ready — paste a media URL.', 'info');
  }
}

function showUpgradeNotice() {
  showToast('👑 Pro plans are managed by the NexLoad administrator. Contact support to upgrade.', 'info');
}

function openNetworkSettings() {
  navigateTo('settings');
  const serverCard = document.getElementById('networkSettingsCard');
  if (serverCard) {
    serverCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
    serverCard.classList.add('settings-card-highlight');
    setTimeout(() => serverCard.classList.remove('settings-card-highlight'), 1400);
  }
  showToast('🌐 Network controls are available in Settings.', 'info');
}

function showAboutModal() {
  const existing = document.getElementById('aboutModal');
  if (existing) existing.remove();
  const modal = document.createElement('div');
  modal.id = 'aboutModal';
  modal.className = 'about-modal';
  modal.innerHTML = `<div class="about-modal-card" role="dialog" aria-modal="true" aria-labelledby="aboutTitle">
    <button class="about-close" onclick="document.getElementById('aboutModal')?.remove()" aria-label="Close">×</button>
    <div class="about-mark">V</div>
    <div class="about-kicker">NEXLOAD STUDIO</div>
    <h2 id="aboutTitle">Vordex <span>v2.0</span></h2>
    <p>Fast, private media downloads with local processing and a clean command console.</p>
    <div class="about-meta"><span>⚡ 8K-ready</span><span>🔒 Local-first</span><span>🌐 1000+ sites</span></div>
    <button class="about-primary" onclick="document.getElementById('aboutModal')?.remove()">Done</button>
  </div>`;
  modal.addEventListener('click', event => { if (event.target === modal) modal.remove(); });
  document.body.appendChild(modal);
}

// ============================================================
// STATS PAGE
// ============================================================
async function loadStats() {
  if (!state.serverOnline) return;
  try {
    const res = await fetch(`${API}/stats`, { headers: authHeaders() });
    const data = await readApiJson(res);
    renderStats(data);
  } catch { /* ignore */ }
}

function renderStats(data) {
  const today = new Date().toISOString().slice(0,10);
  const todayCount = (data.by_day || {})[today] || 0;
  const byPlatform = data.by_platform || {};
  const topPlatform = Object.entries(byPlatform).sort((a,b) => b[1]-a[1])[0];
  const mb = ((data.total_bytes || 0) / 1024 / 1024).toFixed(1);

  const si = id => document.getElementById(id);
  if (si('stat-total')) si('stat-total').textContent = data.total_downloads || 0;
  if (si('stat-bytes')) si('stat-bytes').textContent = mb + ' MB';
  if (si('stat-today')) si('stat-today').textContent = todayCount;
  if (si('stat-top-platform')) si('stat-top-platform').textContent = topPlatform ? topPlatform[0] : '—';

  // Platform bars
  const barContainer = document.getElementById('platformStatsBar');
  if (barContainer) {
    const total = Object.values(byPlatform).reduce((a,b) => a+b, 0) || 1;
    barContainer.innerHTML = Object.entries(byPlatform)
      .sort((a,b) => b[1]-a[1])
      .map(([p,c]) => `
        <div class="platform-bar-row">
          <div class="platform-bar-label">${p}</div>
          <div class="platform-bar-track">
            <div class="platform-bar-fill" style="width:${Math.round(c/total*100)}%"></div>
          </div>
          <div class="platform-bar-count">${c}</div>
        </div>`).join('');
  }

  // Weekly chart
  drawWeekChart(data.by_day || {});

  // License info
  updateLicenseInfoBox(state.licenseInfo);
}

function drawWeekChart(byDay) {
  const canvas = document.getElementById('weekChart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const days = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date(); d.setDate(d.getDate() - i);
    days.push(d.toISOString().slice(0,10));
  }
  const values = days.map(d => byDay[d] || 0);
  const max = Math.max(...values, 1);

  canvas.width = canvas.offsetWidth;
  const W = canvas.width, H = canvas.height;
  ctx.clearRect(0, 0, W, H);

  const barW = Math.floor(W / 7) - 8;
  const grad = ctx.createLinearGradient(0, 0, W, 0);
  grad.addColorStop(0, '#00f5ff');
  grad.addColorStop(1, '#a855f7');

  values.forEach((val, i) => {
    const x = i * (Math.floor(W/7)) + 4;
    const barH = Math.max(4, (val / max) * (H - 30));
    const y = H - barH - 20;
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.roundRect(x, y, barW, barH, 4);
    ctx.fill();
    // Label
    const isLight = document.body.classList.contains('light-theme');
    ctx.fillStyle = isLight ? '#64748b' : 'rgba(255,255,255,0.4)';
    ctx.font = '10px Outfit, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(days[i].slice(5), x + barW/2, H - 4);
    if (val > 0) {
      ctx.fillStyle = isLight ? '#334155' : '#fff';
      ctx.fillText(val, x + barW/2, y - 4);
    }
  });
}

// ============================================================
// CUSTOM FOLDER
// ============================================================
async function setCustomFolder() {
  const input = document.getElementById('folderInput');
  const folder = input?.value.trim();
  if (!folder) { showToast('Please enter a folder path', 'error'); return; }
  if (!state.serverOnline) { showToast('Server offline', 'error'); return; }
  try {
    const res = await fetch(`${API}/set-folder`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ folder }),
    });
    const data = await readApiJson(res);
    if (data.ok) {
      refreshFolderDisplay(data.folder);
      showToast('📂 Download folder set: ' + data.folder, 'success');
    } else {
      showToast('Error: ' + (data.error || 'Unknown'), 'error');
    }
  } catch { showToast('Server error', 'error'); }
}

async function refreshFolderDisplay(folder) {
  const el = document.getElementById('download-dir-display');
  if (!folder && state.serverOnline) {
    try {
      const res = await fetch(`${API}/get-folder`, { headers: authHeaders() });
      const data = await readApiJson(res);
      folder = data.folder;
    } catch { folder = '~/Downloads/NexLoad'; }
  }
  if (el) el.textContent = folder || '~/Downloads/NexLoad';
}

// ============================================================
// SPEED LIMITER
// ============================================================
function setSpeed(btn) {
  document.querySelectorAll('.speed-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  state.settings.speedLimit = btn.dataset.speed || '';
  saveSettings();
  const label = btn.dataset.speed || 'Unlimited';
  showToast(`⏱️ Speed limit set: ${label}`, 'success');
}

// ============================================================
// TOAST
// ============================================================
function showToast(message, type = 'info') {
  if (state.settings.notifications === false && type !== 'error') return;
  const icons = {
    success: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`,
    error: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
    info: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
  };
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span class="toast-icon">${icons[type] || icons.info}</span><span>${message}</span>`;
  document.getElementById('toastContainer').appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(16px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4500);
}

// ============================================================
// PER-PLATFORM BATCH MODE
// ============================================================

async function runWithConcurrency(items, limit, worker) {
  const results = new Array(items.length);
  let nextIndex = 0;
  const runWorker = async () => {
    while (nextIndex < items.length) {
      const index = nextIndex++;
      try {
        results[index] = await worker(items[index], index);
      } catch (error) {
        results[index] = { status: 'rejected', reason: error };
      }
    }
  };
  const workerCount = Math.max(1, Math.min(Number(limit) || 1, items.length));
  await Promise.all(Array.from({ length: workerCount }, runWorker));
  return results;
}

// Mapping for batch prefixes to full names
const batchPrefixMap = {
  yt: 'youtube', tt: 'tiktok', fb: 'facebook', ig: 'instagram', pi: 'pinterest', uni: 'universal'
};

// Toggle batch expand/collapse
function toggleBatch(prefix) {
  const expand = document.getElementById(prefix + '-batch-expand');
  if (!expand) return;
  const isOpen = expand.style.display !== 'none';
  expand.style.display = isOpen ? 'none' : 'block';
}

// Add another URL input
function addBatchUrl(prefix, placeholder) {
  const list = document.getElementById(prefix + '-batch-list');
  if (!list) return;
  const count = list.querySelectorAll('.batch-url-item').length + 1;
  const item = document.createElement('div');
  item.className = 'batch-url-item';
  item.innerHTML = `
    <span class="batch-url-num">#${count}</span>
    <input type="text" class="url-input batch-url-input" placeholder="${placeholder}" />
    <button class="batch-remove-btn" onclick="removeBatchUrl(this)" title="Remove">&times;</button>`;
  list.appendChild(item);
  item.querySelector('input').focus();
  renumberBatch(prefix);
}

// Remove a URL input
function removeBatchUrl(btn) {
  const item = btn.closest('.batch-url-item');
  const list = item?.closest('.batch-url-list');
  if (!list) return;
  if (list.querySelectorAll('.batch-url-item').length <= 1) return;
  item.remove();
  const prefix = list.id.replace('-batch-list', '');
  renumberBatch(prefix);
}

function renumberBatch(prefix) {
  const list = document.getElementById(prefix + '-batch-list');
  if (!list) return;
  list.querySelectorAll('.batch-url-item').forEach((item, i) => {
    const num = item.querySelector('.batch-url-num');
    if (num) num.textContent = '#' + (i + 1);
  });
}

// Clear all inputs
function clearPlatformBatch(prefix) {
  const list = document.getElementById(prefix + '-batch-list');
  if (!list) return;
  list.innerHTML = `
    <div class="batch-url-item">
      <span class="batch-url-num">#1</span>
      <input type="text" class="url-input batch-url-input" placeholder="Paste URL here..." />
      <button class="batch-remove-btn" onclick="removeBatchUrl(this)" title="Remove">&times;</button>
    </div>`;
  const queue = document.getElementById(prefix + '-batch-queue');
  if (queue) queue.innerHTML = '';
}

// Start batch download for a specific platform
async function startPlatformBatch(prefix) {
  if (!state.serverOnline) {
    showToast('Server offline \u2014 start server.py first', 'error');
    return;
  }
  const list = document.getElementById(prefix + '-batch-list');
  if (!list) return;

  const inputs = list.querySelectorAll('.batch-url-input');
  const urls = [];
  let invalidCount = 0;

  inputs.forEach(inp => {
    const u = inp.value.trim();
    if (!u) return;
    if (!isValidUrl(u)) return;

    const fullPlatform = batchPrefixMap[prefix] || prefix;
    if (!validatePlatformUrl(fullPlatform, u)) {
      inp.style.borderColor = 'rgba(239,68,68,0.6)';
      inp.style.background = 'rgba(239,68,68,0.06)';
      invalidCount++;
      return;
    }
    inp.style.borderColor = '';
    inp.style.background = '';
    urls.push(u);
  });

  if (invalidCount > 0) {
    const pname = { yt: 'YouTube', tt: 'TikTok', fb: 'Facebook', ig: 'Instagram', pi: 'Pinterest', uni: 'any site' }[prefix] || prefix;
    showToast(invalidCount + ' URL(s) rejected \u2014 only ' + pname + ' links allowed', 'error');
  }
  if (urls.length === 0) {
    showToast('No valid URLs to download', 'error');
    return;
  }

  const queue = document.getElementById(prefix + '-batch-queue');
  queue.innerHTML = `
    <div class="batch-queue-header">
      <span>&#9889; Queue: ${urls.length} video${urls.length > 1 ? 's' : ''}</span>
      <span class="batch-summary" id="${prefix}-bsum">0 / ${urls.length} done</span>
    </div>`;

  let doneCount = 0;
  const updateSummary = () => {
    const s = document.getElementById(prefix + '-bsum');
    if (s) s.textContent = doneCount + ' / ' + urls.length + ' done';
  };

  urls.forEach((url, i) => {
    const progId = prefix + 'bp-' + i;
    const doneId = prefix + 'bd-' + i;
    const short = url.length > 55 ? url.slice(0, 52) + '...' : url;
    const item = document.createElement('div');
    item.className = 'batch-queue-item';
    item.innerHTML = `
      <div class="bq-header">
        <span class="bq-num">#${i + 1}</span>
        <span class="bq-url" title="${escapeHtml(url)}">${escapeHtml(short)}</span>
        <span class="bq-status" id="${prefix}bs-${i}">&#128336; Waiting</span>
      </div>
      <div class="progress-wrap" id="${progId}" style="margin-top:10px">
        <div class="progress-label">
          <span id="${progId}-label">Queued...</span>
          <span id="${progId}-pct" style="color:var(--grad-mid);font-weight:700">0%</span>
        </div>
        <div class="progress-track"><div class="progress-fill" id="${progId}-fill" style="width:0%"></div></div>
        <div class="progress-meta" id="${progId}-meta"></div>
      </div>
      <div class="download-done-row" id="${doneId}" style="display:none">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
          stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
        Done! <button class="open-folder-btn" onclick="openFolder()">&#128194; Folder</button>
      </div>`;
    queue.appendChild(item);
  });

  showToast('Starting ' + urls.length + ' downloads...', 'info');

  await runWithConcurrency(urls, state.settings.concurrent, async (url, i) => {
    const progId = prefix + 'bp-' + i;
    const doneId = prefix + 'bd-' + i;
    const statusEl = document.getElementById(prefix + 'bs-' + i);
    if (statusEl) statusEl.innerHTML = '&#9654;&#65039; Downloading';

    try {
      const res = await fetch(API + '/download', {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ url: url, quality: '1080', mode: 'video' }),
      });
      const data = await readApiJson(res);
      if (!res.ok || data.error) throw new Error(data.error || 'HTTP ' + res.status);

      await new Promise((resolve, reject) => {
        const tokenParam = data.task_token ? ('?token=' + encodeURIComponent(data.task_token)) : '';
        const es = new EventSource(API + '/progress/' + data.task_id + tokenParam);
        es.onmessage = ev => {
          try {
            const t = JSON.parse(ev.data);
            const pct = Math.round(t.progress || 0);
            const fill = document.getElementById(progId + '-fill');
            const label = document.getElementById(progId + '-label');
            const pctEl = document.getElementById(progId + '-pct');
            const meta = document.getElementById(progId + '-meta');
            if (fill) fill.style.width = pct + '%';
            if (pctEl) pctEl.textContent = pct + '%';
            if (label) label.textContent = t.status === 'done' ? 'Done!' : 'Downloading...';
            if (meta && t.speed) meta.textContent = t.speed + ' | ETA: ' + (t.eta || '--');
            if (t.status === 'done' || t.status === 'error') {
              es.close();
              t.status === 'done' ? resolve() : reject(new Error(t.error || 'Failed'));
            }
          } catch (e) { es.close(); resolve(); }
        };
        es.onerror = () => { es.close(); reject(new Error('Connection lost')); };
      });

      if (statusEl) statusEl.innerHTML = '&#9989;';
      const doneEl = document.getElementById(doneId);
      if (doneEl) doneEl.style.display = 'flex';
      doneCount++;
      updateSummary();
    } catch (err) {
      if (statusEl) statusEl.innerHTML = '&#10060; ' + err.message.slice(0, 30);
      doneCount++;
      updateSummary();
    }
  });

  showToast('Batch complete! ' + urls.length + ' files processed.', 'success');
}




// ============================================================
// INIT
// ============================================================
(function init() {
  renderHistory();
  renderFavorites();
  updateHistoryCount();
  checkServer();

  // Check cached license after a moment (server may need to start)
  setTimeout(async () => {
    await checkCachedLicense();
  }, 800);

  navigateTo('home');
  renderQueue();
  console.log('%cNexLoad v5.0 Commercial — Local Python Backend ✔', 'color:#a855f7;font-size:14px;font-weight:bold;');
})();


function goToKeyStep() {
  const s1 = document.getElementById('step1Google');
  const s2 = document.getElementById('step2Key');
  if (s1) s1.style.display = 'none';
  if (s2) s2.style.display = 'block';
  const badge = document.getElementById('verifiedEmailBadge');
  if (badge) badge.textContent = 'Direct Key Activation';
}

async function checkLocalServerLicense() {
  try {
    const res = await fetch(`${API}/auth/active-license`);
    const data = await readApiJson(res);
    if (data.has_active && data.key) {
      localStorage.setItem('nexload_license', data.key);
      if (data.email) localStorage.setItem('nexload_email', data.email);
      state.licenseKey = data.key;
      state.licenseEmail = data.email || null;
      state.licenseInfo = data.info;
      document.documentElement.classList.add('has-license');
      hideLicenseOverlay();
      updateLicenseInfoBox(data.info);
      return true;
    }
  } catch {}
  return false;
}
