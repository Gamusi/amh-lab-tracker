import os, sys, platform

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

def install():
    print("=" * 60)
    print("  AMH Lab Tracker — One-Time System Installation & Setup")
    print("  Ahmadiyya Muslim Hospital, Mbale, Uganda")
    print("=" * 60)

    # 1. Initialize DB & Seed Data
    print("\n1. Initializing SQLite Database & Seeding Initial Data...")
    from backend.app.seed import seed_database
    seed_database()

    # 2. Configure Autostart (Optional, catches any OS permission hiccups gracefully)
    print("\n2. Setting up Autostart...")
    try:
        if platform.system() == "Linux":
            from launcher import install_autostart_linux
            install_autostart_linux()
        elif platform.system() == "Windows":
            from launcher import install_autostart_windows
            install_autostart_windows()
    except Exception as e:
        print(f"   Autostart note: {e}")

    # 3. Create Desktop Shortcut
    print("\n3. Creating Desktop Shortcut...")
    try:
        from launcher import make_desktop_shortcut
        make_desktop_shortcut()
    except Exception as e:
        print(f"   Desktop shortcut note: {e}")

    print("\n" + "=" * 60)
    print("  INSTALLATION COMPLETE!")
    print("  - Launch the app using 'run.bat' (or Desktop shortcut)")
    print("  - Default Admin Credentials: username 'admin', password 'amh_admin2026'")
    print("  - Default Tech Credentials:  username 'tech1', password 'amh_tech2026'")
    print("  - Database File: data/amh_lab.db")
    print("=" * 60)

if __name__ == "__main__":
    install()
