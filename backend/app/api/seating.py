import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Candidate, Hall, SeatPlan
from app.services.seat_engine import (
    desk_cells, find_violations, place_candidates, plan_to_dict,
)
from app.services.page_rollup import mix_stats, mix_violations
router = APIRouter(prefix="/seating", tags=["seating"])

def build_plan_dict(hall: Hall, db: Session) -> dict:
    """按考室当前配置（含前排行数、监考桌矩形）计算一份排座结果（不落库）。"""
    cands = [{"id": c.id, "name": c.name, "ticket_no": c.ticket_no, "paper_id": c.paper_id}
             for c in db.scalars(select(Candidate).where(Candidate.hall_id == hall.id)).all()]
    blocked = desk_cells(hall.rows, hall.cols, hall.desk_rows or 0,
                         hall.desk_cols or 0, hall.desk_col or 0)
    assigns, unplaced = place_candidates(hall.rows, hall.cols, hall.min_manhattan, cands, blocked)
    viols = find_violations(hall.rows, hall.cols, hall.min_manhattan, assigns)
    result = plan_to_dict(assigns, unplaced, viols, hall.rows, hall.cols,
                          hall.desk_rows or 0, hall.desk_cols or 0, hall.desk_col or 0)
    result["hall"] = {"id": hall.id, "name": hall.name, "min_manhattan": hall.min_manhattan,
                      "front_rows": hall.front_rows or 0}
    return result

@router.post("/run")
def run_seating(hall_id: int = 1, db: Session = Depends(get_db)):
    hall = db.get(Hall, hall_id)
    if not hall:
        raise HTTPException(404, "考室不存在")
    result = build_plan_dict(hall, db)
    plan = SeatPlan(hall_id=hall_id, created_at=datetime.utcnow(),
                    result_json=json.dumps(result, ensure_ascii=False))
    db.add(plan); db.commit(); db.refresh(plan)
    return {"id": plan.id, **result}

@router.get("/latest")
def latest(hall_id: int = 1, db: Session = Depends(get_db)):
    plan = db.scalars(select(SeatPlan).where(SeatPlan.hall_id == hall_id).order_by(SeatPlan.id.desc())).first()
    if not plan:
        return run_seating(hall_id=hall_id, db=db)
    data = json.loads(plan.result_json)
    return {"id": plan.id, **data}

@router.get("/violations")
def violations(hall_id: int = 1, db: Session = Depends(get_db)):
    data = latest(hall_id=hall_id, db=db)
    return {"hall_id": hall_id, **mix_violations(data)}

@router.get("/stats")
def stats(hall_id: int = 1, db: Session = Depends(get_db)):
    data = latest(hall_id=hall_id, db=db)
    return {"hall_id": hall_id, **mix_stats(data)}
