"""
NexLoad Telegram Bot — Media Downloader Module
==============================================
Handles direct URL analysis, yt-dlp downloading, and sending media files back to Telegram chats.
Features:
  - Progress status messages with live updates
  - Interactive buttons after download (Back to Menu)
  - Clean error handling with actionable feedback
"""

import html
import mimetypes
import os, threading, time, tempfile, urllib.parse, shutil
import config

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

_cloud_runtime = bool(os.environ.get("RENDER") or os.environ.get("DYNO"))
_default_temp_dir = os.path.join(tempfile.gettempdir(), "NexLoadBot") if _cloud_runtime else os.path.join(config.BASE_DIR, "bot_temp")
TEMP_DIR = os.environ.get("BOT_TEMP_DIR", _default_temp_dir)
try:
    os.makedirs(TEMP_DIR, exist_ok=True)
except Exception:
    TEMP_DIR = os.path.join(tempfile.gettempdir(), "NexLoadBot")
    os.makedirs(TEMP_DIR, exist_ok=True)

YTDLP_CACHE_DIR = os.path.join(tempfile.gettempdir(), "nexload-bot-ytdlp-cache")
COOKIE_CACHE_DIR = os.path.join(tempfile.gettempdir(), "nexload-bot-cookies")
DOWNLOAD_COOLDOWN_SECONDS = int(os.environ.get("BOT_DOWNLOAD_COOLDOWN_SECONDS", "30"))
_last_download_by_user = {}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".avif"}
MEDIA_EXTS = IMAGE_EXTS | {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".mp3", ".m4a", ".wav"}


def _url_path(url):
    try:
        return urllib.parse.urlparse(url).path
    except Exception:
        return url


def _ext_from_url_or_path(value):
    return os.path.splitext(_url_path(value))[1].lower()


def _is_image_file(value):
    ext = _ext_from_url_or_path(value)
    if ext in IMAGE_EXTS:
        return True
    guessed, _ = mimetypes.guess_type(value)
    return bool(guessed and guessed.startswith("image/"))


def _get_cookies_file():
    candidates = [
        os.environ.get("YTDLP_COOKIES_FILE"),
        "/etc/secrets/cookies.txt",
        "/app/cookies.txt",
        os.path.join(config.BASE_DIR, "cookies.txt"),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


def _writable_cookiefile(path):
    if not path or not os.path.exists(path):
        return None
    try:
        os.makedirs(COOKIE_CACHE_DIR, exist_ok=True)
        dst = os.path.join(COOKIE_CACHE_DIR, "cookies.txt")
        if os.path.abspath(path) != os.path.abspath(dst):
            shutil.copyfile(path, dst)
        return dst
    except Exception:
        return path if os.access(path, os.W_OK) else None


def _apply_cookies(ydl_opts):
    ydl_opts.setdefault("cachedir", YTDLP_CACHE_DIR)
    cookiefile = _writable_cookiefile(_get_cookies_file())
    if cookiefile:
        ydl_opts["cookiefile"] = cookiefile


def _download_direct_url(media_url, prefix):
    import urllib.request as _urq

    ext = _ext_from_url_or_path(media_url)
    if ext not in MEDIA_EXTS:
        ext = ".jpg" if _is_image_file(media_url) else ".mp4"
    filename = os.path.join(TEMP_DIR, f"{prefix}_{int(time.time() * 1000)}{ext}")
    req = _urq.Request(media_url, headers={"User-Agent": "Mozilla/5.0"})
    with _urq.urlopen(req, timeout=45) as res, open(filename, "wb") as out:
        shutil.copyfileobj(res, out)
    return filename


def _extract_page_media_url(url):
    try:
        try:
            import requests
            res = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                timeout=15,
                allow_redirects=True,
            )
            page = res.text
        except Exception:
            import urllib.request as _urq
            req = _urq.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with _urq.urlopen(req, timeout=15) as res:
                page = res.read().decode("utf-8", errors="ignore")

        import re
        patterns = [
            r'<meta[^>]*property=["\']og:video:secure_url["\'][^>]*content=["\']([^"\']+)["\']',
            r'<meta[^>]*property=["\']og:video["\'][^>]*content=["\']([^"\']+)["\']',
            r'<meta[^>]*property=["\']og:image:secure_url["\'][^>]*content=["\']([^"\']+)["\']',
            r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']',
            r'"image_url"\s*:\s*"([^"]+)"',
            r'"url"\s*:\s*"(https:[^"]+\.(?:jpg|jpeg|png|webp|mp4)[^"]*)"',
        ]
        for pattern in patterns:
            match = re.search(pattern, page, re.IGNORECASE)
            if match:
                return html.unescape(match.group(1).replace("\\u002F", "/"))
    except Exception:
        return None
    return None


def _resolve_final_file(prepared_filename, info, started_at):
    candidates = []
    if isinstance(info, dict):
        for key in ("filepath", "_filename", "filename"):
            if info.get(key):
                candidates.append(info.get(key))
        for item in info.get("requested_downloads") or []:
            if isinstance(item, dict):
                for key in ("filepath", "_filename", "filename"):
                    if item.get(key):
                        candidates.append(item.get(key))
    if prepared_filename:
        candidates.append(prepared_filename)

    for path in candidates:
        if path and os.path.exists(path) and not path.endswith(".part"):
            return path

    media_id = str(info.get("id", "")) if isinstance(info, dict) else ""
    recent = []
    for name in os.listdir(TEMP_DIR):
        path = os.path.join(TEMP_DIR, name)
        if not os.path.isfile(path) or name.endswith(".part"):
            continue
        if _ext_from_url_or_path(path) not in MEDIA_EXTS:
            continue
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue
        if mtime < started_at - 5:
            continue
        if media_id and not name.startswith(media_id):
            continue
        recent.append((mtime, path))

    if recent:
        recent.sort(reverse=True)
        return recent[0][1]

    return None


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
                import yt_dlp
                ffmpeg_exe = shutil.which('ffmpeg')
                if not ffmpeg_exe:
                    try:
                        import imageio_ffmpeg
                        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
                    except Exception:
                        ffmpeg_exe = None

                out_tmpl = os.path.join(TEMP_DIR, f"%(id)s.%(ext)s")
                fmt_str = (
                    'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/'
                    'bestvideo[height<=720]+bestaudio/'
                    'best[height<=720][ext=mp4]/best[height<=720]/best[ext=mp4]/best'
                ) if ffmpeg_exe else 'best[height<=720][ext=mp4]/best[height<=720]/best[ext=mp4]/best'
                ydl_opts = {
                    'outtmpl': out_tmpl,
                    'format': fmt_str,
                    'quiet': True,
                    'no_warnings': True,
                    'noprogress': True,
                    'noplaylist': True,
                    'merge_output_format': 'mp4',
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36',
                        'Accept-Language': 'en-US,en;q=0.9',
                    },
                }
                _apply_cookies(ydl_opts)
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
                    started_at = time.time()
                    if _is_image_file(url):
                        filename = _download_direct_url(url, "bot_image")
                        info = {'title': 'Image'}
                    else:
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(url, download=True)
                            prepared = ydl.prepare_filename(info)
                            filename = _resolve_final_file(prepared, info, started_at)
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
                                    filename = _download_direct_url(play_url, f"bot_tiktok_{int(_tm.time())}")
                                    info = {'title': data['data'].get('title', 'TikTok Media')}
                    # Fallback 2: Pinterest or image post via og:video / og:image
                    elif 'pin.it/' in url or 'pinterest.com/' in url:
                        media_url = _extract_page_media_url(url)
                        if media_url:
                            filename = _download_direct_url(media_url, f"bot_pin_{int(_tm.time())}")
                            info = {'title': 'Pinterest Media'}
                    if not filename or not os.path.exists(filename):
                        raise ydl_err

                if filename and os.path.exists(filename):
                    size_mb = os.path.getsize(filename) / (1024 * 1024)
                    if size_mb <= 48:
                        send_method = bot.send_photo if _is_image_file(filename) else bot.send_video
                        bot.edit_message_text(
                            "⬆️ <b>Uploading video to Telegram...</b>\n"
                            f"📦 File size: <b>{size_mb:.1f} MB</b>",
                            message.chat.id,
                            status_msg.message_id,
                            parse_mode="HTML"
                        )
                        with open(filename, 'rb') as vf:
                            title = info.get('title', 'NexLoad Video')
                            try:
                                duration = int(info.get('duration') or 0)
                            except Exception:
                                duration = 0
                            send_method(
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
                full_error = str(e)
                if "Instagram sent an empty media response" in full_error or "cookies" in full_error.lower():
                    error_msg = "Instagram requires logged-in cookies for this link. Set YTDLP_COOKIES_FILE to a valid cookies.txt file on the server."
                else:
                    error_msg = full_error[:200]
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
