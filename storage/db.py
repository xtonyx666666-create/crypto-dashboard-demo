"""SQLite 存储。records：所有指标点；runs：每次采集结果；insights：AI/规则生成的情绪短评。"""
import json
import sqlite3
from contextlib import contextmanager

from settings import db_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    uid        TEXT PRIMARY KEY,         -- 去重键：source|指标:币种|时间
    source_id  TEXT NOT NULL,            -- 交易所 id
    metric     TEXT NOT NULL,            -- funding_rate / oi_hist / lsr_account ...
    symbol     TEXT NOT NULL,
    time       TEXT NOT NULL,
    value      REAL NOT NULL,
    extra      TEXT,                     -- JSON，如 {"interval_h": 8}
    fetched_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_rec ON records(metric, symbol, source_id, time);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT, started_at TEXT, ok INTEGER, fetched INTEGER, inserted INTEGER, message TEXT
);
CREATE TABLE IF NOT EXISTS insights (
    symbol TEXT, created_at TEXT, mode TEXT, stance TEXT, text TEXT, facts TEXT
);
"""


@contextmanager
def connect():
    p = db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(p, timeout=30)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    try:
        yield con
        con.commit()
    finally:
        con.close()


def upsert(rows: list[dict]) -> int:
    """插入新记录；uid 已存在则忽略（历史点），快照点同一分钟内重复也会被忽略。返回新增条数。"""
    n = 0
    with connect() as con:
        for r in rows:
            cur = con.execute(
                "INSERT OR IGNORE INTO records(uid,source_id,metric,symbol,time,value,extra,fetched_at) VALUES (?,?,?,?,?,?,?,?)",
                (r["uid"], r["source_id"], r["metric"], r["symbol"], r["time"], r["value"],
                 json.dumps(r["extra"]) if r.get("extra") else None, r["fetched_at"]))
            n += cur.rowcount
    return n


def log_run(source_id, started_at, ok, fetched, inserted, message=""):
    with connect() as con:
        con.execute("INSERT INTO runs(source_id,started_at,ok,fetched,inserted,message) VALUES (?,?,?,?,?,?)",
                    (source_id, started_at, int(ok), fetched, inserted, message))


def last_runs() -> list[dict]:
    with connect() as con:
        return [dict(r) for r in con.execute(
            "SELECT r.* FROM runs r JOIN (SELECT source_id, MAX(id) mid FROM runs GROUP BY source_id) m ON r.id=m.mid")]


def series(metric: str, symbol: str, source_id: str | None = None) -> list[dict]:
    """某指标的全部点（按时间升序）。返回 [{source_id,time,value,extra}]。"""
    sql = "SELECT source_id,time,value,extra FROM records WHERE metric=? AND symbol=?"
    args: list = [metric, symbol]
    if source_id:
        sql += " AND source_id=?"
        args.append(source_id)
    with connect() as con:
        out = []
        for r in con.execute(sql + " ORDER BY time", args):
            d = dict(r)
            d["extra"] = json.loads(d["extra"]) if d["extra"] else {}
            out.append(d)
        return out


def latest_by_source(metric: str, symbol: str) -> dict[str, dict]:
    """每家交易所最新一个点。"""
    sql = """SELECT r.source_id,r.time,r.value,r.extra FROM records r
             JOIN (SELECT source_id, MAX(time) mt FROM records WHERE metric=? AND symbol=? GROUP BY source_id) m
             ON r.source_id=m.source_id AND r.time=m.mt WHERE r.metric=? AND r.symbol=?"""
    with connect() as con:
        out = {}
        for r in con.execute(sql, (metric, symbol, metric, symbol)):
            d = dict(r)
            d["extra"] = json.loads(d["extra"]) if d["extra"] else {}
            out[d["source_id"]] = d
        return out


def save_insight(symbol, created_at, mode, stance, text, facts):
    with connect() as con:
        con.execute("INSERT INTO insights VALUES (?,?,?,?,?,?)", (symbol, created_at, mode, stance, text, json.dumps(facts, ensure_ascii=False)))


def latest_insight(symbol: str) -> dict | None:
    with connect() as con:
        r = con.execute("SELECT * FROM insights WHERE symbol=? ORDER BY created_at DESC LIMIT 1", (symbol,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["facts"] = json.loads(d["facts"])
        return d


def count_records() -> dict:
    with connect() as con:
        return {r[0]: r[1] for r in con.execute("SELECT source_id, COUNT(*) FROM records GROUP BY source_id")}
