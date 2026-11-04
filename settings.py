"""全局设置：读取 .env 与 config/*.yaml。其它模块都从这里取配置。"""
import os
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
CONFIG_DIR = ROOT / "config"


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """极简 .env 读取（不覆盖已存在的环境变量；支持行尾 # 注释）。"""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.split(" #")[0].strip().strip('"').strip("'"))


load_dotenv()


def env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def db_path() -> Path:
    p = Path(env("DASH_DB", "data/dashboard.db"))
    return p if p.is_absolute() else ROOT / p


def _read_yaml(name: str) -> dict:
    return yaml.safe_load((CONFIG_DIR / name).read_text(encoding="utf-8")) or {}


def load_sources() -> list[dict]:
    """sources.yaml：defaults 里的字段（如 symbols）会补到每个数据源上。"""
    raw = _read_yaml("sources.yaml")
    defaults = raw.get("defaults", {})
    return [{**defaults, **s} for s in raw.get("sources", [])]


def load_symbols() -> list[str]:
    return _read_yaml("sources.yaml").get("defaults", {}).get("symbols", ["BTC", "ETH", "SOL"])


def load_widgets() -> dict:
    return _read_yaml("widgets.yaml")


def get_source(source_id: str) -> dict:
    for s in load_sources():
        if s["id"] == source_id:
            return s
    raise KeyError(f"sources.yaml 里没有 id={source_id}")


@lru_cache(maxsize=None)
def load_prompt(name: str) -> str:
    return (CONFIG_DIR / "prompts" / f"{name}.md").read_text(encoding="utf-8")
