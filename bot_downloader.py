"""
NexLoad Telegram Bot — Media Downloader Module
==============================================
Handles direct URL analysis, yt-dlp downloading, and sending media files back to Telegram chats.
Functions:
  - register_downloader_handlers: Registers URL message handlers
  - download_and_send_media: Background worker thread for downloading and uploading videos
"""

import os, threading
import config

TEMP_DIR = os.path.join(config.BASE_DIR, "bot_temp")
os.makedirs(TEMP_DIR, exist_ok=True)

def register_downloader_handlers(bot):
    """Registers URL downloading handlers to the bot instance."""

    @bot.message_handler(func=lambda m: m.text and (m.text.startswith("http://") or m.text.startswith("https://")))
    def on_url_message(message):
        url = message.text.strip().split()[0]
        status_msg = bot.reply_to(
            message,
            "⏳ *Analyzing video link...*\nDownloading file in progress. Please wait a moment.",
            parse_mode="Markdown"
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
                            "⬆️ *Uploading video directly to Telegram...*",
                            message.chat.id,
                            status_msg.message_id,
                            parse_mode="Markdown"
                        )
                        with open(filename, 'rb') as vf:
                            title = info.get('title', 'NexLoad Video')
                            bot.send_video(
                                message.chat.id,
                                vf,
                                caption=f"🎬 *{title}*\n⚡ Downloaded via NexLoad Cloud",
                                parse_mode="Markdown",
                                reply_to_message_id=message.message_id
                            )
                        bot.delete_message(message.chat.id, status_msg.message_id)
                    else:
                        bot.edit_message_text(
                            f"⚠️ *Video too large ({size_mb:.1f} MB)*\n"
                            "Telegram bots can only upload files up to 50 MB directly. Please use the NexLoad Web App or PC App to download large/4K files!",
                            message.chat.id,
                            status_msg.message_id,
                            parse_mode="Markdown"
                        )
                    try:
                        os.remove(filename)
                    except Exception:
                        pass
                else:
                    bot.edit_message_text("❌ Failed to download video file.", message.chat.id, status_msg.message_id)
            except Exception as e:
                bot.edit_message_text(
                    f"❌ *Download Failed*: {str(e)[:150]}",
                    message.chat.id,
                    status_msg.message_id,
                    parse_mode="Markdown"
                )

        threading.Thread(target=worker, daemon=True).start()
