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
    markup = InlineKeyboardMarkup(row_width=1)
    markup.row(InlineKeyboardButton("🖥 Need YouTube? Get Desktop App", url="https://github.com/Vathanak168/NexLoad/releases"))
    markup.row(InlineKeyboardButton("🔑 My Access", callback_data="nav:validate_prompt"), InlineKeyboardButton("🏠 Main Menu", callback_data="nav:main"))
    return markup


def _kb_error():
    """Keyboard shown after download error."""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.row(InlineKeyboardButton("🌐 Open Web App", url="https://nexload-k7h6.onrender.com/"), InlineKeyboardButton("🖥 Desktop App", url="https://github.com/Vathanak168/NexLoad/releases"))
    markup.row(InlineKeyboardButton("↩️ Main Menu", callback_data="nav:main"))
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
        if 'youtube.com' in url.lower() or 'youtu.be' in url.lower():
            kb_yt = InlineKeyboardMarkup(row_width=1)
            kb_yt.row(InlineKeyboardButton("🖥 Download Desktop App", url="https://github.com/Vathanak168/NexLoad/releases"))
            kb_yt.row(InlineKeyboardButton("🌐 Open Web App", url="https://nexload-k7h6.onrender.com/"))
            bot.reply_to(
                message,
                "📺 <b>YouTube Download — Desktop App Required</b>\n\n"
                "YouTube blocks cloud servers. To download YouTube videos reliably, please use our standalone Desktop App on your computer!",
                parse_mode="HTML",
                reply_markup=kb_yt,
                disable_web_page_preview=True
            )
            return

        status_msg = bot.reply_to(
            message,
            "🔎 <b>Checking link & reading media info...</b>\n"
            "⚡ Please wait a moment.",
            parse_mode="HTML"
        )

        def worker():
            try:
                import yt_dlp, shutil
                ffmpeg_exe = shutil.which('ffmpeg')
                if not ffmpeg_exe:
                    try:
                        import imageio_ffmpeg
                        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
                    except Exception:
                        ffmpeg_exe = None

                out_tmpl = os.path.join(TEMP_DIR, f"%(id)s.%(ext)s")
                fmt_str = 'bestvideo[ext=mp4][filesize<48M]+bestaudio[ext=m4a]/best[ext=mp4][filesize<48M]/best[filesize<48M]' if ffmpeg_exe else 'best[ext=mp4][filesize<48M]/best[filesize<48M]'
                ydl_opts = {
                    'outtmpl': out_tmpl,
                    'format': fmt_str,
                    'quiet': True,
                    'no_warnings': True
                }
                if ffmpeg_exe:
                    ydl_opts['ffmpeg_location'] = ffmpeg_exe
                try:
                    bot.edit_message_text(
                        "⬇️ <b>Downloading media...</b>\n⚡ Extracting best quality under 50 MB.",
                        message.chat.id,
                        status_msg.message_id,
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
                filename = None
                info = {}
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        filename = ydl.prepare_filename(info)
                except Exception as ydl_err:
                    import urllib.request as _urq, json as _js, re as _re, time as _tm
                    # Fallback 1: TikTok via TikWM
                    if 'tiktok.com' in url:
                        req = _urq.Request(f"https://www.tikwm.com/api/?url={url}", headers={'User-Agent': 'Mozilla/5.0'})
                        with _urq.urlopen(req) as res:
                            data = _js.loads(res.read().decode())
                            if data.get('code') == 0 and data.get('data'):
                                play_url = data['data'].get('play') or data['data'].get('wmplay')
                                if not play_url and data['data'].get('images'):
                                    play_url = data['data']['images'][0]
                                if play_url:
                                    ext = '.mp4' if '.mp4' in play_url else '.jpg'
                                    filename = os.path.join(TEMP_DIR, f"bot_tiktok_{int(_tm.time())}{ext}")
                                    _urq.urlretrieve(play_url, filename)
                                    info = {'title': data['data'].get('title', 'TikTok Media')}
                    # Fallback 2: Pinterest or image post via og:video / og:image
                    elif 'pin.it/' in url or 'pinterest.com/' in url:
                        req = _urq.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                        with _urq.urlopen(req) as res:
                            html = res.read().decode('utf-8', errors='ignore')
                            m_vid = _re.search(r'<meta[^>]*property=["\']og:video["\'][^>]*content=["\']([^"\']+)["\']', html)
                            m_img = _re.search(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html)
                            media_url = m_vid.group(1) if m_vid else (m_img.group(1) if m_img else None)
                            if media_url:
                                ext = '.mp4' if '.mp4' in media_url else '.jpg'
                                filename = os.path.join(TEMP_DIR, f"bot_pin_{int(_tm.time())}{ext}")
                                _urq.urlretrieve(media_url, filename)
                                info = {'title': 'Pinterest Media'}
                    if not filename or not os.path.exists(filename):
                        raise ydl_err

                if filename and os.path.exists(filename):
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
