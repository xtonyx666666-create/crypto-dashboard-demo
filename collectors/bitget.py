"""Bitget USDT 永续（api.bitget.com，公开免 Key）。覆盖：资金费率(+历史)、持仓量、账户多空比。"""
from collectors.base import collect

BASE = "https://api.bitget.com/api/v2/mix/market"
PT = "USDT-FUTURES"


def per_symbol(ctx, s, _):
    sym = f"{s}USDT"
    t = ctx.get(BASE + "/ticker", symbol=sym, productType=PT)["data"][0]
    fr = ctx.safe("fund-rate", ctx.get, BASE + "/current-fund-rate", symbol=sym, productType=PT)
    iv = int(fr["data"][0].get("fundingRateInterval") or 8) if fr and fr.get("data") else 8
    mark = float(t["markPrice"])
    ctx.rec("funding_rate", s, None, t["fundingRate"], interval_h=iv, mark=mark)
    ctx.rec("oi_usd", s, None, float(t["holdingAmount"]) * mark)
    ctx.rec("price", s, None, t["lastPr"])
    ctx.rec("volume_24h_usd", s, None, t["usdtVolume"])
    for r in (ctx.safe("fh", ctx.get, BASE + "/history-fund-rate", symbol=sym, productType=PT, pageSize=100) or {}).get("data", []):
        ctx.rec("funding_hist", s, r["fundingTime"], r["fundingRate"], interval_h=iv)
    for r in (ctx.safe("lsr", ctx.get, BASE + "/account-long-short", symbol=sym, period="1h") or {}).get("data", []):
        ctx.rec("lsr_account", s, r["ts"], r["longShortAccountRatio"])


def fetch(source: dict) -> list[dict]:
    return collect(source, per_symbol)
