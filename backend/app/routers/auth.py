import datetime, sqlite3, logging
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Response
from ..database import get_db
from typing import Optional
from ..schemas import LoginRequest, UserCreate, UserRegister, UserUpdate, ChangePasswordRequest
from ..auth import verify_password, hash_password, create_session, get_current_user, require_admin
from ..models import User

logger = logging.getLogger("amh_auth")

router = APIRouter(prefix="/api/auth", tags=["Auth"])

@router.post("/login")
def login(req: LoginRequest, response: Response, conn: sqlite3.Connection = Depends(get_db)):
    logger.info(f"Login attempt for user: '{req.username}'")
    cur = conn.cursor()
    cur.execute("SELECT id, username, full_name, password_hash, role, cadre, is_active, password_reset_required FROM users WHERE username = ?", (req.username,))
    user = cur.fetchone()
    
    if not user or not verify_password(req.password, user["password_hash"]):
        logger.warning(f"Failed login attempt: invalid credentials for '{req.username}'")
        raise HTTPException(status_code=400, detail="Invalid username or password")
    
    if not user["is_active"]:
        logger.warning(f"Failed login attempt: account '{req.username}' is disabled or pending approval")
        raise HTTPException(status_code=400, detail="Account is disabled or pending admin approval")
    
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
    status_str = "reset_required" if user["password_reset_required"] else "success"
    return {
        "status": status_str,
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "role": user["role"],
            "cadre": user["cadre"],
            "password_reset_required": bool(user["password_reset_required"])
        }
    }

@router.post("/logout")
def logout(response: Response, current_user: User = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    response.delete_cookie("amh_session")
    conn.execute("INSERT INTO audit_log (user_id, action, detail) VALUES (?, ?, ?)", (current_user["id"], "logout", f"User {current_user['username']} logged out"))
    conn.commit()
    logger.info(f"Logout successful: user '{current_user['username']}' logged out")
    return {"status": "logged out"}

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "full_name": current_user["full_name"],
        "role": current_user["role"],
        "cadre": current_user["cadre"],
        "password_reset_required": bool(current_user["password_reset_required"])
    }

@router.post("/change-password")
def change_password(req: ChangePasswordRequest, current_user: User = Depends(get_current_user), conn: sqlite3.Connection = Depends(get_db)):
    logger.info(f"Password change requested for user '{current_user['username']}'")
    cur = conn.cursor()
    cur.execute("SELECT id, username, password_hash FROM users WHERE id = ?", (current_user["id"],))
    user = cur.fetchone()
    
    if not user or not verify_password(req.old_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
        
    if not req.new_password or len(req.new_password.strip()) < 4:
        raise HTTPException(status_code=400, detail="New password must be at least 4 characters")
        
    new_hash = hash_password(req.new_password)
    cur.execute(
        "UPDATE users SET password_hash = ?, password_reset_required = 0 WHERE id = ?",
        (new_hash, current_user["id"])
    )
    cur.execute(
        "INSERT INTO audit_log (user_id, action, detail) VALUES (?, ?, ?)",
        (current_user["id"], "change_password", f"User {user['username']} changed their password")
    )
    conn.commit()
    logger.info(f"Password changed successfully for user '{user['username']}'")
    return {"status": "success", "message": "Password changed successfully"}

class AdminResetPasswordRequest(BaseModel):
    temporary_password: Optional[str] = None

@router.post("/users/{user_id}/reset-password")
def admin_reset_password(
    user_id: int,
    req: Optional[AdminResetPasswordRequest] = None,
    admin_user: User = Depends(require_admin),
    conn: sqlite3.Connection = Depends(get_db)
):
    cur = conn.cursor()
    cur.execute("SELECT id, username, role FROM users WHERE id = ?", (user_id,))
    target_user = cur.fetchone()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if admin_user["role"] == "admin" and target_user["role"] in ["admin", "superadmin"] and target_user["id"] != admin_user["id"]:
        raise HTTPException(status_code=403, detail="Admins can only reset passwords for staff accounts.")

    temp_pass = (req.temporary_password if req and req.temporary_password else "").strip() or "AMH@1234"
    new_hash = hash_password(temp_pass)

    cur.execute(
        "UPDATE users SET password_hash = ?, password_reset_required = 1 WHERE id = ?",
        (new_hash, user_id)
    )
    now_str = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        "INSERT INTO audit_log (user_id, action, detail, timestamp) VALUES (?, 'ADMIN_RESET_PASSWORD', ?, ?)",
        (admin_user["id"], f"Reset password for user {target_user['username']} (ID {user_id})", now_str)
    )
    conn.commit()

    return {
        "status": "success",
        "message": f"Password for {target_user['username']} has been reset.",
        "temporary_password": temp_pass
    }

@router.get("/users")
def list_users(admin_user: User = Depends(require_admin), conn: sqlite3.Connection = Depends(get_db)):
    cur = conn.cursor()
    cur.execute("SELECT id, username, full_name, role, cadre, is_active, password_reset_required, created_at FROM users")
    users = cur.fetchall()
    return [dict(u) for u in users]

@router.post("/users")
def create_user(req: UserCreate, admin_user: User = Depends(require_admin), conn: sqlite3.Connection = Depends(get_db)):
    logger.info(f"Admin '{admin_user['username']}' is creating user: '{req.username}' (Role: {req.role})")
    
    if admin_user["role"] == "admin" and req.role == "superadmin":
        raise HTTPException(status_code=403, detail="Admins cannot create Superadmin accounts.")
        
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = ?", (req.username,))
    if cur.fetchone():
        logger.warning(f"User creation failed: username '{req.username}' already exists")
        raise HTTPException(status_code=400, detail="Username already exists")
    
    cur.execute(
        "INSERT INTO users (username, full_name, password_hash, role, cadre) VALUES (?, ?, ?, ?, ?)",
        (req.username, req.full_name, hash_password(req.password), req.role, req.cadre)
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
    
    # First-run bootstrap check: if no users exist in the DB, make this first user an active superadmin
    cur.execute("SELECT COUNT(*) as count FROM users")
    count = cur.fetchone()["count"]
    
    if count == 0:
        role = "superadmin"
        is_active = 1
        logger.info(f"First-run bootstrap: promoting first user '{req.username}' to active superadmin")
    else:
        role = "staff"
        is_active = 0
        logger.info(f"Standard registration: user '{req.username}' registered as pending staff")
        
    cur.execute(
        "INSERT INTO users (username, full_name, password_hash, role, cadre, is_active) VALUES (?, ?, ?, ?, ?, ?)",
        (req.username, req.full_name, hash_password(req.password), role, req.cadre, is_active)
    )
    uid = cur.lastrowid
    conn.commit()
    
    # Audit log the user creation
    # If this is first superadmin, audit log under their own ID, else under user ID None (system registration)
    actor_id = uid if role == "superadmin" else None
    cur.execute("INSERT INTO audit_log (user_id, action, detail) VALUES (?, ?, ?)",
                (actor_id, "register", f"User {req.username} self-registered as {role} (Active: {is_active})"))
    conn.commit()
    
    logger.info(f"User registered successfully: '{req.username}' with ID {uid} (Role: {role}, Active: {is_active})")
    return {"status": "registered", "user_id": uid, "is_active": bool(is_active)}

@router.put("/users/{user_id}")
def update_user(user_id: int, req: UserUpdate, admin_user: User = Depends(require_admin), conn: sqlite3.Connection = Depends(get_db)):
    logger.info(f"Admin '{admin_user['username']}' is updating user ID {user_id}: role={req.role}, active={req.is_active}")
    
    if user_id == admin_user["id"] and (req.role != admin_user["role"] or not req.is_active):
        raise HTTPException(status_code=400, detail="Admins cannot deactivate or demote themselves to avoid lockouts.")
        
    cur = conn.cursor()
    cur.execute("SELECT id, role FROM users WHERE id = ?", (user_id,))
    target_user = cur.fetchone()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Prevent anyone from being promoted to superadmin
    if target_user["role"] != "superadmin" and req.role == "superadmin":
        raise HTTPException(status_code=403, detail="Cannot promote a user to Superadmin. Only one Superadmin is allowed.")
        
    if admin_user["role"] == "admin" and (target_user["role"] == "superadmin" or req.role == "superadmin"):
        raise HTTPException(status_code=403, detail="Admins cannot modify or create Superadmin accounts.")
        
    if req.password:
        cur.execute(
            "UPDATE users SET role = ?, cadre = ?, is_active = ?, password_hash = ?, password_reset_required = 1 WHERE id = ?",
            (req.role, req.cadre, 1 if req.is_active else 0, hash_password(req.password), user_id)
        )
    else:
        cur.execute(
            "UPDATE users SET role = ?, cadre = ?, is_active = ? WHERE id = ?",
            (req.role, req.cadre, 1 if req.is_active else 0, user_id)
        )
    conn.commit()
    
    cur.execute("INSERT INTO audit_log (user_id, action, detail) VALUES (?, ?, ?)",
                (admin_user["id"], "update_user", f"Updated user ID {user_id}: role={req.role}, cadre={req.cadre}, active={req.is_active}, pw_reset={bool(req.password)}"))
    conn.commit()
    
    logger.info(f"User ID {user_id} updated successfully by admin '{admin_user['username']}'")
    return {"status": "updated"}

@router.delete("/users/{user_id}")
def delete_user(user_id: int, admin_user: User = Depends(require_admin), conn: sqlite3.Connection = Depends(get_db)):
    logger.info(f"Admin '{admin_user['username']}' is deleting user ID {user_id}")
    
    if user_id == admin_user["id"]:
        raise HTTPException(status_code=400, detail="Admins cannot delete their own account.")
        
    cur = conn.cursor()
    cur.execute("SELECT id, username, role FROM users WHERE id = ?", (user_id,))
    target_user = cur.fetchone()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if admin_user["role"] == "admin" and target_user["role"] == "superadmin":
        raise HTTPException(status_code=403, detail="Admins cannot delete Superadmin accounts.")
        
    cur.execute("DELETE FROM user_sessions WHERE user_id = ?", (user_id,))
    cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
    cur.execute("INSERT INTO audit_log (user_id, action, detail) VALUES (?, ?, ?)",
                (admin_user["id"], "delete_user", f"Deleted user {target_user['username']} (ID {user_id})"))
    conn.commit()
    
    logger.info(f"User ID {user_id} deleted successfully by admin '{admin_user['username']}'")
    return {"status": "deleted"}
