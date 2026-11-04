"""Bybit USDT 永续（api.bybit.com，公开免 Key）。
主数据源。用到的 v5 market 接口：tickers（资金费率/持仓量/价格/成交额）、funding/history、open-interest、account-ratio（多空比）、kline。
注：Bybit 无公开爆仓 REST 接口。
"""
from collectors.base import collect

BASE = "https://api.bybit.com/v5/market"


def per_symbol(ctx, s, _):
    sym = f"{s}USDT"
    t = ctx.get(BASE + "/tickers", category="linear", symbol=sym)["result"]["list"][0]
    iv = int(t.get("fundingIntervalHour") or 8)
    ctx.rec("funding_rate", s, None, t["fundingRate"], interval_h=iv, mark=float(t["markPrice"]))
    ctx.rec("oi_usd", s, None, t["openInterestValue"])
    ctx.rec("price", s, None, t["lastPrice"])
    ctx.rec("volume_24h_usd", s, None, t["turnover24h"])
    for r in (ctx.safe("fh", ctx.get, BASE + "/funding/history", category="linear", symbol=sym, limit=100) or {}).get("result", {}).get("list", []):
        ctx.rec("funding_hist", s, r["fundingRateTimestamp"], r["fundingRate"], interval_h=iv)
    kl = (ctx.safe("kline", ctx.get, BASE + "/kline", category="linear", symbol=sym, interval=60, limit=200) or {}).get("result", {}).get("list", [])
    close = {int(k[0]): float(k[4]) for k in kl}
    for ts, px in close.items():
        ctx.rec("price_hist", s, ts, px)
    for r in (ctx.safe("oi-hist", ctx.get, BASE + "/open-interest", category="linear", symbol=sym, intervalTime="1h", limit=200) or {}).get("result", {}).get("list", []):
        px = close.get(int(r["timestamp"]))
        if px:
            ctx.rec("oi_hist", s, r["timestamp"], float(r["openInterest"]) * px)
    for r in (ctx.safe("lsr", ctx.get, BASE + "/account-ratio", category="linear", symbol=sym, period="1h", limit=500) or {}).get("result", {}).get("list", []):
        if float(r["sellRatio"]) > 0:
            ctx.rec("lsr_account", s, r["timestamp"], float(r["buyRatio"]) / float(r["sellRatio"]))


def fetch(source: dict) -> list[dict]:
    return collect(source, per_symbol)
