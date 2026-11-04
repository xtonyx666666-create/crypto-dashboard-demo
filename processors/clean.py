"""清洗与去重。

- 去重：uid = 交易所|指标:币种|时间；历史点重复抓取时只保留一份（storage.upsert 里 INSERT OR IGNORE）；
- 清洗：丢弃 NaN/无穷/明显异常值（资金费率绝对值 > 5% 一个周期、多空比 <=0 或 > 100、负的持仓/爆仓额）。
"""
import math

LIMITS = {  # metric: (min, max)
    "funding_rate": (-0.05, 0.05), "funding_hist": (-0.05, 0.05),
    "lsr_account": (0.01, 100), "lsr_top_account": (0.01, 100), "lsr_top_position": (0.01, 100),
    "oi_usd": (0, 1e13), "oi_hist": (0, 1e13), "liq_long_usd": (0, 1e11), "liq_short_usd": (0, 1e11),
    "price_hist": (0, 1e9), "price": (0, 1e9), "volume_24h_usd": (0, 1e13), "fng": (0, 100),
}


def make_uid(source: dict, row: dict) -> str:
    return f"{source['id']}|{row['name']}|{row['time']}"


def is_valid(row: dict) -> bool:
    v = row.get("value")
    if v is None or isinstance(v, bool) or not math.isfinite(v):
        return False
    lo, hi = LIMITS.get(row.get("metric"), (-math.inf, math.inf))
    return lo <= v <= hi


def clean(source: dict, rows: list[dict]) -> list[dict]:
    seen, out = set(), []
    for r in rows:
        if not is_valid(r):
            continue
        r["uid"] = make_uid(source, r)
        if r["uid"] in seen:            # 同一批里的重复
            continue
        seen.add(r["uid"])
        out.append(r)
    return out
