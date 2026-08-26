import sys, os, time, urllib.request, subprocess, webbrowser

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

PORT = int(os.environ.get("PORT", 8756))
SERVER_URL = f"http://127.0.0.1:{PORT}"

def is_server_running():
    try:
        req = urllib.request.urlopen(f"{SERVER_URL}/api/health", timeout=1)
        return req.status == 200
    except Exception:
        return False

def launch():
    server_process = None

    # 1. Start server subprocess if not already active
    if not is_server_running():
        print(f"Starting AMH Lab Tracker backend on {SERVER_URL}...")
        env = os.environ.copy()
        env["PYTHONPATH"] = BASE_DIR
        
        run_server_script = os.path.join(BASE_DIR, "backend", "run_server.py")
        
        server_process = subprocess.Popen(
            [sys.executable, run_server_script],
            cwd=BASE_DIR,
            env=env
        )

        # Wait for backend health check
        for _ in range(30):
            if is_server_running():
                break
            time.sleep(0.3)

    print(f"Server verified active at {SERVER_URL}.")

    # 2. Try launching pywebview native window
    gui_opened = False
    try:
        import webview
        window = webview.create_window("AMH Lab Tracker — Ahmadiyya Muslim Hospital", SERVER_URL, width=1280, height=800)
        gui_opened = True
        webview.start()
    except Exception as e:
        print(f"pywebview GUI shell unavailable ({e}). Falling back to system browser...")

    # 3. Fallback to system web browser if pywebview wasn't used
    if not gui_opened:
        webbrowser.open(SERVER_URL)
        print("Browser opened. Keeping backend server process running in background...")
        if server_process:
            try:
                server_process.wait()
            except KeyboardInterrupt:
                server_process.terminate()

    # Cleanup if GUI window closed
    if server_process and gui_opened:
        try:
            server_process.terminate()
        except Exception:
            pass

if __name__ == "__main__":
    launch()
