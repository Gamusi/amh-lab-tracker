import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from .database import init_db
from .routers import auth, daily_log, config, reports, trends, audit, patients

# Initialize DB
init_db()

app = FastAPI(title="AMH Lab Tracker", version="1.0.0")

# Register API Routers
app.include_router(auth.router)
app.include_router(daily_log.router)
app.include_router(config.router)
app.include_router(reports.router)
app.include_router(trends.router)
app.include_router(audit.router)
app.include_router(patients.router)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend", "static")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# Mount Static Files & Branding Assets
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

if os.path.exists(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": "AMH Lab Tracker", "version": "1.0.0"}

@app.get("/")
def serve_spa():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"message": "AMH Lab Tracker API Running. Static frontend index.html not found."})

@app.get("/{full_path:path}")
def catch_all(full_path: str):
    # Route non-API requests to index.html for SPA client-side routing
    if not full_path.startswith("api/"):
        index_path = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
    return JSONResponse({"detail": "Not found"}, status_code=404)
