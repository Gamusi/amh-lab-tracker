import secrets
import hashlib
import datetime
import sqlite3
from fastapi import Request, HTTPException, Depends, status
from .database import get_db

def hash_password(password: str) -> str:
    salt = b"amh_lab_salt_2026_pbkdf2"
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return key.hex()

def verify_password(plain_password: str, password_hash: str) -> bool:
    return secrets.compare_digest(hash_password(plain_password), password_hash)

def create_session(conn: sqlite3.Connection, user_id: int) -> str:
    token = secrets.token_hex(32)
    expires_at = (datetime.datetime.utcnow() + datetime.timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO user_sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
        (user_id, token, expires_at)
    )
    conn.commit()
    return token

def get_current_user(request: Request, conn: sqlite3.Connection = Depends(get_db)):
    token = request.cookies.get("amh_session") or request.headers.get("Authorization")
    if token and token.startswith("Bearer "):
        token = token[7:]
    
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.cursor()
    cur.execute("""
        SELECT u.id, u.username, u.full_name, u.role, u.is_active
        FROM user_sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.token = ? AND s.expires_at > ?
    """, (token, now_str))
    
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired or invalid")
    
    if not row["is_active"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is disabled")
    
    return dict(row)

def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user
