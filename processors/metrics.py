"""指标计算：资金费率换算、周期重采样、多交易所合并。"""
import datetime as dt

PERIOD_H = {"1h": 1, "4h": 4, "1d": 24}


def annualize(rate: float, interval_h: float) -> float:
    """每个结算周期的费率 → 年化（百分数）。"""
    return rate / (interval_h or 8) * 24 * 365 * 100


def per8h(rate: float, interval_h: float) -> float:
    """统一折算成 8 小时口径（百分数），便于不同结算周期的交易所横向比较。"""
    return rate / (interval_h or 8) * 8 * 100


def _ts(t: str) -> dt.datetime:
    return dt.datetime.fromisoformat(t)


def bucket(t: str, hours: int) -> str:
    d = _ts(t).astimezone(dt.timezone.utc)
    epoch_h = int(d.timestamp() // 3600)
    return dt.datetime.fromtimestamp(epoch_h // hours * hours * 3600, dt.timezone.utc).isoformat()


def resample(points: list[dict], period: str, how: str = "last") -> list[dict]:
    """points: [{time,value}] 升序；how: last（比率/存量取期末）| sum（流量，如爆仓额）。"""
    h = PERIOD_H.get(period, 1)
    if h == 1 and how == "last":
        return [{"time": p["time"], "value": p["value"]} for p in points]
    out: dict[str, float] = {}
    for p in points:
        b = bucket(p["time"], h)
        out[b] = out.get(b, 0) + p["value"] if how == "sum" else p["value"]
    return [{"time": k, "value": v} for k, v in sorted(out.items())]


def change_pct(points: list[dict], hours: int) -> float | None:
    """最新点相对 N 小时前（最近的更早点）的变化百分比。"""
    if len(points) < 2:
        return None
    last = points[-1]
    target = _ts(last["time"]) - dt.timedelta(hours=hours)
    base = None
    for p in points:
        if _ts(p["time"]) <= target:
            base = p
    if not base or not base["value"]:
        return None
    return (last["value"] / base["value"] - 1) * 100


def stack_by_time(series_by_source: dict[str, list[dict]], period: str, how: str = "last") -> tuple[list[str], dict[str, list]]:
    """多个交易所按时间对齐；缺失处存量(last)用前值填充，流量(sum)用 0。"""
    rs = {s: {p["time"]: p["value"] for p in resample(pts, period, how)} for s, pts in series_by_source.items() if pts}
    times = sorted({t for d in rs.values() for t in d})
    out = {}
    for s, d in rs.items():
        vals, prev = [], None
        first = min(d) if d else None
        for t in times:
            if t in d:
                prev = d[t]
                vals.append(prev)
            elif how == "sum":
                vals.append(0)
            else:
                vals.append(prev if first and t > first else None)
        out[s] = vals
    return times, out
