// 持仓量：按交易所堆叠面积（左轴）+ 价格（右轴）；下方为各交易所当前持仓量
window.WIDGETS.oi = {
  async render(body, w, state) {
    const d = await api(`/api/oi?symbol=${state.symbol}&period=${state.period}`);
    ensureBody(body, `<div class="kpis" id="oi-k"></div><div class="chart" data-k="hist" style="height:360px"></div><div class="card-title" style="margin:14px 0 4px">各交易所当前持仓量</div><div class="chart" data-k="now" style="height:300px"></div><div class="note" id="oi-n"></div>`);
    const total = d.current.reduce((a, c) => a + (c.value || 0), 0), last = d.times.length - 1;
    body.querySelector("#oi-k").innerHTML = `<div class="kpi"><small>${d.symbol} 全部交易所当前 OI</small><b>${usd(total)}</b></div>` +
      d.series.map((s) => `<div class="kpi"><small>${s.name}</small><b>${usd(s.data[last])}</b></div>`).join("");
    chartIn(body, "hist", 360).setOption({
      color: COLORS, tooltip: { trigger: "axis", valueFormatter: (v) => usd(v) }, legend: { top: 0, textStyle: { color: "#aab4c6" } },
      grid: GRID, dataZoom: [{ type: "inside" }],
      xAxis: { type: "category", data: d.times.map((t) => shortTime(t, d.period)), boundaryGap: false, ...AXIS },
      yAxis: [{ type: "value", axisLabel: { color: "#7d8aa0", formatter: (v) => usd(v) }, splitLine: AXIS.splitLine }, { type: "value", scale: true, axisLabel: { color: "#f5b83d" }, splitLine: { show: false } }],
      series: [...d.series.map((s) => ({ name: s.name, type: "line", stack: "oi", areaStyle: { opacity: 0.55 }, showSymbol: false, lineStyle: { width: 1 }, data: s.data })),
        { name: d.symbol + " 价格", type: "line", yAxisIndex: 1, showSymbol: false, lineStyle: { width: 1.5, color: "#f5b83d" }, itemStyle: { color: "#f5b83d" }, data: d.price }] }, true);
    const cur = d.current.filter((c) => c.value).sort((a, b) => a.value - b.value);
    chartIn(body, "now", 300).setOption({
      grid: { left: 90, right: 60, top: 10, bottom: 24 }, tooltip: { valueFormatter: (v) => usd(v) },
      xAxis: { type: "value", axisLabel: { color: "#7d8aa0", formatter: (v) => usd(v) }, splitLine: AXIS.splitLine },
      yAxis: { type: "category", data: cur.map((c) => c.name), axisLabel: { color: "#d8dee9" }, axisLine: AXIS.axisLine },
      series: [{ type: "bar", data: cur.map((c) => c.value), itemStyle: { color: "#3b82f6", borderRadius: [0, 3, 3, 0] }, label: { show: true, position: "right", color: "#aab4c6", formatter: (p) => usd(p.value) + (total ? `（${(p.value / total * 100).toFixed(1)}%）` : "") } }] }, true);
    body.querySelector("#oi-n").textContent = "堆叠图仅包含提供 1 小时持仓量历史的交易所（Bybit、Binance、OKX、Gate）；其余交易所只有当前快照，见下方柱状图。OKX 历史为该币种全部合约（含币本位）汇总。";
  },
};
