"""
NexLoad EXE Builder Script
==========================
Automated script to build standalone NexLoad executable for Windows using PyInstaller.
Usage:
    python build_exe.py
"""

import os, sys, subprocess, shutil
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def ensure_package(pkg):
    try:
        __import__(pkg)
    except ImportError:
        print(f"📦 Installing {pkg}...")
        subprocess.run([sys.executable, "-m", "pip", "install", pkg, "-q"], check=False)

def convert_icon():
    ico_path = os.path.join(BASE_DIR, "nexload.ico")
    png_path = os.path.join(BASE_DIR, "nexload_icon.png")
    if not os.path.exists(ico_path) and os.path.exists(png_path):
        ensure_package("PIL")
        try:
            from PIL import Image
            img = Image.open(png_path).convert("RGBA")
            img.save(ico_path, format="ICO", sizes=[(256,256),(128,128),(64,64),(32,32)])
            print("✅ Converted PNG icon to nexload.ico")
        except Exception as e:
            print(f"⚠️ Could not convert icon: {e}")

def build_exe():
    ensure_package("PyInstaller")
    convert_icon()

    print("\n🔨 Starting PyInstaller build for NexLoad Desktop App...")
    
    icon_arg = []
    ico_path = os.path.join(BASE_DIR, "nexload.ico")
    if os.path.exists(ico_path):
        icon_arg = [f"--icon={ico_path}"]

    data_files = [
        ("index.html", "."),
        ("style.css", "."),
        ("app.js", "."),
    ]
    if os.path.exists(ico_path):
        data_files.append(("nexload.ico", "."))

    add_data_args = []
    for src, dst in data_files:
        if os.path.exists(os.path.join(BASE_DIR, src)):
            add_data_args.append(f"--add-data={src};{dst}")

    hidden_imports = [
        "--hidden-import=flask",
        "--hidden-import=flask_cors",
        "--hidden-import=yt_dlp",
        "--hidden-import=requests",
        "--hidden-import=license_manager",
        "--hidden-import=config",
        "--hidden-import=server",
    ]

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=NexLoad",
        "--noconsole",
        "--noconfirm",
        "--clean",
        "main_desktop.py"
    ] + icon_arg + add_data_args + hidden_imports

    print(f"Executing: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=BASE_DIR)

    if result.returncode == 0:
        dist_dir = os.path.join(BASE_DIR, "dist", "NexLoad")
        print("\n" + "═" * 60)
        print("🎉  BUILD SUCCESSFUL!")
        print("═" * 60)
        print(f"📂  Standalone executable created at:\n    {os.path.join(dist_dir, 'NexLoad.exe')}")
        print("═" * 60 + "\n")
    else:
        print("\n❌ Build failed. Check error output above.")

if __name__ == "__main__":
    build_exe()
