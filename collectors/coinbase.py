"""Coinbase。
优先：Coinbase International Exchange 永续（api.international.coinbase.com）→ 资金费率；
降级：该域名在本机网络持续 502/不可达时，改用 Coinbase Exchange 现货（api.exchange.coinbase.com，BTC-USD 等）
      只提供「价格 + 24h 成交额」，用于价格/成交量对比页；资金费率/持仓量没有该所数据。
降级原因会写进运行日志，并在「数据源状态」/报告中说明。
"""
from collectors.base import collect

INTX = "https://api.international.coinbase.com/api/v1/instruments"
SPOT = "https://api.exchange.coinbase.com/products"


def per_symbol(ctx, s, _):
    try:
        q = ctx.get(f"{INTX}/{s}-PERP/quote")
        mark = float(q.get("mark_price") or 0) or None
        if q.get("predicted_funding") is not None:
            ctx.rec("funding_rate", s, None, q["predicted_funding"], interval_h=1, mark=mark)
        if mark:
            ctx.rec("price", s, None, mark)
        return
    except Exception as e:
        ctx.warn(f"{s}: Coinbase International 不可用（{str(e)[:60]}），降级为现货价格/成交额")
    st = ctx.get(f"{SPOT}/{s}-USD/stats")
    last = float(st["last"])
    ctx.rec("price", s, None, last)
    ctx.rec("volume_24h_usd", s, None, float(st["volume"]) * last)


def fetch(source: dict) -> list[dict]:
    return collect(source, per_symbol)
