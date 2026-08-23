import os
import secrets
import hashlib
import datetime
import sqlite3
from fastapi import Request, HTTPException, Depends, status
from .database import get_db
from .models import User

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return f"{salt.hex()}${key.hex()}"

def verify_password(plain_password: str, stored_string: str) -> bool:
    salt_hex, stored_hash_hex = stored_string.split('$')
    salt = bytes.fromhex(salt_hex)
    new_key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 100000)
    return secrets.compare_digest(new_key.hex(), stored_hash_hex)

def create_session(conn: sqlite3.Connection, user_id: int) -> str:
    token = secrets.token_hex(32)
    expires_at = (datetime.datetime.utcnow() + datetime.timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO user_sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
        (user_id, token, expires_at)
    )
    conn.commit()
    return token

def get_current_user(request: Request, conn: sqlite3.Connection = Depends(get_db)) -> User:
    token = request.cookies.get("amh_session") or request.headers.get("Authorization")
    if token and token.startswith("Bearer "):
        token = token[7:]
    
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.cursor()
    cur.execute("""
        SELECT u.id, u.username, u.full_name, u.role, u.cadre, u.is_active, u.password_reset_required, s.expires_at
        FROM user_sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.token = ? AND s.expires_at > ?
    """, (token, now_str))
    
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired or invalid")
    
    if not row["is_active"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is disabled")
    
    # Throttle DB writes: only update expires_at if less than 10 minutes (600 seconds) remain on current session
    expires_dt = datetime.datetime.strptime(row["expires_at"], "%Y-%m-%d %H:%M:%S")
    time_remaining = (expires_dt - datetime.datetime.utcnow()).total_seconds()
    if time_remaining < 600:
        new_expires_at = (datetime.datetime.utcnow() + datetime.timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("UPDATE user_sessions SET expires_at = ? WHERE token = ?", (new_expires_at, token))
        conn.commit()
    
    return User(
        id=row["id"],
        full_name=row["full_name"],
        username=row["username"],
        role=row["role"],
        cadre=row["cadre"],
        is_active=bool(row["is_active"]),
        password_reset_required=bool(row["password_reset_required"])
    )

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user["role"] not in ("admin", "superadmin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user

def require_superadmin(current_user: User = Depends(get_current_user)) -> User:
    if current_user["role"] != "superadmin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super Admin privileges required")
    return current_user
