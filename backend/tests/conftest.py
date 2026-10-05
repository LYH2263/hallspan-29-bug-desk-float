import os
import tempfile

# 必须在导入 app 之前指向文件型 SQLite（:memory: 跨连接不共享）
_DB_FD, _DB_PATH = tempfile.mkstemp(suffix=".sqlite")
os.close(_DB_FD)
os.unlink(_DB_PATH)
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"
os.environ["SEED_ON_EMPTY"] = "false"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models.models import Candidate, Hall, PaperSet, SeatPlan  # noqa: F401


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture()
def hall_with_candidates(db):
    """与种子一致的 5×6 考室：front_rows=1，监考桌 1×2 贴最后一行第 0–1 列。"""
    hall = Hall(code="H101", name="一号考室", rows=5, cols=6, min_manhattan=2,
                front_rows=1, desk_rows=1, desk_cols=2, desk_col=0)
    db.add(hall); db.flush()
    papers = []
    for code in ("P-A", "P-B", "P-C"):
        p = PaperSet(code=code, title=code)
        db.add(p); db.flush()
        papers.append(p)
    for i in range(12):
        db.add(Candidate(hall_id=hall.id, name=f"考生{i}", ticket_no=f"T{i}",
                         paper_id=papers[i % 3].id))
    db.commit()
    return hall.id
