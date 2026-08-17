import sqlite3
from fastapi import APIRouter, Depends
from ..database import get_db
from ..auth import require_superadmin

router = APIRouter(prefix="/api/audit-log", tags=["Audit Log"])

@router.get("")
def get_audit_log(limit: int = 100, conn: sqlite3.Connection = Depends(get_db), admin_user: dict = Depends(require_superadmin)):
    cur = conn.cursor()
    cur.execute("""
        SELECT a.id, a.user_id, u.username, a.action, a.detail, a.timestamp
        FROM audit_log a
        LEFT JOIN users u ON a.user_id = u.id
        ORDER BY a.timestamp DESC
        LIMIT ?
    """, (limit,))
    
    logs = cur.fetchall()
    return [dict(l) for l in logs]
