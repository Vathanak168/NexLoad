"""
NexLoad SQL Database Manager v1.0
=================================
Handles universal SQL storage (SQLite for local PC / PostgreSQL for cloud hosting).
Automatically migrates existing JSON data (licenses.json, stats.json, bot_users.json) on startup.
"""

import os
import sys
import json
import datetime

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

from sqlalchemy import create_engine, Column, String, Integer, Boolean, BigInteger, Text
from sqlalchemy.orm import declarative_base, sessionmaker

import config

Base = declarative_base()

class LicenseRecord(Base):
    __tablename__ = 'licenses'

    key = Column(String(128), primary_key=True)
    user = Column(String(128), default="Unknown")
    tier = Column(String(32), default="trial")
    days = Column(Integer, default=3)
    created = Column(String(64))
    expires = Column(String(64))
    active = Column(Boolean, default=True)
    signature = Column(String(64))
    key_body = Column(String(128))
    hwid = Column(String(128), nullable=True)
    daily_limit = Column(Integer, default=5)
    batch = Column(Boolean, default=False)

    def to_dict(self):
        return {
            "key": self.key,
            "user": self.user,
            "tier": self.tier,
            "days": self.days,
            "created": self.created,
            "expires": self.expires,
            "active": self.active,
            "signature": self.signature,
            "key_body": self.key_body,
            "hwid": self.hwid,
            "daily_limit": self.daily_limit,
            "batch": self.batch
        }

class StatRecord(Base):
    __tablename__ = 'stats'

    id = Column(Integer, primary_key=True, default=1)
    total_downloads = Column(Integer, default=0)
    total_bytes = Column(BigInteger, default=0)
    by_platform = Column(Text, default="{}")
    by_day = Column(Text, default="{}")

class BotUserRecord(Base):
    __tablename__ = 'bot_users'

    telegram_id = Column(String(64), primary_key=True)
    license_key = Column(String(128))


# Setup Engine & Session
db_url = getattr(config, "DATABASE_URL", None) or os.environ.get("DATABASE_URL")
if not db_url:
    db_path = os.path.join(config.BASE_DIR, "nexload.db")
    db_url = f"sqlite:///{db_path}"

# Fix postgres:// prefix for SQLAlchemy 1.4+
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_session():
    return SessionLocal()

def init_db():
    """Create tables and auto-migrate existing JSON data if tables are empty."""
    Base.metadata.create_all(bind=engine)
    session = get_session()
    try:
        # 1. Migrate licenses.json
        if session.query(LicenseRecord).count() == 0:
            json_path = os.path.join(config.BASE_DIR, "licenses.json")
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    for key, rec in data.items():
                        obj = LicenseRecord(
                            key=rec.get("key", key),
                            user=rec.get("user", "Unknown"),
                            tier=rec.get("tier", "trial"),
                            days=rec.get("days", 3),
                            created=str(rec.get("created", "")),
                            expires=str(rec.get("expires", "")),
                            active=rec.get("active", True),
                            signature=rec.get("signature", ""),
                            key_body=rec.get("key_body", ""),
                            hwid=rec.get("hwid", None),
                            daily_limit=rec.get("daily_limit", 5),
                            batch=rec.get("batch", False)
                        )
                        session.merge(obj)
                    session.commit()
                    print(f"[SQL DB] Successfully migrated {len(data)} licenses from JSON to SQL Database!")
                except Exception as e:
                    print(f"[WARN] [SQL DB] Failed to migrate licenses.json: {e}")

        # 2. Migrate stats.json
        if session.query(StatRecord).count() == 0:
            stats_path = os.path.join(config.BASE_DIR, "stats.json")
            stat_obj = StatRecord(id=1, total_downloads=0, total_bytes=0, by_platform="{}", by_day="{}")
            if os.path.exists(stats_path):
                try:
                    with open(stats_path, "r", encoding="utf-8") as f:
                        sdata = json.load(f)
                    stat_obj.total_downloads = sdata.get("total_downloads", 0)
                    stat_obj.total_bytes = sdata.get("total_bytes", 0)
                    stat_obj.by_platform = json.dumps(sdata.get("by_platform", {}))
                    stat_obj.by_day = json.dumps(sdata.get("by_day", {}))
                except Exception:
                    pass
            session.add(stat_obj)
            session.commit()

        # 3. Migrate bot_users.json
        if session.query(BotUserRecord).count() == 0:
            b_path = os.path.join(config.BASE_DIR, "bot_users.json")
            if os.path.exists(b_path):
                try:
                    with open(b_path, "r", encoding="utf-8") as f:
                        bdata = json.load(f)
                    for tid, lkey in bdata.items():
                        session.merge(BotUserRecord(telegram_id=str(tid), license_key=str(lkey)))
                    session.commit()
                except Exception:
                    pass
    finally:
        session.close()

# Initialize DB on import
try:
    init_db()
except Exception as e:
    print(f"[WARN] [SQL DB] Init note: {e}")


# ── LICENSE CRUD OPERATIONS ──────────────────────────────────────────
def get_license(key: str) -> dict:
    session = get_session()
    try:
        rec = session.query(LicenseRecord).filter_by(key=key.strip().upper()).first()
        return rec.to_dict() if rec else None
    finally:
        session.close()

def save_license(data: dict):
    session = get_session()
    try:
        rec = LicenseRecord(
            key=data["key"],
            user=data.get("user", "Unknown"),
            tier=data.get("tier", "trial"),
            days=data.get("days", 3),
            created=str(data.get("created", "")),
            expires=str(data.get("expires", "")),
            active=data.get("active", True),
            signature=data.get("signature", ""),
            key_body=data.get("key_body", ""),
            hwid=data.get("hwid", None),
            daily_limit=data.get("daily_limit", 5),
            batch=data.get("batch", False)
        )
        session.merge(rec)
        session.commit()
    finally:
        session.close()

def revoke_license(key: str) -> bool:
    session = get_session()
    try:
        rec = session.query(LicenseRecord).filter_by(key=key.strip().upper()).first()
        if rec:
            rec.active = False
            session.commit()
            return True
        return False
    finally:
        session.close()

def load_all_licenses() -> dict:
    session = get_session()
    try:
        recs = session.query(LicenseRecord).all()
        return {r.key: r.to_dict() for r in recs}
    finally:
        session.close()


# ── STATS CRUD OPERATIONS ────────────────────────────────────────────
def load_stats() -> dict:
    session = get_session()
    try:
        rec = session.query(StatRecord).filter_by(id=1).first()
        if not rec:
            return {'total_downloads': 0, 'total_bytes': 0, 'by_platform': {}, 'by_day': {}}
        return {
            'total_downloads': rec.total_downloads,
            'total_bytes': rec.total_bytes,
            'by_platform': json.loads(rec.by_platform or "{}"),
            'by_day': json.loads(rec.by_day or "{}")
        }
    except Exception:
        return {'total_downloads': 0, 'total_bytes': 0, 'by_platform': {}, 'by_day': {}}
    finally:
        session.close()

def save_stats(stats: dict):
    session = get_session()
    try:
        rec = session.query(StatRecord).filter_by(id=1).first()
        if not rec:
            rec = StatRecord(id=1)
        rec.total_downloads = stats.get('total_downloads', 0)
        rec.total_bytes = stats.get('total_bytes', 0)
        rec.by_platform = json.dumps(stats.get('by_platform', {}))
        rec.by_day = json.dumps(stats.get('by_day', {}))
        session.merge(rec)
        session.commit()
    finally:
        session.close()


# ── BOT USER OPERATIONS ──────────────────────────────────────────────
def load_bot_users() -> dict:
    session = get_session()
    try:
        recs = session.query(BotUserRecord).all()
        return {r.telegram_id: r.license_key for r in recs}
    finally:
        session.close()

def save_bot_users(users_dict: dict):
    session = get_session()
    try:
        for tid, lkey in users_dict.items():
            session.merge(BotUserRecord(telegram_id=str(tid), license_key=str(lkey)))
        session.commit()
    finally:
        session.close()
