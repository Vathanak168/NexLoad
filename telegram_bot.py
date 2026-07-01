"""
NexLoad Telegram Bot Service
============================
Handles License Key distribution/generation and direct Video/Audio downloading.
Run standalone or alongside server.py using Procfile.
"""

import os, sys, time, threading, re, shutil, json
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

import config
import license_manager

BOT_TOKEN = config.TELEGRAM_BOT_TOKEN

# Initialize bot if token is provided
if not BOT_TOKEN or BOT_TOKEN == "123456789:ABCdefGHIjklMNOpqrsTUVwxyz":
    print("⚠️ Telegram Bot Token not set in config.py or environment variables.")
    print("Set TELEGRAM_BOT_TOKEN to start the bot.")
    bot = telebot.TeleBot("123456789:ABCdefGHIjklMNOpqrsTUVwxyz")
else:
    bot = telebot.TeleBot(BOT_TOKEN)

TEMP_DIR = os.path.join(config.BASE_DIR, "bot_temp")
os.makedirs(TEMP_DIR, exist_ok=True)

# Keep track of user trial keys generated via bot
BOT_USERS_FILE = os.path.join(config.BASE_DIR, "bot_users.json")

def _load_bot_users():
    if os.path.exists(BOT_USERS_FILE):
        try:
            with open(BOT_USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_bot_users(data):
    try:
        with open(BOT_USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def is_admin(user_id):
    if not config.TELEGRAM_ADMIN_IDS:
        return True # If no admin IDs specified, allow first user or CLI testing
    return user_id in config.TELEGRAM_ADMIN_IDS


# ─── USER COMMANDS ──────────────────────────────────────────────────────────

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_msg = (
        "🚀 *Welcome to NexLoad Telegram Bot!*\n\n"
        "Here is what you can do:\n"
        "🔑 `/getkey` — Get a Free Trial License Key for NexLoad App/Web\n"
        "📋 `/mykey <KEY>` — Check status and expiration of your License Key\n"
        "🎬 *Download Videos*: Simply paste any video link (TikTok, YouTube, Facebook, IG) here and I will download it for you!\n\n"
        "💻 *Download Desktop App*: Visit our website or launch NexLoad.exe!"
    )
    bot.reply_to(message, welcome_msg, parse_mode="Markdown")


@bot.message_handler(commands=['getkey', 'trial'])
def handle_getkey(message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or message.from_user.first_name or f"User-{user_id}"
    
    users_db = _load_bot_users()
    if user_id in users_db and users_db[user_id].get("key"):
        existing_key = users_db[user_id]["key"]
        val = license_manager.validate_key(existing_key)
        if val["valid"]:
            bot.reply_to(
                message,
                f"🔑 *You already have an active key!*\n\n"
                f"📋 Key: `{existing_key}`\n"
                f"⏳ Expires: {val['expires'][:10]} ({val['days_left']} days left)\n\n"
                f"Open NexLoad app/website and paste this key to use!",
                parse_mode="Markdown"
            )
            return

    # Generate a new 3-day Trial Key
    info = license_manager.generate_key(f"TG: {username}", "trial", 3)
    users_db[user_id] = {
        "username": username,
        "key": info["key"],
        "created": info["created"]
    }
    _save_bot_users(users_db)

    reply = (
        "✅ *Free Trial License Key Generated!*\n\n"
        f"🔑 Key: `{info['key']}`\n"
        f"👤 User: {username}\n"
        f"🏷️ Tier: Trial (3 Days)\n"
        f"📅 Expires: {info['expires'][:10]}\n\n"
        "📋 Copy the key above and paste it into NexLoad Desktop App or Web interface!"
    )
    bot.reply_to(message, reply, parse_mode="Markdown")


@bot.message_handler(commands=['mykey', 'checkkey'])
def handle_checkkey(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "⚠️ Usage: `/mykey NEXLOAD-XXXX-XXXX-XXXX`", parse_mode="Markdown")
        return
        
    key = args[1].strip()
    val = license_manager.validate_key(key)
    if val["valid"]:
        reply = (
            f"✅ *License Key Valid*\n\n"
            f"🔑 Key: `{val['key']}`\n"
            f"🏷️ Tier: *{val['tier_label']}*\n"
            f"👤 Assigned To: {val['user']}\n"
            f"📅 Expires: {val['expires'][:10]} ({val['days_left']} days left)"
        )
    else:
        reply = f"❌ *Invalid License Key*\nReason: {val['reason']}"
    bot.reply_to(message, reply, parse_mode="Markdown")


# ─── ADMIN COMMANDS ─────────────────────────────────────────────────────────

@bot.message_handler(commands=['genkey'])
def handle_genkey(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ Unauthorized. Admin command only.")
        return

    # Format: /genkey <tier> <days> <user>
    parts = message.text.split(maxsplit=3)
    if len(parts) < 4:
        bot.reply_to(message, "⚠️ Usage: `/genkey <tier: trial|basic|pro|lifetime> <days> <username>`", parse_mode="Markdown")
        return

    tier = parts[1].lower()
    if tier not in license_manager.TIERS:
        bot.reply_to(message, f"❌ Invalid tier. Choose: {', '.join(license_manager.TIERS.keys())}")
        return

    try:
        days = int(parts[2])
    except ValueError:
        bot.reply_to(message, "❌ Days must be an integer.")
        return

    user_name = parts[3].strip()
    info = license_manager.generate_key(user_name, tier, days)
    reply = (
        "🎉 *Admin Key Generated!*\n\n"
        f"🔑 Key: `{info['key']}`\n"
        f"🏷️ Tier: *{tier.upper()}*\n"
        f"⏳ Days: {days}\n"
        f"👤 User: {user_name}\n"
    )
    bot.reply_to(message, reply, parse_mode="Markdown")


@bot.message_handler(commands=['revoke'])
def handle_revoke(message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ Usage: `/revoke NEXLOAD-XXXX-...`")
        return
    key = parts[1].strip()
    if license_manager.revoke_key(key):
        bot.reply_to(message, f"✅ Revoked key: `{key}`", parse_mode="Markdown")
    else:
        bot.reply_to(message, f"❌ Key not found: `{key}`", parse_mode="Markdown")


@bot.message_handler(commands=['stats'])
def handle_stats(message):
    if not is_admin(message.from_user.id):
        return
    stats_file = config.STATS_PATH
    if os.path.exists(stats_file):
        try:
            with open(stats_file, "r", encoding="utf-8") as f:
                st = json.load(f)
            reply = (
                "📊 *NexLoad Statistics*\n\n"
                f"📥 Total Downloads: `{st.get('total_downloads', 0)}`\n"
                f"💾 Total Data: `{st.get('total_bytes', 0) // (1024*1024)} MB`\n"
                f"Platforms: `{json.dumps(st.get('by_platform', {}))}`"
            )
        except Exception as e:
            reply = f"Error loading stats: {e}"
    else:
        reply = "📊 No stats recorded yet."
    bot.reply_to(message, reply, parse_mode="Markdown")


# ─── URL MEDIA DOWNLOADER ───────────────────────────────────────────────────

@bot.message_handler(func=lambda m: m.text and (m.text.startswith("http://") or m.text.startswith("https://")))
def handle_url_download(message):
    url = message.text.strip().split()[0]
    status_msg = bot.reply_to(message, "⏳ *Analyzing link & downloading video...*\nPlease wait a moment.", parse_mode="Markdown")

    def download_thread():
        try:
            import yt_dlp
            out_tmpl = os.path.join(TEMP_DIR, f"%(id)s.%(ext)s")
            ydl_opts = {
                'outtmpl': out_tmpl,
                'format': 'bestvideo[ext=mp4][filesize<48M]+bestaudio[ext=m4a]/best[ext=mp4][filesize<48M]/best[filesize<48M]',
                'quiet': True,
                'no_warnings': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)

            if os.path.exists(filename):
                size_mb = os.path.getsize(filename) / (1024 * 1024)
                if size_mb <= 48:
                    bot.edit_message_text("⬆️ *Uploading video to Telegram...*", message.chat.id, status_msg.message_id, parse_mode="Markdown")
                    with open(filename, 'rb') as vf:
                        title = info.get('title', 'NexLoad Video')
                        bot.send_video(message.chat.id, vf, caption=f"🎬 *{title}*\n⚡ Downloaded via NexLoad Bot", parse_mode="Markdown", reply_to_message_id=message.message_id)
                    bot.delete_message(message.chat.id, status_msg.message_id)
                else:
                    bot.edit_message_text(f"⚠️ *Video too large ({size_mb:.1f} MB)*\nTelegram bots can only upload files up to 50 MB directly. Please use the NexLoad PC or Web App to download large files!", message.chat.id, status_msg.message_id, parse_mode="Markdown")
                try:
                    os.remove(filename)
                except Exception:
                    pass
            else:
                bot.edit_message_text("❌ Failed to download video file.", message.chat.id, status_msg.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ *Download Failed*: {str(e)[:150]}", message.chat.id, status_msg.message_id, parse_mode="Markdown")

    threading.Thread(target=download_thread, daemon=True).start()


if __name__ == "__main__":
    if not BOT_TOKEN or BOT_TOKEN == "123456789:ABCdefGHIjklMNOpqrsTUVwxyz":
        print("Set TELEGRAM_BOT_TOKEN to start polling.")
    else:
        print("🤖 NexLoad Telegram Bot started polling...")
        bot.infinity_polling()
