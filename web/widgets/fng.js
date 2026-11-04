// 恐慌贪婪指数：仪表盘 + 近一年历史折线
(function () {
  const BANDS = [[0.25, "#ea3943"], [0.46, "#f5833d"], [0.54, "#f5b83d"], [0.75, "#9ad13e"], [1, "#16c784"]];
  const ZH = { "Extreme Fear": "极度恐慌", Fear: "恐慌", Neutral: "中性", Greed: "贪婪", "Extreme Greed": "极度贪婪" };
  const col = (v) => BANDS.find((b) => v / 100 <= b[0])[1];
  window.WIDGETS.fng = {
    async render(body, w) {
      const d = await api("/api/fng");
      if (!d.latest) { body.innerHTML = '<div class="empty">暂无数据</div>'; return; }
      ensureBody(body, `<div class="fng-top"><div class="chart" data-k="gauge" style="height:300px"></div><div id="fng-cards"></div></div><div class="chart" data-k="hist" style="height:300px"></div>`);
      const L = d.latest, lab = (v) => v == null ? "—" : `<b style="color:${col(v)}">${v}</b>`;
      body.querySelector("#fng-cards").innerHTML = `<div class="kpis">
        <div class="kpi"><small>当前（${L.time}）</small><b style="color:${col(L.value)}">${L.value} · ${ZH[L.label] || L.label}</b></div>
        <div class="kpi"><small>昨天</small>${lab(d.yesterday)}</div><div class="kpi"><small>7 天前</small>${lab(d.week)}</div><div class="kpi"><small>30 天前</small>${lab(d.month)}</div></div>
        <div class="note">0–24 极度恐慌 · 25–46 恐慌 · 47–54 中性 · 55–75 贪婪 · 76–100 极度贪婪。数据来源：alternative.me 免费 API（每日更新一次）。</div>`;
      echarts.getInstanceByDom(body.querySelector('[data-k="gauge"]')) || echarts.init(body.querySelector('[data-k="gauge"]'));
      echarts.getInstanceByDom(body.querySelector('[data-k="gauge"]')).setOption({
        series: [{ type: "gauge", min: 0, max: 100, startAngle: 200, endAngle: -20, radius: "95%", center: ["50%", "62%"],
          axisLine: { lineStyle: { width: 22, color: BANDS } }, pointer: { width: 6, length: "62%", itemStyle: { color: "#fff" } },
          axisTick: { show: false }, splitLine: { length: 12, lineStyle: { color: "#0b0e14", width: 3 } }, axisLabel: { color: "#7d8aa0", distance: 28 },
          detail: { valueAnimation: true, fontSize: 40, color: col(L.value), offsetCenter: [0, "30%"], formatter: `{value}` },
          title: { offsetCenter: [0, "55%"], color: "#d8dee9", fontSize: 16 }, data: [{ value: L.value, name: ZH[L.label] || L.label }] }] });
      chartIn(body, "hist", 300).setOption({
        grid: { left: 44, right: 20, top: 24, bottom: 36 }, tooltip: { trigger: "axis" },
        xAxis: { type: "category", data: d.history.map((h) => h.t), ...AXIS, boundaryGap: false },
        yAxis: { type: "value", min: 0, max: 100, ...AXIS },
        visualMap: { show: false, dimension: 1, pieces: [{ lte: 24, color: "#ea3943" }, { gt: 24, lte: 46, color: "#f5833d" }, { gt: 46, lte: 54, color: "#f5b83d" }, { gt: 54, lte: 75, color: "#9ad13e" }, { gt: 75, color: "#16c784" }] },
        dataZoom: [{ type: "inside" }],
        series: [{ name: "恐慌贪婪指数", type: "line", showSymbol: false, data: d.history.map((h) => [h.t, h.v]), lineStyle: { width: 2 },
          markLine: { silent: true, symbol: "none", lineStyle: { color: "#3b4660", type: "dashed" }, label: { color: "#7d8aa0" }, data: [{ yAxis: 25 }, { yAxis: 50 }, { yAxis: 75 }] } }] }, true);
    },
  };
})();
