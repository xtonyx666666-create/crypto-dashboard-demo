// 多空比：每个交易所一条横条，左绿（多）右红（空），分隔线在多空交界处，两端标百分比
window.WIDGETS.lsr_bars = {
  async render(body, w, state) {
    const d = await api(`/api/lsr?symbol=${state.symbol}&kind=${state.kind}`);
    const rows = d.rows.map((r) => r.long_pct == null
      ? `<div class="lsr-row"><div class="lsr-name">${r.name}</div><div class="lsr-pct l">—</div><div class="lsr-bar na">该交易所没有公开的${d.label}接口</div><div class="lsr-pct s">—</div></div>`
      : `<div class="lsr-row" title="${r.name} ${d.symbol} ${d.label} ${r.ratio.toFixed(3)}（多 ${r.long_pct.toFixed(2)}% / 空 ${r.short_pct.toFixed(2)}%）">
           <div class="lsr-name">${r.name} <span class="lsr-ratio">${r.ratio.toFixed(2)}</span></div>
           <div class="lsr-pct l">${r.long_pct.toFixed(2)}%</div>
           <div class="lsr-bar"><div class="l" style="width:${r.long_pct}%"></div><div class="s" style="width:${r.short_pct}%"></div><div class="mid" style="left:${r.long_pct}%"></div></div>
           <div class="lsr-pct s">${r.short_pct.toFixed(2)}%</div></div>`);
    body.innerHTML = `<div class="muted" style="margin-bottom:6px">${d.symbol} · ${d.label}（多头占比 / 空头占比，1 小时口径，取最新一根）</div>` + rows.join("") +
      `<div class="note">多空比 = 多头账户（或持仓）数 ÷ 空头；百分比 = 多/(多+空)。Bybit、Binance、OKX、Bitget、Gate 提供账户多空比；HTX 仅提供大户口径。</div>`;
  },
};
