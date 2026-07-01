"""
NexLoad Server v4.0 — Commercial Edition
Python + Flask + yt-dlp backend
Supports: YouTube, TikTok, Instagram, Facebook, Pinterest, Twitter/X, 1000+ more
Features: License auth, stats, custom folder, subtitles, speed limiter
"""

import os, sys, json, uuid, threading, time, shutil, re, hmac, hashlib, datetime
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import yt_dlp
import requests

try:
    import config
    HOST = config.HOST
    PORT = config.PORT
    SECRET_KEY = config.SECRET_KEY
except ImportError:
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", 5000))
    SECRET_KEY = b"NexLoad-Secret-2026-ChangeThis-To-Something-Unique"

# ── HWID & Validation config ──────────────────────────────────────
ADMIN_SERVER_URL = os.environ.get("ADMIN_SERVER_URL", "http://127.0.0.1:5050")

def get_hwid():
    """Generate a unique Machine ID based on MAC address"""
    mac = uuid.getnode()
    return f"PC-{mac:X}"[-12:]

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LICENSE_DB_PATH = os.path.join(_BASE_DIR, 'licenses.json')
STATS_PATH      = os.path.join(_BASE_DIR, 'stats.json')

def _validate_license(full_key: str) -> dict:
    """Validate license locally using licenses.json"""
    hwid = get_hwid()
    
    if not full_key:
        return {'valid': False, 'reason': 'Key missing. Please enter your license.', 'hwid': hwid}
        
    try:
        if not os.path.exists(LICENSE_DB_PATH):
            return {'valid': False, 'reason': 'License database not found.', 'hwid': hwid}
            
        with open(LICENSE_DB_PATH, "r", encoding="utf-8") as f:
            db = json.load(f)
            
        if full_key not in db:
            return {'valid': False, 'reason': 'Key not found in system', 'hwid': hwid}
            
        rec = db[full_key]
        
        if not rec.get('active'):
            return {'valid': False, 'reason': 'Key has been revoked or banned', 'hwid': hwid}
            
        # Check HWID Lock if it exists on the key
        if rec.get('hwid') and rec.get('hwid') != hwid:
            return {'valid': False, 'reason': 'Device Mismatch! This key belongs to another PC.', 'hwid': hwid}
            
        # Verify Cryptographic Signature
        SECRET_KEY = b"NexLoad-Secret-2026-ChangeThis-To-Something-Unique"
        sig16 = hmac.new(SECRET_KEY, rec['key_body'].encode(), hashlib.sha256).hexdigest()[:16].upper()
        sig4 = hmac.new(SECRET_KEY, rec['key_body'].encode(), hashlib.sha256).hexdigest()[:4].upper()
        sig6 = hmac.new(SECRET_KEY, rec['key_body'].encode(), hashlib.sha256).hexdigest()[:6].upper()
        
        if rec.get('signature') not in [sig16, sig6, sig4]:
            return {'valid': False, 'reason': 'Key Signature Invalid (Tampered)', 'hwid': hwid}
            
        expire_dt = datetime.datetime.fromisoformat(rec['expires'])
        now = datetime.datetime.now(datetime.timezone.utc)
        days_left = (expire_dt - now).days
        
        if days_left < 0:
            return {'valid': False, 'reason': f'Key expired {-days_left} days ago', 'hwid': hwid}
            
        TIERS = {
            "trial":    {"label": "Trial"},
            "basic":    {"label": "Basic"},
            "pro":      {"label": "Pro"},
            "lifetime": {"label": "Lifetime"},
        }
            
        return {
            'valid':       True,
            'reason':      'OK',
            'key':         full_key,
            'hwid':        hwid,
            'tier':        rec['tier'],
            'tier_label':  TIERS.get(rec['tier'], {}).get('label', rec['tier']),
            'user':        rec.get('user', 'Unknown'),
            'expires':     rec['expires'],
            'days_left':   days_left,
            'daily_limit': rec.get('daily_limit', 0),
            'batch':       rec.get('batch', True),
        }
    except Exception as e:
        return {'valid': False, 'reason': f'Validation Error: {str(e)}', 'hwid': hwid}

# ── Stats tracking ────────────────────────────────────────────────
def _load_stats():
    if os.path.exists(STATS_PATH):
        with open(STATS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'total_downloads': 0, 'total_bytes': 0, 'by_platform': {}, 'by_day': {}}

def _save_stats(stats):
    with open(STATS_PATH, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2)

def _record_download(platform='unknown', file_size=0):
    try:
        stats = _load_stats()
        stats['total_downloads'] = stats.get('total_downloads', 0) + 1
        stats['total_bytes'] = stats.get('total_bytes', 0) + file_size
        bp = stats.setdefault('by_platform', {})
        bp[platform] = bp.get(platform, 0) + 1
        day = datetime.datetime.utcnow().strftime('%Y-%m-%d')
        bd = stats.setdefault('by_day', {})
        bd[day] = bd.get(day, 0) + 1
        _save_stats(stats)
    except Exception:
        pass

# ── Optional: requests for direct image URLs ──────────────────────
try:
    import requests as _requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.avif', '.bmp', '.tiff', '.svg'}


# ── tikwm.com free API — supports TikTok photo/slideshow posts ────
def _clean_tiktok_url(url):
    """Strip tracking query params from TikTok URL for cleaner API requests."""
    from urllib.parse import urlparse, urlunparse
    p = urlparse(url)
    # Keep only scheme + netloc + path (drop ?_r=1&_t=... tracking params)
    return urlunparse((p.scheme, p.netloc, p.path, '', '', ''))


def _tikwm_fetch(url):
    """
    Fetch TikTok media info via tikwm.com free API.
    Handles /photo/ slideshow posts that yt-dlp cannot extract.
    Returns the 'data' dict on success, or None on failure.
    """
    if not HAS_REQUESTS:
        print('  ⚠️  tikwm: requests library not available')
        return None

    clean_url = _clean_tiktok_url(url)
    print(f'\n  🔍 tikwm: requesting → {clean_url}')

    # ── Attempt 1: tikwm.com ──────────────────────────────────────
    try:
        resp = _requests.post(
            'https://www.tikwm.com/api/',
            data={'url': clean_url, 'hd': '1'},
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept':     'application/json, text/plain, */*',
                'Referer':    'https://www.tikwm.com/',
            },
            timeout=20,
        )
        print(f'  tikwm HTTP {resp.status_code}')
        payload = resp.json()
        print(f'  tikwm code={payload.get("code")}  msg={payload.get("msg")}')
        if payload.get('code') == 0 and payload.get('data'):
            print('  ✅ tikwm success')
            return payload['data']
        print(f'  ❌ tikwm non-zero code, trying fallback...')
    except Exception as e:
        print(f'  ❌ tikwm error: {e}')

    # ── Attempt 2: douyin.wtf API ─────────────────────────────────
    try:
        resp2 = _requests.get(
            'https://api.douyin.wtf/api',
            params={'url': clean_url, 'minimal': 'false'},
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=20,
        )
        print(f'  douyin.wtf HTTP {resp2.status_code}')
        d2 = resp2.json()
        images = d2.get('images') or d2.get('image_list') or []
        title  = d2.get('title') or d2.get('desc') or 'TikTok Slideshow'
        cover  = d2.get('cover') or (images[0] if images else '')
        if images:
            print(f'  ✅ douyin.wtf success: {len(images)} images')
            return {'title': title, 'cover': cover, 'images': images}
        print(f'  ❌ douyin.wtf: no images in response')
    except Exception as e:
        print(f'  ❌ douyin.wtf error: {e}')

    print('  ❌ All TikTok photo APIs failed')
    return None


def _is_any_tiktok(url):
    """
    Return True for ANY TikTok URL:
      - tiktok.com/@user/video/ID   (normal video)
      - tiktok.com/@user/photo/ID   (slideshow)
      - vt.tiktok.com/XXXXX/        (short link — could be either!)
    """
    return 'tiktok.com' in url  # covers tiktok.com + vt.tiktok.com + vm.tiktok.com


def _download_image_bytes(img_url, out_path, task_id, progress_base=0, progress_max=95, total_imgs=1, img_idx=0):
    """Download a single image URL to out_path, updating tasks[task_id] progress."""
    r = _requests.get(img_url, timeout=30, headers={'User-Agent': 'Mozilla/5.0'})
    r.raise_for_status()
    with open(out_path, 'wb') as f:
        f.write(r.content)
    pct = int(progress_base + ((img_idx + 1) / total_imgs) * (progress_max - progress_base))
    tasks[task_id].update({'progress': pct})



app = Flask(__name__, static_folder=_BASE_DIR, static_url_path='')
CORS(app)

# ── Serve the UI from root ────────────────────────────────────────
@app.route('/')
def index():
    from flask import send_from_directory
    return send_from_directory(_BASE_DIR, 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    from flask import send_from_directory
    safe_exts = {'.html', '.js', '.css', '.png', '.jpg', '.ico', '.svg', '.webp'}
    import os as _os
    ext = _os.path.splitext(filename)[1].lower()
    if ext in safe_exts:
        return send_from_directory(_BASE_DIR, filename)
    from flask import abort
    abort(404)

# ── Detect ffmpeg (local project folder first, then system PATH) ──
_BASE = os.path.dirname(os.path.abspath(__file__))
_LOCAL_FFMPEG = os.path.join(_BASE, 'ffmpeg', 'bin', 'ffmpeg.exe')

if os.path.exists(_LOCAL_FFMPEG):
    FFMPEG_PATH = _LOCAL_FFMPEG
    print(f'  ✅ ffmpeg found (local): {FFMPEG_PATH}')
else:
    FFMPEG_PATH = shutil.which('ffmpeg')
    if FFMPEG_PATH:
        print(f'  ✅ ffmpeg found (system): {FFMPEG_PATH}')
    else:
        print('  ⚠️  ffmpeg NOT found — max quality: 720p')
        print('      Run setup_ffmpeg.bat to install automatically!')

# ── Download destination ──────────────────────────────────────────
DEFAULT_DOWNLOAD_DIR = os.path.join(os.path.expanduser('~'), 'Downloads', 'NexLoad')
os.makedirs(DEFAULT_DOWNLOAD_DIR, exist_ok=True)

CUSTOM_FOLDER_PATH = os.path.join(_BASE_DIR, 'custom_folder.txt')
def get_download_dir():
    if os.path.exists(CUSTOM_FOLDER_PATH):
        with open(CUSTOM_FOLDER_PATH, 'r', encoding='utf-8') as f:
            d = f.read().strip()
        if d and os.path.isdir(d):
            return d
    return DEFAULT_DOWNLOAD_DIR

DOWNLOAD_DIR = get_download_dir()

# ── In-memory task store ──────────────────────────────────────────
tasks = {}  # task_id → { status, progress, speed, eta, filename, error }


# ─────────────────────────────────────────────────────────────────
# ROUTE: GET /api/info?url=...
# Returns video metadata: title, channel, thumbnail, duration, formats
# ─────────────────────────────────────────────────────────────────
@app.route('/api/info')
def get_info():
    url = request.args.get('url', '').strip()
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    # ── Intercept Pexels before yt-dlp (which fails via Cloudflare 403) ──
    if 'pexels.com' in url.lower():
        return jsonify({
            'title':          'Pexels Media',
            'channel':        '',
            'thumbnail':      '',
            'duration':       '',
            'views':          '',
            'platform':       'Pexels',
            'webpage_url':    url,
            'formats':        [],
            'isImageCandidate': True,
        })

    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'extract_flat': 'in_playlist',
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        # Collect unique video heights
        heights = set()
        for f in (info.get('formats') or []):
            h = f.get('height')
            vc = f.get('vcodec', 'none')
            if h and vc and vc != 'none' and h >= 144:
                heights.add(h)

        all_heights = sorted(heights, reverse=True)   # e.g. [4320, 2160, 1440, 1080, 720, 480]
        max_height  = all_heights[0] if all_heights else 0

        # Quality name mapping
        def _q_label(h):
            if h >= 4320: return f'{h}p (8K)'
            if h >= 2160: return f'{h}p (4K)'
            if h >= 1440: return f'{h}p (2K)'
            if h == 1080: return '1080p (FHD)'
            # 1081–1439: non-standard (e.g. 1280p portrait) — show exact height
            return f'{h}p'

        # Only expose 1080p+ options (hide 720p / 480p / etc.)
        high_heights = [h for h in all_heights if h >= 1080]

        if high_heights:
            fmt_list = [{'label': _q_label(h), 'height': h} for h in high_heights[:6]]
        elif all_heights:
            # Video max < 1080p — show one "Best Available" entry so user isn't stuck
            best = all_heights[0]
            fmt_list = [{'label': f'{best}p (Best Available)', 'height': best, 'best_only': True}]
        else:
            fmt_list = []
            
        # ── Playlist / Profile Support ──
        is_playlist = False
        playlist_count = 0
        if info.get('_type') in ['playlist', 'multi_video']:
            is_playlist = True
            entries = info.get('entries') or []
            # some extractors return generator, try to count if it's a list
            playlist_count = len(list(entries)) if isinstance(entries, list) else info.get('playlist_count', 0)
            if not fmt_list:
                fmt_list = [{'label': f'Download All Videos (Best Quality)', 'height': '1080', 'best_only': True}]

        # Duration string
        dur = info.get('duration')
        dur_str = ''
        if dur:
            m, s = divmod(int(dur), 60)
            h2, m2 = divmod(m, 60)
            dur_str = f'{h2}:{m2:02d}:{s:02d}' if h2 else f'{m2}:{s:02d}'

        # Views format
        views = info.get('view_count') or 0
        views_str = f'{views:,}' if views else '—'

        return jsonify({
            'title':      info.get('title', 'Unknown'),
            'channel':    info.get('uploader') or info.get('channel') or '',
            'thumbnail':  info.get('thumbnail') or '',
            'duration':   dur_str,
            'views':      views_str,
            'platform':   info.get('extractor_key', ''),
            'webpage_url': info.get('webpage_url', url),
            'formats':    fmt_list,
            'max_height': max_height,   # 🆕 for frontend MAX badge
            'is_playlist': is_playlist,
            'playlist_count': playlist_count,
        })

    except yt_dlp.utils.DownloadError as e:
        msg = str(e)
        # 🆕 "Unsupported URL" or cloudflare 403 usually means it's an image/photo post 
        # Return empty formats + candidate flag so frontend tries /api/image-info instead
        if 'Unsupported URL' in msg or 'unsupported url' in msg.lower() or 'HTTP Error 403' in msg:
            return jsonify({
                'title':          'Unknown',
                'channel':        '',
                'thumbnail':      '',
                'duration':       '',
                'views':          '',
                'platform':       '',
                'webpage_url':    url,
                'formats':        [],
                'isImageCandidate': True,
            })
        msg = msg.replace('[youtube]', '').strip()
        return jsonify({'error': msg}), 422
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────
# ROUTE: GET /api/image-info?url=...
# Sniff URL to detect: direct image OR platform post with images
# ─────────────────────────────────────────────────────────────────
@app.route('/api/image-info')
def get_image_info():
    url = request.args.get('url', '').strip()
    if not url:
        return jsonify({'error': 'URL required'}), 400

    # Check if it's a direct image URL by extension or Content-Type
    from urllib.parse import urlparse
    parsed = urlparse(url)
    ext = os.path.splitext(parsed.path)[1].lower()

    if ext in IMAGE_EXTS:
        # Direct image URL
        filename = os.path.basename(parsed.path) or 'image' + ext
        return jsonify({
            'type':      'direct',
            'filename':  filename,
            'ext':       ext.lstrip('.'),
            'thumbnail': url,
            'title':     filename,
        })

    # Try HEAD request to sniff Content-Type
    if HAS_REQUESTS:
        try:
            head = _requests.head(url, timeout=5, allow_redirects=True,
                                  headers={'User-Agent': 'Mozilla/5.0'})
            ct = head.headers.get('Content-Type', '')
            if any(t in ct for t in ('image/', 'jpeg', 'png', 'gif', 'webp')):
                ext2 = ct.split('/')[-1].split(';')[0].strip()
                fname = f'image.{ext2}'
                return jsonify({
                    'type':      'direct',
                    'filename':  fname,
                    'ext':       ext2,
                    'thumbnail': url,
                    'title':     fname,
                })
        except Exception:
            pass

    # ── Pexels photo (parses ID directly to get original image) ──
    if 'pexels.com/photo/' in url:
        m = re.search(r'(?:photo/[^/]+-|/photo/)(\d+)/?', url)
        if m:
            pid = m.group(1)
            img_url = f"https://images.pexels.com/photos/{pid}/pexels-photo-{pid}.jpeg"
            return jsonify({
                'type':      'direct',
                'filename':  f'Pexels_{pid}.jpg',
                'ext':       'jpg',
                'thumbnail': img_url,
                'title':     f'Pexels Photo {pid}'
            })

    # ── TikTok slideshow — tikwm.com API (handles /photo/ AND short vt.tiktok.com links) ──
    if _is_any_tiktok(url) and HAS_REQUESTS:
        td = _tikwm_fetch(url)
        if td:
            images = td.get('images', [])  # list of image URLs for slideshow
            title  = td.get('title') or 'TikTok Slideshow'
            cover  = td.get('cover') or (images[0] if images else '')
            imgs   = [
                {'url': img, 'thumb': img, 'title': f'Slide {i+1}'}
                for i, img in enumerate(images)
            ]
            return jsonify({
                'type':      'slideshow',
                'platform':  'TikTok',
                'title':     title,
                'thumbnail': cover,
                'count':     len(imgs),
                'images':    imgs,
                'is_image':  True,
                'source':    'tikwm',
            })
        # tikwm failed — fall through to yt-dlp strategies below

    # Try yt-dlp for platform image posts (Instagram, Pinterest, Twitter, Reddit, TikTok...)
    # Strategy 1: Standard yt-dlp
    ydl_base_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}

    # Strategy 2: Force-generic extractor (helps with TikTok /photo/ slideshow URLs)
    ydl_generic_opts = {
        'quiet': True, 'no_warnings': True, 'skip_download': True,
        'force_generic_extractor': True,
    }

    # Strategy 3: With extra TikTok options
    ydl_tiktok_opts = {
        'quiet': True, 'no_warnings': True, 'skip_download': True,
        'extractor_args': {'tiktok': {'api_hostname': 'api16-normal-c-useast1a.tiktokv.com'}},
    }

    info = None
    strategies = [ydl_base_opts, ydl_tiktok_opts]
    last_err = None

    for opts in strategies:
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            break  # success
        except Exception as e:
            last_err = e
            info = None

    if info is not None:
        # Detect image post: no duration or duration==0
        is_image = not info.get('duration') or info.get('duration') == 0
        imgs = []
        if info.get('entries'):  # carousel / album
            for e in info['entries'][:20]:
                if e.get('thumbnail') or e.get('url'):
                    imgs.append({
                        'url':   e.get('url') or e.get('thumbnail'),
                        'thumb': e.get('thumbnail', ''),
                        'title': e.get('title', ''),
                    })
        else:
            imgs.append({
                'url':   info.get('url') or info.get('thumbnail'),
                'thumb': info.get('thumbnail', ''),
                'title': info.get('title', ''),
            })

        return jsonify({
            'type':       'platform',
            'platform':   info.get('extractor_key', ''),
            'title':      info.get('title', 'Image Post'),
            'thumbnail':  info.get('thumbnail', ''),
            'count':      len(imgs),
            'images':     imgs,
            'is_image':   is_image,
        })

    # 🆕 Strategy 3 (last resort): For TikTok /photo/ URLs, try to sniff thumbnail via HEAD request
    # yt-dlp can't extract slideshow posts — return a minimal candidate so download can try
    from urllib.parse import urlparse as _up
    _parsed = _up(url)
    is_tiktok_photo = 'tiktok.com' in _parsed.netloc and '/photo/' in _parsed.path

    if is_tiktok_photo:
        return jsonify({
            'type':       'candidate',
            'platform':   'TikTok',
            'title':      'TikTok Photo / Slideshow',
            'thumbnail':  '',
            'count':      0,
            'images':     [],
            'is_image':   True,
            'note':       'TikTok slideshow — will attempt best-effort download',
        })

    return jsonify({'error': str(last_err)}), 422


# ─────────────────────────────────────────────────────────────────
# ROUTE: POST /api/download
# Body: { url, quality, mode }   mode: 'video' | 'audio' | 'image'
# Returns: { task_id }
# ─────────────────────────────────────────────────────────────────
@app.route('/api/download', methods=['POST'])
def start_download():
    data        = request.get_json() or {}
    url         = data.get('url', '').strip()
    quality     = str(data.get('quality', '1080')).replace('p', '')
    mode        = data.get('mode', 'video')    # 'video' | 'audio' | 'image'
    direct_urls = data.get('direct_urls', [])  # selective slideshow images
    dl_title    = data.get('title', '')        # title for file naming
    subtitles   = data.get('subtitles', False) # download subtitles
    sub_lang    = data.get('sub_lang', 'en')   # subtitle language
    speed_limit = data.get('speed_limit', '')  # e.g. '1M', '500K'

    if not url:
        return jsonify({'error': 'URL is required'}), 400

    # Refresh download dir in case it was changed
    DOWNLOAD_DIR = get_download_dir()
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    task_id = uuid.uuid4().hex[:8]
    tasks[task_id] = {
        'status':   'starting',
        'progress': 0,
        'speed':    '',
        'eta':      '',
        'size':     '',
        'filename': '',
        'filepath': '',
        'error':    None,
    }

    def progress_hook(d):
        t = tasks[task_id]
        if d['status'] == 'downloading':
            total  = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            done   = d.get('downloaded_bytes', 0)
            pct    = int(done / total * 100) if total else 0
            t.update({
                'status':   'downloading',
                'progress': pct,
                'speed':    d.get('_speed_str', '').strip(),
                'eta':      d.get('_eta_str', '').strip(),
                'size':     d.get('_total_bytes_str', '').strip() or d.get('_total_bytes_estimate_str', '').strip(),
                'filename': os.path.basename(d.get('filename', '')),
            })
        elif d['status'] == 'finished':
            t.update({
                'status':   'processing',
                'progress': 99,
                'filepath': d.get('filename', ''),
                'filename': os.path.basename(d.get('filename', '')),
            })

    def run():
        nonlocal url
        try:
            # ── IMAGE MODE ────────────────────────────────────────
            if mode == 'image':

                # ── Selective slideshow download via direct_urls[] ───────────
                if direct_urls and HAS_REQUESTS:
                    safe_t = re.sub(r'[^\w.\-]', '_', dl_title or 'slideshow')[:50]
                    tasks[task_id].update({
                        'status':   'downloading',
                        'filename': f'{safe_t} ({len(direct_urls)} selected)',
                    })
                    n = len(direct_urls)
                    for i, img_url in enumerate(direct_urls):
                        tasks[task_id].update({'progress': int((i / n) * 95)})
                        low = img_url.lower()
                        img_ext = '.jpg'
                        if 'png'  in low: img_ext = '.png'
                        elif 'webp' in low: img_ext = '.webp'
                        fname    = f'{safe_t}_slide{i+1:02d}{img_ext}'
                        out_path = os.path.join(DOWNLOAD_DIR, fname)
                        r = _requests.get(img_url, timeout=30,
                                          headers={'User-Agent': 'Mozilla/5.0'})
                        r.raise_for_status()
                        with open(out_path, 'wb') as f:
                            f.write(r.content)
                    tasks[task_id].update({
                        'status':   'done', 'progress': 100,
                        'filename': f'{safe_t} — {n} image(s) saved',
                    })
                    return

                from urllib.parse import urlparse
                parsed  = urlparse(url)
                ext     = os.path.splitext(parsed.path)[1].lower()
                is_direct = ext in IMAGE_EXTS

                # ── Custom URL mapping for Pexels to direct image ──
                if 'pexels.com/photo/' in url:
                    m = re.search(r'(?:photo/[^/]+-|/photo/)(\d+)/?', url)
                    if m:
                        pid = m.group(1)
                        url = f"https://images.pexels.com/photos/{pid}/pexels-photo-{pid}.jpeg"
                        is_direct = True
                        ext = '.jpg'

                # Also sniff Content-Type for direct detection
                if not is_direct and HAS_REQUESTS:
                    try:
                        head = _requests.head(url, timeout=4, allow_redirects=True,
                                              headers={'User-Agent': 'Mozilla/5.0'})
                        ct = head.headers.get('Content-Type', '')
                        if any(t in ct for t in ('image/', 'jpeg', 'png', 'gif', 'webp')):
                            is_direct = True
                            ext = '.' + ct.split('/')[-1].split(';')[0].strip()
                    except Exception:
                        pass

                if is_direct and HAS_REQUESTS:
                    # Direct image download via requests with progress
                    safe_name = os.path.basename(parsed.path) or f'image{ext or ".jpg"}'
                    safe_name = re.sub(r'[^\w.\-]', '_', safe_name)
                    out_path  = os.path.join(DOWNLOAD_DIR, safe_name)
                    resp = _requests.get(url, stream=True, timeout=30,
                                         headers={'User-Agent': 'Mozilla/5.0'})
                    resp.raise_for_status()
                    total = int(resp.headers.get('Content-Length', 0))
                    done  = 0
                    tasks[task_id].update({'status': 'downloading', 'filename': safe_name})
                    with open(out_path, 'wb') as f:
                        for chunk in resp.iter_content(8192):
                            if chunk:
                                f.write(chunk)
                                done += len(chunk)
                                pct = int(done / total * 100) if total else 50
                                tasks[task_id].update({
                                    'progress': pct,
                                    'size':     f'{done // 1024} KB',
                                })
                    tasks[task_id].update({
                        'status': 'done', 'progress': 100,
                        'filepath': out_path, 'filename': safe_name,
                    })
                    return

                else:
                    # Platform image post (Pinterest, Instagram, TikTok slideshow, etc.)

                    # ── Strategy 0: TikTok — try tikwm (handles /photo/ AND vt.tiktok.com short links) ──
                    if _is_any_tiktok(url) and HAS_REQUESTS:
                        td = _tikwm_fetch(url)
                        if td:
                            images = td.get('images', [])
                            title  = td.get('title') or f'TikTok_Slideshow_{task_id}'
                            safe_t = re.sub(r'[^\w.\-]', '_', title)[:60]

                            if images:
                                tasks[task_id].update({
                                    'status':   'downloading',
                                    'filename': f'{safe_t} ({len(images)} slides)',
                                })
                                for i, img_url in enumerate(images):
                                    pct = int((i / len(images)) * 95)
                                    tasks[task_id].update({'progress': pct})
                                    img_ext = '.jpg'
                                    low = img_url.lower()
                                    if 'png' in low:  img_ext = '.png'
                                    elif 'webp' in low: img_ext = '.webp'
                                    fname    = f'{safe_t}_slide{i+1:02d}{img_ext}'
                                    out_path = os.path.join(DOWNLOAD_DIR, fname)
                                    r = _requests.get(
                                        img_url, timeout=30,
                                        headers={'User-Agent': 'Mozilla/5.0'},
                                    )
                                    r.raise_for_status()
                                    with open(out_path, 'wb') as f:
                                        f.write(r.content)
                                tasks[task_id].update({
                                    'status':   'done',
                                    'progress': 100,
                                    'filename': f'{safe_t} — {len(images)} slides saved',
                                })
                                return
                            elif td.get('play'):  # it's actually a video, fall through
                                pass
                            else:
                                raise Exception(
                                    'tikwm returned no images for this post. '
                                    'The post may be private or region-locked.'
                                )

                    # ── Strategy A/B: yt-dlp (for other platforms) ──────────────────
                    info = None
                    _info_strategies = [
                        {'quiet': True, 'no_warnings': True, 'skip_download': True},
                        {'quiet': True, 'no_warnings': True, 'skip_download': True,
                         'extractor_args': {'tiktok': {'api_hostname': 'api16-normal-c-useast1a.tiktokv.com'}}},
                    ]
                    if FFMPEG_PATH:
                        for s in _info_strategies:
                            s['ffmpeg_location'] = os.path.dirname(FFMPEG_PATH)

                    for _opts in _info_strategies:
                        try:
                            with yt_dlp.YoutubeDL(_opts) as ydl:
                                info = ydl.extract_info(url, download=False)
                            break
                        except Exception:
                            info = None

                    if info is not None:
                        # Try yt-dlp download if it found formats
                        if info.get('formats'):
                            img_fmt = 'bestvideo[vcodec=none]/best[vcodec=none]/best'
                            ydl_opts = {
                                'format':         img_fmt,
                                'outtmpl':        os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
                                'progress_hooks': [progress_hook],
                                'quiet':          True,
                                'no_warnings':    True,
                            }
                            if FFMPEG_PATH:
                                ydl_opts['ffmpeg_location'] = os.path.dirname(FFMPEG_PATH)
                            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                                ydl.download([url])
                            tasks[task_id].update({'status': 'done', 'progress': 100})
                            return

                        # Fallback: grab best thumbnail / direct URL from info
                        img_url = info.get('url')
                        if not img_url and info.get('thumbnails'):
                            imgs_list = info.get('thumbnails', [])
                            if imgs_list:
                                img_url = imgs_list[-1].get('url')
                        if not img_url:
                            img_url = info.get('thumbnail')

                        if img_url and HAS_REQUESTS:
                            ext = '.jpg'
                            if 'png' in img_url.lower(): ext = '.png'
                            elif 'webp' in img_url.lower(): ext = '.webp'
                            title = info.get('title') or f'image_{task_id}'
                            safe_title = re.sub(r'[^\w.\-]', '_', title)
                            filename = f'{safe_title}{ext}'
                            out_path = os.path.join(DOWNLOAD_DIR, filename)
                            tasks[task_id].update({'status': 'downloading', 'filename': filename})
                            resp = _requests.get(img_url, stream=True, timeout=30,
                                                 headers={'User-Agent': 'Mozilla/5.0'})
                            resp.raise_for_status()
                            total = int(resp.headers.get('Content-Length', 0))
                            done = 0
                            with open(out_path, 'wb') as f:
                                for chunk in resp.iter_content(8192):
                                    if chunk:
                                        f.write(chunk)
                                        done += len(chunk)
                                        pct = int(done / total * 100) if total else 50
                                        tasks[task_id].update({'progress': pct, 'size': f'{done//1024} KB'})
                            tasks[task_id].update({'status': 'done', 'progress': 100,
                                                   'filepath': out_path, 'filename': filename})
                            return

                    # Strategy C — yt-dlp failed entirely (e.g. TikTok /photo/ slideshow)
                    # Try yt-dlp direct download with best format as last resort
                    try:
                        dl_opts_fallback = {
                            'format':         'best',
                            'outtmpl':        os.path.join(DOWNLOAD_DIR, f'image_{task_id}.%(ext)s'),
                            'progress_hooks': [progress_hook],
                            'quiet':          True,
                            'no_warnings':    True,
                        }
                        if FFMPEG_PATH:
                            dl_opts_fallback['ffmpeg_location'] = os.path.dirname(FFMPEG_PATH)
                        with yt_dlp.YoutubeDL(dl_opts_fallback) as ydl:
                            ydl.download([url])
                        tasks[task_id].update({'status': 'done', 'progress': 100})
                        return
                    except Exception as fallback_err:
                        raise Exception(
                            f'TikTok slideshow/photo posts are not yet fully supported by yt-dlp. '
                            f'Try updating yt-dlp: pip install -U yt-dlp  (detail: {fallback_err})'
                        )

            # ── AUDIO MODE ────────────────────────────────────────
            elif mode == 'audio':
                fmt = 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best'
                pp  = []
            else:
                if FFMPEG_PATH:
                    # ffmpeg available → merge best video + best audio
                    fmt = (
                        f'bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]'
                        f'/bestvideo[height<={quality}]+bestaudio'
                        f'/bestvideo+bestaudio'
                        f'/best'
                    )
                else:
                    # No ffmpeg → use pre-merged single file (max ~720p)
                    fmt = (
                        f'best[height<={quality}][ext=mp4]'
                        f'/best[height<={quality}]'
                        f'/best[ext=mp4]/best'
                    )
                pp = []

            ydl_opts = {
                'format':              fmt,
                'outtmpl':             os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
                'progress_hooks':      [progress_hook],
                'postprocessors':      pp,
                'merge_output_format': 'mp4',
                'quiet':               True,
                'no_warnings':         True,
                'noprogress':          False,
            }

            # Speed limit (e.g. '1M' = 1 MB/s, '500K' = 500 KB/s)
            if speed_limit and speed_limit != 'unlimited':
                ydl_opts['ratelimit'] = speed_limit

            # Subtitles
            if subtitles and FFMPEG_PATH:
                ydl_opts['writesubtitles']   = True
                ydl_opts['writeautomaticsub'] = True
                ydl_opts['subtitleslangs']    = [sub_lang, 'en']
                ydl_opts['postprocessors'] = ydl_opts.get('postprocessors', []) + [{
                    'key': 'FFmpegEmbedSubtitle',
                    'already_have_subtitle': False,
                }]

            # Tell yt-dlp exactly where ffmpeg is
            if FFMPEG_PATH:
                ydl_opts['ffmpeg_location'] = os.path.dirname(FFMPEG_PATH)

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Record stats
            _record_download(platform=url.split('/')[2] if '/' in url else 'unknown')
            tasks[task_id].update({'status': 'done', 'progress': 100})

        except yt_dlp.utils.DownloadError as e:
            tasks[task_id].update({'status': 'error', 'error': str(e).replace('[youtube]','').strip()})
        except Exception as e:
            tasks[task_id].update({'status': 'error', 'error': str(e)})

    threading.Thread(target=run, daemon=True).start()
    return jsonify({'task_id': task_id, 'download_dir': DOWNLOAD_DIR})


# ─────────────────────────────────────────────────────────────────
# ROUTE: GET /api/progress/<task_id>
# Server-Sent Events stream — frontend listens with EventSource
# ─────────────────────────────────────────────────────────────────
@app.route('/api/progress/<task_id>')
def get_progress(task_id):
    def stream():
        while True:
            task = tasks.get(task_id, {'status': 'not_found', 'error': 'Task not found'})
            yield f'data: {json.dumps(task)}\n\n'
            if task['status'] in ('done', 'error', 'not_found'):
                break
            time.sleep(0.4)

    return Response(
        stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control':    'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection':       'keep-alive',
        }
    )


# ─────────────────────────────────────────────────────────────────
# ROUTE: GET /api/ping
# ─────────────────────────────────────────────────────────────────
@app.route('/api/ping')
def ping():
    return jsonify({'ok': True, 'dir': get_download_dir(), 'version': '4.0'})


# ─────────────────────────────────────────────────────────────────
# ROUTE: POST /api/auth/validate  -  Validate license key via Local/Remote Admin
# Body: { key: "NEXLOAD-..." }
# ─────────────────────────────────────────────────────────────────
@app.route('/api/auth/validate', methods=['POST'])
def auth_validate():
    data = request.get_json() or {}
    key  = data.get('key', '').strip().upper()
    
    # We always retrieve a response containing valid: bool, and hwid: string
    result = _validate_license(key)
    
    # Optional shortcut for frontend debugging during setup
    if not key:
        return jsonify(result), 400
        
    return jsonify(result)


# ─────────────────────────────────────────────────────────────────
# ROUTE: GET /api/stats — Return download statistics
# ─────────────────────────────────────────────────────────────────
@app.route('/api/stats')
def get_stats():
    return jsonify(_load_stats())


# ─────────────────────────────────────────────────────────────────
# ROUTE: POST /api/set-folder — Change download folder
# Body: { folder: "C:\\path\\to\\folder" }
# ─────────────────────────────────────────────────────────────────
@app.route('/api/set-folder', methods=['POST'])
def set_folder():
    data   = request.get_json() or {}
    folder = data.get('folder', '').strip()
    if not folder:
        return jsonify({'error': 'No folder provided'}), 400
    if not os.path.isdir(folder):
        try:
            os.makedirs(folder, exist_ok=True)
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    with open(CUSTOM_FOLDER_PATH, 'w', encoding='utf-8') as f:
        f.write(folder)
    return jsonify({'ok': True, 'folder': folder})


# ─────────────────────────────────────────────────────────────────
# ROUTE: GET /api/get-folder — Returns current download folder
# ─────────────────────────────────────────────────────────────────
@app.route('/api/get-folder')
def get_folder():
    return jsonify({'folder': get_download_dir()})


# ─────────────────────────────────────────────────────────────────
# ROUTE: POST /api/open-folder
# Opens Windows Explorer to the download folder
# ─────────────────────────────────────────────────────────────────
@app.route('/api/open-folder', methods=['POST'])
def open_folder():
    import subprocess, platform as _plat
    try:
        system = _plat.system()
        if system == 'Windows':
            subprocess.Popen(['explorer', DOWNLOAD_DIR])
        elif system == 'Darwin':
            subprocess.Popen(['open', DOWNLOAD_DIR])
        else:
            subprocess.Popen(['xdg-open', DOWNLOAD_DIR])
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────
# AUTO-START TELEGRAM BOT (Works in Python, Gunicorn & Docker)
# ─────────────────────────────────────────────────────────────────
def _try_start_bot():
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token and hasattr(config, 'TELEGRAM_BOT_TOKEN'):
        token = config.TELEGRAM_BOT_TOKEN
    if token and token != "123456789:ABCdefGHIjklMNOpqrsTUVwxyz":
        import threading
        def _run():
            try:
                print("🤖 [Server Boot] Starting Telegram Bot service...")
                import telegram_bot
                telegram_bot.run_bot()
            except Exception as e:
                print(f"⚠️ [Server Boot] Bot start failed: {e}")
        threading.Thread(target=_run, daemon=True).start()

_try_start_bot()

# ─────────────────────────────────────────────────────────────────
# STARTUP
# ─────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = 'YOUR_PC_IP'

    print('\n' + '═' * 50)
    print('  🚀  NexLoad Server v4.5 — Commercial & Cloud Edition')
    print('═' * 50)
    print(f'  📁  Downloads → {DOWNLOAD_DIR}')
    print(f'  💻  Local URL  → http://localhost:{PORT}')
    print(f'  🌐  Host Binding → {HOST}:{PORT}')
    print('═' * 50 + '\n')
    app.run(host=HOST, port=PORT, debug=False, threaded=True)
