"""
NexLoad Telegram Bot — Key Management Module
============================================
Handles License Key distribution, user verification, and admin key generation.
Functions:
  - handle_start: Welcome message and usage guide
  - handle_getkey / handle_mykey: User license key retrieval
  - handle_genkey / handle_revoke: Admin license management
  - handle_stats: Server usage statistics display
"""

import os, json, time
import config
import license_manager

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

def register_key_handlers(bot):
    """Registers all key management and statistics commands to the bot instance."""

    @bot.message_handler(commands=['start', 'help'])
    def on_start(message):
        user_first = message.from_user.first_name or "User"
        welcome_text = (
            f"👋 *Welcome to NexLoad Bot, {user_first}!*\n\n"
            "Here is what I can do for you:\n"
            "🔑 `/getkey` — Get a free Trial License Key for NexLoad App/Web\n"
            "📋 `/mykey` — Check your active License Key & status\n"
            "🎬 *Video Download* — Simply paste any video link (YouTube, TikTok, Facebook, Reels) directly here and I will download & send the MP4 file to you!\n\n"
            "🌐 *Need HD / 4K or Batch Downloads?*\n"
            "Use the NexLoad PC App or Cloud Web Interface."
        )
        bot.reply_to(message, welcome_text, parse_mode="Markdown")

    @bot.message_handler(commands=['getkey', 'mykey'])
    def on_getkey(message):
        user_id = str(message.from_user.id)
        user_name = message.from_user.first_name or f"TG_{user_id}"
        users = _load_bot_users()

        # Check if user already got a key via bot
        if user_id in users:
            existing_key = users[user_id]
            valid, reason, info = license_manager.validate_license(existing_key)
            if valid:
                reply = (
                    f"🔑 *Your Active NexLoad License Key*\n\n"
                    f"`{existing_key}`\n\n"
                    f"⭐ Tier: *{info.get('tier_label')}*\n"
                    f"⏳ Days Left: *{info.get('days_left')} days*\n\n"
                    "_Copy the key above and paste it into the NexLoad Web App or Desktop App to unlock full features!_"
                )
                bot.reply_to(message, reply, parse_mode="Markdown")
                return

        # Generate a new 3-day trial key for this Telegram user
        new_key = license_manager.generate_license(
            tier="TRI",
            user=f"TG_{user_name}",
            days=3,
            max_hwid=1,
            daily_limit=20,
            batch=False
        )
        users[user_id] = new_key
        _save_bot_users(users)

        reply = (
            f"🎉 *Free License Generated!*\n\n"
            f"`{new_key}`\n\n"
            f"⭐ Tier: *Trial (3 Days)*\n"
            f"📥 Daily Limit: *20 downloads/day*\n\n"
            "_Copy the key above and paste it into the NexLoad Web App or Desktop App!_"
        )
        bot.reply_to(message, reply, parse_mode="Markdown")

    @bot.message_handler(commands=['genkey'])
    def on_genkey(message):
        # Admin command: /genkey PRO 365 ClientName
        admin_ids = config.TELEGRAM_ADMIN_IDS
        if admin_ids and message.from_user.id not in admin_ids:
            bot.reply_to(message, "⚠️ *Permission Denied*: You are not authorized to generate commercial keys.", parse_mode="Markdown")
            return

        parts = message.text.split()
        if len(parts) < 3:
            bot.reply_to(message, "⚙️ *Usage*: `/genkey <PRO|LIF|TRI> <days> [UserName]`\nExample: `/genkey PRO 365 JohnDoe`", parse_mode="Markdown")
            return

        tier = parts[1].upper()
        if tier not in ["PRO", "LIF", "TRI"]:
            tier = "PRO"
        
        try:
            days = int(parts[2])
        except ValueError:
            days = 365

        user = parts[3] if len(parts) > 3 else f"TG_AdminGen_{int(time.time())}"

        key = license_manager.generate_license(tier=tier, user=user, days=days)
        bot.reply_to(message, f"✅ *Commercial Key Generated!*\n\n`{key}`\n\nUser: `{user}`\nTier: *{tier}* ({days} days)", parse_mode="Markdown")

    @bot.message_handler(commands=['revoke'])
    def on_revoke(message):
        admin_ids = config.TELEGRAM_ADMIN_IDS
        if admin_ids and message.from_user.id not in admin_ids:
            return
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "⚙️ *Usage*: `/revoke <LICENSE_KEY>`", parse_mode="Markdown")
            return
        key = parts[1].strip().upper()
        if license_manager.revoke_license(key):
            bot.reply_to(message, f"🚫 Key `{key}` has been revoked successfully.", parse_mode="Markdown")
        else:
            bot.reply_to(message, f"❌ Key `{key}` not found.", parse_mode="Markdown")

    @bot.message_handler(commands=['stats'])
    def on_stats(message):
        stats_file = config.STATS_PATH
        if os.path.exists(stats_file):
            try:
                with open(stats_file, "r", encoding="utf-8") as f:
                    st = json.load(f)
                reply = (
                    "📊 *NexLoad Cloud Server Statistics*\n\n"
                    f"📥 Total Downloads: `{st.get('total_downloads', 0)}`\n"
                    f"💾 Total Processed Data: `{st.get('total_bytes', 0) // (1024*1024)} MB`\n"
                )
            except Exception as e:
                reply = f"Error loading stats: {e}"
        else:
            reply = "📊 No statistics recorded yet."
        bot.reply_to(message, reply, parse_mode="Markdown")
