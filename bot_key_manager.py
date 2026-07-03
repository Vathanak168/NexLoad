"""
NexLoad Telegram Bot — Admin Control Panel
===========================================
Full admin panel for managing the NexLoad Download Tool via Telegram.

Features:
  - 🔑 Key Management: Create, List, Validate, Revoke license keys (for selling)
  - 📊 Server Dashboard: Live stats, downloads, data processed
  - 🎬 Quick Download: Download videos directly within the bot
  - Structured callback routing: "nav:", "tier:", "confirm:", "page:", "action:"
"""

import os, json, time, datetime
import config
import license_manager
import db
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_USERS_FILE = os.path.join(config.BASE_DIR, "bot_users.json")

# ─────────────────────────────────────────────────────────────────
# USER DATA PERSISTENCE
# ─────────────────────────────────────────────────────────────────

def _load_bot_users():
    try:
        return db.load_bot_users()
    except Exception:
        if os.path.exists(BOT_USERS_FILE):
            try:
                with open(BOT_USERS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}


def _save_bot_users(data):
    try:
        db.save_bot_users(data)
    except Exception as e:
        print(f"⚠️ [SQL DB] Save bot users note: {e}")
    try:
        with open(BOT_USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


_key_check_timestamps = {}


# ─────────────────────────────────────────────────────────────────
# ADMIN CHECK HELPER
# ─────────────────────────────────────────────────────────────────

def _is_admin(user_id):
    """Check if user is admin. If no admin IDs configured, deny admin access."""
    admin_ids = config.TELEGRAM_ADMIN_IDS
    if not admin_ids:
        return False
    return user_id in admin_ids


# ─────────────────────────────────────────────────────────────────
# KEYBOARD BUILDERS
# ─────────────────────────────────────────────────────────────────

def _kb_copy_key(key, back_nav="nav:main"):
    markup = InlineKeyboardMarkup(row_width=1)
    try:
        from telebot.types import CopyTextButton
        markup.row(InlineKeyboardButton("📋 Copy Access Key", copy_text=CopyTextButton(key)))
    except Exception:
        pass
    if back_nav:
        markup.row(InlineKeyboardButton("↩️ Back to Menu", callback_data=back_nav))
    return markup


def _kb_main_menu(user_id):
    """Build Main Menu — downloader-first for users, operations panel for admins."""
    markup = InlineKeyboardMarkup(row_width=2)

    if _is_admin(user_id):
        markup.row(
            InlineKeyboardButton("🔑 Generate Key", callback_data="nav:create_key"),
            InlineKeyboardButton("📋 List Keys", callback_data="nav:list_keys")
        )
        markup.row(
            InlineKeyboardButton("🚫 Revoke Key", callback_data="nav:revoke_prompt"),
            InlineKeyboardButton("📊 Server Stats", callback_data="nav:dashboard")
        )
        markup.row(InlineKeyboardButton("🖥 YouTube Desktop App", url="https://github.com/Vathanak168/NexLoad/releases"))
        return markup

    # Regular user section (downloader-first)
    markup.row(InlineKeyboardButton("🖥 YouTube Desktop App", url="https://github.com/Vathanak168/NexLoad/releases"))
    markup.row(
        InlineKeyboardButton("🔑 My Access", callback_data="nav:validate_prompt"),
        InlineKeyboardButton("❓ Help Guide", callback_data="nav:help_dl")
    )
    return markup


def _kb_key_management():
    """Key Management submenu for admins."""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.row(
        InlineKeyboardButton("➕ Create New Key", callback_data="nav:create_key"),
    )
    markup.row(
        InlineKeyboardButton("📋 List All Keys", callback_data="nav:list_keys"),
        InlineKeyboardButton("🔍 Validate Key", callback_data="nav:validate_prompt")
    )
    markup.row(
        InlineKeyboardButton("🚫 Revoke Key", callback_data="nav:revoke_prompt"),
    )
    markup.row(InlineKeyboardButton("↩️ Back to Menu", callback_data="nav:main"))
    return markup


def _kb_select_tier():
    """Tier selection for key creation wizard."""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.row(
        InlineKeyboardButton("🆓 Trial (3 days)", callback_data="tier:trial"),
        InlineKeyboardButton("⭐ Basic (30 days)", callback_data="tier:basic")
    )
    markup.row(
        InlineKeyboardButton("💎 Pro (365 days)", callback_data="tier:pro"),
        InlineKeyboardButton("👑 Lifetime", callback_data="tier:lifetime")
    )
    markup.row(InlineKeyboardButton("↩️ Cancel", callback_data="nav:keys"))
    return markup


def _kb_confirm_keygen(tier, days):
    """Confirm key generation."""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.row(
        InlineKeyboardButton("✅ Generate Now", callback_data=f"confirm:gen:{tier}:{days}"),
        InlineKeyboardButton("❌ Cancel", callback_data="nav:keys")
    )
    return markup


def _kb_after_keygen(key=None):
    """After key is generated."""
    markup = InlineKeyboardMarkup(row_width=2)
    if key:
        try:
            from telebot.types import CopyTextButton
            markup.row(InlineKeyboardButton("📋 Copy Access Key", copy_text=CopyTextButton(key)))
        except Exception:
            pass
    markup.row(
        InlineKeyboardButton("➕ Create Another", callback_data="nav:create_key"),
        InlineKeyboardButton("📋 List All Keys", callback_data="nav:list_keys")
    )
    markup.row(InlineKeyboardButton("↩️ Back to Menu", callback_data="nav:main"))
    return markup


def _kb_back(target="nav:main"):
    """Simple back button."""
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("↩️ Back", callback_data=target))
    return markup


def _kb_back_to_keys():
    """Back to key management."""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("↩️ Key Management", callback_data="nav:keys"),
        InlineKeyboardButton("🏠 Main Menu", callback_data="nav:main")
    )
    return markup


def _kb_list_pagination(page, total_pages):
    """Pagination for key list."""
    markup = InlineKeyboardMarkup(row_width=3)
    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page:keys:{page-1}"))
    buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"page:keys:{page+1}"))
    markup.row(*buttons)
    markup.row(
        InlineKeyboardButton("↩️ Key Management", callback_data="nav:keys"),
        InlineKeyboardButton("🏠 Main Menu", callback_data="nav:main")
    )
    return markup


# ─────────────────────────────────────────────────────────────────
# TEXT BUILDERS
# ─────────────────────────────────────────────────────────────────

def _text_main_menu(user_first, is_admin):
    if not is_admin:
        return (
            f"⚡ <b>Welcome to NexLoad, {user_first}!</b>\n\n"
            "Send me any social media video or photo link and I'll download it directly here for you.\n\n"
            "📱 <b>Supported Platforms:</b>\n"
            "• TikTok • Instagram • Facebook • X/Twitter • Pinterest\n\n"
            "🖥 <b>YouTube Downloads:</b>\n"
            "YouTube blocks cloud servers. To download YouTube videos reliably, please use our standalone Desktop App.\n\n"
            "💡 <i>Just paste a link below to begin!</i>"
        )

    return (
        f"🛠 <b>NexLoad Admin Operations Panel</b>\n"
        f"Welcome back, <b>{user_first}</b>!\n\n"
        "👑 <b>Management Capabilities:</b>\n"
        "┣ 🔑 Create, List & Revoke Access Keys\n"
        "┣ 📋 Inspect Active License Plans\n"
        "┗ 📊 View Live Server Download Analytics\n\n"
        "💡 <i>Select an operation below or send a link to download.</i>"
    )


def _text_key_management():
    # Count active/total keys
    db = license_manager._load_db()
    total = len(db)
    active = sum(1 for v in db.values() if v.get('active', False))
    expired = 0
    now = datetime.datetime.now(datetime.timezone.utc)
    for v in db.values():
        if v.get('active'):
            try:
                exp = datetime.datetime.fromisoformat(v['expires'])
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=datetime.timezone.utc)
                if (exp - now).days < 0:
                    expired += 1
            except Exception:
                pass

    return (
        "🔑 <b>Key Management Panel</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 Total Keys: <b>{total}</b>\n"
        f"✅ Active: <b>{active}</b>\n"
        f"⏰ Expired: <b>{expired}</b>\n"
        f"🚫 Revoked: <b>{total - active}</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Select an action below:"
    )


def _text_tier_select():
    return (
        "➕ <b>Create New License Key</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Select the license tier:\n\n"
        "🆓 <b>Trial</b> — 3 days, 5 downloads/day\n"
        "⭐ <b>Basic</b> — 30 days, 50 downloads/day\n"
        "💎 <b>Pro</b> — 365 days, unlimited downloads\n"
        "👑 <b>Lifetime</b> — Forever, unlimited downloads\n\n"
        "━━━━━━━━━━━━━━━━━━━━━"
    )


TIER_INFO = {
    "trial":    {"emoji": "🆓", "label": "Trial",    "days": 3,    "limit": "5/day"},
    "basic":    {"emoji": "⭐", "label": "Basic",    "days": 30,   "limit": "50/day"},
    "pro":      {"emoji": "💎", "label": "Pro",      "days": 365,  "limit": "Unlimited"},
    "lifetime": {"emoji": "👑", "label": "Lifetime", "days": 9999, "limit": "Unlimited"},
}


def _text_confirm_keygen(tier, days):
    info = TIER_INFO.get(tier, {})
    return (
        f"⚡ <b>Confirm Key Generation</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{info.get('emoji','')} Tier: <b>{info.get('label', tier)}</b>\n"
        f"📅 Duration: <b>{days} days</b>\n"
        f"📥 Download Limit: <b>{info.get('limit', '?')}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Tap <b>Generate Now</b> to create the key."
    )


def _text_help_download():
    return (
        "🎬 <b>How to Download Videos</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📱 <b>Via This Bot (Quick):</b>\n"
        "   Simply paste any video link directly into this chat!\n"
        "   Supported: YouTube, TikTok, Instagram, Facebook, Twitter/X & more.\n\n"
        "💻 <b>Via NexLoad Web App:</b>\n"
        "   1. Open the Web App (button below)\n"
        "   2. Enter your License Key\n"
        "   3. Paste URL → Choose quality → Download!\n\n"
        "🖥️ <b>Via Desktop App (HD/4K):</b>\n"
        "   Use NexLoad.exe for batch downloads, 4K, subtitles.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ <i>Bot downloads limited to 48MB. Use Web/Desktop for larger files.</i>"
    )


# ─────────────────────────────────────────────────────────────────
# HANDLER REGISTRATION
# ─────────────────────────────────────────────────────────────────

def register_key_handlers(bot):
    """Registers all admin panel handlers to the bot instance."""

    # ── /start, /help ────────────────────────────────────────────
    @bot.message_handler(commands=['start', 'help'])
    def on_start(message):
        user = message.from_user
        user_first = user.first_name or "User"
        is_admin = _is_admin(user.id)
        bot.send_message(
            message.chat.id,
            _text_main_menu(user_first, is_admin),
            parse_mode="HTML",
            reply_markup=_kb_main_menu(user.id)
        )

    # ── /admin shortcut ──────────────────────────────────────────
    @bot.message_handler(commands=['admin'])
    def on_admin(message):
        if not _is_admin(message.from_user.id):
            bot.reply_to(message, "🤷 <b>Command Not Recognized</b>\n\nSend me a video link to download media, or tap /help to see available options.", parse_mode="HTML")
            return
        bot.send_message(
            message.chat.id,
            _text_key_management(),
            parse_mode="HTML",
            reply_markup=_kb_key_management()
        )

    # ── /myid — Show user's Telegram ID ──────────────────────────
    @bot.message_handler(commands=['myid'])
    def on_myid(message):
        user = message.from_user
        hint = ""
        if _is_admin(user.id):
            hint = (
                f"\n\n💡 <i>Copy the ID above and put it in</i>\n"
                f"<code>TELEGRAM_ADMIN_IDS={user.id}</code>\n"
                f"<i>in your .env file to lock admin access.</i>"
            )
        bot.reply_to(
            message,
            f"🆔 <b>Your Telegram Info</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔢 User ID: <code>{user.id}</code>\n"
            f"👤 Name: <b>{user.first_name or ''} {user.last_name or ''}</b>\n"
            f"📛 Username: @{user.username or 'N/A'}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━{hint}",
            parse_mode="HTML"
        )

    # ── /genkey shortcut (text command) ──────────────────────────
    @bot.message_handler(commands=['genkey'])
    def on_genkey_cmd(message):
        if not _is_admin(message.from_user.id):
            bot.reply_to(message, "🤷 <b>Command Not Recognized</b>\n\nSend me a video link to download media, or tap /help to see available options.", parse_mode="HTML")
            return

        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(
                message,
                "⚙️ <b>Usage:</b>\n"
                "<code>/genkey pro 365 ClientName</code>\n"
                "<code>/genkey trial</code>\n"
                "<code>/genkey lifetime</code>\n\n"
                "Or use the interactive menu: /admin",
                parse_mode="HTML"
            )
            return

        tier_input = parts[1].lower()
        tier_map = {"pro": "pro", "tri": "trial", "trial": "trial", "bas": "basic",
                     "basic": "basic", "lif": "lifetime", "lifetime": "lifetime"}
        tier = tier_map.get(tier_input, "pro")
        tier_info = TIER_INFO.get(tier, {})

        try:
            days = int(parts[2]) if len(parts) > 2 else tier_info.get("days", 365)
        except ValueError:
            days = tier_info.get("days", 365)

        user_name = parts[3] if len(parts) > 3 else f"Customer_{int(time.time()) % 10000}"

        try:
            info = license_manager.generate_key(user_name=user_name, tier=tier, days=days)
            key = info["key"]
            bot.reply_to(
                message,
                f"✅ <b>Key Generated Successfully!</b>\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🔐 Key:\n<code>{key}</code>\n\n"
                f"{tier_info.get('emoji','')} Tier: <b>{tier_info.get('label', tier)}</b>\n"
                f"📅 Duration: <b>{days} days</b>\n"
                f"👤 Customer: <b>{user_name}</b>\n"
                f"📥 Limit: <b>{tier_info.get('limit','?')}</b>\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"💡 <i>Send this key to your customer!</i>",
                parse_mode="HTML",
                reply_markup=_kb_after_keygen(key)
            )
        except Exception as e:
            bot.reply_to(message, f"❌ <b>Error:</b> {str(e)[:200]}", parse_mode="HTML")

    # ── /revoke shortcut ─────────────────────────────────────────
    @bot.message_handler(commands=['revoke'])
    def on_revoke_cmd(message):
        if not _is_admin(message.from_user.id):
            bot.reply_to(message, "🤷 <b>Command Not Recognized</b>\n\nSend me a video link to download media, or tap /help to see available options.", parse_mode="HTML")
            return
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "⚙️ <b>Usage:</b> <code>/revoke NEXLOAD-XXXX-XXX-XXX-XXXX</code>", parse_mode="HTML")
            return
        key = parts[1].strip().upper()
        if license_manager.revoke_key(key):
            bot.reply_to(message, f"🚫 Key <code>{key}</code> revoked successfully.", parse_mode="HTML")
        else:
            bot.reply_to(message, f"❌ Key <code>{key}</code> not found.", parse_mode="HTML")

    # ── /stats, /getkey, /mykey shortcuts ────────────────────────
    @bot.message_handler(commands=['stats'])
    def cmd_stats(message):
        _send_stats_msg(bot, message)

    @bot.message_handler(commands=['getkey'])
    def cmd_getkey(message):
        _send_getkey(bot, message)

    @bot.message_handler(commands=['mykey'])
    def cmd_mykey(message):
        _send_mykey(bot, message)

    # ══════════════════════════════════════════════════════════════
    # CALLBACK QUERY ROUTING
    # ══════════════════════════════════════════════════════════════

    # ── Navigation Router ────────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data and call.data.startswith("nav:"))
    def on_nav(call):
        bot.answer_callback_query(call.id)
        action = call.data.split(":")[1]
        uid = call.from_user.id

        try:
            if action == "main":
                _nav_main(bot, call)
            elif action == "keys":
                _nav_key_management(bot, call, uid)
            elif action == "create_key":
                _nav_create_key(bot, call, uid)
            elif action == "list_keys":
                _nav_list_keys(bot, call, uid, page=0)
            elif action == "dashboard":
                _nav_dashboard(bot, call, uid)
            elif action == "help_dl":
                _nav_help_dl(bot, call)
            elif action == "validate_prompt":
                _nav_validate_prompt(bot, call, uid)
            elif action == "revoke_prompt":
                _nav_revoke_prompt(bot, call, uid)
        except Exception as e:
            print(f"⚠️ [Bot] Nav error ({action}): {e}")
            _safe_edit(bot, call, f"❌ <b>Error:</b> {str(e)[:200]}", _kb_back())

    # ── Tier Selection ───────────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data and call.data.startswith("tier:"))
    def on_tier_select(call):
        bot.answer_callback_query(call.id)
        if not _is_admin(call.from_user.id):
            return

        tier = call.data.split(":")[1]
        info = TIER_INFO.get(tier, {})
        days = info.get("days", 365)

        _safe_edit(
            bot, call,
            _text_confirm_keygen(tier, days),
            _kb_confirm_keygen(tier, days)
        )

    # ── Confirm Key Generation ───────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data and call.data.startswith("confirm:gen:"))
    def on_confirm_gen(call):
        bot.answer_callback_query(call.id)
        if not _is_admin(call.from_user.id):
            return

        parts = call.data.split(":")
        tier = parts[2]
        days = int(parts[3])
        user_name = f"Customer_{int(time.time()) % 10000}"

        try:
            info = license_manager.generate_key(user_name=user_name, tier=tier, days=days)
            key = info["key"]
            tier_data = TIER_INFO.get(tier, {})

            text = (
                f"✅ <b>Key Generated Successfully!</b>\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🔐 Key:\n<code>{key}</code>\n\n"
                f"{tier_data.get('emoji','')} Tier: <b>{tier_data.get('label', tier)}</b>\n"
                f"📅 Duration: <b>{days} days</b>\n"
                f"👤 Customer: <b>{user_name}</b>\n"
                f"📥 Limit: <b>{tier_data.get('limit','?')}</b>\n"
                f"📅 Expires: <b>{info['expires'][:10]}</b>\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"💡 <i>Tap the key above to copy, then send to customer!</i>"
            )
            _safe_edit(bot, call, text, _kb_after_keygen(key))
        except Exception as e:
            _safe_edit(bot, call, f"❌ <b>Generation Failed:</b> {str(e)[:200]}", _kb_back_to_keys())

    # ── Pagination ───────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data and call.data.startswith("page:keys:"))
    def on_page(call):
        bot.answer_callback_query(call.id)
        page = int(call.data.split(":")[2])
        _nav_list_keys(bot, call, call.from_user.id, page=page)

    # ── Noop (for page indicator button) ─────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data == "noop")
    def on_noop(call):
        bot.answer_callback_query(call.id)

    # ══════════════════════════════════════════════════════════════
    # TEXT INPUT HANDLERS (for validate/revoke prompts)
    # ══════════════════════════════════════════════════════════════

    @bot.message_handler(func=lambda m: m.text and m.text.upper().startswith("NEXLOAD-") and not m.text.startswith("/"))
    def on_key_input(message):
        """When user pastes a NEXLOAD key, validate it automatically."""
        user_id = message.from_user.id
        is_adm = _is_admin(user_id)
        import time as _tm
        if not is_adm:
            now = _tm.time()
            last_check = _key_check_timestamps.get(user_id, 0)
            if now - last_check < 5.0:
                bot.reply_to(message, "⏳ Please wait a few seconds before checking another key.")
                return
            _key_check_timestamps[user_id] = now

        key = message.text.strip().upper()
        result = license_manager.validate_key(key)

        if not is_adm:
            if result.get("valid"):
                text = (
                    f"✅ <b>License Key Valid</b>\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"🔐 Key: <code>{key[:12]}...</code>\n"
                    f"✅ Status: <b>Active</b>\n\n"
                    f"💡 <i>Detailed customer information (name, tier, expiration) is restricted to administrators for privacy.</i>\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━"
                )
            else:
                text = (
                    f"❌ <b>License Key Invalid</b>\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"🔐 Key: <code>{key[:12]}...</code>\n"
                    f"❌ Status: <b>Invalid or Expired</b>\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━"
                )
        else:
            if result.get("valid"):
                text = (
                    f"✅ <b>Key Valid!</b>\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"🔐 Key: <code>{key}</code>\n\n"
                    f"✅ Status: <b>Active</b>\n"
                    f"⭐ Tier: <b>{result.get('tier_label', '?')}</b>\n"
                    f"👤 User: <b>{result.get('user', '?')}</b>\n"
                    f"⏳ Days Left: <b>{result.get('days_left', '?')}</b>\n"
                    f"📅 Expires: <b>{result.get('expires', '?')[:10]}</b>\n"
                    f"📥 Daily Limit: <b>{result.get('daily_limit', '?')}</b>\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━"
                )
            else:
                text = (
                    f"❌ <b>Key Invalid</b>\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"🔐 Key: <code>{key}</code>\n\n"
                    f"❌ Status: <b>Invalid</b>\n"
                    f"📝 Reason: <i>{result.get('reason', 'Unknown')}</i>\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━"
                )

        markup = InlineKeyboardMarkup(row_width=2)
        if is_adm and result.get("valid"):
            markup.row(InlineKeyboardButton("🚫 Revoke This Key", callback_data=f"action:revoke:{key}"))
        markup.row(InlineKeyboardButton("🏠 Main Menu", callback_data="nav:main"))

        bot.reply_to(message, text, parse_mode="HTML", reply_markup=markup)

    # ── Action: Revoke from button ───────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data and call.data.startswith("action:revoke:"))
    def on_action_revoke(call):
        bot.answer_callback_query(call.id)
        if not _is_admin(call.from_user.id):
            return

        key = call.data.split(":", 2)[2]
        if license_manager.revoke_key(key):
            _safe_edit(
                bot, call,
                f"🚫 <b>Key Revoked!</b>\n\n<code>{key}</code>\n\nThis key is now deactivated.",
                _kb_back_to_keys()
            )
        else:
            _safe_edit(
                bot, call,
                f"❌ Key <code>{key}</code> not found.",
                _kb_back_to_keys()
            )


# ─────────────────────────────────────────────────────────────────
# NAVIGATION ACTIONS — Edit Message In-Place
# ─────────────────────────────────────────────────────────────────

def _safe_edit(bot, call, text, markup):
    """Safely edit a message, catching API errors."""
    try:
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=markup
        )
    except Exception as e:
        # If message wasn't modified (same content), just ignore
        if "message is not modified" not in str(e).lower():
            print(f"⚠️ [Bot] Edit error: {e}")


def _nav_main(bot, call):
    """Navigate to main menu."""
    user = call.from_user
    user_first = user.first_name or "User"
    is_admin = _is_admin(user.id)
    _safe_edit(
        bot, call,
        _text_main_menu(user_first, is_admin),
        _kb_main_menu(user.id)
    )


def _nav_key_management(bot, call, uid):
    """Navigate to Key Management panel."""
    if not _is_admin(uid):
        _safe_edit(bot, call, "⛔ <b>Admin access required.</b>", _kb_back())
        return
    _safe_edit(bot, call, _text_key_management(), _kb_key_management())


def _nav_create_key(bot, call, uid):
    """Navigate to Create Key wizard — tier selection."""
    if not _is_admin(uid):
        _safe_edit(bot, call, "⛔ <b>Admin access required.</b>", _kb_back())
        return
    _safe_edit(bot, call, _text_tier_select(), _kb_select_tier())


def _nav_list_keys(bot, call, uid, page=0):
    """Show paginated list of all license keys."""
    if not _is_admin(uid):
        _safe_edit(bot, call, "⛔ <b>Admin access required.</b>", _kb_back())
        return

    db = license_manager._load_db()
    keys_list = list(db.items())

    if not keys_list:
        _safe_edit(
            bot, call,
            "📋 <b>No License Keys</b>\n\nNo keys have been generated yet.",
            _kb_back_to_keys()
        )
        return

    # Sort by created date (newest first)
    keys_list.sort(key=lambda x: x[1].get('created', ''), reverse=True)

    per_page = 5
    total_pages = max(1, (len(keys_list) + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    start = page * per_page
    page_keys = keys_list[start:start + per_page]

    now = datetime.datetime.now(datetime.timezone.utc)
    lines = [f"📋 <b>All License Keys</b> ({len(keys_list)} total)\n\n━━━━━━━━━━━━━━━━━━━━━\n"]

    for key, rec in page_keys:
        tier = rec.get("tier", "?")
        tier_data = TIER_INFO.get(tier, {"emoji": "❓", "label": tier})
        user = rec.get("user", "?")
        active = rec.get("active", False)

        # Status calculation
        if not active:
            status = "🚫 Revoked"
        else:
            try:
                exp = datetime.datetime.fromisoformat(rec.get("expires", ""))
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=datetime.timezone.utc)
                dl = (exp - now).days
                status = f"✅ {dl}d left" if dl >= 0 else f"⏰ Expired {-dl}d"
            except Exception:
                status = "❓ Unknown"

        # Truncate key for display
        short_key = key if len(key) <= 30 else key[:15] + "..." + key[-8:]
        lines.append(
            f"\n{tier_data['emoji']} <b>{tier_data['label']}</b> | {status}\n"
            f"   <code>{key}</code>\n"
            f"   👤 {user}\n"
        )

    lines.append("\n━━━━━━━━━━━━━━━━━━━━━")

    _safe_edit(bot, call, "".join(lines), _kb_list_pagination(page, total_pages))


def _nav_dashboard(bot, call, uid):
    """Show server dashboard with live stats."""
    if not _is_admin(uid):
        _safe_edit(bot, call, "⛔ <b>Admin access required.</b>", _kb_back())
        return

    stats_file = config.STATS_PATH
    if os.path.exists(stats_file):
        try:
            with open(stats_file, "r", encoding="utf-8") as f:
                st = json.load(f)
            total_dl = st.get("total_downloads", 0)
            total_bytes = st.get("total_bytes", 0)
            total_mb = total_bytes // (1024 * 1024)
            total_gb = total_bytes / (1024 * 1024 * 1024)

            # Count keys
            db = license_manager._load_db()
            total_keys = len(db)
            active_keys = sum(1 for v in db.values() if v.get('active'))

            text = (
                "📊 <b>NexLoad Server Dashboard</b>\n\n"
                "━━━━━━━━━━━━━━━━━━━━━\n\n"
                "📥 <b>Downloads</b>\n"
                f"   Total: <b>{total_dl:,}</b>\n"
                f"   Data Processed: <b>{total_gb:.2f} GB</b> ({total_mb:,} MB)\n\n"
                "🔑 <b>License Keys</b>\n"
                f"   Total: <b>{total_keys}</b>\n"
                f"   Active: <b>{active_keys}</b>\n"
                f"   Revoked: <b>{total_keys - active_keys}</b>\n\n"
                "🟢 <b>Server Status: Online</b>\n\n"
                "━━━━━━━━━━━━━━━━━━━━━"
            )
        except Exception as e:
            text = f"❌ <b>Error loading stats:</b> {e}"
    else:
        text = (
            "📊 <b>NexLoad Server Dashboard</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📥 Total Downloads: <b>0</b>\n"
            "💾 Data Processed: <b>0 MB</b>\n"
            "🟢 Server: <b>Online</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "<i>No download history yet.</i>"
        )

    markup = InlineKeyboardMarkup(row_width=2)
    markup.row(
        InlineKeyboardButton("🔄 Refresh", callback_data="nav:dashboard"),
        InlineKeyboardButton("🔑 Keys", callback_data="nav:keys")
    )
    markup.row(InlineKeyboardButton("↩️ Back to Menu", callback_data="nav:main"))
    _safe_edit(bot, call, text, markup)


def _nav_help_dl(bot, call):
    """Show download instructions."""
    _safe_edit(bot, call, _text_help_download(), _kb_back())


def _nav_validate_prompt(bot, call, uid):
    """Show validate key prompt."""
    text = (
        "🔍 <b>Validate License Key</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📝 Paste a <b>NEXLOAD-</b> key directly into the chat to validate it.\n\n"
        "Example:\n"
        "<code>NEXLOAD-XXXX-PRO-365-XXXX</code>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "<i>I will automatically check its status!</i>"
    )
    _safe_edit(bot, call, text, _kb_back())


def _nav_revoke_prompt(bot, call, uid):
    """Show revoke key prompt."""
    if not _is_admin(uid):
        _safe_edit(bot, call, "⛔ <b>Admin access required.</b>", _kb_back())
        return

    text = (
        "🚫 <b>Revoke License Key</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "To revoke a key, use the command:\n\n"
        "<code>/revoke NEXLOAD-XXXX-XXX-XXX-XXXX</code>\n\n"
        "Or paste a key into the chat to view it, then use the <b>Revoke</b> button.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ <i>Revoked keys cannot be re-activated.</i>"
    )
    _safe_edit(bot, call, text, _kb_back("nav:keys"))


# ─────────────────────────────────────────────────────────────────
# SLASH COMMAND RESPONSE HELPERS (new message, not edit)
# ─────────────────────────────────────────────────────────────────

def _send_getkey(bot, message):
    """Handle /getkey — free trial key for users."""
    user = message.from_user
    user_id = str(user.id)
    user_name = user.first_name or f"TG_{user_id}"
    users = _load_bot_users()

    if user_id in users:
        existing_key = users[user_id]
        result = license_manager.validate_key(existing_key)
        if result.get("valid"):
            bot.reply_to(
                message,
                f"🔑 <b>Your Active Key</b>\n\n"
                f"<code>{existing_key}</code>\n\n"
                f"⭐ {result.get('tier_label','Trial')} | ⏳ {result.get('days_left','?')} days left",
                parse_mode="HTML",
                reply_markup=_kb_copy_key(existing_key)
            )
            return

    try:
        info = license_manager.generate_key(user_name=f"TG_{user_name}", tier="trial", days=3)
        new_key = info["key"]
        users[user_id] = new_key
        _save_bot_users(users)
        bot.reply_to(
            message,
            f"🎉 <b>Free Trial Key!</b>\n\n<code>{new_key}</code>\n\n"
            f"⭐ Trial (3 days) | 📥 5 downloads/day",
            parse_mode="HTML",
            reply_markup=_kb_copy_key(new_key)
        )
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)[:200]}", parse_mode="HTML")


def _send_mykey(bot, message):
    """Handle /mykey — check user's key status."""
    user_id = str(message.from_user.id)
    users = _load_bot_users()
    if user_id not in users:
        bot.reply_to(message, "📋 No key found. Use /getkey for a free trial!", parse_mode="HTML")
        return
    key = users[user_id]
    result = license_manager.validate_key(key)
    status = "✅ Active" if result.get("valid") else f"❌ {result.get('reason','Invalid')}"
    bot.reply_to(
        message,
        f"📋 <code>{key}</code>\n{status}",
        parse_mode="HTML",
        reply_markup=_kb_copy_key(key)
    )


def _send_stats_msg(bot, message):
    """Handle /stats command."""
    if not _is_admin(message.from_user.id):
        bot.reply_to(message, "🤷 <b>Command Not Recognized</b>\n\nSend me a video link to download media, or tap /help to see available options.", parse_mode="HTML")
        return
    db = license_manager._load_db()
    total_keys = len(db)
    active_keys = sum(1 for v in db.values() if v.get("active", False))

    stats_file = config.STATS_PATH
    dl_count = 0
    mb_total = 0
    if os.path.exists(stats_file):
        try:
            with open(stats_file, "r", encoding="utf-8") as f:
                st = json.load(f)
            dl_count = st.get("total_downloads", 0)
            mb_total = st.get("total_bytes", 0) // (1024 * 1024)
        except Exception:
            pass

    gb_str = f"{mb_total / 1024:.2f} GB" if mb_total >= 1024 else f"{mb_total} MB"

    msg_text = (
        f"📊 <b>NexLoad Live System Dashboard</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🚀 <b>Media Processing:</b>\n"
        f"┣ ⬇️ Total Downloads: <b>{dl_count:,}</b>\n"
        f"┗ 💾 Bandwidth Processed: <b>{gb_str}</b>\n\n"
        f"🔑 <b>Access Key Management:</b>\n"
        f"┣ ✅ Active Access Keys: <b>{active_keys}</b>\n"
        f"┗ 📋 Total Issued Keys: <b>{total_keys}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━"
    )
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🔄 Refresh Dashboard", callback_data="nav:dashboard"))
    bot.reply_to(message, msg_text, parse_mode="HTML", reply_markup=markup)
