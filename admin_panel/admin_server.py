import os, json, datetime, hmac, hashlib, uuid
from flask import Flask, render_template, request, jsonify, redirect, session
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("ADMIN_SESSION_SECRET") or os.environ.get("SECRET_KEY") or os.urandom(32)

# Configuration
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.abspath(os.path.join(BASE_DIR, '..'))
LICENSE_DB = os.path.join(PARENT_DIR, "licenses.json")
_secret_env = os.environ.get("SECRET_KEY", "NexLoad-Secret-2026-ChangeThis-To-Something-Unique")
SECRET_KEY = _secret_env.encode() if isinstance(_secret_env, str) else _secret_env

TIERS = {
    "trial":    {"days": 3,    "label": "Trial",    "daily_limit": 5,   "batch": False},
    "basic":    {"days": 30,   "label": "Basic",    "daily_limit": 50,  "batch": True},
    "pro":      {"days": 365,  "label": "Pro",      "daily_limit": 0,   "batch": True},
    "lifetime": {"days": 9999, "label": "Lifetime", "daily_limit": 0,   "batch": True},
}

def _load_db():
    if os.path.exists(LICENSE_DB):
        with open(LICENSE_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def _save_db(db):
    with open(LICENSE_DB, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

def _make_signature(key_body: str) -> str:
    sig = hmac.new(SECRET_KEY, key_body.encode(), hashlib.sha256).hexdigest()
    return sig[:16].upper()

def _password_ok(password: str) -> bool:
    if ADMIN_PASSWORD_HASH:
        return check_password_hash(ADMIN_PASSWORD_HASH, password or "")
    if ADMIN_PASSWORD:
        return hmac.compare_digest(ADMIN_PASSWORD, password or "")
    return False

# ─── Admin Web UI Routes ──────────────────────────────────────────────

@app.route('/')
def index():
    if not session.get('logged_in'): return render_template('login.html')
    return redirect('/dashboard')

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    if data.get('username') == ADMIN_USERNAME and _password_ok(data.get('password')):
        session['logged_in'] = True
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Incorrect credentials"}), 401

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect('/')

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'): return redirect('/')
    return render_template('dashboard.html', tiers=TIERS)

@app.route('/api/keys', methods=['GET'])
def get_keys():
    if not session.get('logged_in'): return jsonify({"error": "Unauthorized"}), 401
    db = _load_db()
    keys = list(db.values())
    keys.sort(key=lambda x: x.get('created', ''), reverse=True)
    return jsonify(keys)

@app.route('/api/generate', methods=['POST'])
def api_generate():
    if not session.get('logged_in'): return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    user_name = data.get('user', '').strip()
    tier = data.get('tier')
    hwid = data.get('hwid', '').strip() # Newly required field!
    
    if not user_name or tier not in TIERS or not hwid:
        return jsonify({"error": "Missing info. HWID is required!"}), 400

    tier_info = TIERS[tier]
    days = tier_info["days"]

    uid = uuid.uuid4().hex[:8].upper()
    key_body = f"{uid}-{tier.upper()}-{days}-{hwid}" # Hardware ID bound into key body
    sig = _make_signature(key_body)
    full_key = f"NEXLOAD-{uid}-{tier.upper()[:3]}-{sig[:6]}"

    now = datetime.datetime.now(datetime.timezone.utc)
    expire = now + datetime.timedelta(days=days)

    info = {
        "key":        full_key,
        "user":       user_name,
        "hwid":       hwid,
        "tier":       tier,
        "days":       days,
        "created":    now.isoformat(),
        "expires":    expire.isoformat(),
        "active":     True,
        "signature":  sig,
        "key_body":   key_body,
        "daily_limit": tier_info["daily_limit"],
        "batch":      tier_info["batch"],
    }

    db = _load_db()
    db[full_key] = info
    _save_db(db)
    return jsonify({"success": True, "key": info})

@app.route('/api/revoke', methods=['POST'])
def api_revoke():
    if not session.get('logged_in'): return jsonify({"error": "Unauthorized"}), 401
    key = request.json.get('key')
    db = _load_db()
    if key in db:
        db[key]["active"] = False
        _save_db(db)
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Not found"}), 404


# ─── API for External Client App (server.py) ──────────────────────────

@app.route('/api/client/validate', methods=['POST'])
def client_validate():
    data = request.get_json() or {}
    key = data.get('key', '').strip()
    req_hwid = data.get('hwid', '').strip()

    if not key or not req_hwid:
        return jsonify({"valid": False, "reason": "Missing Key or HWID"})

    db = _load_db()
    if key not in db:
        return jsonify({'valid': False, 'reason': 'Key not found in system'})
    
    rec = db[key]
    
    # Check if Active
    if not rec.get('active'):
        return jsonify({'valid': False, 'reason': 'Key has been revoked or banned'})

    # Check HWID Lock
    if rec.get('hwid') != req_hwid:
        return jsonify({'valid': False, 'reason': 'Device Mismatch! This key belongs to another PC.'})

    # Verify Cryptographic Signature
    expected_sig = _make_signature(rec['key_body'])
    if rec.get('signature') != expected_sig:
        return jsonify({'valid': False, 'reason': 'Key Signature Invalid (Tampered)'})

    # Check Expiry Dates
    expire_dt = datetime.datetime.fromisoformat(rec['expires'])
    now = datetime.datetime.now(datetime.timezone.utc)
    days_left = (expire_dt - now).days
    
    if days_left < 0:
        return jsonify({'valid': False, 'reason': f'Key expired {-days_left} days ago'})

    # If everything is golden:
    return jsonify({
        'valid':       True,
        'reason':      'OK',
        'key':         key,
        'tier':        rec['tier'],
        'tier_label':  TIERS.get(rec['tier'], {}).get('label', rec['tier']),
        'user':        rec.get('user', 'Unknown'),
        'expires':     rec['expires'],
        'days_left':   days_left,
        'daily_limit': rec.get('daily_limit', 0),
        'batch':       rec.get('batch', True),
    })

if __name__ == '__main__':
    if not ADMIN_PASSWORD and not ADMIN_PASSWORD_HASH:
        print("Admin login disabled: set ADMIN_PASSWORD or ADMIN_PASSWORD_HASH.")
    host = os.environ.get("ADMIN_HOST", "127.0.0.1")
    port = int(os.environ.get("ADMIN_PORT", 5050))
    debug = os.environ.get("ADMIN_DEBUG", "").lower() in ("1", "true", "yes")
    app.run(host=host, port=port, debug=debug)
