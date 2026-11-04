"""K 线（行情走势）：Bybit v5 /market/kline 历史回补 + 最新K线实时刷新，失败时降级 OKX。
存储：独立 SQLite 文件 data/klines.db（WITHOUT ROWID，按 币种+周期+时间 主键），不常驻内存。
懒加载：某个 币种×周期 第一次被请求时才在后台线程回补到 2025-01-01；启动后另有一个预热线程按顺序回补全部组合。
"""
import sqlite3
import threading
import time
from datetime import datetime, timezone

import httpx

from settings import ROOT

SYMBOLS = ["BTC", "ETH", "SOL"]
INTERVALS = {"5m": ("5", "5m", 300), "15m": ("15", "15m", 900), "4h": ("240", "4H", 14400),
             "1d": ("D", "1Dutc", 86400), "1w": ("W", "1Wutc", 604800)}
START_MS = int(datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
DB = ROOT / "data" / "klines.db"
_locks = {k: threading.Lock() for k in [(s, i) for s in SYMBOLS for i in INTERVALS]}
_state: dict = {}          # (sym, iv) -> {"done": bool, "source": str, "error": str}
_last_live: dict = {}
_client = httpx.Client(timeout=15, headers={"User-Agent": "crypto-dashboard-demo"})


def _con():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB, timeout=30)
    c.execute("CREATE TABLE IF NOT EXISTS k (s TEXT, i TEXT, t INTEGER, o REAL, h REAL, l REAL, c REAL, v REAL,"
              " PRIMARY KEY (s, i, t)) WITHOUT ROWID")
    return c


def _save(sym, iv, rows):
    rows = [r for r in rows if r[0] >= START_MS - INTERVALS[iv][2] * 1000 * 7]   # 只保留 2025-01 起（周线多留一根）
    if not rows:
        return
    with _con() as c:
        c.executemany("INSERT OR REPLACE INTO k VALUES (?,?,?,?,?,?,?,?)", [(sym, iv, *r) for r in rows])


def _bybit(sym, iv, end_ms, limit=1000):
    r = _client.get("https://api.bybit.com/v5/market/kline", params={"category": "linear", "symbol": sym + "USDT",
                    "interval": INTERVALS[iv][0], "end": end_ms, "limit": limit})
    r.raise_for_status()
    j = r.json()
    if j.get("retCode") != 0:
        raise RuntimeError(j.get("retMsg"))
    return [(int(x[0]), float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5])) for x in j["result"]["list"]]


def _okx(sym, iv, end_ms, limit=300):
    r = _client.get("https://www.okx.com/api/v5/market/history-candles", params={"instId": f"{sym}-USDT-SWAP",
                    "bar": INTERVALS[iv][1], "after": end_ms + 1, "limit": limit})
    r.raise_for_status()
    # OKX 合约成交量单位是张，这里用 volCcy（币数量）
    return [(int(x[0]), float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[6])) for x in r.json()["data"]]


def _fetch(sym, iv, end_ms, small=False):
    st = _state.setdefault((sym, iv), {"done": False, "source": "bybit", "error": ""})
    if st["source"] == "bybit":
        try:
            return _bybit(sym, iv, end_ms, 3 if small else 1000)
        except Exception as e:                      # 被地区封锁 / 限流 → 降级 OKX
            st["error"] = f"Bybit: {e}"[:200]
            st["source"] = "okx"
    return _okx(sym, iv, end_ms, 3 if small else 300)


def _range(sym, iv):
    with _con() as c:
        return c.execute("SELECT MIN(t), MAX(t), COUNT(*) FROM k WHERE s=? AND i=?", (sym, iv)).fetchone()


def backfill(sym, iv):
    """从现在往回翻页（limit 1000）：先补到已有最新一根，再从已有最早一根补到 2025-01-01。"""
    lock = _locks[(sym, iv)]
    if not lock.acquire(blocking=False):
        return
    try:
        lo, hi, _ = _range(sym, iv)
        segments = [(int(time.time() * 1000), hi or START_MS)] + ([(lo - 1, START_MS)] if lo else [])
        for end, stop in segments:
            while end > stop:
                rows = _fetch(sym, iv, end)
                if not rows:
                    break
                _save(sym, iv, rows)
                oldest = min(r[0] for r in rows)
                if oldest >= end:
                    break
                end = oldest - 1
                time.sleep(0.05)
        _state[(sym, iv)]["done"] = True
    except Exception as e:
        _state.setdefault((sym, iv), {}).update(error=str(e)[:200])
    finally:
        lock.release()


def ensure(sym, iv):
    st = _state.get((sym, iv))
    if not (st and st.get("done")) and not _locks[(sym, iv)].locked():
        threading.Thread(target=backfill, args=(sym, iv), daemon=True).start()


def live(sym, iv):
    """刷新最新 3 根（同一组合 20 秒内最多一次，前端每 30 秒轮询）。"""
    if time.time() - _last_live.get((sym, iv), 0) < 20:
        return
    _last_live[(sym, iv)] = time.time()
    try:
        _save(sym, iv, _fetch(sym, iv, int(time.time() * 1000), small=True))
    except Exception as e:
        _state.setdefault((sym, iv), {}).update(error=str(e)[:200])


def query(sym, iv, before=None, limit=2000, since=None):
    with _con() as c:
        if since is not None:
            rows = c.execute("SELECT t,o,h,l,c,v FROM k WHERE s=? AND i=? AND t>=? ORDER BY t", (sym, iv, since)).fetchall()
        else:
            rows = c.execute("SELECT t,o,h,l,c,v FROM k WHERE s=? AND i=? AND t<? ORDER BY t DESC LIMIT ?",
                             (sym, iv, before or 1 << 62, limit)).fetchall()[::-1]
    lo, hi, n = _range(sym, iv)
    st = _state.get((sym, iv), {})
    return {"symbol": sym, "interval": iv, "rows": rows, "first": lo, "last": hi, "count": n,
            "complete": bool(st.get("done")), "source": st.get("source", "bybit"), "error": st.get("error", ""),
            "start": START_MS}


def warm():
    """启动预热：先补数据量小的周期，最后补 5m。"""
    for iv in ["1w", "1d", "4h", "15m", "5m"]:
        ts = [threading.Thread(target=backfill, args=(s, iv), daemon=True) for s in SYMBOLS]
        for t in ts:
            t.start()
        for t in ts:
            t.join()


def start_warm():
    threading.Thread(target=warm, daemon=True).start()
