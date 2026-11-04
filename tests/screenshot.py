"""无头 Chrome 给 7 个指标页截图：python tests/screenshot.py [URL]（需 pip install playwright，使用本机 Chrome）"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
OUT = Path(__file__).resolve().parent.parent / "screenshots"
OUT.mkdir(exist_ok=True)
PAGES = ["funding", "lsr", "fng", "oi", "liq", "market", "kline"]

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    for i, name in enumerate(PAGES, 1):
        pg.goto(f"{URL}/#/{name}")
        pg.reload()
        pg.wait_for_timeout(3000)
        pg.screenshot(path=str(OUT / f"{i:02d}-{name}.png"), full_page=True)
        print("saved", name)
    print("console errors:", errors)
    b.close()
