import os, subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESKTOP_APP = os.path.join(BASE_DIR, "launcher", "desktop_app.py")

def install_autostart_windows():
    startup_dir = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")
    os.makedirs(startup_dir, exist_ok=True)

    lnk_path = os.path.join(startup_dir, "AMH Lab Tracker.lnk")
    base_win = BASE_DIR.replace("/", "\\")
    app_path = DESKTOP_APP.replace("/", "\\")

    ps_cmd = (
        f'$WshShell = New-Object -ComObject WScript.Shell; '
        f'$Shortcut = $WshShell.CreateShortcut("{lnk_path}"); '
        f'$Shortcut.TargetPath = "pythonw.exe"; '
        f'$Shortcut.Arguments = "\\"{app_path}\\""; '
        f'$Shortcut.WorkingDirectory = "{base_win}"; '
        f'$Shortcut.Save()'
    )

    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
        print(f"Windows autostart shortcut created at: {lnk_path}")
        return lnk_path
    except Exception as e:
        print(f"Windows autostart setup note: {e}")
        return None

if __name__ == "__main__":
    install_autostart_windows()
