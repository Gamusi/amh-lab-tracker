import os, platform, subprocess, tempfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_windows_desktop_dir():
    """Detect actual Windows Desktop path even if redirected by OneDrive or localized."""
    candidates = []
    
    # 1. Check registry / user profile paths
    user_profile = os.environ.get("USERPROFILE", "")
    if user_profile:
        candidates.append(os.path.join(user_profile, "Desktop"))
        candidates.append(os.path.join(user_profile, "OneDrive", "Desktop"))
    
    # 2. Expanduser fallback
    candidates.append(os.path.expanduser("~/Desktop"))
    
    for c in candidates:
        if os.path.exists(c):
            return c
            
    # Default fallback
    fallback = os.path.expanduser("~/Desktop")
    os.makedirs(fallback, exist_ok=True)
    return fallback

def make_desktop_shortcut():
    run_sh = os.path.join(BASE_DIR, "run.sh")
    run_bat = os.path.join(BASE_DIR, "run.bat")
    icon_ico = os.path.join(BASE_DIR, "assets", "branding", "app.ico")
    icon_png = os.path.join(BASE_DIR, "assets", "branding", "logo.png")

    if platform.system() == "Linux":
        desktop_dir = os.path.expanduser("~/Desktop")
        os.makedirs(desktop_dir, exist_ok=True)
        shortcut_path = os.path.join(desktop_dir, "M-LIS.desktop")
        content = f"""[Desktop Entry]
Type=Application
Name=M-LIS
Comment=Laboratory Information System
Exec="{run_sh}"
Icon={icon_png}
Terminal=true
Categories=Medical;Healthcare;
"""
        with open(shortcut_path, "w") as f:
            f.write(content)
        os.chmod(shortcut_path, 0o755)
        print(f"Linux desktop shortcut created at: {shortcut_path}")
        return shortcut_path
    else:
        desktop_dir = get_windows_desktop_dir()
        os.makedirs(desktop_dir, exist_ok=True)
        lnk_shortcut = os.path.join(desktop_dir, "M-LIS.lnk")
        
        # Build VBScript to create genuine Windows .lnk shortcut with icon
        vbs_script = f"""
Set WshShell = WScript.CreateObject("WScript.Shell")
Set Shortcut = WshShell.CreateShortcut("{lnk_shortcut.replace('\\', '\\\\')}")
Shortcut.TargetPath = "{run_bat.replace('\\', '\\\\')}"
Shortcut.WorkingDirectory = "{BASE_DIR.replace('\\', '\\\\')}"
Shortcut.WindowStyle = 1
Shortcut.Description = "M-LIS - Laboratory Information System"
Shortcut.IconLocation = "{icon_ico.replace('\\', '\\\\')},0"
Shortcut.Save
"""
        with tempfile.NamedTemporaryFile("w", suffix=".vbs", delete=False) as tf:
            tf.write(vbs_script)
            vbs_file = tf.name
            
        try:
            subprocess.run(["cscript", "//nologo", vbs_file], check=True, capture_output=True)
            print(f"Windows desktop shortcut created with custom icon at: {lnk_shortcut}")
        except Exception as e:
            print(f"VBS shortcut creation warning ({e}), falling back to direct batch shortcut...")
            bat_shortcut = os.path.join(desktop_dir, "M-LIS.bat")
            with open(bat_shortcut, "w", encoding="utf-8") as f:
                f.write(f'@echo off\ncd /d "{BASE_DIR}"\ncall "{run_bat}"\n')
            print(f"Windows desktop fallback shortcut created at: {bat_shortcut}")
            return bat_shortcut
        finally:
            if os.path.exists(vbs_file):
                try:
                    os.remove(vbs_file)
                except Exception:
                    pass
                    
        return lnk_shortcut

if __name__ == "__main__":
    make_desktop_shortcut()

