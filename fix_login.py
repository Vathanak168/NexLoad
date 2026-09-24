import os
import re

# 1. Fix NexLoad.pyw
with open('NexLoad.pyw', 'r', encoding='utf-8') as f:
    code = f.read()
code = code.replace("SERVER_URL = 'http://localhost:5000'", "SERVER_URL = 'http://127.0.0.1:5000'")
with open('NexLoad.pyw', 'w', encoding='utf-8') as f:
    f.write(code)

# 2. Fix index.html
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()
html = html.replace('<div class="login-overlay" id="loginOverlay">', '<div class="login-overlay hidden" id="loginOverlay">')
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

# 3. Fix app.js
with open('app.js', 'r', encoding='utf-8') as f:
    app_js = f.read()

new_checkCachedLicense = """async function checkCachedLicense() {
  const key = state.licenseKey;
  const email = state.licenseEmail;
  if (!key && !email) {
    const overlay = document.getElementById('loginOverlay');
    if (overlay) {
      overlay.classList.remove('hidden');
      overlay.style.opacity = '1';
    }
    return false;
  }
  // Wait for server to be online
  await checkServer();
  if (!state.serverOnline) {
    hideLicenseOverlay();
    showToast('⚠️ Running in offline mode. Connect server to validate license.', 'info');
    return true;
  }

  if (!key) return false;
  try {
    const res = await fetch(`${API}/auth/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key, email }),
    });
    const data = await readApiJson(res);
    if (data.valid) {
      state.licenseInfo = data;
      hideLicenseOverlay();
      updateLicenseInfoBox(data);
      return true;
    }
    
    localStorage.removeItem('nexload_license');
    localStorage.removeItem('nexload_email');
    state.licenseKey = null;
    state.licenseEmail = null;
    const errEl = document.getElementById('loginError1') || document.getElementById('loginError');
    if (errEl) errEl.textContent = '❌ ' + (data.reason || 'License verification failed');
    
    const overlay = document.getElementById('loginOverlay');
    if (overlay) {
      overlay.classList.remove('hidden');
      overlay.style.opacity = '1';
    }
    
    return false;
  } catch {
    hideLicenseOverlay();
    return false;
  }
}"""

app_js = re.sub(r'async function checkCachedLicense\(\) \{.*?\n\}', new_checkCachedLicense, app_js, flags=re.DOTALL)

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(app_js)

print("Patch applied successfully.")
