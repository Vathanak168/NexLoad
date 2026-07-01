"""
NexLoad Icon Converter + First-Time Setup
Run this once to convert the PNG icon to .ico format
and generate a test license key.
"""
import os, sys, subprocess

BASE = os.path.dirname(os.path.abspath(__file__))

def install(pkg):
    subprocess.run([sys.executable, '-m', 'pip', 'install', pkg, '-q'], check=False)

# ── Step 1: Convert PNG → ICO ─────────────────────────────────────
print("\n  [1/3] Converting app icon...")
try:
    install('Pillow')
    from PIL import Image

    # Look for the icon
    candidates = [
        os.path.join(BASE, 'nexload_icon.png'),
        os.path.join(BASE, 'icon.png'),
    ]
    src = next((p for p in candidates if os.path.exists(p)), None)

    if src:
        img = Image.open(src).convert('RGBA')
        ico_path = os.path.join(BASE, 'nexload.ico')
        img.save(ico_path, format='ICO',
                 sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])
        print(f"  ✅ Icon saved: nexload.ico")
    else:
        print("  ⚠️  No source PNG found — skipping icon conversion.")
        print("      Place nexload_icon.png next to this script and re-run.")
except ImportError:
    print("  ⚠️  Pillow not available — skipping icon conversion.")
except Exception as e:
    print(f"  ⚠️  Icon error: {e}")

# ── Step 2: Generate a TEST license key ──────────────────────────
print("\n  [2/3] Generating test license key...")
try:
    sys.path.insert(0, BASE)
    from license_manager import generate_key, TIERS

    info = generate_key("Test User — Pro", "pro", 365)
    print("\n  ╔══════════════════════════════════════════════════╗")
    print("  ║         🔑  TEST LICENSE KEY GENERATED           ║")
    print("  ╠══════════════════════════════════════════════════╣")
    print(f"  ║  Key:     {info['key']:<39}║")
    print(f"  ║  Tier:    Pro (365 days)                        ║")
    print("  ╚══════════════════════════════════════════════════╝")
    print(f"\n  📋 Copy this key and paste it in the NexLoad login screen:")
    print(f"\n     ➤  {info['key']}\n")

    # Save it to a readable text file
    keyfile = os.path.join(BASE, 'MY_LICENSE_KEY.txt')
    with open(keyfile, 'w') as f:
        f.write(f"NexLoad License Key\n{'='*40}\n")
        f.write(f"Key:     {info['key']}\n")
        f.write(f"User:    {info['user']}\n")
        f.write(f"Tier:    Pro\n")
        f.write(f"Expires: {info['expires'][:10]}\n")
        f.write(f"\nKeep this file safe!\n")
    print(f"  💾 Saved to: MY_LICENSE_KEY.txt")

except Exception as e:
    print(f"  ❌ Could not generate key: {e}")

# ── Step 3: Create Desktop Shortcut ───────────────────────────────
print("\n  [3/3] Creating Desktop shortcut...")
try:
    ps_script = os.path.join(BASE, 'create_shortcut.ps1')
    if os.path.exists(ps_script):
        result = subprocess.run(
            ['powershell', '-ExecutionPolicy', 'Bypass', '-File', ps_script],
            capture_output=True, text=True, timeout=20
        )
        if result.returncode == 0:
            print("  ✅ Desktop shortcut created!")
        else:
            print("  ⚠️  Shortcut creation needs manual step.")
    else:
        print("  ⚠️  create_shortcut.ps1 not found.")
except Exception as e:
    print(f"  ⚠️  Shortcut error: {e}")

print("\n" + "="*52)
print("  🚀  Setup complete! How to use NexLoad:")
print("="*52)
print("  1. Double-click 'NexLoad' icon on your Desktop")
print("  2. Enter your license key from MY_LICENSE_KEY.txt")
print("  3. Download videos from any platform!")
print("="*52)
input("\n  Press ENTER to close...")
