# 合约衍生品看板 · 可运行 Demo

一个最基本的单页看板：**左侧 6 个指标按钮，点击后右侧显示对应看板**（深色、参考 CoinGlass 的呈现形式，非其品牌/代码）。
数据全部来自各交易所**公开免 Key** 接口，以 **Bybit v5 market 接口为主数据源**，其它交易所能免费拿到就一并接入。

| 指标按钮 | 呈现 | 数据来源 |
|---|---|---|
| 资金费率 | 币种 × 交易所 红绿热力矩阵（8h 折算 / 年化切换） | 各所 funding rate（Bybit tickers 等） |
| 多空比 | 每个交易所一条横条：左绿(多) 右红(空)，交界处白色分隔线，两端百分比 | Bybit `account-ratio`、Binance、OKX、Bitget、Gate |
| 恐慌贪婪指数 | 仪表盘 + 近一年折线 | alternative.me |
| 持仓量 OI | 按交易所堆叠面积 + 价格线 + 各所当前值柱状 | Bybit `open-interest`、Binance、OKX、Gate + 各所快照 |
| 爆仓数据 | 多单(绿，向上)/空单(红，向下)柱状 + 各所合计 | Gate `contract_stats`、OKX `liquidation-orders` |
| 价格与成交量 | 各所最新价（偏离中位价）+ 24h 成交额柱状 | 各所 ticker |

## 启动

```bash
./run.sh                 # 本机：建虚拟环境→装依赖→先抓一遍真实数据→后台定时采集→启动网页 http://localhost:8000
# 或
docker compose up -d     # api(网页+接口) + scheduler(定时采集)，数据在 ./data/dashboard.db
```

手动命令：

```bash
pip install -r requirements.txt
python -m scheduler.jobs --once            # 全部数据源抓一次
python -m scheduler.jobs --once bybit      # 只抓 Bybit
python -m scheduler.jobs                   # 常驻：按每个源的 every_min（默认 REFRESH_MINUTES=5）循环采集
uvicorn api.main:app --port 8000           # 网页 + 接口
python -m pytest tests -q                  # 离线单元测试
python tests/screenshot.py http://localhost:8000   # 无头 Chrome 截图到 screenshots/（需 pip install playwright）
```

页面每 60 秒自动重绘一次；右上角「立即刷新 Bybit」会让后端马上重抓 Bybit（30 秒内最多一次）。

## 目录（与说明文档的骨架一致）

```text
config/sources.yaml     数据源清单：每家交易所一条（type = collectors/ 下的文件名），defaults.symbols 为币种
config/widgets.yaml     页面与卡片清单：pages = 左侧按钮；widgets = 右侧卡片（chart 类型 → web/widgets/<chart>.js）
collectors/             每家交易所一个插件，统一接口 fetch(source) -> list[dict]；base.py 放公共 HTTP/并发/容错
processors/             clean.py 清洗+去重；metrics.py 资金费率折算、周期重采样
storage/db.py           SQLite（data/dashboard.db）：records / runs 两张表
scheduler/jobs.py       采集流水线 采集→清洗→入库；--once 或常驻循环
api/main.py             FastAPI：/api/{meta,funding,lsr,fng,oi,liq,market,status} + 托管 web/
web/                    index.html + app.js(导航/路由/自动刷新) + widgets/*.js(每种图表一个文件) + vendor/echarts.min.js
docker-compose.yml      api + scheduler 两个服务
```

没有登录、没有 AI 摘要（按需求从简；原骨架里的登录权限、AI 层可按说明文档 01 再加回来）。

## 统一数据格式（所有插件都必须输出）

每条记录：`time`(ISO UTC)、`name`(`指标:币种`)、`value`(float)、`text`、`link`、`metric`、`symbol`、`extra`(dict，如 `{"interval_h": 8}`)。
指标名（`metric`）见 `collectors/base.py` 的 `METRICS`：

`funding_rate`(当前费率，每个结算周期，小数) · `funding_hist` · `oi_usd`(当前 OI，美元) · `oi_hist`(1h) · `lsr_account` / `lsr_top_account` / `lsr_top_position`(多头÷空头，1h) · `liq_long_usd` / `liq_short_usd`(1h) · `price` · `volume_24h_usd` · `price_hist`(1h) · `fng`(0-100，symbol=MARKET)

## 如何新增（写给 AI 编程助手）

> 一次只做一个改动；改完先 `python -m scheduler.jobs --once <id>` 再 `python -m pytest tests -q`，最后刷新页面确认。不要改其它交易所的插件。

**A. 新增一个交易所（例如 Bitfinex）**
1. 复制 `collectors/bybit.py` 为 `collectors/bitfinex.py`，实现 `per_symbol(ctx, s, shared)`：用 `ctx.get(url, **params)` 取数，用 `ctx.rec(metric, s, ts_ms或None, value, interval_h=8)` 产出记录（`ts=None` 表示“现在”，用于快照类指标）。取不到的指标直接不写；单个接口失败用 `ctx.safe(...)` 包起来，只会记警告。末尾 `def fetch(source): return collect(source, per_symbol)`。
2. 在 `config/sources.yaml` 的 `sources:` 加一行 `- { id: bitfinex, type: bitfinex, kind: metric, name: Bitfinex, doc: "<文档链接>" }`。列表顺序 = 页面上的显示顺序。
3. 币种映射不同（如 `BTC`→`tBTCF0:USTF0`）在插件里转换，对外永远用 `BTC/ETH/SOL…`。
4. 验证：`python -m scheduler.jobs --once bitfinex`，在「数据源状态」（`/api/status`）里看 ok 与警告；前端各页会自动出现新交易所列/行。
- 资金费率必须带 `interval_h`（结算周期小时数），矩阵会折算成 8 小时口径。
- OI 一律折成美元名义价值；多空比一律输出「多÷空」。

**B. 新增币种**：改 `config/sources.yaml` 的 `defaults.symbols`（单个源可写 `symbols:` 覆盖），重新采集即可，币种选择器自动出现。

**C. 新增一种指标（例如“基差”）**：① 在 `collectors/base.py` 的 `METRICS` 加名字，在相关插件里 `ctx.rec("basis", ...)`；② `processors/clean.py` 的 `LIMITS` 加合理范围；③ `api/main.py` 加一个 `/api/basis`（用 `db.series / db.latest_by_source` 取数）；④ 见 D。

**D. 新增一个指标页 / 卡片**：
1. `config/widgets.yaml` 的 `pages` 加一项：`{id: basis, title: 基差, desc: ..., widgets: [{id: basis, chart: basis, title: ..., controls: [symbol, period]}]}`；
2. `web/widgets/basis.js`：`window.WIDGETS.basis = { async render(body, w, state, meta) { const d = await api('/api/basis?...'); /* 渲染 */ } }`（参考 `oi.js`；`chartIn()` 复用 ECharts 实例，`fmtUsd()` 格式化金额）；
3. 在 `web/index.html` 加 `<script src="/widgets/basis.js">`；左侧按钮会自动出现（图标可在 `app.js` 的 `ICONS` 里加）。
- `controls` 可选：`symbol`（币种）、`period`（1h/4h/1d）、`kind`（多空比口径）、`unit`（费率单位）。

**E. 新增一种非交易所数据源**：参考 `collectors/fear_greed.py`（全市场指标，`symbols: [MARKET]`）。

## 已知限制（Demo 级别）

- **Bybit 本机可正常访问**（未被地区屏蔽）。Bybit 没有公开的爆仓 REST 接口，所以爆仓图改用 **Gate**（1 小时统计，近 20 天）和 **OKX**（只返回最近一小段强平单）；Binance/Bybit/Bitget 等无免费爆仓历史。
- **Coinbase**：`api.international.coinbase.com`（国际站永续）在本机持续返回 502，插件自动降级为 Coinbase 现货（BTC-USD 等）只提供价格和 24h 成交额，没有资金费率/OI/多空比。
- 多空比：KuCoin、MEXC、Deribit、Coinbase、Hyperliquid 无公开多空比接口，页面显示“无数据”；HTX 只有大户口径。各所口径（账户数 vs 持仓量、统计人群）不完全相同，仅作情绪参考，不要跨所精确比较。
- OI 历史：Bybit 约 8 天（接口单次上限 200 个 1h 点），Binance/OKX/Gate 约 20 天；OKX 的历史是该币种全部合约汇总（含币本位），与快照口径略有差异；其余交易所只有快照，没有历史。
- “实时”= 后端每 5 分钟采集（或点右上角立即刷新 Bybit）+ 前端每 60 秒重新读取，不是 WebSocket 逐笔推送。
- 资金费率为各所当前（预测）值，不同结算周期折算成 8h 仅为便于比较；Deribit 用其 8h 口径的 funding_8h。
- 没有登录/权限；`/api/refresh` 未鉴权（仅限内网/本机演示，上线前请加鉴权或删除）。
- 免费公开接口可能限频（如 Bitget 偶发 429，已自动重试）或随时调整；单个接口失败不会影响其它指标，详见 `/api/status`。
- Docker 配置已写好但本次环境没有安装 Docker，未实际执行 `docker compose up`；本机 `./run.sh` 已实测。
