import io
import csv
import json
import sqlite3
import datetime
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("amh_import")

def parse_import_payload(raw_content: Any, filename: Optional[str] = None) -> List[Dict[str, Any]]:
    raw_bytes = None
    if isinstance(raw_content, bytes):
        raw_bytes = raw_content
    elif isinstance(raw_content, str):
        raw_bytes = raw_content.encode("utf-8")

    if not raw_bytes or len(raw_bytes) == 0:
        return []

    # Check for XLSX format (magic bytes b'PK\x03\x04' or filename ending with .xlsx)
    if raw_bytes.startswith(b'PK\x03\x04') or (filename and filename.lower().endswith(".xlsx")):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(raw_bytes), read_only=True, data_only=True)
            ws = wb.active
            rows_iter = ws.iter_rows(values_only=True)
            headers = next(rows_iter, None)
            if not headers:
                return []
            
            norm_headers = [
                str(h).strip().lower().replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "") if h is not None else f"col_{i}"
                for i, h in enumerate(headers)
            ]
            
            records = []
            for row in rows_iter:
                if row is None or all(c is None or str(c).strip() == "" for c in row):
                    continue
                clean_row = {}
                for h, val in zip(norm_headers, row):
                    if h:
                        if isinstance(val, (datetime.date, datetime.datetime)):
                            clean_row[h] = val.isoformat()
                        elif val is not None:
                            clean_row[h] = str(val).strip()
                        else:
                            clean_row[h] = ""
                records.append(clean_row)
            return records
        except Exception as e:
            logger.warning(f"Failed XLSX parsing: {e}")
            raise ValueError(f"Failed to parse Excel (.xlsx) file: {str(e)}")

    # JSON or CSV
    text_content = raw_bytes.decode("utf-8", errors="replace").strip()
    if text_content.startswith("[") or (filename and filename.lower().endswith(".json")):
        try:
            parsed = json.loads(text_content)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                return [parsed]
        except Exception as e:
            logger.warning(f"Failed JSON parsing: {e}")
            
    # CSV Parsing
    reader = csv.DictReader(io.StringIO(text_content))
    records = []
    for row in reader:
        clean_row = {}
        for k, v in row.items():
            if k:
                norm_k = k.strip().lower().replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "")
                clean_row[norm_k] = v.strip() if isinstance(v, str) else v
        records.append(clean_row)
    return records

def get_or_create_client(cur: sqlite3.Cursor, record: Dict[str, Any]) -> Tuple[int, str, bool]:
    c_num = record.get("client_number") or record.get("client_no")
    name = record.get("full_name") or record.get("name") or "Unknown Client"
    dob = record.get("date_of_birth") or record.get("dob")
    age_yrs = record.get("age_years") or record.get("age")
    age_cat = record.get("age_category")
    sex = record.get("sex") or record.get("gender")
    phone = record.get("phone") or record.get("phone_number")
    created_at = record.get("created_at")
    
    try:
        age_yrs_val = float(age_yrs) if age_yrs not in (None, "") else None
    except (ValueError, TypeError):
        age_yrs_val = None

    if c_num:
        cur.execute("SELECT id, client_number FROM clients WHERE client_number = ?", (c_num,))
        existing = cur.fetchone()
        if existing:
            cid = existing["id"]
            cur.execute("""
                UPDATE clients
                SET full_name = COALESCE(NULLIF(?, ''), full_name),
                    date_of_birth = COALESCE(NULLIF(?, ''), date_of_birth),
                    age_years = COALESCE(?, age_years),
                    age_category = COALESCE(NULLIF(?, ''), age_category),
                    sex = COALESCE(NULLIF(?, ''), sex),
                    phone = COALESCE(NULLIF(?, ''), phone)
                WHERE id = ?
            """, (name, dob, age_yrs_val, age_cat, sex, phone, cid))
            return cid, c_num, False

    # Create new client
    today = datetime.date.today()
    yy_str = today.strftime("%y")
    seq_name = f"client_number_{yy_str}"
    cur.execute("INSERT OR IGNORE INTO sequence_tracker (seq_name, last_value) VALUES (?, 0)", (seq_name,))
    cur.execute("UPDATE sequence_tracker SET last_value = last_value + 1 WHERE seq_name = ?", (seq_name,))
    cur.execute("SELECT last_value FROM sequence_tracker WHERE seq_name = ?", (seq_name,))
    seq_row = cur.fetchone()
    seq_val = seq_row["last_value"] if seq_row else 1
    gen_client_number = c_num or f"AMH-C{yy_str}-{seq_val:04d}"
    
    if created_at:
        cur.execute("""
            INSERT INTO clients (client_number, full_name, date_of_birth, age_years, age_category, sex, phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (gen_client_number, name, dob, age_yrs_val, age_cat, sex, phone, created_at))
    else:
        cur.execute("""
            INSERT INTO clients (client_number, full_name, date_of_birth, age_years, age_category, sex, phone)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (gen_client_number, name, dob, age_yrs_val, age_cat, sex, phone))
        
    return cur.lastrowid, gen_client_number, True

def import_clients_records(conn: sqlite3.Connection, records: List[Dict[str, Any]], dry_run: bool = False) -> Dict[str, Any]:
    cur = conn.cursor()
    inserted = 0
    updated = 0
    errors = []
    
    for idx, rec in enumerate(records, 1):
        try:
            name = rec.get("full_name") or rec.get("name")
            if not name and not rec.get("client_number"):
                errors.append(f"Row {idx}: missing required full_name or client_number")
                continue
                
            _, _, is_new = get_or_create_client(cur, rec)
            if is_new:
                inserted += 1
            else:
                updated += 1
        except Exception as e:
            errors.append(f"Row {idx}: {str(e)}")
            
    if dry_run:
        conn.rollback()
    else:
        conn.commit()
        
    return {
        "total": len(records),
        "processed": inserted + updated,
        "inserted": inserted,
        "updated": updated,
        "errors": errors,
        "dry_run": dry_run
    }

def import_results_records(conn: sqlite3.Connection, records: List[Dict[str, Any]], dry_run: bool = False, current_user_id: int = 1) -> Dict[str, Any]:
    cur = conn.cursor()
    inserted = 0
    updated = 0
    errors = []
    
    # Cache test names and parameters
    cur.execute("SELECT id, name, section_id FROM tests")
    test_cache = {row["name"].strip().lower(): dict(row) for row in cur.fetchall()}
    
    cur.execute("SELECT id, test_id, parameter_name FROM test_parameters")
    param_cache = {}
    for row in cur.fetchall():
        key = (row["test_id"], row["parameter_name"].strip().lower())
        param_cache[key] = row["id"]
        
    cur.execute("SELECT id, username FROM users")
    user_cache = {row["username"].lower(): row["id"] for row in cur.fetchall()}
    
    cur.execute("SELECT id, name FROM clinicians")
    clinician_cache = {row["name"].strip().lower(): row["id"] for row in cur.fetchall()}
    
    for idx, rec in enumerate(records, 1):
        try:
            test_name = (rec.get("test_name") or rec.get("test") or "").strip()
            if not test_name:
                errors.append(f"Row {idx}: Missing test_name")
                continue
                
            t_obj = test_cache.get(test_name.lower())
            if not t_obj:
                errors.append(f"Row {idx}: Test '{test_name}' not found in system catalog")
                continue
            test_id = t_obj["id"]
            
            # Resolve or create Client
            cid, _, _ = get_or_create_client(cur, rec)
            
            # Resolve Clinician
            clinician_name = (rec.get("clinician_name") or rec.get("clinician") or "").strip()
            clinician_id = None
            if clinician_name:
                c_key = clinician_name.lower()
                if c_key in clinician_cache:
                    clinician_id = clinician_cache[c_key]
                else:
                    cur.execute("INSERT OR IGNORE INTO clinicians (name, is_active) VALUES (?, 1)", (clinician_name,))
                    cur.execute("SELECT id FROM clinicians WHERE name = ?", (clinician_name,))
                    c_row = cur.fetchone()
                    clinician_id = c_row["id"] if c_row else None
                    if clinician_id:
                        clinician_cache[c_key] = clinician_id
                        
            # Resolve Visit
            lab_number = (rec.get("lab_number") or rec.get("lab_no") or "").strip() or None
            ward = (rec.get("ward_of_origin") or rec.get("ward") or "OPD").strip() or "OPD"
            order_category = rec.get("order_category") or "in-house"
            visit_date = rec.get("visit_date") or rec.get("created_at") or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            visit_id = None
            if lab_number:
                cur.execute("SELECT id FROM visits WHERE lab_number = ?", (lab_number,))
                v_row = cur.fetchone()
                if v_row:
                    visit_id = v_row["id"]
                    
            if not visit_id:
                if not lab_number:
                    today_dt = datetime.date.today()
                    seq_key = f"lab_num_{today_dt.strftime('%Y%m%d')}"
                    cur.execute("INSERT OR IGNORE INTO sequence_tracker (seq_name, last_value) VALUES (?, 0)", (seq_key,))
                    cur.execute("UPDATE sequence_tracker SET last_value = last_value + 1 WHERE seq_name = ?", (seq_key,))
                    cur.execute("SELECT last_value FROM sequence_tracker WHERE seq_name = ?", (seq_key,))
                    s_row = cur.fetchone()
                    s_val = s_row["last_value"] if s_row else 1
                    lab_number = f"AMH-{today_dt.strftime('%y-%m')}-{s_val:03d}"
                    
                cur.execute("""
                    INSERT INTO visits (client_id, clinician_id, ward_of_origin, lab_number, order_category, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (cid, clinician_id, ward, lab_number, order_category, visit_date))
                visit_id = cur.lastrowid
                
            # Resolve Test Order
            cur.execute("SELECT id FROM test_orders WHERE visit_id = ? AND test_id = ?", (visit_id, test_id))
            ord_row = cur.fetchone()
            if ord_row:
                order_id = ord_row["id"]
            else:
                cur.execute("""
                    INSERT INTO test_orders (visit_id, test_id, ordered_by_user_id, ordered_at, status, order_category)
                    VALUES (?, ?, ?, ?, 'completed', ?)
                """, (visit_id, test_id, current_user_id, visit_date, order_category))
                order_id = cur.lastrowid
                
            # Resolve Parameter
            parameter_name = (rec.get("parameter_name") or rec.get("parameter") or "").strip()
            parameter_id = None
            if parameter_name:
                pkey = (test_id, parameter_name.lower())
                parameter_id = param_cache.get(pkey)
                
            # User attribution
            entered_by_user = (rec.get("entered_by") or "").strip().lower()
            entered_by_id = user_cache.get(entered_by_user) if entered_by_user in user_cache else current_user_id
            entered_at = rec.get("entered_at") or visit_date
            
            verified_by_user = (rec.get("verified_by") or "").strip().lower()
            verified_by_id = user_cache.get(verified_by_user) if verified_by_user in user_cache else None
            verified_at = rec.get("verified_at")
            
            result_val = rec.get("result_value") or rec.get("result") or ""
            result_unit = rec.get("result_unit") or rec.get("unit") or ""
            clinical_flag = rec.get("clinical_flag") or "NORMAL"
            is_pos_val = rec.get("is_positive")
            if is_pos_val in (1, "1", True, "true", "True"):
                is_pos = 1
            elif is_pos_val in (0, "0", False, "false", "False"):
                is_pos = 0
            else:
                is_pos = None
                
            if parameter_id:
                cur.execute("SELECT id FROM test_results WHERE order_id = ? AND parameter_id = ?", (order_id, parameter_id))
            else:
                cur.execute("SELECT id FROM test_results WHERE order_id = ? AND parameter_id IS NULL", (order_id,))
                
            existing_res = cur.fetchone()
            if existing_res:
                rid = existing_res["id"]
                cur.execute("""
                    UPDATE test_results
                    SET result_value = ?,
                        result_unit = ?,
                        clinical_flag = ?,
                        is_positive = ?,
                        entered_by_user_id = ?,
                        entered_at = ?,
                        verified_by_user_id = ?,
                        verified_at = ?
                    WHERE id = ?
                """, (result_val, result_unit, clinical_flag, is_pos, entered_by_id, entered_at, verified_by_id, verified_at, rid))
                updated += 1
            else:
                cur.execute("""
                    INSERT INTO test_results (
                        order_id, parameter_id, result_value, result_unit, clinical_flag,
                        is_positive, entered_by_user_id, entered_at, verified_by_user_id, verified_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (order_id, parameter_id, result_val, result_unit, clinical_flag, is_pos, entered_by_id, entered_at, verified_by_id, verified_at))
                inserted += 1
                
        except Exception as e:
            errors.append(f"Row {idx}: {str(e)}")
            
    if dry_run:
        conn.rollback()
    else:
        conn.commit()
        
    return {
        "total": len(records),
        "processed": inserted + updated,
        "inserted": inserted,
        "updated": updated,
        "errors": errors,
        "dry_run": dry_run
    }
