// 各交易所价格与 24h 成交额对比
window.WIDGETS.market = {
  async render(body, w, state) {
    const d = await api(`/api/market?symbol=${state.symbol}`);
    ensureBody(body, `<div class="kpis" id="m-k"></div><div class="grid2"><div class="chart" data-k="vol" style="height:340px"></div><div id="m-t"></div></div><div class="note" id="m-n"></div>`);
    const rows = d.rows.filter((r) => r.price != null), tv = rows.reduce((a, r) => a + (r.volume || 0), 0);
    body.querySelector("#m-k").innerHTML = `<div class="kpi"><small>${d.symbol} 中位价</small><b>${d.median == null || !isFinite(d.median) ? "—" : "$" + Number(d.median).toLocaleString("en-US")}</b></div><div class="kpi"><small>24h 总成交额（${rows.length} 家）</small><b>${usd(tv)}</b></div>`;
    const vs = rows.filter((r) => r.volume).sort((a, b) => a.volume - b.volume);
    chartIn(body, "vol", 340).setOption({
      title: { text: "24h 成交额（美元）", textStyle: { color: "#aab4c6", fontSize: 13 } },
      grid: { left: 90, right: 70, top: 30, bottom: 24 }, tooltip: { valueFormatter: (v) => usd(v) },
      xAxis: { type: "value", axisLabel: { color: "#7d8aa0", formatter: (v) => usd(v) }, splitLine: AXIS.splitLine },
      yAxis: { type: "category", data: vs.map((r) => r.name), axisLabel: { color: "#d8dee9" }, axisLine: AXIS.axisLine },
      series: [{ type: "bar", data: vs.map((r) => r.volume), itemStyle: { color: "#3b82f6", borderRadius: [0, 3, 3, 0] }, label: { show: true, position: "right", color: "#aab4c6", formatter: (p) => usd(p.value) } }] }, true);
    const fmtP = (v) => v >= 1000 ? v.toLocaleString("en-US", { maximumFractionDigits: 1 }) : v >= 1 ? v.toFixed(3) : v.toFixed(5);
    body.querySelector("#m-t").innerHTML = `<table class="tbl"><thead><tr><th>交易所</th><th>最新价</th><th>较中位价</th><th>24h 成交额</th><th>占比</th></tr></thead><tbody>` +
      d.rows.map((r) => r.price == null ? `<tr><td>${r.name}</td><td colspan="4" class="muted">暂无数据</td></tr>` :
        `<tr><td>${r.name}</td><td>$${fmtP(r.price)}</td><td class="${r.dev_pct >= 0 ? "up" : "down"}">${r.dev_pct >= 0 ? "+" : ""}${r.dev_pct.toFixed(3)}%</td><td>${r.volume ? usd(r.volume) : "—"}</td><td>${r.share != null ? `<span class="share" style="width:${Math.max(2, r.share * 1.2)}px"></span>${r.share.toFixed(1)}%` : "—"}</td></tr>`).join("") + `</tbody></table>`;
    body.querySelector("#m-n").textContent = "永续合约最新成交价与 24h 成交额（USDT/USD 计价）。Coinbase 本机无法访问其衍生品域名，改用现货 BTC-USD 等交易对，成交额口径为现货。";
  },
};
