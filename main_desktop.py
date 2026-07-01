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

if __name__ == "__main__":
    if not is_server_running():
        server_thread = threading.Thread(target=run_flask_server, daemon=True)
        server_thread.start()
    
    open_app_window()
    
    # Keep main process running while server thread is active
    while True:
        time.sleep(1)
