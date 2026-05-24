import os, sys, subprocess, traceback
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import sounds

m = sounds.SoundManager(r"C:\Users\aj918\.py-os")
m.save_theme_name("Windows XP")

print(f"sounddevice installed: {sounds.HAS_SOUNDDEVICE}")
print(f"use_ffmpeg flag: {m.get_ffmpeg_flag()}")

xp = m.default_themes["Windows XP"]
for evt, path in xp.items():
    exists = os.path.exists(path)
    size = os.path.getsize(path) if exists else 0
    print(f"  {evt}: exists={exists}, size={size}")

# Try playing each sound
for evt in ["nav", "launch", "close", "alert", "notify", "shutdown"]:
    print(f"\nPlaying '{evt}'...")
    try:
        m.play(evt)
        import time
        time.sleep(1)
    except Exception as e:
        print(f"  CRASHED: {e}")
        traceback.print_exc()

# Check ffplay availability
try:
    r = subprocess.run(["ffplay", "-version"], capture_output=True, text=True, timeout=5)
    print(f"\nffplay available: yes ({r.stdout[:50]})")
except:
    print(f"\nffplay available: NO")
