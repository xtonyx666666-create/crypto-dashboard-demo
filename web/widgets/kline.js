// 行情走势：K 线 + 成交量（CoinGlass 风格）。币种 / 周期切换在卡片内部；
// 首屏只取最近 2000 根，dataZoom 拖到最左侧时用 before= 向前懒加载更早数据，直到 2025-01-01；每 30 秒增量刷新最新一根。
(function () {
  const UP = "#16c784", DN = "#ea3943";
  const K = { sym: localStorage.kSym || "BTC", iv: localStorage.kIv || "4h", rows: [], meta: null, busy: false, timer: null, body: null, gen: 0 };
  const pad = (n) => String(n).padStart(2, "0");
  const lab = (t) => { const d = new Date(t); const day = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
    return K.iv === "1d" || K.iv === "1w" ? day : `${day} ${pad(d.getHours())}:${pad(d.getMinutes())}`; };
  const fmt = (v) => v >= 1000 ? v.toLocaleString("en-US", { maximumFractionDigits: 1 }) : v.toFixed(v >= 10 ? 2 : 4);

  function seg(items, cur, on) {
    return `<div class="seg">${items.map((x) => `<span data-v="${x}" class="${x === cur ? "on" : ""}">${x}</span>`).join("")}</div>`;
  }
  function chart() { return chartIn(K.body, "k", 560); }

  function draw(keepView) {
    const c = chart(), r = K.rows, n = r.length;
    let sv = Math.max(0, n - 200), ev = n - 1;
    if (keepView) { const o = c.getOption().dataZoom[0]; sv = o.startValue + keepView; ev = o.endValue + keepView; }
    c.setOption({
      animation: false, backgroundColor: "transparent",
      tooltip: { trigger: "axis", axisPointer: { type: "cross" }, backgroundColor: "#151c28", borderColor: "#2a3448", textStyle: { color: "#d8dee9" },
        formatter: (ps) => { const i = ps[0].dataIndex, x = r[i]; if (!x) return ""; const ch = (x[4] / x[1] - 1) * 100;
          return `${lab(x[0])}<br/>开 ${fmt(x[1])}　高 ${fmt(x[2])}<br/>低 ${fmt(x[3])}　收 ${fmt(x[4])}<br/>涨跌 <b style="color:${ch >= 0 ? UP : DN}">${ch.toFixed(2)}%</b><br/>成交量 ${fmtUsd(x[5])} ${K.sym}`; } },
      axisPointer: { link: [{ xAxisIndex: "all" }] },
      grid: [{ left: 64, right: 64, top: 20, height: "62%" }, { left: 64, right: 64, top: "75%", height: "14%" }],
      xAxis: [{ type: "category", data: r.map((x) => lab(x[0])), boundaryGap: true, ...AXIS, axisLabel: { show: false }, axisTick: { show: false } },
              { type: "category", gridIndex: 1, data: r.map((x) => lab(x[0])), ...AXIS }],
      yAxis: [{ scale: true, position: "right", ...AXIS, axisLabel: { color: "#7d8aa0", formatter: (v) => fmt(v) } },
              { gridIndex: 1, position: "right", splitNumber: 2, ...AXIS, axisLabel: { color: "#7d8aa0", formatter: (v) => fmtUsd(v) } }],
      dataZoom: [{ type: "inside", xAxisIndex: [0, 1], startValue: sv, endValue: ev },
                 { type: "slider", xAxisIndex: [0, 1], bottom: 6, height: 22, startValue: sv, endValue: ev, borderColor: "#2a3448",
                   textStyle: { color: "#7d8aa0" }, fillerColor: "rgba(59,130,246,.15)", dataBackground: { lineStyle: { color: "#3b82f6" }, areaStyle: { color: "rgba(59,130,246,.15)" } } }],
      series: [{ name: K.sym, type: "candlestick", large: true, largeThreshold: 3000, data: r.map((x) => [x[1], x[4], x[3], x[2]]),
                 itemStyle: { color: UP, color0: DN, borderColor: UP, borderColor0: DN } },
               { name: "成交量", type: "bar", xAxisIndex: 1, yAxisIndex: 1, large: true, data: r.map((x) => ({ value: x[5], itemStyle: { color: x[4] >= x[1] ? UP + "99" : DN + "99" } })) }],
    }, true);
    info();
  }

  function info() {
    const r = K.rows, m = K.meta || {}; if (!r.length) return;
    const last = r[r.length - 1], prev = r.length > 1 ? r[r.length - 2][4] : last[1], ch = (last[4] / prev - 1) * 100;
    K.body.querySelector("#k-kpi").innerHTML =
      `<div class="kpi"><small>${K.sym}USDT 永续 · ${K.iv}</small><b style="color:${ch >= 0 ? UP : DN}">${fmt(last[4])}</b></div>` +
      `<div class="kpi"><small>较上一根</small><b style="color:${ch >= 0 ? UP : DN}">${ch >= 0 ? "+" : ""}${ch.toFixed(2)}%</b></div>` +
      `<div class="kpi"><small>本周期最高 / 最低</small><b>${fmt(last[2])} / ${fmt(last[3])}</b></div>` +
      `<div class="kpi"><small>已加载 / 服务器已缓存</small><b>${r.length.toLocaleString()} / ${(m.count || 0).toLocaleString()} 根</b></div>`;
    const from = m.first ? lab(m.first) : "—";
    K.body.querySelector("#k-note").textContent = `数据源：${m.source === "okx" ? "OKX（Bybit 不可用，已自动降级）" : "Bybit v5 /market/kline（category=linear）"}；` +
      `服务器缓存最早 ${from}${m.complete ? "（已回补到 2025-01-01）" : "，历史回补中…"}；当前已加载最早 ${lab(r[0][0])}。拖动或缩放到最左侧会自动加载更早数据；最新一根每 30 秒刷新。`;
  }

  async function load() {
    const g = ++K.gen; K.rows = [];
    const d = await api(`/api/kline?symbol=${K.sym}&interval=${K.iv}&limit=2000`);
    if (g !== K.gen) return;
    K.meta = d; K.rows = d.rows;
    if (!K.rows.length) { K.body.querySelector("#k-note").textContent = "首次加载，正在从 Bybit 回补历史…"; setTimeout(() => g === K.gen && load(), 4000); return; }
    draw(0);
    if (!d.complete) setTimeout(() => g === K.gen && older(true), 5000);
  }

  async function older(retry) {
    if (K.busy || !K.rows.length) return;
    const m = K.meta || {};
    if (m.complete && m.first && K.rows[0][0] <= m.first) return;      // 已到最早
    K.busy = true; const g = K.gen;
    try {
      const d = await api(`/api/kline?symbol=${K.sym}&interval=${K.iv}&before=${K.rows[0][0]}&limit=5000`);
      if (g !== K.gen) return;
      K.meta = { ...d, rows: undefined };
      if (d.rows.length) { K.rows = d.rows.concat(K.rows); draw(d.rows.length); }
      else { info(); if (!d.complete && retry) setTimeout(() => g === K.gen && older(true), 5000); }
    } finally { K.busy = false; }
  }

  async function all() {
    const b = K.body.querySelector("#k-all"); b.disabled = true; b.textContent = "加载中…";
    for (let i = 0; i < 80; i++) { const n = K.rows.length; await older(false); if (K.rows.length === n) break; }
    chart().dispatchAction({ type: "dataZoom", startValue: 0, endValue: K.rows.length - 1 });
    b.disabled = false; b.textContent = "⇤ 加载全部（2025-01 起）";
  }

  async function tick() {
    if (!K.rows.length || !document.body.contains(K.body)) return;
    const g = K.gen, lastT = K.rows[K.rows.length - 1][0];
    const d = await api(`/api/kline?symbol=${K.sym}&interval=${K.iv}&since=${lastT}`);
    if (g !== K.gen || !d.rows.length) return;
    K.meta = { ...d, rows: undefined };
    K.rows.pop(); const add = d.rows.length - 1; K.rows = K.rows.concat(d.rows);
    const o = chart().getOption().dataZoom[0], atEnd = o.endValue >= K.rows.length - 1 - add - 1;
    draw(0); if (!atEnd) chart().dispatchAction({ type: "dataZoom", startValue: o.startValue, endValue: o.endValue });
    else chart().dispatchAction({ type: "dataZoom", startValue: o.startValue + add, endValue: K.rows.length - 1 });
  }

  window.WIDGETS.kline = {
    async render(body) {
      if (K.body === body && body.dataset.ready) return;                // 60 秒全局重绘时不重载，靠自身 30 秒增量刷新
      K.body = body; body.dataset.ready = "1";
      body.innerHTML = `<div class="k-bar" style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:12px">
        <div id="k-sym">${seg(["BTC", "ETH", "SOL"], K.sym)}</div><div id="k-iv">${seg(["5m", "15m", "4h", "1d", "1w"], K.iv)}</div>
        <button class="btn" id="k-all">⇤ 加载全部（2025-01 起）</button></div>
        <div class="kpis" id="k-kpi"></div><div class="chart" data-k="k" style="height:560px"></div><div class="note" id="k-note">加载中…</div>`;
      const bind = (id, key, ls) => body.querySelector(id).onclick = (e) => { const s = e.target.closest("span"); if (!s) return;
        K[key] = s.dataset.v; localStorage[ls] = s.dataset.v; body.querySelectorAll(id + " span").forEach((x) => x.classList.toggle("on", x === s)); load(); };
      bind("#k-sym", "sym", "kSym"); bind("#k-iv", "iv", "kIv");
      body.querySelector("#k-all").onclick = all;
      chart().on("datazoom", () => { const o = chart().getOption().dataZoom[0]; if (o.startValue < 50) older(false); });
      clearInterval(K.timer); K.timer = setInterval(() => tick().catch(() => {}), 30000);
      await load();
    },
  };
})();
