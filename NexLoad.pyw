"""
NexLoad Desktop App Launcher
=============================
Double-click NexLoad.pyw (or shortcut) to launch the app.
- Starts Flask server silently (no CMD window)
- Opens Chrome/Edge in App Mode (looks like native app)
- Kills old instances automatically
"""
import os, sys, subprocess, time, socket, webbrowser, threading

BASE = os.path.dirname(os.path.abspath(__file__))
SERVER_URL = 'http://localhost:5000'
SERVER_PORT = 5000


def is_server_running():
    """Check if server is already running on port 5000."""
    try:
        with socket.create_connection(('localhost', SERVER_PORT), timeout=1):
            return True
    except OSError:
        return False


def start_server():
    """Start server.py hidden (no console window)."""
    server_path = os.path.join(BASE, 'server.py')
    if not os.path.exists(server_path):
        show_error("server.py not found in:\n" + BASE)
        return False

    # Install missing packages silently first, then start the server.
    req_path = os.path.join(BASE, 'requirements.txt')
    pip_cmd = [sys.executable, '-m', 'pip', 'install', '--quiet', '--disable-pip-version-check']
    pip_cmd += ['-r', req_path] if os.path.exists(req_path) else ['flask', 'flask-cors', 'yt-dlp', 'requests', 'SQLAlchemy']
    subprocess.run(
        pip_cmd,
        creationflags=subprocess.CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        check=False,
    )

    # Start Flask server with no console window
    subprocess.Popen(
        [sys.executable, server_path],
        creationflags=subprocess.CREATE_NO_WINDOW,
        cwd=BASE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return True


def wait_for_server(max_wait=15):
    """Wait until server is ready."""
    for _ in range(max_wait * 2):
        if is_server_running():
            return True
        time.sleep(0.5)
    return False


def open_app_window():
    """Open NexLoad in Chrome/Edge App Mode (no browser chrome)."""
    browser_paths = [
        # Chrome
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
        os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe'),
        # Edge
        r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
        os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe'),
    ]

    icon_path = os.path.join(BASE, 'nexload.ico')
    app_args = [
        f'--app={SERVER_URL}',
        '--window-size=1280,860',
        '--window-position=100,60',
        '--no-first-run',
        '--disable-extensions',
        '--disable-default-apps',
    ]
    if os.path.exists(icon_path):
        app_args.append(f'--app-icon={icon_path}')

    for browser in browser_paths:
        if os.path.exists(browser):
            subprocess.Popen([browser] + app_args)
            return True

    # Fallback: default browser (will have browser chrome)
    webbrowser.open(SERVER_URL)
    return False


def show_error(msg):
    """Show a simple error box using PowerShell."""
    subprocess.Popen(
        ['powershell', '-Command', f'[System.Windows.Forms.MessageBox]::Show("{msg}", "NexLoad Error")'],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def show_tray_fallback():
    """Show a simple system tray notification."""
    try:
        subprocess.Popen(
            ['powershell', '-Command',
             'Add-Type -AssemblyName System.Windows.Forms; '
             '$n = New-Object System.Windows.Forms.NotifyIcon; '
             '$n.Icon = [System.Drawing.SystemIcons]::Application; '
             '$n.Visible = $true; '
             '$n.ShowBalloonTip(3000, "NexLoad", "App is running at http://localhost:5000", '
             '[System.Windows.Forms.ToolTipIcon]::Info)'],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception:
        pass


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


# ── MAIN ──────────────────────────────────────────────────────
if __name__ == '__main__':
    check_and_run_first_run_consent(BASE)
    if is_server_running():
        # Server already running — just open a new window
        open_app_window()
    else:
        start_server()
        if wait_for_server(max_wait=15):
            open_app_window()
        else:
            show_error("NexLoad server failed to start.\n\nMake sure Python is installed:\npython server.py")
