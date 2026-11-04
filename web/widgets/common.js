window.WIDGETS = window.WIDGETS || {};
// 卡片公共工具
window.COLORS = ["#3b82f6", "#f5b83d", "#16c784", "#a855f7", "#ea3943", "#22d3ee", "#fb923c", "#94a3b8", "#e879f9", "#84cc16", "#f472b6"];
window.GRID = { left: 56, right: 56, top: 36, bottom: 40 };
window.AXIS = { axisLine: { lineStyle: { color: "#2a3448" } }, axisLabel: { color: "#7d8aa0" }, splitLine: { lineStyle: { color: "#1a2230" } } };

// 在 body 里复用同一个 ECharts 实例（自动刷新时不闪烁）。key 区分同一张卡里的多个图。
window.chartIn = function (body, key = "main", height = 340) {
  let el = body.querySelector(`.chart[data-k="${key}"]`);
  if (!el) { el = document.createElement("div"); el.className = "chart"; el.dataset.k = key; el.style.height = height + "px"; body.appendChild(el); }
  return echarts.getInstanceByDom(el) || echarts.init(el, null, { renderer: "canvas" });
};
// 首次渲染时清掉“加载中”
window.ensureBody = function (body, html) { if (!body.dataset.ready) { body.innerHTML = html || ""; body.dataset.ready = "1"; } };
window.shortTime = (t, period) => { const d = new Date(t); const p = (n) => String(n).padStart(2, "0");
  return period === "1d" ? `${p(d.getMonth() + 1)}-${p(d.getDate())}` : `${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:00`; };
