# HallSpan 考场间距排座

在考室网格上按最小曼哈顿距离排座，同试卷套不得四邻相邻，并输出违规与统计。

监考桌为一块**贴后墙**（最大行号那一侧）的矩形占格：矩形内每一格不落考生，
可坐容量、排座图空区、未排人数都按去掉整块矩形对齐。桌子不接受任意行号放置
（「贴后墙」与「任意放置」互斥）；桌区行号区间与考室登记的前排行数区间重叠、
矩形越界或宽高非正时，`POST /api/halls/{id}/config` 一律 400 拒绝、不落库。
修改桌尺寸时若已有方案，配置与最新方案在同一事务内同成同败地重写，历史方案不回刷。

技术栈：Python 3.12 / FastAPI / SQLAlchemy / PostgreSQL / Vue 3 / TypeScript / Vite

## 启动

```bash
docker compose up --build
```

| 服务 | 地址 |
| --- | --- |
| 前端 | http://localhost:4900 |
| API | http://localhost:9900 |
| API 文档 | http://localhost:9900/docs |
| Postgres | localhost:5450 |

健康检查：`GET http://localhost:9900/api/health`

## 使用说明

1. 在「考室」「考生」「试卷套」确认基础数据。
2. 打开「排座图」执行间距排座。
3. 在「违规」查看间距或同卷相邻问题。
4. 在「统计」查看占用与违规汇总。

## 开发与测试

```bash
docker compose exec api pytest -q
```
