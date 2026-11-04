"""MEXC 合约（contract.mexc.com，公开免 Key）。覆盖：资金费率(+历史)、持仓量（无公开多空比）。"""
from collectors.base import collect

BASE = "https://contract.mexc.com/api/v1/contract"


def pre(ctx):
    return {d["symbol"]: float(d["contractSize"]) for d in ctx.get(BASE + "/detail")["data"]}


def per_symbol(ctx, s, sizes):
    c = f"{s}_USDT"
    fr = ctx.get(f"{BASE}/funding_rate/{c}")["data"]
    tk = ctx.get(BASE + "/ticker", symbol=c)["data"]
    mark = float(tk["fairPrice"])
    iv = int(fr.get("collectCycle") or 8)
    ctx.rec("funding_rate", s, None, fr["fundingRate"], interval_h=iv, mark=mark)
    ctx.rec("price", s, None, tk["lastPrice"])
    ctx.rec("volume_24h_usd", s, None, tk["amount24"])
    if sizes and c in sizes:
        ctx.rec("oi_usd", s, None, float(tk["holdVol"]) * sizes[c] * mark)
    h = ctx.safe("fh", ctx.get, f"{BASE}/funding_rate/history", symbol=c, page_num=1, page_size=100)
    for r in (h or {}).get("data", {}).get("resultList", []):
        ctx.rec("funding_hist", s, r["settleTime"], r["fundingRate"], interval_h=iv)


def fetch(source: dict) -> list[dict]:
    return collect(source, per_symbol, pre)
