"""Deribit 永续（www.deribit.com，公开免 Key）。BTC/ETH 为币本位反向合约（持仓量即美元），SOL/XRP 为 USDC 线性合约。
覆盖：资金费率（8h 口径）、持仓量、资金费率历史。
"""
from collectors.base import collect

BASE = "https://www.deribit.com/api/v2/public"
NAMES = {"BTC": "BTC-PERPETUAL", "ETH": "ETH-PERPETUAL"}


def per_symbol(ctx, s, _):
    name = NAMES.get(s, f"{s}_USDC-PERPETUAL")
    t = ctx.get(BASE + "/ticker", instrument_name=name)["result"]
    mark = float(t["mark_price"])
    ctx.rec("funding_rate", s, None, t["funding_8h"], interval_h=8, mark=mark)
    ctx.rec("price", s, None, t["last_price"])
    ctx.rec("volume_24h_usd", s, None, t["stats"].get("volume_usd"))
    oi = float(t["open_interest"])
    ctx.rec("oi_usd", s, None, oi * mark if name.endswith("_USDC-PERPETUAL") else oi)
    now = int(t["timestamp"])
    h = ctx.safe("fh", ctx.get, BASE + "/get_funding_rate_history", instrument_name=name,
                 start_timestamp=now - 8 * 86400_000, end_timestamp=now)
    for r in (h or {}).get("result", []):
        if (r["timestamp"] // 3_600_000) % 8 == 0:        # 取 00/08/16 点作为 8 小时结算点
            ctx.rec("funding_hist", s, r["timestamp"], r["interest_8h"], interval_h=8)


def fetch(source: dict) -> list[dict]:
    return collect(source, per_symbol)
