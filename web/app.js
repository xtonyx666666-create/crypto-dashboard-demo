// 单页入口：左侧 7 个指标按钮 → 右侧渲染该页的卡片（widgets）。
// 卡片组件注册在 window.WIDGETS[chart]：render(bodyEl, widgetCfg, state, meta) → Promise；每 60 秒自动重绘。
window.WIDGETS = window.WIDGETS || {};
const $ = (s) => document.querySelector(s);
const ICONS = { funding: "%", lsr: "⇅", fng: "☺", oi: "▦", liq: "⚡", market: "$", kline: "📈" };
const state = { symbol: localStorage.symbol || "BTC", period: null, kind: "account", unit: "8h" };
let META = null, PAGE = null;

window.api = async (path) => { const r = await fetch(path); if (!r.ok) throw new Error(`${path} → ${r.status}`); return r.json(); };
window.fmtUsd = (v) => (v == null || !isFinite(v)) ? "—" : v >= 1e9 ? (v / 1e9).toFixed(2) + "B" : v >= 1e6 ? (v / 1e6).toFixed(2) + "M" : v >= 1e3 ? (v / 1e3).toFixed(1) + "K" : v.toFixed(0);

window.usd = (v) => (v == null || !isFinite(v)) ? "—" : (v < 0 ? "-$" : "$") + fmtUsd(Math.abs(v));
const TZ = (() => { const o = -new Date().getTimezoneOffset() / 60; return "UTC" + (o >= 0 ? "+" : "") + o; })();

async function boot() {
  META = await api("/api/meta");
  document.title = META.title;
  $("#brand-title").textContent = META.title; $("#brand-sub").textContent = META.subtitle;
  $("#nav").innerHTML = META.pages.map((p) => `<button data-id="${p.id}"><span class="ic">${ICONS[p.id] || "•"}</span>${p.title}</button>`).join("");
  $("#nav").onclick = (e) => { const b = e.target.closest("button"); if (b) location.hash = "#/" + b.dataset.id; };
  window.addEventListener("hashchange", route);
  setInterval(() => renderAll(false), 60000);
  $("#refresh").onclick = async () => {
    const b = $("#refresh"); b.disabled = true; b.textContent = "刷新中…";
    try { await fetch("/api/refresh?source=bybit", { method: "POST" }); await renderAll(false); } finally { b.disabled = false; b.textContent = "⟳ 立即刷新 Bybit"; }
  };
  route();
}

function route() {
  const id = (location.hash.match(/#\/(\w+)/) || [])[1] || META.pages[0].id;
  PAGE = META.pages.find((p) => p.id === id) || META.pages[0];
  document.querySelectorAll("#nav button").forEach((b) => b.classList.toggle("active", b.dataset.id === PAGE.id));
  $("#page-title").textContent = PAGE.title; $("#page-desc").textContent = PAGE.desc || "";
  const box = $("#content"); box.innerHTML = "";
  for (const w of PAGE.widgets) {
    const card = document.createElement("div"); card.className = "card"; card.dataset.id = w.id;
    card.innerHTML = `<div class="card-head"><div class="card-title">${w.title}</div><div class="controls"></div></div><div class="body"><div class="empty">加载中…</div></div>`;
    box.appendChild(card);
    buildControls(card.querySelector(".controls"), w);
  }
  renderAll(true);
}

function seg(items, key, labels, onchange) {
  const g = document.createElement("div"); g.className = "seg";
  items.forEach((it) => {
    const s = document.createElement("span"); s.textContent = labels ? labels[it] : it; s.className = state[key] === it ? "on" : "";
    s.onclick = () => { state[key] = it; if (key === "symbol") localStorage.symbol = it; g.querySelectorAll("span").forEach((x) => x.classList.remove("on")); s.classList.add("on"); onchange(); };
    g.appendChild(s);
  });
  return g;
}

function buildControls(el, w) {
  const ctl = w.controls || [];
  if (w.default_period && !state.period) state.period = w.default_period;
  if (w.default_period) state.period = w.default_period;
  if (ctl.includes("symbol")) el.appendChild(seg(META.symbols, "symbol", null, () => renderAll(true)));
  if (ctl.includes("period")) el.appendChild(seg(["1h", "4h", "1d"], "period", null, () => renderAll(true)));
  if (ctl.includes("unit")) el.appendChild(seg(["8h", "annual"], "unit", { "8h": "8 小时费率 %", annual: "年化 %" }, () => renderAll(true)));
  if (ctl.includes("kind")) el.appendChild(seg(["account", "top_account", "top_position"], "kind", { account: "账户", top_account: "大户账户", top_position: "大户持仓" }, () => renderAll(true)));
}

async function renderAll(showLoading) {
  if (!PAGE) return;
  for (const w of PAGE.widgets) {
    const body = document.querySelector(`.card[data-id="${w.id}"] .body`);
    const impl = window.WIDGETS[w.chart];
    try {
      if (!impl) throw new Error("没有这种图表组件：" + w.chart);
      await impl.render(body, w, state, META);
    } catch (e) { body.innerHTML = `<div class="empty">加载失败：${e.message}</div>`; }
  }
  try {
    const m = await api("/api/meta");
    $("#updated").textContent = m.updated_at ? "数据更新 " + new Date(m.updated_at).toLocaleTimeString("zh-CN", { hour12: false }) + `（${TZ}）` : "暂无数据";
  } catch (e) {}
}
window.addEventListener("resize", () => document.querySelectorAll(".chart").forEach((el) => echarts.getInstanceByDom(el)?.resize()));
boot();
