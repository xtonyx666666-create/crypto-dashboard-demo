"""KuCoin Futures（api-futures.kucoin.com，公开免 Key）。覆盖：资金费率、持仓量（无公开多空比/历史接口）。"""
from collectors.base import collect

BASE = "https://api-futures.kucoin.com/api/v1"


def pre(ctx):
    return {c["baseCurrency"].replace("XBT", "BTC"): c for c in ctx.get(BASE + "/contracts/active")["data"]
            if c.get("quoteCurrency") == "USDT" and c.get("type") == "FFWCSX" and not c.get("isInverse")}


def per_symbol(ctx, s, contracts):
    c = (contracts or {}).get(s)
    if not c:
        raise KeyError(f"KuCoin 没有 {s} USDT 永续")
    mark = float(c["markPrice"])
    iv = round(int(c.get("currentFundingRateGranularity") or c.get("fundingRateGranularity") or 28800000) / 3_600_000)
    ctx.rec("funding_rate", s, None, c["fundingFeeRate"], interval_h=iv, mark=mark)
    ctx.rec("price", s, None, c["lastTradePrice"])
    ctx.rec("volume_24h_usd", s, None, c["turnoverOf24h"])
    ctx.rec("oi_usd", s, None, float(c["openInterest"]) * float(c["multiplier"]) * mark)


def fetch(source: dict) -> list[dict]:
    return collect(source, per_symbol, pre)
