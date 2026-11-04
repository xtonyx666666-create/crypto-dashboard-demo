"""采集器公共工具：HTTP、记录构造、并发、容错。

每个交易所插件只需要写一个 `fetch(source) -> list[dict]`（统一接口），
内部用 `collect(source, per_symbol)` 并发地为每个币种取数。
单个接口失败只记警告，不影响其它指标；整家交易所一条都没取到才抛异常（例如被地区封锁）。
"""
import datetime as dt
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

HEADERS = {"User-Agent": "Mozilla/5.0 (dashboard-demo/0.2)"}
_client = httpx.Client(headers=HEADERS, timeout=20, follow_redirects=True)

# 指标名（统一）——widgets.yaml / API / 前端都用这些 key
METRICS = {
    "funding_rate": "当前资金费率（每个结算周期，小数，0.0001 = 0.01%）；extra.interval_h = 结算周期小时数",
    "funding_hist": "历史已结算资金费率（同上）",
    "oi_usd": "当前持仓量（美元名义价值）",
    "oi_hist": "持仓量历史（美元，1 小时一个点）",
    "lsr_account": "账户多空比（多头账户数 / 空头账户数，1 小时）",
    "lsr_top_account": "大户账户多空比（1 小时）",
    "lsr_top_position": "大户持仓多空比（1 小时）",
    "liq_long_usd": "多单爆仓金额（美元，1 小时累计）",
    "liq_short_usd": "空单爆仓金额（美元，1 小时累计）",
    "price": "最新成交价（快照）",
    "volume_24h_usd": "24 小时成交额（美元，快照）",
    "fng": "恐慌贪婪指数（0-100，全市场，symbol=MARKET）",
    "price_hist": "价格（1 小时收盘价，用于图上叠加）",
}


class Ctx:
    """一次采集的上下文：负责 HTTP 请求、造记录、收集警告。"""

    def __init__(self, source: dict):
        self.source = source
        self.rows: list[dict] = []
        self.warnings: list[str] = []
        self.link = source.get("doc", "")

    # ---- HTTP ----
    def get(self, url: str, **params):
        return self._req("GET", url, params=params or None)

    def post(self, url: str, json: dict):
        return self._req("POST", url, json=json)

    def _req(self, method: str, url: str, **kw):
        last = None
        for attempt in range(3):
            try:
                r = _client.request(method, url, **kw)
                if r.status_code in (403, 451):
                    raise RuntimeError(f"HTTP {r.status_code}（可能被地区限制）")
                r.raise_for_status()
                return r.json()
            except Exception as e:
                last = e
                time.sleep(1.5 if '429' in str(e) else 0.4)
        raise last

    # ---- 记录 ----
    def rec(self, metric: str, symbol: str, ts, value, **extra) -> dict | None:
        """ts：毫秒时间戳（int/str）或 None（=现在）。value 为 None/无法转换时丢弃。"""
        try:
            v = float(value)
        except (TypeError, ValueError):
            return None
        t = dt.datetime.now(dt.timezone.utc) if ts is None else dt.datetime.fromtimestamp(float(ts) / 1000, dt.timezone.utc)
        if ts is None:
            t = t.replace(second=0, microsecond=0)
        r = {"time": t.isoformat(), "name": f"{metric}:{symbol}", "value": v, "text": "", "link": self.link,
             "metric": metric, "symbol": symbol, "extra": extra or None}
        self.rows.append(r)
        return r

    def warn(self, msg: str):
        self.warnings.append(msg)

    def safe(self, label: str, fn, *a, **kw):
        try:
            return fn(*a, **kw)
        except Exception as e:
            self.warn(f"{label}: {type(e).__name__}: {str(e)[:120]}")
            return None


def collect(source: dict, per_symbol, pre=None, workers: int = 6) -> list[dict]:
    """per_symbol(ctx, symbol, shared) 为每个币种执行；pre(ctx) 先执行一次返回共享数据。"""
    ctx = Ctx(source)
    shared = ctx.safe("pre", pre, ctx) if pre else None
    syms = source.get("symbols", ["BTC", "ETH", "SOL"])
    with ThreadPoolExecutor(int(source.get('workers', workers))) as ex:
        list(ex.map(lambda s: ctx.safe(f"{s}", per_symbol, ctx, s, shared), syms))
    source["_warnings"] = ctx.warnings
    if not ctx.rows:
        raise RuntimeError("没有取到任何数据：" + ("; ".join(ctx.warnings[:2]) or "未知原因"))
    return ctx.rows
