import os, sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESKTOP_APP = os.path.join(BASE_DIR, "launcher", "desktop_app.py")
app_path = DESKTOP_APP.replace("/", "\\")

# Use Windows Startup Folder with a direct PowerShell shortcut calling pythonw (no VBScript needed)
startup_dir = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")
os.makedirs(startup_dir, exist_ok=True)

lnk_path = os.path.join(startup_dir, "AMH Lab Tracker.lnk")
base_win = BASE_DIR.replace("/", "\\")

# PowerShell command to create shortcut pointing directly to pythonw.exe
import subprocess
ps_cmd = f'$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut("{lnk_path}"); $Shortcut.TargetPath = "pythonw.exe"; $Shortcut.Arguments = "\\"{app_path}\\""; $Shortcut.WorkingDirectory = "{base_win}"; $Shortcut.Save()'

try:
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
    print(f"Windows autostart shortcut created at: {lnk_path}")
except Exception as e:
    print(f"Windows autostart setup note: {e}")
