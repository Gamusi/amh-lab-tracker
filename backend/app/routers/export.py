import sqlite3
import datetime
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse, Response
from ..database import get_db
from ..auth import require_admin
from ..export_manager import (
    stream_clients_csv,
    stream_clients_json,
    generate_clients_xlsx,
    stream_results_csv,
    stream_results_json,
    generate_results_xlsx
)
from ..import_manager import (
    parse_import_payload,
    import_clients_records,
    import_results_records
)

logger = logging.getLogger("amh_export_api")

router = APIRouter(tags=["Bulk Data Export & Import"])

@router.get("/api/export/clients")
def export_clients(
    format: str = Query("csv", pattern="^(csv|json|xlsx)$"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    logger.info(f"Admin '{current_user['username']}' requested clients export (format={format}, start={start_date}, end={end_date})")
    filters = {"start_date": start_date, "end_date": end_date}
    today_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Audit log
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO audit_log (user_id, action, detail, timestamp) VALUES (?, 'BULK_EXPORT', ?, ?)",
        (current_user["id"], f"Exported clients registry ({format.upper()}) filters={filters}", now_str)
    )
    conn.commit()
    
    if format == "json":
        filename = f"clients_export_{today_str}.json"
        return StreamingResponse(
            stream_clients_json(conn, filters),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    elif format == "xlsx":
        filename = f"clients_export_{today_str}.xlsx"
        xlsx_bytes = generate_clients_xlsx(conn, filters)
        return Response(
            content=xlsx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    else:
        filename = f"clients_export_{today_str}.csv"
        return StreamingResponse(
            stream_clients_csv(conn, filters),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

@router.get("/api/export/results")
def export_results(
    format: str = Query("csv", pattern="^(csv|json|xlsx)$"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    ward: Optional[str] = None,
    section_id: Optional[int] = None,
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    logger.info(f"Admin '{current_user['username']}' requested results export (format={format}, start={start_date}, end={end_date}, ward={ward}, section_id={section_id})")
    filters = {
        "start_date": start_date,
        "end_date": end_date,
        "ward": ward,
        "section_id": section_id
    }
    today_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Audit log
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO audit_log (user_id, action, detail, timestamp) VALUES (?, 'BULK_EXPORT', ?, ?)",
        (current_user["id"], f"Exported diagnostic results ({format.upper()}) filters={filters}", now_str)
    )
    conn.commit()
    
    if format == "json":
        filename = f"lab_results_export_{today_str}.json"
        return StreamingResponse(
            stream_results_json(conn, filters),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    elif format == "xlsx":
        filename = f"lab_results_export_{today_str}.xlsx"
        xlsx_bytes = generate_results_xlsx(conn, filters)
        return Response(
            content=xlsx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    else:
        filename = f"lab_results_export_{today_str}.csv"
        return StreamingResponse(
            stream_results_csv(conn, filters),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

@router.post("/api/import/clients")
async def import_clients(
    request: Request,
    dry_run: bool = Query(False),
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    logger.info(f"Admin '{current_user['username']}' initiated clients import (dry_run={dry_run})")
    
    body = await request.body()
    try:
        records = parse_import_payload(body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not records:
        raise HTTPException(status_code=400, detail="No valid records found in payload.")
        
    result = import_clients_records(conn, records, dry_run=dry_run)
    
    # Audit log
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO audit_log (user_id, action, detail, timestamp) VALUES (?, 'BULK_IMPORT', ?, ?)",
        (current_user["id"], f"Imported clients (total={result['total']}, inserted={result['inserted']}, updated={result['updated']}, errors={len(result['errors'])}, dry_run={dry_run})", now_str)
    )
    conn.commit()
    
    return {"status": "ok", **result}

@router.post("/api/import/results")
async def import_results(
    request: Request,
    dry_run: bool = Query(False),
    conn: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    logger.info(f"Admin '{current_user['username']}' initiated results import (dry_run={dry_run})")
    
    body = await request.body()
    try:
        records = parse_import_payload(body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not records:
        raise HTTPException(status_code=400, detail="No valid records found in payload.")
        
    result = import_results_records(conn, records, dry_run=dry_run, current_user_id=current_user["id"])
    
    # Audit log
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO audit_log (user_id, action, detail, timestamp) VALUES (?, 'BULK_IMPORT', ?, ?)",
        (current_user["id"], f"Imported diagnostic results (total={result['total']}, inserted={result['inserted']}, updated={result['updated']}, errors={len(result['errors'])}, dry_run={dry_run})", now_str)
    )
    conn.commit()
    
    return {"status": "ok", **result}
