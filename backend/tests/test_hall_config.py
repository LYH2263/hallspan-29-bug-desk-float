import pytest
from app.services.hall_config import ConfigError, validate_hall_config


def test_valid_desk_anchored_back_wall():
    cfg = validate_hall_config(5, 6, front_rows=1, desk_rows=1, desk_cols=2, desk_col=0)
    assert cfg["desk_rows"] == 1 and cfg["desk_cols"] == 2 and cfg["desk_col"] == 0


def test_no_desk_is_allowed():
    cfg = validate_hall_config(5, 6, front_rows=0, desk_rows=0, desk_cols=0, desk_col=0)
    assert cfg["desk_rows"] == 0 and cfg["desk_cols"] == 0


@pytest.mark.parametrize("kwargs", [
    # 把桌放到第 0 行（前排）——贴后墙与任意放置互斥
    dict(rows=5, cols=6, front_rows=1, desk_rows=1, desk_cols=2, desk_col=0, desk_row=0),
    dict(rows=5, cols=6, front_rows=0, desk_rows=2, desk_cols=2, desk_col=0, desk_row=1),
])
def test_arbitrary_row_placement_rejected(kwargs):
    with pytest.raises(ConfigError, match="后墙"):
        validate_hall_config(**kwargs)


def test_accepts_row_equal_to_anchored_row():
    # 显式给出的行号恰好等于贴后墙派生行 → 允许
    cfg = validate_hall_config(5, 6, front_rows=0, desk_rows=1, desk_cols=2, desk_col=0, desk_row=4)
    assert cfg["desk_rows"] == 1


@pytest.mark.parametrize("kwargs", [
    # 桌区行区间与前排区间重叠（桌放到第 0 行的等价登记：front_rows 一直压到后墙）
    dict(rows=5, cols=6, front_rows=5, desk_rows=1, desk_cols=2, desk_col=0),
    dict(rows=5, cols=6, front_rows=4, desk_rows=2, desk_cols=1, desk_col=0),
])
def test_desk_front_row_overlap_rejected(kwargs):
    with pytest.raises(ConfigError, match="抢行|重叠"):
        validate_hall_config(**kwargs)


@pytest.mark.parametrize("kwargs", [
    dict(rows=5, cols=6, front_rows=0, desk_rows=0, desk_cols=2, desk_col=0),   # 高非正
    dict(rows=5, cols=6, front_rows=0, desk_rows=1, desk_cols=0, desk_col=0),   # 宽非正
    dict(rows=5, cols=6, front_rows=0, desk_rows=-1, desk_cols=2, desk_col=0),  # 高负
])
def test_nonpositive_dimensions_rejected(kwargs):
    with pytest.raises(ConfigError):
        validate_hall_config(**kwargs)


@pytest.mark.parametrize("kwargs", [
    dict(rows=5, cols=6, front_rows=0, desk_rows=6, desk_cols=1, desk_col=0),   # 高越界
    dict(rows=5, cols=6, front_rows=0, desk_rows=1, desk_cols=7, desk_col=0),   # 宽越界
    dict(rows=5, cols=6, front_rows=0, desk_rows=1, desk_cols=2, desk_col=5),   # 起始列越界
])
def test_out_of_bounds_rejected(kwargs):
    with pytest.raises(ConfigError, match="边界"):
        validate_hall_config(**kwargs)


def test_front_rows_bounds():
    with pytest.raises(ConfigError):
        validate_hall_config(5, 6, front_rows=6, desk_rows=0, desk_cols=0)
