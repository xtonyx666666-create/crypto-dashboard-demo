"""Hyperliquid（链上永续 DEX，api.hyperliquid.xyz，公开免 Key；非前十中心化交易所，作为补充）。
资金费率每 1 小时结算一次。覆盖：资金费率(+历史)、持仓量。
"""
import time

from collectors.base import collect

URL = "https://api.hyperliquid.xyz/info"


def pre(ctx):
    meta, ctxs = ctx.post(URL, {"type": "metaAndAssetCtxs"})
    return {u["name"]: c for u, c in zip(meta["universe"], ctxs)}


def per_symbol(ctx, s, assets):
    a = (assets or {}).get(s)
    if not a:
        raise KeyError(f"Hyperliquid 没有 {s}")
    mark = float(a["markPx"])
    ctx.rec("funding_rate", s, None, a["funding"], interval_h=1, mark=mark)
    ctx.rec("price", s, None, mark)
    ctx.rec("volume_24h_usd", s, None, a["dayNtlVlm"])
    ctx.rec("oi_usd", s, None, float(a["openInterest"]) * mark)
    start = int(time.time() * 1000) - 3 * 86400_000
    for r in ctx.safe("fh", ctx.post, URL, {"type": "fundingHistory", "coin": s, "startTime": start}) or []:
        ctx.rec("funding_hist", s, r["time"], r["fundingRate"], interval_h=1)


def fetch(source: dict) -> list[dict]:
    return collect(source, per_symbol, pre)
