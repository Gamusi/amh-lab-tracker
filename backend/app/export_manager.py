import io
import csv
import json
import sqlite3
from typing import Iterator, Dict, Any, Optional

CLIENT_CSV_HEADERS = [
    "client_number",
    "full_name",
    "date_of_birth",
    "age_years",
    "age_category",
    "sex",
    "phone",
    "created_at"
]

RESULTS_CSV_HEADERS = [
    "lab_number",
    "visit_date",
    "ward_of_origin",
    "order_category",
    "client_number",
    "full_name",
    "sex",
    "age_years",
    "age_category",
    "clinician_name",
    "section_name",
    "test_name",
    "parameter_name",
    "result_value",
    "result_unit",
    "clinical_flag",
    "is_positive",
    "entered_by",
    "entered_at",
    "verified_by",
    "verified_at"
]

def stream_clients_csv(conn: sqlite3.Connection, filters: Optional[Dict[str, Any]] = None) -> Iterator[str]:
    filters = filters or {}
    start_date = filters.get("start_date")
    end_date = filters.get("end_date")
    
    query = "SELECT client_number, full_name, date_of_birth, age_years, age_category, sex, phone, created_at FROM clients WHERE 1=1"
    params = []
    
    if start_date:
        query += " AND date(created_at) >= date(?)"
        params.append(start_date)
    if end_date:
        query += " AND date(created_at) <= date(?)"
        params.append(end_date)
        
    query += " ORDER BY id ASC"
    
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(CLIENT_CSV_HEADERS)
    yield buf.getvalue()
    buf.seek(0)
    buf.truncate(0)
    
    cur = conn.cursor()
    cur.execute(query, params)
    
    while True:
        rows = cur.fetchmany(500)
        if not rows:
            break
        for row in rows:
            writer.writerow([
                row[0] or "",
                row[1] or "",
                row[2] or "",
                row[3] if row[3] is not None else "",
                row[4] or "",
                row[5] or "",
                row[6] or "",
                row[7] or ""
            ])
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)

def stream_clients_json(conn: sqlite3.Connection, filters: Optional[Dict[str, Any]] = None) -> Iterator[str]:
    filters = filters or {}
    start_date = filters.get("start_date")
    end_date = filters.get("end_date")
    
    query = "SELECT client_number, full_name, date_of_birth, age_years, age_category, sex, phone, created_at FROM clients WHERE 1=1"
    params = []
    
    if start_date:
        query += " AND date(created_at) >= date(?)"
        params.append(start_date)
    if end_date:
        query += " AND date(created_at) <= date(?)"
        params.append(end_date)
        
    query += " ORDER BY id ASC"
    
    cur = conn.cursor()
    cur.execute(query, params)
    
    yield "[\n"
    first = True
    
    while True:
        rows = cur.fetchmany(500)
        if not rows:
            break
        for row in rows:
            item = {
                "client_number": row[0] or "",
                "full_name": row[1] or "",
                "date_of_birth": row[2] or "",
                "age_years": row[3],
                "age_category": row[4] or "",
                "sex": row[5] or "",
                "phone": row[6] or "",
                "created_at": row[7] or ""
            }
            line = ("" if first else ",\n") + "  " + json.dumps(item)
            first = False
            yield line
            
    yield "\n]"

def stream_results_csv(conn: sqlite3.Connection, filters: Optional[Dict[str, Any]] = None) -> Iterator[str]:
    filters = filters or {}
    start_date = filters.get("start_date")
    end_date = filters.get("end_date")
    ward = filters.get("ward")
    section_id = filters.get("section_id")
    
    query = """
SELECT 
    v.lab_number,
    v.created_at AS visit_date,
    v.ward_of_origin,
    v.order_category,
    c.client_number,
    c.full_name,
    c.sex,
    c.age_years,
    c.age_category,
    cl.name AS clinician_name,
    s.name AS section_name,
    t.name AS test_name,
    tp.parameter_name,
    tr.result_value,
    tr.result_unit,
    tr.clinical_flag,
    tr.is_positive,
    u_enter.username AS entered_by,
    tr.entered_at,
    u_ver.username AS verified_by,
    tr.verified_at
FROM test_results tr
JOIN test_orders ord ON tr.order_id = ord.id
JOIN tests t ON ord.test_id = t.id
JOIN sections s ON t.section_id = s.id
JOIN visits v ON ord.visit_id = v.id
JOIN clients c ON v.client_id = c.id
LEFT JOIN test_parameters tp ON tr.parameter_id = tp.id
LEFT JOIN clinicians cl ON v.clinician_id = cl.id
LEFT JOIN users u_enter ON tr.entered_by_user_id = u_enter.id
LEFT JOIN users u_ver ON tr.verified_by_user_id = u_ver.id
WHERE v.is_deleted = 0
"""
    params = []
    
    if start_date:
        query += " AND date(v.created_at) >= date(?)"
        params.append(start_date)
    if end_date:
        query += " AND date(v.created_at) <= date(?)"
        params.append(end_date)
    if ward:
        query += " AND v.ward_of_origin = ?"
        params.append(ward)
    if section_id:
        query += " AND t.section_id = ?"
        params.append(section_id)
        
    query += " ORDER BY tr.id ASC"
    
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(RESULTS_CSV_HEADERS)
    yield buf.getvalue()
    buf.seek(0)
    buf.truncate(0)
    
    cur = conn.cursor()
    cur.execute(query, params)
    
    while True:
        rows = cur.fetchmany(500)
        if not rows:
            break
        for row in rows:
            writer.writerow([
                row[0] or "",
                row[1] or "",
                row[2] or "",
                row[3] or "in-house",
                row[4] or "",
                row[5] or "",
                row[6] or "",
                row[7] if row[7] is not None else "",
                row[8] or "",
                row[9] or "",
                row[10] or "",
                row[11] or "",
                row[12] or "",
                row[13] or "",
                row[14] or "",
                row[15] or "",
                1 if row[16] else 0 if row[16] is not None else "",
                row[17] or "",
                row[18] or "",
                row[19] or "",
                row[20] or ""
            ])
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)

def stream_results_json(conn: sqlite3.Connection, filters: Optional[Dict[str, Any]] = None) -> Iterator[str]:
    filters = filters or {}
    start_date = filters.get("start_date")
    end_date = filters.get("end_date")
    ward = filters.get("ward")
    section_id = filters.get("section_id")
    
    query = """
SELECT 
    v.lab_number,
    v.created_at AS visit_date,
    v.ward_of_origin,
    v.order_category,
    c.client_number,
    c.full_name,
    c.sex,
    c.age_years,
    c.age_category,
    cl.name AS clinician_name,
    s.name AS section_name,
    t.name AS test_name,
    tp.parameter_name,
    tr.result_value,
    tr.result_unit,
    tr.clinical_flag,
    tr.is_positive,
    u_enter.username AS entered_by,
    tr.entered_at,
    u_ver.username AS verified_by,
    tr.verified_at
FROM test_results tr
JOIN test_orders ord ON tr.order_id = ord.id
JOIN tests t ON ord.test_id = t.id
JOIN sections s ON t.section_id = s.id
JOIN visits v ON ord.visit_id = v.id
JOIN clients c ON v.client_id = c.id
LEFT JOIN test_parameters tp ON tr.parameter_id = tp.id
LEFT JOIN clinicians cl ON v.clinician_id = cl.id
LEFT JOIN users u_enter ON tr.entered_by_user_id = u_enter.id
LEFT JOIN users u_ver ON tr.verified_by_user_id = u_ver.id
WHERE v.is_deleted = 0
"""
    params = []
    
    if start_date:
        query += " AND date(v.created_at) >= date(?)"
        params.append(start_date)
    if end_date:
        query += " AND date(v.created_at) <= date(?)"
        params.append(end_date)
    if ward:
        query += " AND v.ward_of_origin = ?"
        params.append(ward)
    if section_id:
        query += " AND t.section_id = ?"
        params.append(section_id)
        
    query += " ORDER BY tr.id ASC"
    
    cur = conn.cursor()
    cur.execute(query, params)
    
    yield "[\n"
    first = True
    
    while True:
        rows = cur.fetchmany(500)
        if not rows:
            break
        for row in rows:
            item = {
                "lab_number": row[0] or "",
                "visit_date": row[1] or "",
                "ward_of_origin": row[2] or "",
                "order_category": row[3] or "in-house",
                "client_number": row[4] or "",
                "full_name": row[5] or "",
                "sex": row[6] or "",
                "age_years": row[7],
                "age_category": row[8] or "",
                "clinician_name": row[9] or "",
                "section_name": row[10] or "",
                "test_name": row[11] or "",
                "parameter_name": row[12] or "",
                "result_value": row[13] or "",
                "result_unit": row[14] or "",
                "clinical_flag": row[15] or "",
                "is_positive": 1 if row[16] else 0 if row[16] is not None else None,
                "entered_by": row[17] or "",
                "entered_at": row[18] or "",
                "verified_by": row[19] or "",
                "verified_at": row[20] or ""
            }
            line = ("" if first else ",\n") + "  " + json.dumps(item)
            first = False
            yield line
            
    yield "\n]"
