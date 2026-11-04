// 资金费率热力矩阵：行=币种，列=交易所；绿=正（多头付费），红=负（空头付费）
(function () {
  const CAP = { "8h": 0.03, annual: 30 };            // 色阶封顶：8h 费率 ±0.03% / 年化 ±30%
  function color(v, cap) {
    const a = Math.min(Math.abs(v) / cap, 1);
    const [r, g, b] = v >= 0 ? [22, 199, 132] : [234, 57, 67];
    const base = [42, 47, 58], k = 0.15 + 0.85 * a;
    return `rgb(${base.map((c, i) => Math.round(c + ([r, g, b][i] - c) * k)).join(",")})`;
  }
  window.WIDGETS.funding_matrix = {
    async render(body, w, state) {
      const d = await api("/api/funding"), unit = state.unit, cap = CAP[unit];
      const key = unit === "annual" ? "annual" : "per8h", digits = unit === "annual" ? 1 : 4;
      let html = `<table class="mx"><thead><tr><th></th>${d.exchanges.map((e) => `<th>${e.name}</th>`).join("")}</tr></thead><tbody>`;
      for (const s of d.symbols) {
        html += `<tr><td class="sym">${s}</td>`;
        for (const e of d.exchanges) {
          const c = (d.cells[s] || {})[e.id];
          html += c ? `<td style="background:${color(c[key], cap)}" title="${e.name} ${s}\n当期费率 ${c.rate.toFixed(4)}%（每 ${c.interval_h}h 结算）\n8h 折算 ${c.per8h.toFixed(4)}% · 年化 ${c.annual.toFixed(1)}%">${c[key].toFixed(digits)}%</td>` : `<td class="na">—</td>`;
        }
        html += "</tr>";
      }
      body.innerHTML = html + `</tbody></table>
        <div class="legend"><span>${(-cap).toFixed(unit === "annual" ? 0 : 2)}%</span><i></i><span>+${cap.toFixed(unit === "annual" ? 0 : 2)}%</span>
        <span>· 绿 = 资金费率为正（多头付给空头，市场偏多拥挤）　红 = 为负（空头付给多头）　"—" = 该所无该币种或未提供数据</span></div>
        <div class="note">不同交易所结算周期不同（Hyperliquid 1h，其余多为 8h），默认折算成 8 小时口径横向比较；悬停可看原始费率。</div>`;
    },
  };
})();
