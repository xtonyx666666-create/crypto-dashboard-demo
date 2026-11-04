"""Gate USDT 永续（api.gateio.ws，公开免 Key）。
contract_stats 一个接口同时给出：持仓量、账户/大户账户/大户持仓多空比、爆仓金额（1 小时）。
"""
from collectors.base import collect

BASE = "https://api.gateio.ws/api/v4/futures/usdt"


def per_symbol(ctx, s, _):
    c = f"{s}_USDT"
    d = ctx.get(f"{BASE}/contracts/{c}")
    iv = round(int(d.get("funding_interval", 28800)) / 3600)
    ctx.rec("funding_rate", s, None, d["funding_rate"], interval_h=iv, mark=float(d["mark_price"]))
    tk = ctx.safe("ticker", ctx.get, f"{BASE}/tickers", contract=c)
    if tk:
        ctx.rec("price", s, None, tk[0]["last"])
        ctx.rec("volume_24h_usd", s, None, tk[0]["volume_24h_quote"])
    for r in ctx.safe("fh", ctx.get, f"{BASE}/funding_rate", contract=c, limit=100) or []:
        ctx.rec("funding_hist", s, r["t"] * 1000, r["r"], interval_h=iv)
    stats = ctx.get(f"{BASE}/contract_stats", contract=c, interval="1h", limit=480)
    for r in stats:
        ms = r["time"] * 1000
        ctx.rec("oi_hist", s, ms, r.get("open_interest_usd"))
        ctx.rec("lsr_account", s, ms, r.get("lsr_account"))
        ctx.rec("lsr_top_account", s, ms, r.get("top_lsr_account"))
        ctx.rec("lsr_top_position", s, ms, r.get("top_lsr_size"))
        ctx.rec("liq_long_usd", s, ms, r.get("long_liq_usd"))
        ctx.rec("liq_short_usd", s, ms, r.get("short_liq_usd"))
    if stats:
        ctx.rec("oi_usd", s, None, stats[-1].get("open_interest_usd"))


def fetch(source: dict) -> list[dict]:
    return collect(source, per_symbol)
