"""
NexLoad License Manager
=======================
CLI tool to generate, validate, and revoke license keys.
Run this on YOUR machine (not distributed to customers).

Usage:
  python license_manager.py generate --user "John Doe" --tier pro --days 365
  python license_manager.py generate --user "Trial User" --tier trial
  python license_manager.py list
  python license_manager.py revoke NEXLOAD-XXXX-XXXX-XXXX-XXXX
  python license_manager.py info NEXLOAD-XXXX-XXXX-XXXX-XXXX
"""

import hmac, hashlib, json, os, argparse, uuid, datetime, sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

import config
import db

# ── SECRET KEY — CHANGE THIS TO SOMETHING ONLY YOU KNOW ──────────
SECRET_KEY = getattr(config, "SECRET_KEY", b"NexLoad-Secret-2026-ChangeThis-To-Something-Unique")
if isinstance(SECRET_KEY, str):
    SECRET_KEY = SECRET_KEY.encode()

LICENSE_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "licenses.json")

TIERS = {
    "trial":    {"days": 3,    "label": "Trial",    "daily_limit": 5,   "batch": False},
    "basic":    {"days": 30,   "label": "Basic",    "daily_limit": 50,  "batch": True},
    "pro":      {"days": 365,  "label": "Pro",      "daily_limit": 0,   "batch": True},
    "lifetime": {"days": 9999, "label": "Lifetime", "daily_limit": 0,   "batch": True},
}


def _load_db():
    try:
        return db.load_all_licenses()
    except Exception:
        if os.path.exists(LICENSE_DB):
            with open(LICENSE_DB, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}


def _save_db(data):
    try:
        for k, v in data.items():
            db.save_license(v)
    except Exception as e:
        print(f"⚠️ [SQL DB] Save note: {e}")
    # Also backup to JSON for backward compatibility
    try:
        with open(LICENSE_DB, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def _make_signature(key_body: str) -> str:
    """Create HMAC-SHA256 signature for a key body string."""
    sig = hmac.new(SECRET_KEY, key_body.encode(), hashlib.sha256).hexdigest()
    return sig[:16].upper()


def generate_key(user_name: str, tier: str, days: int = None) -> dict:
    """
    Generate a new license key.
    Returns dict with key info.
    """
    if tier not in TIERS:
        raise ValueError(f"Unknown tier: {tier}. Choose from {list(TIERS)}")

    tier_info = TIERS[tier]
    days = days or tier_info["days"]

    # Key body: unique ID + tier + days
    uid = uuid.uuid4().hex[:8].upper()
    key_body = f"{uid}-{tier.upper()}-{days}"
    sig = _make_signature(key_body)
    full_key = f"NEXLOAD-{uid}-{tier.upper()[:3]}-{days}-{sig[:4]}"

    now = datetime.datetime.now(datetime.timezone.utc)
    expire = now + datetime.timedelta(days=days)

    info = {
        "key":        full_key,
        "user":       user_name,
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
    return info


def validate_key(full_key: str) -> dict:
    """
    Validate a license key.
    Returns: { valid, reason, tier, user, expires, days_left }
    """
    db = _load_db()

    if full_key not in db:
        return {"valid": False, "reason": "Key not found"}

    record = db[full_key]

    if not record.get("active"):
        return {"valid": False, "reason": "Key has been revoked"}

    # Verify signature
    expected_sig = _make_signature(record["key_body"])
    if record["signature"] != expected_sig:
        return {"valid": False, "reason": "Key signature invalid (tampered)"}

    # Check expiry
    expire_dt = datetime.datetime.fromisoformat(record["expires"])
    if expire_dt.tzinfo is None:
        expire_dt = expire_dt.replace(tzinfo=datetime.timezone.utc)
    now = datetime.datetime.now(datetime.timezone.utc)
    days_left = (expire_dt - now).days

    if days_left < 0:
        return {"valid": False, "reason": f"Key expired {-days_left} days ago"}

    return {
        "valid":       True,
        "reason":      "OK",
        "key":         full_key,
        "tier":        record["tier"],
        "tier_label":  TIERS.get(record["tier"], {}).get("label", record["tier"]),
        "user":        record.get("user", "Unknown"),
        "expires":     record["expires"],
        "days_left":   days_left,
        "daily_limit": record.get("daily_limit", 0),
        "batch":       record.get("batch", True),
    }


def revoke_key(full_key: str) -> bool:
    db = _load_db()
    if full_key in db:
        db[full_key]["active"] = False
        _save_db(db)
        return True
    return False


def list_keys():
    db = _load_db()
    if not db:
        print("No licenses generated yet.")
        return
    now = datetime.datetime.now(datetime.timezone.utc)
    print(f"\n{'KEY':<45} {'USER':<20} {'TIER':<10} {'EXPIRES':<12} {'STATUS'}")
    print("─" * 110)
    for key, rec in db.items():
        expire = datetime.datetime.fromisoformat(rec["expires"])
        if expire.tzinfo is None:
            expire = expire.replace(tzinfo=datetime.timezone.utc)
        days_left = (expire - now).days
        status = "REVOKED" if not rec["active"] else ("EXPIRED" if days_left < 0 else f"{days_left}d left")
        print(f"{key:<45} {rec.get('user','?'):<20} {rec['tier']:<10} {expire.date()!s:<12} {status}")
    print()


# ── CLI ──────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="NexLoad License Manager")
    sub = parser.add_subparsers(dest="cmd")

    gen = sub.add_parser("generate", help="Generate a new key")
    gen.add_argument("--user", required=True, help="Customer name/email")
    gen.add_argument("--tier", required=True, choices=list(TIERS), help="License tier")
    gen.add_argument("--days", type=int, help="Override default days")

    val = sub.add_parser("validate", help="Validate a key")
    val.add_argument("key")

    rev = sub.add_parser("revoke", help="Revoke a key")
    rev.add_argument("key")

    sub.add_parser("list", help="List all keys")

    info_p = sub.add_parser("info", help="Show key info")
    info_p.add_argument("key")

    args = parser.parse_args()

    if args.cmd == "generate":
        info = generate_key(args.user, args.tier, args.days)
        print("\n" + "═" * 60)
        print(f"  [OK] License Key Generated!")
        print("═" * 60)
        print(f"  Key:      {info['key']}")
        print(f"  User:     {info['user']}")
        print(f"  Tier:     {TIERS[info['tier']]['label']}")
        print(f"  Duration: {info['days']} days")
        print(f"  Expires:  {info['expires'][:10]}")
        print("═" * 60)
        print(f"\n  [COPY] Send this key to the customer:\n  {info['key']}\n")

    elif args.cmd == "validate":
        result = validate_key(args.key)
        if result["valid"]:
            print(f"\n  [VALID] — {result['tier_label']} | User: {result['user']}")
            print(f"     Expires: {result['expires'][:10]} ({result['days_left']} days left)")
        else:
            print(f"\n  [INVALID] — {result['reason']}")

    elif args.cmd == "revoke":
        if revoke_key(args.key):
            print(f"  [OK] Key revoked: {args.key}")
        else:
            print(f"  [INVALID] Key not found: {args.key}")

    elif args.cmd == "list":
        list_keys()

    elif args.cmd == "info":
        db = _load_db()
        if args.key in db:
            rec = db[args.key]
            print(json.dumps(rec, indent=2))
        else:
            print("Key not found.")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
