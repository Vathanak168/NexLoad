# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main_desktop.py'],
    pathex=[],
    binaries=[],
    datas=[('index.html', '.'), ('style.css', '.'), ('app.js', '.'), ('nexload.ico', '.')],
    hiddenimports=['flask', 'flask_cors', 'yt_dlp', 'requests', 'license_manager', 'config', 'server', 'telegram_bot', 'bot_key_manager', 'bot_downloader'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='NexLoad',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:/Users/U-ser/Desktop/AI_Tool/nexload.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='NexLoad',
)
