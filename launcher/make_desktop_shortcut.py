import os, sys, platform

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
desktop_dir = os.path.expanduser("~/Desktop")
os.makedirs(desktop_dir, exist_ok=True)

run_sh = os.path.join(BASE_DIR, "run.sh")
run_bat = os.path.join(BASE_DIR, "run.bat")

# Create desktop shortcut scripts
if platform.system() == "Linux":
    shortcut_path = os.path.join(desktop_dir, "AMH Lab Tracker.desktop")
    content = f"""[Desktop Entry]
Type=Application
Name=AMH Lab Tracker
Comment=Laboratory Data Capture and Reporting System
Exec="{run_sh}"
Terminal=true
Categories=Medical;Healthcare;
"""
    with open(shortcut_path, "w") as f:
        f.write(content)
    os.chmod(shortcut_path, 0o755)
    print(f"Linux desktop shortcut created at: {shortcut_path}")
else:
    bat_shortcut = os.path.join(desktop_dir, "AMH Lab Tracker.bat")
    with open(bat_shortcut, "w", encoding="utf-8") as f:
        f.write(f'@echo off\ncall "{run_bat}"\n')
    print(f"Windows batch desktop shortcut created at: {bat_shortcut}")
