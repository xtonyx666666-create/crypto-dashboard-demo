"""离线测试：python -m pytest tests -q（不访问网络）"""
import math

from processors import clean, metrics


def test_annualize_and_8h():
    assert math.isclose(metrics.per8h(0.0001, 8), 0.01)
    assert math.isclose(metrics.per8h(0.0000125, 1), 0.01)           # 1h 费率折成 8h
    assert math.isclose(metrics.annualize(0.0001, 8), 10.95)


def test_resample_sum_and_last():
    pts = [{"time": f"2026-11-01T0{h}:00:00+00:00", "value": h + 1} for h in range(8)]
    assert [p["value"] for p in metrics.resample(pts, "4h", "sum")] == [10, 26]
    assert [p["value"] for p in metrics.resample(pts, "4h", "last")] == [4, 8]


def test_clean_drops_bad_and_dupes():
    src = {"id": "x"}
    rows = [{"name": "funding_rate:BTC", "metric": "funding_rate", "time": "t1", "value": 0.0001},
            {"name": "funding_rate:BTC", "metric": "funding_rate", "time": "t1", "value": 0.0001},     # 重复
            {"name": "funding_rate:BTC", "metric": "funding_rate", "time": "t2", "value": 5.0},        # 异常
            {"name": "funding_rate:BTC", "metric": "funding_rate", "time": "t3", "value": float("nan")}]
    assert len(clean.clean(src, rows)) == 1


def test_collector_registry():
    import collectors
    import pytest
    with pytest.raises(ValueError):
        collectors.get_collector("no_such_exchange")
    assert callable(collectors.get_collector("bybit"))
