import json
from app.database import SessionLocal
from app.models.models import SeatPlan


def _run(client):
    return client.post("/api/seating/run?hall_id=1")


def test_run_respects_seed_desk_cells(client, hall_with_candidates):
    res = _run(client)
    assert res.status_code == 200, res.text
    data = res.json()
    desk = {(p[0], p[1]) for p in data["desk"]["cells"]}
    assert desk == {(4, 0), (4, 1)}
    seated = {(a["row"], a["col"]) for a in data["assignments"]}
    assert seated.isdisjoint(desk)          # 矩形内每一格不落考生
    assert data["stats"]["capacity"] == 28  # 可坐容量按去掉整块矩形对齐
    assert data["stats"]["desk_blocked"] == 2
    assert data["stats"]["seated"] == 12 and data["stats"]["unplaced"] == 0


def test_placing_desk_at_row_zero_fails_and_everything_stays(client, hall_with_candidates):
    # 先产生一个有效方案
    plan = _run(client).json()
    plan_id = plan["id"]

    # 把桌放到第 0 行 → 保存必须失败
    res = client.post("/api/halls/1/config", json={
        "rows": 5, "cols": 6, "front_rows": 1,
        "desk_rows": 1, "desk_cols": 2, "desk_col": 0, "desk_row": 0,
    })
    assert res.status_code == 400

    # 考室停在保存前
    hall = client.get("/api/halls/1").json()
    assert hall["desk"]["row"] == 4

    # 方案与统计停在保存前：仍是原方案，桌区仍在最后一行
    latest = client.get("/api/seating/latest?hall_id=1").json()
    assert latest["id"] == plan_id
    assert {(p[0], p[1]) for p in latest["desk"]["cells"]} == {(4, 0), (4, 1)}
    assert client.get("/api/seating/stats?hall_id=1").json()["capacity"] == 28

    db = SessionLocal()
    try:
        assert db.query(SeatPlan).count() == 1
    finally:
        db.close()


def test_front_row_overlap_save_fails(client, hall_with_candidates):
    _run(client)
    # front_rows 压到后墙，与桌区抢行
    res = client.post("/api/halls/1/config", json={
        "rows": 5, "cols": 6, "front_rows": 5,
        "desk_rows": 1, "desk_cols": 2, "desk_col": 0,
    })
    assert res.status_code == 400
    assert client.get("/api/halls/1").json()["front_rows"] == 1


def test_out_of_bounds_and_nonpositive_rejected(client, hall_with_candidates):
    for bad in [
        {"rows": 5, "cols": 6, "desk_rows": 6, "desk_cols": 1, "desk_col": 0},
        {"rows": 5, "cols": 6, "desk_rows": 1, "desk_cols": 7, "desk_col": 0},
        {"rows": 5, "cols": 6, "desk_rows": 0, "desk_cols": 2, "desk_col": 0},
        {"rows": 5, "cols": 6, "desk_rows": 1, "desk_cols": 2, "desk_col": 5},
    ]:
        r = client.post("/api/halls/1/config", json=bad)
        assert r.status_code == 400, bad


def test_resize_atomically_rewrites_latest_plan(client, hall_with_candidates):
    p1 = _run(client).json()["id"]
    p2 = _run(client).json()["id"]
    assert p2 > p1

    # 改桌尺寸：尺寸与方案重写同成同败；最新方案被原地重写，历史方案不回刷
    res = client.post("/api/halls/1/config", json={
        "rows": 5, "cols": 6, "front_rows": 1,
        "desk_rows": 1, "desk_cols": 3, "desk_col": 0,
    })
    assert res.status_code == 200, res.text
    assert res.json()["rewritten_plan_id"] == p2

    latest = client.get("/api/seating/latest?hall_id=1").json()
    assert latest["id"] == p2                    # 仍是同一条（同成同败、未新增）
    assert latest["desk"]["cols"] == 3
    assert latest["stats"]["capacity"] == 27
    seated = {(a["row"], a["col"]) for a in latest["assignments"]}
    assert seated.isdisjoint({(4, c) for c in range(3)})

    # 历史方案 p1 不回刷
    db = SessionLocal()
    try:
        old = json.loads(db.get(SeatPlan, p1).result_json)
        assert old["desk"]["cols"] == 2
        assert db.query(SeatPlan).count() == 2
    finally:
        db.close()


def test_save_without_plan_does_not_create_one(client, hall_with_candidates):
    res = client.post("/api/halls/1/config", json={
        "rows": 5, "cols": 6, "front_rows": 1,
        "desk_rows": 1, "desk_cols": 1, "desk_col": 0,
    })
    assert res.status_code == 200
    assert res.json()["rewritten_plan_id"] is None
    db = SessionLocal()
    try:
        assert db.query(SeatPlan).count() == 0
    finally:
        db.close()


def test_partial_save_keeps_existing_fields_and_rewrites_plan(client, hall_with_candidates):
    _run(client)
    # 只改桌宽，省略 front_rows/desk_rows/desk_col —— 其余字段沿用现值
    res = client.post("/api/halls/1/config", json={"desk_cols": 3})
    assert res.status_code == 200, res.text
    h = client.get("/api/halls/1").json()
    assert h["front_rows"] == 1 and h["desk_rows"] == 1 and h["desk_col"] == 0
    assert h["desk_cols"] == 3
    latest = client.get("/api/seating/latest?hall_id=1").json()
    assert latest["stats"]["capacity"] == 27


def test_remove_desk_returns_to_full_capacity(client, hall_with_candidates):
    _run(client)
    res = client.post("/api/halls/1/config", json={
        "rows": 5, "cols": 6, "front_rows": 0,
        "desk_rows": 0, "desk_cols": 0, "desk_col": 0,
    })
    assert res.status_code == 200, res.text
    latest = client.get("/api/seating/latest?hall_id=1").json()
    assert latest["stats"]["capacity"] == 30
    assert latest["desk"]["configured"] is False
