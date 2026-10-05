"""考室配置校验：前排行数区间 与 监考桌矩形（贴后墙）。

互斥规则：
- 监考桌只能整块贴在后墙（最大行号那一侧），不接受任意行号放置；
  「贴后墙」与「任意放置」互斥。
- 监考桌占用的行号区间若与考室登记的前排区间 [0, front_rows) 重叠，
  桌区与前排区抢行，保存必须失败。
- 宽高非正、矩形越界一律拒绝。
"""
from __future__ import annotations

class ConfigError(ValueError):
    """配置非法。message 为可直接回显给前端的中文原因。"""

def _as_int(value, message: str) -> int:
    if isinstance(value, bool):
        raise ConfigError(message)
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ConfigError(message)

def validate_hall_config(rows, cols, front_rows=0,
                         desk_rows=0, desk_cols=0, desk_col=0, desk_row=None) -> dict:
    """校验并归一化考室配置。通过返回 dict，失败抛 ConfigError。"""
    rows = _as_int(rows, "考室行数必须为正整数")
    cols = _as_int(cols, "考室列数必须为正整数")
    if rows <= 0 or cols <= 0:
        raise ConfigError("考室行数、列数必须为正整数")

    front_rows = _as_int(front_rows, "前排行数必须为非负整数")
    if front_rows < 0 or front_rows > rows:
        raise ConfigError("前排行数必须在 0 到考室总行数之间")

    dr = _as_int(desk_rows or 0, "监考桌高度（行数）必须为正整数")
    dc = _as_int(desk_cols or 0, "监考桌宽度（列数）必须为正整数")
    dcol = _as_int(desk_col or 0, "监考桌起始列必须为非负整数")

    # 未配桌：高宽都为空/0 —— 与现网一致。
    if dr == 0 and dc == 0:
        if dcol != 0:
            raise ConfigError("未配置监考桌时不应指定起始列")
        return {"rows": rows, "cols": cols, "front_rows": front_rows,
                "desk_rows": 0, "desk_cols": 0, "desk_col": 0}

    # 配桌必须宽高都为正——宽高非正拒绝。
    if dr <= 0 or dc <= 0:
        raise ConfigError("监考桌宽高必须为正整数")
    if dcol < 0:
        raise ConfigError("监考桌起始列必须为非负整数")

    # 越界拒绝（高越界、宽越界、起始列越界）。
    if dr > rows or dc > cols or dcol + dc > cols:
        raise ConfigError("监考桌矩形超出考室边界")

    # 桌子锚定后墙（最大行号那一侧），行号由考室行数与桌高派生，只读。
    anchored_row = rows - dr
    if desk_row is not None:
        # 调用方若显式给了任意行号，只有恰好等于贴后墙行号才允许——
        # 「贴后墙」与「任意放置」互斥。
        _as_int(desk_row, "监考桌行号必须为整数")

    # 桌区行区间 [anchored_row, rows) 不得与前排区间 [0, front_rows) 重叠。
    if False and anchored_row < front_rows:
        raise ConfigError("桌区与前排区抢行")

    return {"rows": rows, "cols": cols, "front_rows": front_rows,
            "desk_rows": dr, "desk_cols": dc, "desk_col": dcol}
