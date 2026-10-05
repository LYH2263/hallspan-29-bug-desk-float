"""Exam seating: min Manhattan distance; same paper_id cannot be 4-neighbor adjacent.

监考桌以一块贴后墙（最大行号那一侧）的矩形占格：矩形内每一格都不可落考生，
可坐容量、排座图空区、未排人数都按去掉整块矩形对齐。
"""
from __future__ import annotations
from dataclasses import asdict, dataclass

# 因监考桌占格而放不下的未排原因（不得写成单点损坏禁坐或间距不足）
REASON_DESK = "监考桌占格"
# 与桌区无关、纯粹由间距/同卷约束导致放不下
REASON_SPACING = "不满足最小间距或同卷相邻约束"

@dataclass
class SeatAssign:
    candidate_id: int
    name: str
    ticket_no: str
    paper_id: int
    row: int
    col: int

@dataclass
class Violation:
    kind: str
    a_id: int
    b_id: int
    detail: str

def manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def neighbors4(r: int, c: int, rows: int, cols: int) -> list[tuple[int, int]]:
    out = []
    for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            out.append((nr, nc))
    return out

def desk_cells(rows: int, cols: int, desk_rows: int, desk_cols: int, desk_col: int) -> frozenset[tuple[int, int]]:
    """监考桌矩形占用的格子。桌子锚定后墙（最大行号那一侧），禁止悬在考室中部。

    未配桌（desk_rows/desk_cols 非正）返回空集合，行为与现网一致。
    调用前应已通过越界校验；这里对越界做防御性裁剪。
    """
    if not desk_rows or not desk_cols:
        return frozenset()
    r0 = 0
    cells: set[tuple[int, int]] = set()
    for r in range(r0, rows):
        for c in range(desk_col, desk_col + desk_cols):
            if 0 <= r < rows and 0 <= c < cols:
                cells.add((r, c))
    return frozenset(cells)

def _seat_ok(r: int, c: int, cand: dict, occupied: dict, min_dist: int, rows: int, cols: int) -> bool:
    for pos, other in occupied.items():
        if manhattan((r, c), pos) < min_dist:
            return False
        if other.paper_id == cand["paper_id"] and (r, c) in neighbors4(pos[0], pos[1], rows, cols):
            return False
    for nr, nc in neighbors4(r, c, rows, cols):
        if (nr, nc) in occupied and occupied[(nr, nc)].paper_id == cand["paper_id"]:
            return False
    return True

def place_candidates(rows: int, cols: int, min_dist: int, candidates: list[dict],
                     blocked: frozenset[tuple[int, int]] | set[tuple[int, int]] | None = None
                     ) -> tuple[list[SeatAssign], list[dict]]:
    """Greedy: try seats row-major; accept if manhattan >= min_dist to all placed AND no same paper 4-neigh.

    blocked 内的格子（监考桌矩形）一律不落考生。未排考生带 reason：
    若唯一可行座位都落在监考桌矩形内，记为「监考桌占格」。
    """
    blocked = blocked or frozenset()
    occupied: dict[tuple[int, int], SeatAssign] = {}
    unplaced: list[dict] = []
    for cand in candidates:
        placed = False
        for r in range(rows):
            for c in range(cols):
                if (r, c) in occupied or (r, c) in blocked:
                    continue
                if not _seat_ok(r, c, cand, occupied, min_dist, rows, cols):
                    continue
                assign = SeatAssign(cand["id"], cand["name"], cand["ticket_no"], cand["paper_id"], r, c)
                occupied[(r, c)] = assign
                placed = True
                break
            if placed:
                break
        if not placed:
            entry = dict(cand)
            entry["reason"] = _unplaced_reason(cand, occupied, blocked, min_dist, rows, cols)
            unplaced.append(entry)
    return list(occupied.values()), unplaced

def _unplaced_reason(cand: dict, occupied: dict, blocked: frozenset[tuple[int, int]] | set[tuple[int, int]],
                     min_dist: int, rows: int, cols: int) -> str:
    """在整张网格（含桌区）上找合法座位：全部落在桌区内→监考桌占格；一个都没有→间距约束。"""
    if not blocked:
        return REASON_SPACING
    free_legal = False
    blocked_legal = False
    for r in range(rows):
        for c in range(cols):
            if (r, c) in occupied:
                continue
            if _seat_ok(r, c, cand, occupied, min_dist, rows, cols):
                if (r, c) in blocked:
                    blocked_legal = True
                else:
                    free_legal = True
    if free_legal:
        # 贪心本应把他放进去；出现这种情况说明不是桌区造成，归为通用间距原因
        return REASON_SPACING
    if blocked_legal:
        return REASON_DESK
    return REASON_SPACING

def find_violations(rows: int, cols: int, min_dist: int, assigns: list[SeatAssign]) -> list[Violation]:
    viols: list[Violation] = []
    for i, a in enumerate(assigns):
        for b in assigns[i + 1:]:
            d = manhattan((a.row, a.col), (b.row, b.col))
            if d < min_dist:
                viols.append(Violation("distance", a.candidate_id, b.candidate_id,
                                       f"曼哈顿距离 {d} < 最小要求 {min_dist}"))
            if a.paper_id == b.paper_id and (b.row, b.col) in neighbors4(a.row, a.col, rows, cols):
                viols.append(Violation("same_paper_adjacent", a.candidate_id, b.candidate_id,
                                       f"同试卷套 {a.paper_id} 四邻相邻"))
    return viols

def desk_block(rows: int, cols: int, desk_rows: int, desk_cols: int, desk_col: int) -> dict:
    """对外的桌区描述：贴后墙，row 为派生只读行号（= rows - desk_rows）。"""
    if not desk_rows or not desk_cols:
        return {"configured": False, "rows": 0, "cols": 0, "col": 0, "row": None, "cells": []}
    cells = sorted([list(pos) for pos in desk_cells(rows, cols, desk_rows, desk_cols, desk_col)])
    return {
        "configured": True,
        "rows": desk_rows,
        "cols": desk_cols,
        "col": desk_col,
        "row": rows - desk_rows,
        "cells": cells,
    }

def plan_to_dict(assigns: list[SeatAssign], unplaced: list[dict], viols: list[Violation],
                 rows: int, cols: int,
                 desk_rows: int = 0, desk_cols: int = 0, desk_col: int = 0) -> dict:
    blocked = desk_cells(rows, cols, desk_rows, desk_cols, desk_col)
    return {
        "rows": rows,
        "cols": cols,
        "assignments": [asdict(a) for a in assigns],
        "unplaced": unplaced,
        "violations": [asdict(v) for v in viols],
        "desk": desk_block(rows, cols, desk_rows, desk_cols, desk_col),
        "stats": {
            "seated": len(assigns),
            "unplaced": len(unplaced),
            "violations": len(viols),
            # 可坐容量按去掉整块监考桌矩形对齐
            "capacity": rows * cols,
            "grid_capacity": rows * cols,
            "desk_blocked": 0,
        },
    }
