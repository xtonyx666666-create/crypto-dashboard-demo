"""恐慌贪婪指数（alternative.me，免 Key）。全市场指标，symbol 固定为 MARKET。
sources.yaml 字段：days（取最近多少天，默认 365）。0-24 极度恐慌 / 25-46 恐慌 / 47-54 中性 / 55-75 贪婪 / 76-100 极度贪婪。
"""
from collectors.base import Ctx


def fetch(source: dict) -> list[dict]:
    ctx = Ctx(source)
    d = ctx.get("https://api.alternative.me/fng/", limit=int(source.get("days", 365)), format="json")
    for r in d["data"]:
        ctx.rec("fng", "MARKET", int(r["timestamp"]) * 1000, r["value"], label=r["value_classification"])
    source["_warnings"] = ctx.warnings
    return ctx.rows
