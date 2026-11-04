"""OKX 永续（www.okx.com，公开免 Key）。
覆盖：资金费率(+历史)、持仓量(+历史，按币种汇总全部合约)、账户/大户账户/大户持仓多空比、
爆仓（最近成交的强平单，按小时汇总，只覆盖最近一段时间）。
"""
from collections import defaultdict

from collectors.base import collect

BASE = "https://www.okx.com/api/v5"


def per_symbol(ctx, s, _):
    inst = f"{s}-USDT-SWAP"
    d = ctx.get(BASE + "/public/funding-rate", instId=inst)["data"][0]
    iv = round((int(d["nextFundingTime"]) - int(d["fundingTime"])) / 3_600_000) or 8
    ctx.rec("funding_rate", s, None, d["fundingRate"], interval_h=iv)
    tk = ctx.safe("ticker", ctx.get, BASE + "/market/ticker", instId=inst)
    if tk and tk["data"]:
        last = float(tk["data"][0]["last"])
        ctx.rec("price", s, None, last)
        ctx.rec("volume_24h_usd", s, None, float(tk["data"][0]["volCcy24h"]) * last)   # 币数 × 价格
    oi = ctx.safe("open-interest", ctx.get, BASE + "/public/open-interest", instType="SWAP", instId=inst)
    if oi and oi["data"]:
        ctx.rec("oi_usd", s, None, oi["data"][0]["oiUsd"])
    for r in (ctx.safe("fh", ctx.get, BASE + "/public/funding-rate-history", instId=inst, limit=100) or {}).get("data", []):
        ctx.rec("funding_hist", s, r["fundingTime"], r["realizedRate"] or r["fundingRate"], interval_h=iv)
    rub = BASE + "/rubik/stat/contracts"
    for r in (ctx.safe("oi-hist", ctx.get, rub + "/open-interest-volume", ccy=s, period="1H") or {}).get("data", [])[:480]:
        ctx.rec("oi_hist", s, r[0], r[1])
    for metric, path, k in (("lsr_account", "long-short-account-ratio", {"ccy": s}),
                            ("lsr_top_account", "long-short-account-ratio-contract-top-trader", {"instId": inst}),
                            ("lsr_top_position", "long-short-position-ratio-contract-top-trader", {"instId": inst})):
        for r in (ctx.safe(path, ctx.get, f"{rub}/{path}", period="1H", **k) or {}).get("data", [])[:480]:
            ctx.rec(metric, s, r[0], r[1])
    # 爆仓：张数 × 面值(ctVal) × 破产价
    ct = ctx.safe("ctVal", ctx.get, BASE + "/public/instruments", instType="SWAP", instId=inst)
    ct_val = float(ct["data"][0]["ctVal"]) if ct and ct["data"] else None
    liq = ctx.safe("liquidation", ctx.get, BASE + "/public/liquidation-orders", instType="SWAP", uly=f"{s}-USDT", state="filled")
    if ct_val and liq:
        buckets = defaultdict(float)
        for item in liq["data"]:
            for x in item.get("details", []):
                hour = int(x["ts"]) // 3_600_000 * 3_600_000
                buckets[(hour, x["posSide"])] += float(x["sz"]) * ct_val * float(x["bkPx"])
        for (hour, side), usd in buckets.items():
            ctx.rec("liq_long_usd" if side == "long" else "liq_short_usd", s, hour, usd)


def fetch(source: dict) -> list[dict]:
    return collect(source, per_symbol)
