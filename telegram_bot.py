"""
NexLoad Telegram Bot Main Entry Point
=====================================
Modular bot engine connecting Key Management and Media Downloader services.
Modules:
  - bot_key_manager: Handles /start, /getkey, /mykey, /genkey, /revoke, /stats
  - bot_downloader: Handles direct video downloading from pasted URLs
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

def run_bot():
    """Initializes and starts the Telegram bot polling engine dynamically."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or config.TELEGRAM_BOT_TOKEN
    
    if not token or token == "123456789:ABCdefGHIjklMNOpqrsTUVwxyz":
        print("⚠️ [Telegram Bot] TELEGRAM_BOT_TOKEN is not configured or empty. Bot will not start.")
        return

    print(f"🤖 [Telegram Bot] Initializing with token: {token[:8]}...{token[-4:]}")
    
    bot = telebot.TeleBot(token)

    # 1. Register Key Management & Admin commands
    bot_key_manager.register_key_handlers(bot)

    # 2. Register Video Downloading handler
    bot_downloader.register_downloader_handlers(bot)

    print("🤖 [Telegram Bot] Polling started successfully. Listening for messages...")
    bot.infinity_polling()

def main():
    run_bot()

if __name__ == "__main__":
    run_bot()
