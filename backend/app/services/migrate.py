"""轻量幂等迁移：为已存在的 halls 表补齐新列（无 Alembic 依赖）。

create_all 只会建新表、不会给老表加列，所以这里按检查结果补列并回填默认值。
"""
from sqlalchemy import inspect, text
from app.database import engine

_NEW_COLUMNS = {
    "front_rows": "INTEGER DEFAULT 0",
    "desk_rows": "INTEGER DEFAULT 0",
    "desk_cols": "INTEGER DEFAULT 0",
    "desk_col": "INTEGER DEFAULT 0",
}

def ensure_hall_columns() -> None:
    inspector = inspect(engine)
    if "halls" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("halls")}
    with engine.begin() as conn:
        for name, ddl in _NEW_COLUMNS.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE halls ADD COLUMN {name} {ddl}"))
                conn.execute(text(f"UPDATE halls SET {name} = 0 WHERE {name} IS NULL"))
