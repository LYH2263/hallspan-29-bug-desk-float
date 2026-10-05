from app.services.seat_engine import (
    REASON_DESK, REASON_SPACING, desk_cells, find_violations, manhattan,
    place_candidates, plan_to_dict, SeatAssign,
)

def test_manhattan():
    assert manhattan((0, 0), (2, 1)) == 3

def test_min_distance_placement():
    cands = [{"id": i, "name": f"C{i}", "ticket_no": f"T{i}", "paper_id": 1 + (i % 2)} for i in range(4)]
    assigns, unplaced = place_candidates(4, 4, 2, cands)
    assert len(assigns) + len(unplaced) == 4
    for i, a in enumerate(assigns):
        for b in assigns[i+1:]:
            assert manhattan((a.row, a.col), (b.row, b.col)) >= 2

def test_same_paper_not_adjacent_in_result():
    # Force two same paper — engine should avoid 4-neigh
    cands = [
        {"id": 1, "name": "A", "ticket_no": "T1", "paper_id": 1},
        {"id": 2, "name": "B", "ticket_no": "T2", "paper_id": 1},
        {"id": 3, "name": "C", "ticket_no": "T3", "paper_id": 2},
    ]
    assigns, _ = place_candidates(3, 3, 1, cands)
    viols = find_violations(3, 3, 1, assigns)
    assert not any(v.kind == "same_paper_adjacent" for v in viols)

def test_violation_detection():
    assigns = [
        SeatAssign(1, "A", "T1", 1, 0, 0),
        SeatAssign(2, "B", "T2", 1, 0, 1),
    ]
    viols = find_violations(2, 2, 2, assigns)
    kinds = {v.kind for v in viols}
    assert "distance" in kinds
    assert "same_paper_adjacent" in kinds


# —— 监考桌矩形占格 ——

def test_desk_cells_anchor_back_wall():
    # 1×2 贴最后一行第 0–1 列
    assert desk_cells(5, 6, 1, 2, 0) == frozenset({(4, 0), (4, 1)})
    # 2×3 贴后墙占最后两行
    assert desk_cells(5, 6, 2, 3, 1) == frozenset(
        {(3, 1), (3, 2), (3, 3), (4, 1), (4, 2), (4, 3)})

def test_no_desk_matches_current_network():
    # 未配桌 → 空占格，行为与现网一致
    assert desk_cells(5, 6, 0, 0, 0) == frozenset()

def test_seed_desk_cells_hold_no_candidate():
    names = ["陈一", "李二", "张三", "赵四", "钱五", "孙六", "周七",
             "吴八", "郑九", "王十", "冯十一", "陈十二"]
    cands = [{"id": i + 1, "name": n, "ticket_no": f"T{2026001 + i}", "paper_id": (i % 3) + 1}
             for i, n in enumerate(names)]
    blocked = desk_cells(5, 6, 1, 2, 0)
    assigns, unplaced = place_candidates(5, 6, 2, cands, blocked)
    assert all((a.row, a.col) not in blocked for a in assigns)
    assert {(a.row, a.col) for a in assigns}.isdisjoint({(4, 0), (4, 1)})
    assert len(assigns) == 12 and not unplaced

def test_capacity_aligns_after_removing_desk_rectangle():
    viols = find_violations(5, 6, 2, [])
    d = plan_to_dict([], [], viols, 5, 6, 1, 2, 0)
    assert d["stats"]["capacity"] == 28          # 30 网格 - 2 桌格
    assert d["stats"]["grid_capacity"] == 30
    assert d["stats"]["desk_blocked"] == 2
    assert d["desk"]["configured"] and d["desk"]["row"] == 4
    # 无桌时容量回到整网格
    d0 = plan_to_dict([], [], [], 5, 6, 0, 0, 0)
    assert d0["stats"]["capacity"] == 30 and d0["stats"]["desk_blocked"] == 0

def test_overflow_due_to_desk_is_labeled_desk_reason():
    # min_dist=1 让唯一放不下的原因是桌区占格（30 网格仅 28 可坐）
    cands = [{"id": i, "name": f"C{i}", "ticket_no": f"T{i}", "paper_id": (i % 3) + 1}
             for i in range(30)]
    blocked = desk_cells(5, 6, 1, 2, 0)
    assigns, unplaced = place_candidates(5, 6, 1, cands, blocked)
    assert len(assigns) == 28 and len(unplaced) == 2
    assert all(u["reason"] == REASON_DESK for u in unplaced)
    # 不得写成单点损坏禁坐或间距不足
    assert all(u["reason"] != REASON_SPACING for u in unplaced)

def test_unplaced_without_desk_uses_spacing_reason():
    # 无桌但 min_dist 很大，放不下 → 间距原因
    cands = [{"id": i, "name": f"C{i}", "ticket_no": f"T{i}", "paper_id": 1}
             for i in range(40)]
    assigns, unplaced = place_candidates(5, 6, 5, cands, frozenset())
    assert unplaced and all(u["reason"] == REASON_SPACING for u in unplaced)
