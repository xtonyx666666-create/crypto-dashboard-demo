"""HTX（原火币）USDT 本位永续（api.hbdm.com，公开免 Key）。覆盖：资金费率(+历史)、持仓量、精英账户/持仓多空比。"""
from collectors.base import collect

BASE = "https://api.hbdm.com/linear-swap-api/v1"


def per_symbol(ctx, s, _):
    c = f"{s}-USDT"
    d = ctx.get(f"{BASE}/swap_funding_rate", contract_code=c)["data"]
    ctx.rec("funding_rate", s, None, d["funding_rate"], interval_h=8)
    md = ctx.safe("detail", ctx.get, "https://api.hbdm.com/linear-swap-ex/market/detail/merged", contract_code=c)
    if md and md.get("tick"):
        ctx.rec("price", s, None, md["tick"]["close"])
        ctx.rec("volume_24h_usd", s, None, md["tick"]["trade_turnover"])
    oi = ctx.safe("oi", ctx.get, f"{BASE}/swap_open_interest", contract_code=c)
    if oi and oi.get("data"):
        ctx.rec("oi_usd", s, None, oi["data"][0]["value"])
    fh = ctx.safe("fh", ctx.get, f"{BASE}/swap_historical_funding_rate", contract_code=c, page_size=50)
    for r in (fh or {}).get("data", {}).get("data", []):
        ctx.rec("funding_hist", s, r["funding_time"], r["funding_rate"], interval_h=8)
    for metric, path in (("lsr_top_account", "swap_elite_account_ratio"), ("lsr_top_position", "swap_elite_position_ratio")):
        res = ctx.safe(path, ctx.get, f"{BASE}/{path}", contract_code=c, period="60min")
        for r in (res or {}).get("data", {}).get("list", []):
            if r["sell_ratio"]:
                ctx.rec(metric, s, r["ts"], r["buy_ratio"] / r["sell_ratio"])


def fetch(source: dict) -> list[dict]:
    return collect(source, per_symbol)
