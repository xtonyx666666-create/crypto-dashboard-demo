"""采集流水线与定时任务（极简版）。

    python -m scheduler.jobs --once            # 全部数据源采集一次（并发）
    python -m scheduler.jobs --once binance    # 只采一个
    python -m scheduler.jobs                   # 常驻：启动先采一次，之后按各数据源的 every_min（默认 REFRESH_MINUTES=5 分钟）循环采集
"""
import datetime as dt
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

import collectors
from processors import clean
from settings import env, get_source, load_sources
from storage import db


def run_source(source: dict) -> dict:
    """一个数据源的流水线：采集 → 清洗/去重 → 入库。"""
    started = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    try:
        rows = collectors.fetch(source)
        for r in rows:
            r.update(source_id=source["id"], fetched_at=started)
        rows = clean.clean(source, rows)
        inserted = db.upsert(rows)
        warn = "; ".join(source.pop("_warnings", [])[:3])
        db.log_run(source["id"], started, True, len(rows), inserted, warn)
        print(f"[{source['id']}] 清洗后 {len(rows)} 条，新入库 {inserted} 条" + (f"（警告：{warn[:100]}）" if warn else ""))
        return {"source": source["id"], "ok": True, "fetched": len(rows), "inserted": inserted}
    except Exception as e:
        traceback.print_exc()
        db.log_run(source["id"], started, False, 0, 0, f"{type(e).__name__}: {e}"[:300])
        print(f"[{source['id']}] 失败：{e}")
        return {"source": source["id"], "ok": False, "error": str(e)}


def run_all(only: str | None = None) -> list[dict]:
    sources = [get_source(only)] if only else load_sources()
    with ThreadPoolExecutor(4) as ex:
        return list(ex.map(run_source, sources))


def serve() -> None:
    """常驻：每个数据源按自己的 every_min（默认 REFRESH_MINUTES=5）循环采集。"""
    default = int(env("REFRESH_MINUTES", "5"))
    due: dict[str, float] = {}
    while True:
        now = time.time()
        todo = [s for s in load_sources() if due.get(s["id"], 0) <= now]
        with ThreadPoolExecutor(4) as ex:
            list(ex.map(run_source, todo))
        for s in todo:
            due[s["id"]] = time.time() + 60 * int(s.get("every_min", default))
        time.sleep(15)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--once":
        run_all(args[1] if len(args) > 1 else None)
    else:
        serve()
