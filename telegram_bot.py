"""
NexLoad Telegram Bot Main Entry Point
=====================================
Admin Control Panel + Media Downloader bot engine.
Modules:
  - bot_key_manager: Admin panel, key management, interactive menus
  - bot_downloader: Direct video downloading from URLs
"""

import os, sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

import telebot
import config
import bot_key_manager
import bot_downloader

from telebot.types import BotCommand
import time

def run_bot():
    """Initializes and starts the Telegram bot polling engine."""
    token = (os.environ.get("TELEGRAM_BOT_TOKEN") or getattr(config, "TELEGRAM_BOT_TOKEN", "")).strip().strip('"').strip("'")
    
    if not token or token == "123456789:ABCdefGHIjklMNOpqrsTUVwxyz":
        print("⚠️ [Telegram Bot] TELEGRAM_BOT_TOKEN is not configured. Bot will not start.")
        return

    print(f"🤖 [Telegram Bot] Initializing with token: {token[:8]}...{token[-4:]}")
    
    bot = telebot.TeleBot(token)

    # ── Verify Token ──────────────────────────────────────────────
    try:
        me = bot.get_me()
        print(f"✅ [Telegram Bot] Connected as @{me.username} ({me.first_name})")
    except Exception as e:
        print(f"❌ [Telegram Bot] Token verification FAILED: {e}")
        return

    # ── Register Menu Commands ────────────────────────────────────
    try:
        commands = [
            BotCommand("start", "🏠 Open Admin Control Panel"),
            BotCommand("admin", "🔑 Key Management Panel"),
            BotCommand("genkey", "➕ Generate License Key (Admin)"),
            BotCommand("getkey", "🆓 Get Free Trial Key"),
            BotCommand("mykey", "📋 Check My Key Status"),
            BotCommand("stats", "📊 Server Statistics"),
            BotCommand("revoke", "🚫 Revoke a License Key (Admin)"),
            BotCommand("help", "❓ Help & Commands"),
        ]
        bot.set_my_commands(commands)
        print("✅ [Telegram Bot] Command menu registered!")
    except Exception as e:
        print(f"⚠️ [Telegram Bot] Could not set menu commands: {e}")

    # ── Register Handlers ─────────────────────────────────────────
    bot_key_manager.register_key_handlers(bot)
    bot_downloader.register_downloader_handlers(bot)

    # ── Start Polling ─────────────────────────────────────────────
    admin_ids = config.TELEGRAM_ADMIN_IDS
    if admin_ids:
        print(f"🔒 [Telegram Bot] Admin IDs: {admin_ids}")
    else:
        print("⚠️ [Telegram Bot] No TELEGRAM_ADMIN_IDS set — admin commands are disabled.")

    print("🤖 [Telegram Bot] Polling started. Listening for messages...")
    retry_delay = 5
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except KeyboardInterrupt:
            print("🛑 [Telegram Bot] Stopped.")
            break
        except Exception as e:
            print(f"⚠️ [Telegram Bot] Polling error: {e}. Reconnecting in {retry_delay}s...")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)

def main():
    run_bot()

if __name__ == "__main__":
    run_bot()
