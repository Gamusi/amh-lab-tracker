import uvicorn, os, sys

if __name__ == "__main__":
    # Ensure app directory is on path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    port = int(os.environ.get("PORT", 8756))
    print(f"Starting AMH Lab Tracker server on http://127.0.0.1:{port}")
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=port, log_level="info")
