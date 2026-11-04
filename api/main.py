"""FastAPI 后端（只读）：把 SQLite 里的指标整理成各卡片需要的 JSON，同时托管 web/ 静态页面。

启动：uvicorn api.main:app --host 0.0.0.0 --port 8000
接口一览：/api/meta  /api/funding  /api/lsr  /api/fng  /api/oi  /api/liq  /api/market  /api/status
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from processors import metrics
from settings import ROOT, load_sources, load_symbols, load_widgets
from storage import db

app = FastAPI(title="Derivatives Dashboard API")
LIMIT = {"1h": 168, "4h": 120, "1d": 30}      # 各周期最多返回多少根


def exchanges() -> list[dict]:
    return [{"id": s["id"], "name": s.get("name", s["id"])} for s in load_sources() if s["type"] != "fear_greed"]


def _check(symbol: str) -> str:
    symbol = symbol.upper()
    if symbol not in load_symbols():
        raise HTTPException(404, f"不支持的币种 {symbol}")
    return symbol


@app.get("/api/meta")
def meta():
    runs = db.last_runs()
    last = max((r["started_at"] for r in runs), default=None)
    w = load_widgets()
    return {"title": w.get("title"), "subtitle": w.get("subtitle"), "pages": w.get("pages", []),
            "symbols": load_symbols(), "exchanges": exchanges(), "updated_at": last}


@app.get("/api/status")
def status():
    names = {s["id"]: s.get("name", s["id"]) for s in load_sources()}
    counts = db.count_records()
    return {"runs": [{**r, "name": names.get(r["source_id"], r["source_id"]), "records": counts.get(r["source_id"], 0)}
                     for r in sorted(db.last_runs(), key=lambda r: list(names).index(r["source_id"]) if r["source_id"] in names else 99)]}


# 1) 资金费率矩阵：行=币种，列=交易所
@app.get("/api/funding")
def funding():
    syms, exs = load_symbols(), exchanges()
    cells: dict = {}
    for sym in syms:
        for ex_id, p in db.latest_by_source("funding_rate", sym).items():
            iv = p["extra"].get("interval_h", 8)
            cells.setdefault(sym, {})[ex_id] = {"rate": p["value"] * 100, "interval_h": iv,
                                                "per8h": metrics.per8h(p["value"], iv), "annual": metrics.annualize(p["value"], iv)}
    return {"symbols": syms, "exchanges": exs, "cells": cells}


# 2) 多空比：每个交易所一条横条
LSR_KINDS = {"account": ("lsr_account", "账户多空比"), "top_account": ("lsr_top_account", "大户账户多空比"),
             "top_position": ("lsr_top_position", "大户持仓多空比")}


@app.get("/api/lsr")
def lsr(symbol: str = "BTC", kind: str = "account"):
    symbol = _check(symbol)
    if kind not in LSR_KINDS:
        raise HTTPException(400, f"kind 可选 {list(LSR_KINDS)}")
    metric, label = LSR_KINDS[kind]
    latest = db.latest_by_source(metric, symbol)
    rows = []
    for ex in exchanges():
        p = latest.get(ex["id"])
        if p:
            r = p["value"]
            rows.append({**ex, "ratio": r, "long_pct": r / (1 + r) * 100, "short_pct": 100 / (1 + r), "time": p["time"]})
        else:
            rows.append({**ex, "ratio": None, "long_pct": None, "short_pct": None})
    return {"symbol": symbol, "kind": kind, "label": label, "kinds": {k: v[1] for k, v in LSR_KINDS.items()}, "rows": rows}


# 3) 恐慌贪婪指数
@app.get("/api/fng")
def fng():
    pts = db.series("fng", "MARKET")
    if not pts:
        return {"latest": None, "history": []}
    hist = [{"t": p["time"][:10], "v": p["value"]} for p in pts]
    cur = pts[-1]

    def ago(n):
        return hist[-1 - n]["v"] if len(hist) > n else None
    return {"latest": {"value": cur["value"], "label": cur["extra"].get("label"), "time": cur["time"][:10]},
            "yesterday": ago(1), "week": ago(7), "month": ago(30), "history": hist}


# 4) 持仓量：按交易所堆叠（历史）+ 各所当前值
@app.get("/api/oi")
def oi(symbol: str = "BTC", period: str = "4h"):
    symbol = _check(symbol)
    names = {e["id"]: e["name"] for e in exchanges()}
    by_ex = {}
    for p in db.series("oi_hist", symbol):
        by_ex.setdefault(p["source_id"], []).append(p)
    times, stacked = metrics.stack_by_time(by_ex, period, "last")
    n = LIMIT.get(period, 120)
    price = [p for p in db.series("price_hist", symbol, "bybit")]
    ptimes = {t: v for t, v in ((x["time"], x["value"]) for x in metrics.resample(price, period))}
    now = db.latest_by_source("oi_usd", symbol)
    return {"symbol": symbol, "period": period, "times": times[-n:],
            "series": [{"id": k, "name": names.get(k, k), "data": v[-n:]} for k, v in stacked.items()],
            "price": [ptimes.get(t) for t in times[-n:]],
            "current": [{"id": e["id"], "name": e["name"], "value": now[e["id"]]["value"] if e["id"] in now else None} for e in exchanges()]}


# 5) 爆仓：多单/空单
@app.get("/api/liq")
def liq(symbol: str = "BTC", period: str = "1h"):
    symbol = _check(symbol)
    names = {e["id"]: e["name"] for e in exchanges()}
    out = {}
    for side, metric in (("long", "liq_long_usd"), ("short", "liq_short_usd")):
        pts = [p for p in db.series(metric, symbol, "gate")]                 # 只用有完整小时历史的 Gate 画图
        out[side] = {x["time"]: x["value"] for x in metrics.resample(pts, period, "sum")}
    times = sorted(set(out["long"]) | set(out["short"]))[-LIMIT.get(period, 168):]
    # 各交易所近期合计（Gate 近 24h；OKX 为公开接口返回的最近一段强平单，时间窗口较短）
    table = []
    for ex in ("gate", "okx"):
        l = db.series("liq_long_usd", symbol, ex)
        s = db.series("liq_short_usd", symbol, ex)
        if not l and not s:
            continue
        span = sorted(p["time"] for p in l + s)
        last24 = lambda pts: sum(p["value"] for p in pts[-24:]) if ex == "gate" else sum(p["value"] for p in pts)
        table.append({"id": ex, "name": names[ex], "long": last24(l), "short": last24(s),
                      "window": "近 24 小时" if ex == "gate" else f"{span[0][5:16]} ~ {span[-1][5:16]} UTC（接口仅返回最近一段）"})
    return {"symbol": symbol, "period": period, "times": times,
            "long": [out["long"].get(t, 0) for t in times], "short": [out["short"].get(t, 0) for t in times], "table": table,
            "note": "Binance/Bybit/Bitget 等未提供免费公开爆仓历史接口；图表使用 Gate 的 1 小时爆仓统计，OKX 为最近强平单。"}


# 6) 各交易所价格与成交量
@app.get("/api/market")
def market(symbol: str = "BTC"):
    symbol = _check(symbol)
    px, vol = db.latest_by_source("price", symbol), db.latest_by_source("volume_24h_usd", symbol)
    prices = sorted(p["value"] for p in px.values())
    med = prices[len(prices) // 2] if prices else None
    total = sum(v["value"] for v in vol.values()) or 1
    rows = []
    for e in exchanges():
        p, v = px.get(e["id"]), vol.get(e["id"])
        rows.append({**e, "price": p["value"] if p else None,
                     "dev_pct": (p["value"] / med - 1) * 100 if p and med else None,
                     "volume": v["value"] if v else None, "share": v["value"] / total * 100 if v else None})
    return {"symbol": symbol, "median": med, "rows": rows}


_last_refresh: dict[str, float] = {}


@app.post("/api/refresh")
def refresh(source: str = "bybit"):
    """手动立即刷新一个数据源（默认 Bybit，主数据源）。每个源最少间隔 30 秒，避免被频繁点击打爆上游接口。"""
    import time
    from scheduler.jobs import run_all
    if source not in {s["id"] for s in load_sources()}:
        raise HTTPException(404, "未知数据源")
    if time.time() - _last_refresh.get("_all", 0) < 60:
        return {"skipped": True, "reason": "60 秒内已刷新过"}
    _last_refresh["_all"] = time.time()
    return {"results": run_all(source)}


@app.get("/")
def index():
    return FileResponse(ROOT / "web" / "index.html")


app.mount("/", StaticFiles(directory=ROOT / "web"), name="web")
