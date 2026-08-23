import os
import sys
import shutil
import zipfile
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, "dist")
STAGE_DIR = os.path.join(DIST_DIR, "amh-lab-tracker")
ZIP_OUTPUT = os.path.join(DIST_DIR, "amh-lab-tracker-release.zip")
WHEELS_DIR = os.path.join(BASE_DIR, "offline_packages", "wheels")

def run_cmd(cmd):
    print(f">> {cmd}")
    res = subprocess.run(cmd, shell=True, cwd=BASE_DIR)
    if res.returncode != 0:
        print(f"[ERROR] Command failed with code {res.returncode}")
        return False
    return True

def pack():
    print("=" * 60)
    print("  AMH Lab Tracker — Release Packager (Zip Distribution)")
    print("  Ahmadiyya Muslim Hospital, Mbale, Uganda")
    print("=" * 60)

    # 1. Ensure offline wheels are downloaded
    os.makedirs(WHEELS_DIR, exist_ok=True)
    print("\n1. Checking / downloading offline dependency wheels...")
    req_file = os.path.join(BASE_DIR, "requirements.txt")
    run_cmd(f"{sys.executable} -m pip download -r requirements.txt --python-version 3.11 --platform win_amd64 --only-binary=:all: -d \"{WHEELS_DIR}\"")

    # 2. Clean and create stage directory
    print("\n2. Staging files for release...")
    if os.path.exists(DIST_DIR):
        shutil.rmtree(DIST_DIR)
    os.makedirs(STAGE_DIR, exist_ok=True)

    # Folders to include (pure runtime only - no docs or planning artifacts)
    include_dirs = ["backend", "frontend", "assets", "launcher"]
    for d in include_dirs:
        src = os.path.join(BASE_DIR, d)
        dst = os.path.join(STAGE_DIR, d)
        if os.path.exists(src):
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns(
                "__pycache__", "*.pyc", ".pytest_cache", "*.db", "*.log"
            ))
            print(f"   [+] Copied runtime folder: {d}/")


    # Copy offline wheels
    if os.path.exists(WHEELS_DIR) and os.listdir(WHEELS_DIR):
        dst_wheels = os.path.join(STAGE_DIR, "offline_packages", "wheels")
        shutil.copytree(WHEELS_DIR, dst_wheels)
        print(f"   [+] Copied {len(os.listdir(WHEELS_DIR))} offline wheel packages")

    # Files to include
    include_files = [
        "requirements.txt",
        "setup.bat",
        "run.bat",
        "install.py",
        "INSTRUCTIONS.txt"
    ]
    for f in include_files:
        src = os.path.join(BASE_DIR, f)
        dst = os.path.join(STAGE_DIR, f)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"   [+] Copied file: {f}")

    # Ensure empty data directory exists in release
    os.makedirs(os.path.join(STAGE_DIR, "data"), exist_ok=True)
    print("   [+] Created empty data/ directory (ready for SQLite DB)")

    # 3. Create zip archive
    print("\n3. Building ZIP archive...")
    with zipfile.ZipFile(ZIP_OUTPUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(STAGE_DIR):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, os.path.dirname(STAGE_DIR))
                zf.write(abs_path, rel_path)

    zip_size_mb = os.path.getsize(ZIP_OUTPUT) / (1024 * 1024)
    print(f"\n" + "=" * 60)
    print(f"  RELEASE ZIP PACKAGING COMPLETE!")
    print(f"  Package Location: {ZIP_OUTPUT}")
    print(f"  Package Size:     {zip_size_mb:.2f} MB")
    print(f"")
    print(f"  DEPLOYMENT ON TARGET MACHINE:")
    print(f"  1. Transfer 'amh-lab-tracker-release.zip' to target PC.")
    print(f"  2. Right-click -> 'Extract All...'.")
    print(f"  3. Open the extracted folder and double-click 'setup.bat'.")
    print(f"  4. Double-click 'run.bat' (or Desktop shortcut) to launch.")
    print("=" * 60)

if __name__ == "__main__":
    pack()
