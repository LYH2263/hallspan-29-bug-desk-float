from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.models import Candidate, Hall, PaperSet

def seed_if_empty(db: Session) -> None:
    if (db.scalar(select(func.count()).select_from(Hall)) or 0) > 0:
        return
    # front_rows=1：行 0 为前排区；监考桌 1×2 锚定后墙（最后一行）第 0–1 列。
    # 两块行区间 [0,1) 与 [4,5) 不重叠，配置合法；这两格被桌区盖住、不落考生。
    hall = Hall(code="H101", name="一号考室", rows=5, cols=6, min_manhattan=2,
                front_rows=1, desk_rows=1, desk_cols=2, desk_col=0)
    db.add(hall); db.flush()
    papers = [("P-A", "语文 A 卷"), ("P-B", "语文 B 卷"), ("P-C", "语文 C 卷")]
    paper_ids = []
    for code, title in papers:
        p = PaperSet(code=code, title=title)
        db.add(p); db.flush()
        paper_ids.append(p.id)
    names = ["陈一", "李二", "张三", "赵四", "钱五", "孙六", "周七", "吴八", "郑九", "王十", "冯十一", "陈十二"]
    for i, name in enumerate(names):
        db.add(Candidate(hall_id=hall.id, name=name, ticket_no=f"T{2026001+i}",
                         paper_id=paper_ids[i % len(papers)]))
    db.commit()
