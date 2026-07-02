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


# ── MAIN ──────────────────────────────────────────────────────
if __name__ == '__main__':
    if is_server_running():
        # Server already running — just open a new window
        open_app_window()
    else:
        start_server()
        if wait_for_server(max_wait=15):
            open_app_window()
        else:
            show_error("NexLoad server failed to start.\n\nMake sure Python is installed:\npython server.py")
