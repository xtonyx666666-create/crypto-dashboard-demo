"""采集器注册表。

统一接口（所有采集器必须遵守）：

    def fetch(source: dict) -> list[dict]

`source` 是 config/sources.yaml 里的一条配置（含 symbols 币种列表）；返回记录列表，字段：
    time   : str    ISO8601（UTC）
    name   : str    "指标:币种"，如 "funding_rate:BTC"
    value  : float  数值
    text   : str    备注（可空）
    link   : str    来源/文档链接
    metric : str    指标名，见 collectors/base.py 的 METRICS
    symbol : str    币种，如 BTC
    extra  : dict   可选附加信息（如 {"interval_h": 8}）
新增交易所 = 在本目录新建 <type>.py（可抄 binance.py），写 fetch(source)，sources.yaml 里 type 填文件名。
"""
import importlib
from typing import Callable


def get_collector(type_: str) -> Callable[[dict], list[dict]]:
    try:
        mod = importlib.import_module(f"collectors.{type_}")
    except ModuleNotFoundError as e:
        raise ValueError(f"未知的数据源类型 type={type_}：请在 collectors/ 下新建 {type_}.py") from e
    return mod.fetch


def fetch(source: dict) -> list[dict]:
    return get_collector(source["type"])(source)
