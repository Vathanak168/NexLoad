"""
NexLoad Configuration Module
============================
Central configuration loaded from environment variables or defaults.
Supports both Local Desktop execution and Cloud Hosting (Render/VPS/Docker).
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Server Networking
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 5000))
ADMIN_PORT = int(os.environ.get("ADMIN_PORT", 5050))

# Secret Key for Cryptographic Signature & Session Auth
_secret_env = os.environ.get("SECRET_KEY", "NexLoad-Secret-2026-ChangeThis-To-Something-Unique")
SECRET_KEY = _secret_env.encode() if isinstance(_secret_env, str) else _secret_env

# Database Paths
LICENSE_DB_PATH = os.path.join(BASE_DIR, "licenses.json")
STATS_PATH = os.path.join(BASE_DIR, "stats.json")

# Telegram Bot Integration
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
# List of Telegram User IDs who have Admin permissions on the Bot (e.g. "12345678,87654321")
_admin_ids_str = os.environ.get("TELEGRAM_ADMIN_IDS", "")
TELEGRAM_ADMIN_IDS = [int(x.strip()) for x in _admin_ids_str.split(",") if x.strip().isdigit()]

# Default Downloads Directory
DEFAULT_DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", os.path.join(os.path.expanduser("~"), "Downloads", "NexLoad"))

# Ensure download directory exists when running locally
try:
    os.makedirs(DEFAULT_DOWNLOAD_DIR, exist_ok=True)
except Exception:
    pass
