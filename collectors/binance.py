"""Binance U 本位永续（fapi.binance.com，公开免 Key）。
覆盖：资金费率(+历史)、持仓量(+历史)、账户/大户账户/大户持仓多空比、1h 价格。
注：Binance 不公开爆仓历史（需 WebSocket 或 Key），故无爆仓数据。
"""
from collectors.base import collect

BASE = "https://fapi.binance.com"
HIST = 480  # 1 小时 × 480 ≈ 20 天


def pre(ctx):
    info = {i["symbol"]: i.get("fundingIntervalHours", 8) for i in ctx.get(BASE + "/fapi/v1/fundingInfo")}
    return info


def per_symbol(ctx, s, info):
    sym = f"{s}USDT"
    iv = (info or {}).get(sym, 8)
    p = ctx.get(BASE + "/fapi/v1/premiumIndex", symbol=sym)
    mark = float(p["markPrice"])
    ctx.rec("funding_rate", s, None, p["lastFundingRate"], interval_h=iv, mark=mark)
    tk = ctx.safe("ticker24h", ctx.get, BASE + "/fapi/v1/ticker/24hr", symbol=sym)
    if tk:
        ctx.rec("price", s, None, tk["lastPrice"])
        ctx.rec("volume_24h_usd", s, None, tk["quoteVolume"])
    oi = ctx.safe("openInterest", ctx.get, BASE + "/fapi/v1/openInterest", symbol=sym)
    if oi:
        ctx.rec("oi_usd", s, None, float(oi["openInterest"]) * mark)
    for r in ctx.safe("fundingRate", ctx.get, BASE + "/fapi/v1/fundingRate", symbol=sym, limit=100) or []:
        ctx.rec("funding_hist", s, r["fundingTime"], r["fundingRate"], interval_h=iv)
    for r in ctx.safe("openInterestHist", ctx.get, BASE + "/futures/data/openInterestHist", symbol=sym, period="1h", limit=HIST) or []:
        ctx.rec("oi_hist", s, r["timestamp"], r["sumOpenInterestValue"])
    for metric, path in (("lsr_account", "globalLongShortAccountRatio"), ("lsr_top_account", "topLongShortAccountRatio"),
                         ("lsr_top_position", "topLongShortPositionRatio")):
        for r in ctx.safe(path, ctx.get, f"{BASE}/futures/data/{path}", symbol=sym, period="1h", limit=HIST) or []:
            ctx.rec(metric, s, r["timestamp"], r["longShortRatio"])
    for k in ctx.safe("klines", ctx.get, BASE + "/fapi/v1/klines", symbol=sym, interval="1h", limit=HIST) or []:
        ctx.rec("price_hist", s, k[0], k[4])


def fetch(source: dict) -> list[dict]:
    return collect(source, per_symbol, pre)
