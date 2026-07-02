"""
NexLoad Standalone Desktop Entry Point
======================================
Bundled by PyInstaller into a standalone Windows Desktop Executable (NexLoad.exe).
Starts the embedded server and opens the native application window.
"""

import os, sys, time, threading, webbrowser, subprocess, socket

# Ensure PyInstaller bundled files are accessible
if getattr(sys, 'frozen', False):
    BUNDLE_DIR = sys._MEIPASS
    APP_DIR = os.path.dirname(sys.executable)
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    APP_DIR = BUNDLE_DIR

sys.path.insert(0, BUNDLE_DIR)

import config
import server

PORT = config.PORT
SERVER_URL = f"http://127.0.0.1:{PORT}"

def is_server_running():
    try:
        with socket.create_connection(('127.0.0.1', PORT), timeout=1):
            return True
    except OSError:
        return False

def run_flask_server():
    # Run embedded server
    server.app.run(host='127.0.0.1', port=PORT, debug=False, threaded=True, use_reloader=False)

def open_app_window():
    # Wait for server to be ready
    for _ in range(30):
        if is_server_running():
            break
        time.sleep(0.2)

    browser_paths = [
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
        os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe'),
        r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
        os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe'),
    ]

    icon_path = os.path.join(BUNDLE_DIR, 'nexload.ico')
    if not os.path.exists(icon_path):
        icon_path = os.path.join(APP_DIR, 'nexload.ico')

    app_args = [
        f'--app={SERVER_URL}',
        '--window-size=1280,860',
        '--window-position=100,60',
        '--no-first-run',
        '--disable-extensions',
    ]
    if os.path.exists(icon_path):
        app_args.append(f'--app-icon={icon_path}')

    for browser in browser_paths:
        if os.path.exists(browser):
            subprocess.Popen([browser] + app_args)
            return

    # Fallback to default browser
    webbrowser.open(SERVER_URL)

def check_and_run_first_run_consent(app_dir):
    import json
    consent_file = os.path.join(app_dir, 'youtube_consent.json')
    if os.path.exists(consent_file):
        return

    try:
        import tkinter as tk
        root = tk.Tk()
        root.title("NexLoad Desktop — First Run Setup")
        root.geometry("540x360")
        root.resizable(False, False)

        frame = tk.Frame(root, padx=24, pady=20)
        frame.pack(fill="both", expand=True)

        lbl_title = tk.Label(frame, text="Welcome to NexLoad Desktop", font=("Arial", 14, "bold"), anchor="w")
        lbl_title.pack(fill="x", pady=(0, 10))

        lbl_sub = tk.Label(frame, text="Please configure your local video extraction components below before launching.", font=("Arial", 10), wraplength=480, justify="left", anchor="w")
        lbl_sub.pack(fill="x", pady=(0, 15))

        var_yt = tk.BooleanVar(value=False)
        chk_yt = tk.Checkbutton(frame, text="Enable YouTube Download (optional) — this installs a local component that runs on your computer to download YouTube videos directly using your own internet connection.", variable=var_yt, font=("Arial", 9, "bold"), wraplength=460, justify="left")
        chk_yt.pack(fill="x", pady=(0, 15))

        lbl_info = tk.Label(frame, text="Why is this needed?\nYouTube blocks cloud servers. To download YouTube videos reliably, the extraction engine (yt-dlp + ffmpeg) must run directly on your personal computer using your home internet connection. No personal account cookies are used without explicit permission.", font=("Arial", 8), fg="#555555", wraplength=480, justify="left", bg="#f5f5f5", padx=10, pady=8)
        lbl_info.pack(fill="x", pady=(0, 20))

        def on_continue():
            data = {"youtube_enabled": bool(var_yt.get()), "timestamp": time.time()}
            try:
                with open(consent_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            except Exception:
                pass
            root.destroy()

        btn_launch = tk.Button(frame, text="Continue & Launch NexLoad", command=on_continue, bg="#0078D7", fg="white", font=("Arial", 10, "bold"), padx=15, pady=6)
        btn_launch.pack(side="right")

        root.protocol("WM_DELETE_WINDOW", on_continue)
        root.mainloop()
    except Exception:
        try:
            with open(consent_file, "w", encoding="utf-8") as f:
                json.dump({"youtube_enabled": False, "timestamp": time.time()}, f, indent=2)
        except Exception:
            pass

if __name__ == "__main__":
    check_and_run_first_run_consent(APP_DIR)
    if not is_server_running():
        server_thread = threading.Thread(target=run_flask_server, daemon=True)
        server_thread.start()
    
    open_app_window()
    
    # Keep main process running while server thread is active
    while True:
        time.sleep(1)
