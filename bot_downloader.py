"""
NexLoad Telegram Bot — Media Downloader Module
==============================================
Handles direct URL analysis, yt-dlp downloading, and sending media files back to Telegram chats.
Features:
  - Progress status messages with live updates
  - Interactive buttons after download (Back to Menu)
  - Clean error handling with actionable feedback
"""

import os, threading, time
import config

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TEMP_DIR = os.path.join(config.BASE_DIR, "bot_temp")
os.makedirs(TEMP_DIR, exist_ok=True)
DOWNLOAD_COOLDOWN_SECONDS = int(os.environ.get("BOT_DOWNLOAD_COOLDOWN_SECONDS", "30"))
_last_download_by_user = {}


def _kb_after_download():
    """Keyboard shown after successful download."""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.row(
        InlineKeyboardButton("🔑 Get License Key", callback_data="nav:getkey"),
        InlineKeyboardButton("📊 Server Stats", callback_data="nav:stats")
    )
    markup.row(InlineKeyboardButton("↩️ Main Menu", callback_data="nav:main"))
    return markup


def _kb_error():
    """Keyboard shown after download error."""
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("↩️ Back to Menu", callback_data="nav:main"))
    return markup


def register_downloader_handlers(bot):
    """Registers URL downloading handlers to the bot instance."""

    @bot.message_handler(func=lambda m: m.text and (m.text.startswith("http://") or m.text.startswith("https://")))
    def on_url_message(message):
        user_id = str(message.from_user.id)
        now = time.time()
        last = _last_download_by_user.get(user_id, 0)
        if now - last < DOWNLOAD_COOLDOWN_SECONDS:
            wait = int(DOWNLOAD_COOLDOWN_SECONDS - (now - last))
            bot.reply_to(message, f"⏳ Please wait {wait}s before starting another bot download.", parse_mode="HTML")
            return
        _last_download_by_user[user_id] = now

        url = message.text.strip().split()[0]
        status_msg = bot.reply_to(
            message,
            "⏳ <b>Analyzing video link...</b>\n"
            "🔄 Downloading file in progress. Please wait.",
            parse_mode="HTML"
        )

        def worker():
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
                        bot.edit_message_text(
                            "⬆️ <b>Uploading video to Telegram...</b>\n"
                            f"📦 File size: <b>{size_mb:.1f} MB</b>",
                            message.chat.id,
                            status_msg.message_id,
                            parse_mode="HTML"
                        )
                        with open(filename, 'rb') as vf:
                            title = info.get('title', 'NexLoad Video')
                            duration = info.get('duration', 0)
                            bot.send_video(
                                message.chat.id,
                                vf,
                                caption=(
                                    f"🎬 <b>{title}</b>\n"
                                    f"📦 Size: {size_mb:.1f} MB"
                                    f"{f' | ⏱ {duration//60}:{duration%60:02d}' if duration else ''}\n"
                                    f"⚡ Downloaded via <b>NexLoad Cloud</b>"
                                ),
                                parse_mode="HTML",
                                reply_to_message_id=message.message_id
                            )
                        # Delete the status message and send completion with menu
                        try:
                            bot.delete_message(message.chat.id, status_msg.message_id)
                        except Exception:
                            pass

                        bot.send_message(
                            message.chat.id,
                            "✅ <b>Download Complete!</b>\n\n"
                            "💡 <i>Paste another URL to download more, or use the buttons below.</i>",
                            parse_mode="HTML",
                            reply_markup=_kb_after_download()
                        )
                    else:
                        bot.edit_message_text(
                            f"⚠️ <b>Video Too Large ({size_mb:.1f} MB)</b>\n\n"
                            "Telegram bots can only upload files up to 50 MB.\n"
                            "Please use the <b>NexLoad Web App</b> or <b>Desktop App</b> "
                            "to download large/4K files!",
                            message.chat.id,
                            status_msg.message_id,
                            parse_mode="HTML",
                            reply_markup=_kb_error()
                        )
                    try:
                        os.remove(filename)
                    except Exception:
                        pass
                else:
                    bot.edit_message_text(
                        "❌ <b>Download Failed</b>\n\n"
                        "Could not save the video file. Try a different URL.",
                        message.chat.id,
                        status_msg.message_id,
                        parse_mode="HTML",
                        reply_markup=_kb_error()
                    )
            except Exception as e:
                error_msg = str(e)[:200]
                bot.edit_message_text(
                    f"❌ <b>Download Failed</b>\n\n"
                    f"<i>{error_msg}</i>\n\n"
                    "💡 <b>Tips:</b>\n"
                    "• Make sure the URL is correct and publicly accessible\n"
                    "• Some sites may restrict bot access\n"
                    "• Try the NexLoad Web App for better compatibility",
                    message.chat.id,
                    status_msg.message_id,
                    parse_mode="HTML",
                    reply_markup=_kb_error()
                )

        threading.Thread(target=worker, daemon=True).start()
