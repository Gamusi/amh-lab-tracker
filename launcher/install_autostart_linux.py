import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESKTOP_APP = os.path.join(BASE_DIR, "launcher", "desktop_app.py")

def install_autostart_linux():
    autostart_dir = os.path.expanduser("~/.config/autostart")
    os.makedirs(autostart_dir, exist_ok=True)

    desktop_file = os.path.join(autostart_dir, "amh-lab-tracker.desktop")

    content = f"""[Desktop Entry]
Type=Application
Name=AMH Lab Tracker
Comment=Laboratory Data Capture and Reporting System - Ahmadiyya Muslim Hospital
Exec=python3 "{DESKTOP_APP}"
Icon={os.path.join(BASE_DIR, "assets", "branding", "logo.png")}
Terminal=false
Categories=Medical;Laboratory;Healthcare;
X-GNOME-Autostart-enabled=true
"""

    with open(desktop_file, "w") as f:
        f.write(content)

    os.chmod(desktop_file, 0o755)
    print(f"Linux autostart configured at: {desktop_file}")
    return desktop_file

if __name__ == "__main__":
    install_autostart_linux()
