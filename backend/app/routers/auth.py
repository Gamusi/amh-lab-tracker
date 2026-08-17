import datetime, sqlite3, logging
from fastapi import APIRouter, Depends, HTTPException, Response, status
from ..database import get_db
from typing import Optional
from ..schemas import LoginRequest, UserCreate, UserRegister, UserUpdate
from ..auth import verify_password, hash_password, create_session, get_current_user, require_admin

logger = logging.getLogger("amh_auth")

router = APIRouter(prefix="/api/auth", tags=["Auth"])

@router.post("/login")
def login(req: LoginRequest, response: Response, conn: sqlite3.Connection = Depends(get_db)):
    logger.info(f"Login attempt for user: '{req.username}'")
    cur = conn.cursor()
    cur.execute("SELECT id, username, full_name, password_hash, role, is_active FROM users WHERE username = ?", (req.username,))
    user = cur.fetchone()
    
    if not user or not verify_password(req.password, user["password_hash"]):
        logger.warning(f"Failed login attempt: invalid credentials for '{req.username}'")
        raise HTTPException(status_code=400, detail="Invalid username or password")
    
    if not user["is_active"]:
        logger.warning(f"Failed login attempt: account '{req.username}' is disabled")
        raise HTTPException(status_code=400, detail="Account is disabled")
    
    token = create_session(conn, user["id"])
    response.set_cookie(
        key="amh_session",
        value=token,
        httponly=True,
        samesite="lax"
    )
    
    cur.execute("INSERT INTO audit_log (user_id, action, detail) VALUES (?, ?, ?)", (user["id"], "login", f"User {user['username']} logged in"))
    conn.commit()
    
    logger.info(f"Login successful: user '{req.username}' logged in successfully (Role: {user['role']})")
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
    logger.info(f"Logout successful: user '{current_user['username']}' logged out")
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
    logger.info(f"Admin '{admin_user['username']}' is creating user: '{req.username}' (Role: {req.role})")
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = ?", (req.username,))
    if cur.fetchone():
        logger.warning(f"User creation failed: username '{req.username}' already exists")
        raise HTTPException(status_code=400, detail="Username already exists")
    
    cur.execute(
        "INSERT INTO users (username, full_name, password_hash, role) VALUES (?, ?, ?, ?)",
        (req.username, req.full_name, hash_password(req.password), req.role)
    )
    uid = cur.lastrowid
    
    cur.execute("INSERT INTO audit_log (user_id, action, detail) VALUES (?, ?, ?)", (admin_user["id"], "create_user", f"Created user {req.username} ({req.role})"))
    conn.commit()
    
    logger.info(f"User created successfully: '{req.username}' with ID {uid}")
    return {"status": "created", "user_id": uid}

@router.post("/register")
def register(req: UserRegister, conn: sqlite3.Connection = Depends(get_db)):
    logger.info(f"Registration attempt for username: '{req.username}'")
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = ?", (req.username,))
    if cur.fetchone():
        logger.warning(f"Registration failed: username '{req.username}' already exists")
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # First-run bootstrap check: if no users exist in the DB, make this first user an active admin
    cur.execute("SELECT COUNT(*) as count FROM users")
    count = cur.fetchone()["count"]
    
    if count == 0:
        role = "admin"
        is_active = 1
        logger.info(f"First-run bootstrap: promoting first user '{req.username}' to active admin")
    else:
        role = "technician"
        is_active = 0
        logger.info(f"Standard registration: user '{req.username}' registered as pending technician")
        
    cur.execute(
        "INSERT INTO users (username, full_name, password_hash, role, is_active) VALUES (?, ?, ?, ?, ?)",
        (req.username, req.full_name, hash_password(req.password), role, is_active)
    )
    uid = cur.lastrowid
    conn.commit()
    
    # Audit log the user creation
    # If this is first admin, audit log under their own ID, else under user ID 0 (system registration)
    actor_id = uid if role == "admin" else None
    cur.execute("INSERT INTO audit_log (user_id, action, detail) VALUES (?, ?, ?)",
                (actor_id, "register", f"User {req.username} self-registered as {role} (Active: {is_active})"))
    conn.commit()
    
    logger.info(f"User registered successfully: '{req.username}' with ID {uid} (Role: {role}, Active: {is_active})")
    return {"status": "registered", "user_id": uid, "is_active": bool(is_active)}

@router.put("/users/{user_id}")
def update_user(user_id: int, req: UserUpdate, admin_user: dict = Depends(require_admin), conn: sqlite3.Connection = Depends(get_db)):
    logger.info(f"Admin '{admin_user['username']}' is updating user ID {user_id}: role={req.role}, active={req.is_active}")
    
    if user_id == admin_user["id"] and (req.role != "admin" or not req.is_active):
        raise HTTPException(status_code=400, detail="Administrators cannot deactivate or demote themselves to avoid lockouts.")
        
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="User not found")
        
    if req.password:
        cur.execute(
            "UPDATE users SET role = ?, is_active = ?, password_hash = ? WHERE id = ?",
            (req.role, 1 if req.is_active else 0, hash_password(req.password), user_id)
        )
    else:
        cur.execute(
            "UPDATE users SET role = ?, is_active = ? WHERE id = ?",
            (req.role, 1 if req.is_active else 0, user_id)
        )
    conn.commit()
    
    cur.execute("INSERT INTO audit_log (user_id, action, detail) VALUES (?, ?, ?)",
                (admin_user["id"], "update_user", f"Updated user ID {user_id}: role={req.role}, active={req.is_active}"))
    conn.commit()
    
    logger.info(f"User ID {user_id} updated successfully by admin '{admin_user['username']}'")
    return {"status": "updated"}
