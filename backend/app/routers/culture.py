import datetime
import sqlite3
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from ..database import get_db
from ..auth import get_current_user
from ..schemas import (
    CultureOrderSaveRequest,
    CultureOrderResponse,
    CultureIsolateItem,
    CultureAstItem,
)
from ..culture_engine import (
    evaluate_urine_colony_count,
    evaluate_blood_culture_isolate,
    evaluate_sterile_fluid_isolate,
    apply_phenotypic_safety_overrides,
    URINE_CATEGORY_NO_GROWTH,
    URINE_CATEGORY_CONTAMINATION,
    URINE_CATEGORY_SIGNIFICANT,
)

router = APIRouter(prefix="/api/culture", tags=["culture"])

@router.get("/order/{order_id}", response_model=CultureOrderResponse)
def get_culture_order(
    order_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    cur = db.cursor()
    cur.execute("SELECT id FROM test_orders WHERE id = ?", (order_id,))
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Test order not found")

    cur.execute("""
        SELECT id, order_id, phase, preliminary_micro, preliminary_micro_date,
               colony_count_cfu, growth_category, incubation_hours, media_used,
               clinical_notes, is_emergency_callback_done, emergency_callback_time,
               emergency_callback_recipient, created_at, updated_at
        FROM culture_orders
        WHERE order_id = ?
    """, (order_id,))
    co = cur.fetchone()

    if not co:
        return CultureOrderResponse(
            order_id=order_id,
            phase=1,
            incubation_hours=24,
            isolates=[]
        )

    co_id = co["id"]
    cur.execute("""
        SELECT id, isolate_number, organism_name, colony_morphology, is_pathogen, is_contaminant
        FROM culture_isolates
        WHERE culture_order_id = ?
        ORDER BY isolate_number ASC
    """, (co_id,))
    iso_rows = cur.fetchall()

    isolates_list = []
    alerts_collected = []

    for iso in iso_rows:
        iso_id = iso["id"]
        cur.execute("""
            SELECT id, antimicrobial_class, agent_name, measurement_type,
                   measurement_value, raw_sir, overridden_sir, override_reason, clinical_note
            FROM culture_ast_results
            WHERE isolate_id = ?
            ORDER BY antimicrobial_class ASC, agent_name ASC
        """, (iso_id,))
        ast_rows = cur.fetchall()

        ast_items = []
        raw_ast_for_engine = []
        for a in ast_rows:
            ast_items.append(CultureAstItem(
                id=a["id"],
                antimicrobial_class=a["antimicrobial_class"],
                agent_name=a["agent_name"],
                measurement_type=a["measurement_type"],
                measurement_value=a["measurement_value"],
                raw_sir=a["raw_sir"],
                overridden_sir=a["overridden_sir"],
                override_reason=a["override_reason"],
                clinical_note=a["clinical_note"]
            ))
            raw_ast_for_engine.append({
                "antimicrobial_class": a["antimicrobial_class"],
                "agent_name": a["agent_name"],
                "raw_sir": a["raw_sir"]
            })

        _, iso_alerts = apply_phenotypic_safety_overrides(iso["organism_name"], raw_ast_for_engine)
        alerts_collected.extend(iso_alerts)

        isolates_list.append(CultureIsolateItem(
            id=iso["id"],
            isolate_number=iso["isolate_number"],
            organism_name=iso["organism_name"],
            colony_morphology=iso["colony_morphology"],
            is_pathogen=bool(iso["is_pathogen"]),
            is_contaminant=bool(iso["is_contaminant"]),
            ast_results=ast_items
        ))

    return CultureOrderResponse(
        id=co["id"],
        order_id=co["order_id"],
        phase=co["phase"],
        preliminary_micro=co["preliminary_micro"],
        preliminary_micro_date=str(co["preliminary_micro_date"]) if co["preliminary_micro_date"] else None,
        colony_count_cfu=co["colony_count_cfu"],
        growth_category=co["growth_category"],
        incubation_hours=co["incubation_hours"] or 24,
        media_used=co["media_used"],
        clinical_notes=co["clinical_notes"],
        is_emergency_callback_done=bool(co["is_emergency_callback_done"]),
        emergency_callback_time=str(co["emergency_callback_time"]) if co["emergency_callback_time"] else None,
        emergency_callback_recipient=co["emergency_callback_recipient"],
        alerts=list(dict.fromkeys(alerts_collected)),
        isolates=isolates_list,
        created_at=str(co["created_at"]) if co["created_at"] else None,
        updated_at=str(co["updated_at"]) if co["updated_at"] else None
    )

@router.post("/order/{order_id}/save")
def save_culture_order(
    order_id: int,
    payload: CultureOrderSaveRequest,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    cur = db.cursor()
    cur.execute("SELECT o.id, t.name AS test_name FROM test_orders o JOIN tests t ON o.test_id = t.id WHERE o.id = ?", (order_id,))
    order_row = cur.fetchone()
    if not order_row:
        raise HTTPException(status_code=404, detail="Test order not found")

    test_name = order_row["test_name"]
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    callback_time = now_str if payload.is_emergency_callback_done else None
    micro_date = now_str if payload.preliminary_micro else None

    # Upsert culture_orders
    cur.execute("SELECT id FROM culture_orders WHERE order_id = ?", (order_id,))
    existing = cur.fetchone()

    growth_cat = payload.growth_category
    if not growth_cat and "urine" in test_name.lower() and payload.colony_count_cfu:
        org_cnt = len(payload.isolates) if payload.isolates else 1
        org_n = payload.isolates[0].organism_name if payload.isolates else None
        eval_res = evaluate_urine_colony_count(payload.colony_count_cfu, organism_count=org_cnt, organism_name=org_n)
        growth_cat = eval_res["category"]

    if existing:
        co_id = existing["id"]
        cur.execute("""
            UPDATE culture_orders
            SET phase = ?,
                preliminary_micro = COALESCE(?, preliminary_micro),
                preliminary_micro_date = COALESCE(?, preliminary_micro_date),
                colony_count_cfu = ?,
                growth_category = ?,
                incubation_hours = ?,
                media_used = ?,
                clinical_notes = ?,
                is_emergency_callback_done = ?,
                emergency_callback_time = COALESCE(?, emergency_callback_time),
                emergency_callback_recipient = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            payload.phase,
            payload.preliminary_micro,
            micro_date,
            payload.colony_count_cfu,
            growth_cat,
            payload.incubation_hours,
            payload.media_used,
            payload.clinical_notes,
            1 if payload.is_emergency_callback_done else 0,
            callback_time,
            payload.emergency_callback_recipient,
            now_str,
            co_id
        ))
    else:
        cur.execute("""
            INSERT INTO culture_orders (
                order_id, phase, preliminary_micro, preliminary_micro_date,
                colony_count_cfu, growth_category, incubation_hours, media_used,
                clinical_notes, is_emergency_callback_done, emergency_callback_time,
                emergency_callback_recipient, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_id,
            payload.phase,
            payload.preliminary_micro,
            micro_date,
            payload.colony_count_cfu,
            growth_cat,
            payload.incubation_hours,
            payload.media_used,
            payload.clinical_notes,
            1 if payload.is_emergency_callback_done else 0,
            callback_time,
            payload.emergency_callback_recipient,
            now_str,
            now_str
        ))
        co_id = cur.lastrowid

    # If isolates supplied, delete existing and reinsert (idempotent overwrite)
    if payload.isolates is not None:
        cur.execute("DELETE FROM culture_isolates WHERE culture_order_id = ?", (co_id,))
        for idx, iso in enumerate(payload.isolates, start=1):
            cur.execute("""
                INSERT INTO culture_isolates (
                    culture_order_id, isolate_number, organism_name,
                    colony_morphology, is_pathogen, is_contaminant, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                co_id,
                iso.isolate_number or idx,
                iso.organism_name,
                iso.colony_morphology,
                1 if iso.is_pathogen else 0,
                1 if iso.is_contaminant else 0,
                now_str
            ))
            iso_id = cur.lastrowid

            if iso.ast_results:
                raw_ast_dicts = [a.dict() for a in iso.ast_results]
                overridden_ast, _ = apply_phenotypic_safety_overrides(
                    iso.organism_name,
                    raw_ast_dicts,
                    is_esbl_positive=bool(payload.is_esbl_positive),
                    is_mrsa_positive=bool(payload.is_mrsa_positive)
                )

                for ast_row in overridden_ast:
                    cur.execute("""
                        INSERT INTO culture_ast_results (
                            isolate_id, antimicrobial_class, agent_name,
                            measurement_type, measurement_value, raw_sir,
                            overridden_sir, override_reason, clinical_note
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        iso_id,
                        ast_row["antimicrobial_class"],
                        ast_row["agent_name"],
                        ast_row.get("measurement_type") or "zone_mm",
                        ast_row.get("measurement_value"),
                        ast_row["raw_sir"],
                        ast_row["overridden_sir"],
                        ast_row.get("override_reason"),
                        ast_row.get("clinical_note")
                    ))

    # Synchronize test_orders status and test_results summary
    is_completed = (payload.phase >= 4) or (growth_cat in (URINE_CATEGORY_NO_GROWTH, URINE_CATEGORY_CONTAMINATION))
    new_status = "completed" if is_completed else "entered"
    cur.execute("UPDATE test_orders SET status = ? WHERE id = ?", (new_status, order_id))

    # Synthesize readable result_value for daily log / surveillance tracking
    summary_parts = []
    if payload.preliminary_micro and payload.phase == 1:
        summary_parts.append(f"Smear: {payload.preliminary_micro}")
    if growth_cat == URINE_CATEGORY_NO_GROWTH:
        summary_parts.append("No growth after 48 hours")
    elif growth_cat == URINE_CATEGORY_CONTAMINATION:
        summary_parts.append("Polymicrobial growth (contamination)")
    elif payload.isolates:
        org_names = [iso.organism_name for iso in payload.isolates]
        cfu_prefix = f" ({payload.colony_count_cfu} CFU/mL)" if payload.colony_count_cfu else ""
        summary_parts.append(f"Isolated: {', '.join(org_names)}{cfu_prefix}")
    elif payload.colony_count_cfu:
        summary_parts.append(f"Colony count: {payload.colony_count_cfu} CFU/mL")

    final_summary_text = " | ".join(summary_parts) if summary_parts else "Culture in progress"
    is_positive_finding = (growth_cat == URINE_CATEGORY_SIGNIFICANT) or any(iso.is_pathogen for iso in (payload.isolates or []))

    cur.execute("SELECT id FROM test_results WHERE order_id = ? AND parameter_id IS NULL", (order_id,))
    r_row = cur.fetchone()
    if r_row:
        cur.execute("""
            UPDATE test_results
            SET result_value = ?, is_positive = ?, clinical_flag = ?,
                edited_by_user_id = ?, edited_at = ?, edit_reason = ?
            WHERE id = ?
        """, (
            final_summary_text,
            1 if is_positive_finding else 0,
            "\u26A0" if is_positive_finding else None,
            current_user["id"],
            now_str,
            payload.edit_reason,
            r_row["id"]
        ))
    else:
        cur.execute("""
            INSERT INTO test_results (
                order_id, parameter_id, result_value, is_positive, clinical_flag,
                entered_by_user_id, entered_at
            ) VALUES (?, NULL, ?, ?, ?, ?, ?)
        """, (
            order_id,
            final_summary_text,
            1 if is_positive_finding else 0,
            "\u26A0" if is_positive_finding else None,
            current_user["id"],
            now_str
        ))

    # Audit log
    cur.execute("""
        INSERT INTO audit_log (user_id, action, detail, timestamp)
        VALUES (?, 'SAVE_CULTURE_RESULT', ?, ?)
    """, (
        current_user["id"],
        f"order_id={order_id} phase={payload.phase} summary={final_summary_text!r}",
        now_str
    ))

    db.commit()
    return {"message": "Culture and sensitivity record saved successfully", "order_id": order_id, "phase": payload.phase}
