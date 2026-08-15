import datetime, sqlite3
from fastapi import APIRouter, Depends, HTTPException, Response, status
from ..database import get_db
from ..schemas import LoginRequest, UserCreate
from ..auth import verify_password, hash_password, create_session, get_current_user, require_admin

router = APIRouter(prefix="/api/auth", tags=["Auth"])

@router.post("/login")
def login(req: LoginRequest, response: Response, conn: sqlite3.Connection = Depends(get_db)):
    cur = conn.cursor()
    cur.execute("SELECT id, username, full_name, password_hash, role, is_active FROM users WHERE username = ?", (req.username,))
    user = cur.fetchone()
    
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Invalid username or password")
    
    if not user["is_active"]:
        raise HTTPException(status_code=400, detail="Account is disabled")
    
    token = create_session(conn, user["id"])
    response.set_cookie(
        key="amh_session",
        value=token,
        httponly=True,
        max_age=7 * 86400,
        samesite="lax"
    )
    
    cur.execute("INSERT INTO audit_log (user_id, action, detail) VALUES (?, ?, ?)", (user["id"], "login", f"User {user['username']} logged in"))
    conn.commit()
    
    return {
        "status": "success",
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "role": user["role"]
        }
    }

@router.post("/logout")
def logout(response: Response, current_user: dict = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    response.delete_cookie("amh_session")
    conn.execute("INSERT INTO audit_log (user_id, action, detail) VALUES (?, ?, ?)", (current_user["id"], "logout", f"User {current_user['username']} logged out"))
    conn.commit()
    return {"status": "logged out"}

@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "full_name": current_user["full_name"],
        "role": current_user["role"]
    }

@router.get("/users")
def list_users(admin_user: dict = Depends(require_admin), conn: sqlite3.Connection = Depends(get_db)):
    cur = conn.cursor()
    cur.execute("SELECT id, username, full_name, role, is_active, created_at FROM users")
    users = cur.fetchall()
    return [dict(u) for u in users]

@router.post("/users")
def create_user(req: UserCreate, admin_user: dict = Depends(require_admin), conn: sqlite3.Connection = Depends(get_db)):
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = ?", (req.username,))
    if cur.fetchone():
        raise HTTPException(status_code=400, detail="Username already exists")
    
    cur.execute(
        "INSERT INTO users (username, full_name, password_hash, role) VALUES (?, ?, ?, ?)",
        (req.username, req.full_name, hash_password(req.password), req.role)
    )
    uid = cur.lastrowid
    
    cur.execute("INSERT INTO audit_log (user_id, action, detail) VALUES (?, ?, ?)", (admin_user["id"], "create_user", f"Created user {req.username} ({req.role})"))
    conn.commit()
    
    return {"status": "created", "user_id": uid}
