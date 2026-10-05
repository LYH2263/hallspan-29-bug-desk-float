import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Candidate, Hall, SeatPlan
from app.services.hall_config import ConfigError, validate_hall_config
from app.services.seat_engine import (
    desk_block, desk_cells, find_violations, place_candidates, plan_to_dict,
)

router = APIRouter(prefix="/halls", tags=["halls"])

def _hall_out(r: Hall) -> dict:
    dr, dc, dcol = r.desk_rows or 0, r.desk_cols or 0, r.desk_col or 0
    return {
        "id": r.id, "code": r.code, "name": r.name,
        "rows": r.rows, "cols": r.cols, "min_manhattan": r.min_manhattan,
        "front_rows": r.front_rows or 0,
        "desk_rows": dr, "desk_cols": dc, "desk_col": dcol,
        "desk": desk_block(r.rows, r.cols, dr, dc, dcol),
    }

@router.get("")
def list_halls(db: Session = Depends(get_db)):
    return [_hall_out(r) for r in db.scalars(select(Hall).order_by(Hall.id)).all()]

@router.get("/{hall_id}")
def get_hall(hall_id: int, db: Session = Depends(get_db)):
    hall = db.get(Hall, hall_id)
    if not hall:
        raise HTTPException(404, "考室不存在")
    return _hall_out(hall)

class HallConfigIn(BaseModel):
    rows: int | None = None
    cols: int | None = None
    front_rows: int | None = None
    desk_rows: int | None = None
    desk_cols: int | None = None
    desk_col: int | None = None
    # 只读锚点：前端如回传任意行号，校验会强制其等于贴后墙行号
    desk_row: int | None = None

@router.post("/{hall_id}/config")
def save_hall_config(hall_id: int, body: HallConfigIn, db: Session = Depends(get_db)):
    hall = db.get(Hall, hall_id)
    if not hall:
        raise HTTPException(404, "考室不存在")

    new_rows = hall.rows if body.rows is None else body.rows
    new_cols = hall.cols if body.cols is None else body.cols
    front_rows = hall.front_rows or 0 if body.front_rows is None else body.front_rows
    dr = hall.desk_rows or 0 if body.desk_rows is None else body.desk_rows
    dc = hall.desk_cols or 0 if body.desk_cols is None else body.desk_cols
    dcol = hall.desk_col or 0 if body.desk_col is None else body.desk_col

    # —— 先校验，任何失败都不写库：考室、方案、统计停在保存前 ——
    try:
        cfg = validate_hall_config(
            new_rows, new_cols, front_rows,
            desk_rows=dr, desk_cols=dc, desk_col=dcol, desk_row=body.desk_row,
        )
    except ConfigError as e:
        db.rollback()
        raise HTTPException(400, str(e))

    # 已有有效方案时，尺寸/桌区与方案重写同成同败（同一事务）；历史方案不回刷。
    latest_plan = db.scalars(
        select(SeatPlan).where(SeatPlan.hall_id == hall_id).order_by(SeatPlan.id.desc())
    ).first()

    try:
        hall.rows = cfg["rows"]
        hall.cols = cfg["cols"]
        hall.front_rows = cfg["front_rows"]
        hall.desk_rows = cfg["desk_rows"]
        hall.desk_cols = cfg["desk_cols"]
        hall.desk_col = cfg["desk_col"]
        db.flush()

        rewritten_plan_id = None
        if latest_plan is not None:
            cands = [{"id": c.id, "name": c.name, "ticket_no": c.ticket_no, "paper_id": c.paper_id}
                     for c in db.scalars(select(Candidate).where(Candidate.hall_id == hall_id)).all()]
            blocked = desk_cells(hall.rows, hall.cols, hall.desk_rows, hall.desk_cols, hall.desk_col)
            assigns, unplaced = place_candidates(hall.rows, hall.cols, hall.min_manhattan, cands, blocked)
            viols = find_violations(hall.rows, hall.cols, hall.min_manhattan, assigns)
            result = plan_to_dict(assigns, unplaced, viols, hall.rows, hall.cols,
                                  hall.desk_rows, hall.desk_cols, hall.desk_col)
            result["hall"] = {"id": hall.id, "name": hall.name,
                              "min_manhattan": hall.min_manhattan, "front_rows": hall.front_rows}
            latest_plan.result_json = json.dumps(result, ensure_ascii=False)
            latest_plan.created_at = datetime.utcnow()
            rewritten_plan_id = latest_plan.id

        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(500, "配置保存失败，已回滚到保存前状态")

    return {"ok": True, "hall": _hall_out(hall), "rewritten_plan_id": rewritten_plan_id}
