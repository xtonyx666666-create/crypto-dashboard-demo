// 爆仓：多单（绿，向上）/ 空单（红，向下）柱状图 + 各交易所合计
window.WIDGETS.liq = {
  async render(body, w, state) {
    const d = await api(`/api/liq?symbol=${state.symbol}&period=${state.period}`);
    ensureBody(body, `<div class="kpis" id="q-k"></div><div class="chart" data-k="main" style="height:360px"></div><div id="q-t"></div><div class="note" id="q-n"></div>`);
    const sum = (a) => a.reduce((x, y) => x + y, 0), L = sum(d.long), S = sum(d.short);
    body.querySelector("#q-k").innerHTML = `<div class="kpi"><small>区间多单爆仓</small><b class="up">${usd(L)}</b></div><div class="kpi"><small>区间空单爆仓</small><b class="down">${usd(S)}</b></div><div class="kpi"><small>合计</small><b>${usd(L + S)}</b></div>`;
    chartIn(body, "main", 360).setOption({
      tooltip: { trigger: "axis", valueFormatter: (v) => usd(Math.abs(v)) }, legend: { top: 0, textStyle: { color: "#aab4c6" } }, grid: GRID, dataZoom: [{ type: "inside" }],
      xAxis: { type: "category", data: d.times.map((t) => shortTime(t, d.period)), ...AXIS },
      yAxis: { type: "value", axisLabel: { color: "#7d8aa0", formatter: (v) => usd(Math.abs(v)) }, splitLine: AXIS.splitLine },
      series: [{ name: "多单爆仓", type: "bar", stack: "liq", itemStyle: { color: "#16c784" }, data: d.long },
               { name: "空单爆仓", type: "bar", stack: "liq", itemStyle: { color: "#ea3943" }, data: d.short.map((v) => -v) }] }, true);
    body.querySelector("#q-t").innerHTML = `<table class="tbl" style="margin-top:12px"><thead><tr><th>交易所</th><th>多单爆仓</th><th>空单爆仓</th><th>合计</th><th>占比</th><th>统计窗口</th></tr></thead><tbody>` +
      d.table.map((r) => `<tr><td>${r.name}</td><td class="up">${usd(r.long)}</td><td class="down">${usd(r.short)}</td><td>${usd((r.long||0)+(r.short||0))}</td><td>${(()=>{const T=d.table.reduce((a,x)=>a+(x.long||0)+(x.short||0),0);return T?(((r.long||0)+(r.short||0))/T*100).toFixed(1)+"%":"—";})()}</td><td class="muted">${r.window}</td></tr>`).join("") + `</tbody></table>`;
    body.querySelector("#q-n").textContent = d.note;
  },
};
