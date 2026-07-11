// Yandex Form Bot — Mini App front-end
// Uses MAX WebApp SDK for initData signature.
//
// Backend endpoints (all under /api):
//   GET  /api/healthz
//   GET  /api/summary?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&foreman=…
//   GET  /api/submissions/{id}
//   GET  /api/screenshot/{id}
//   GET  /api/summary.xlsx?date=YYYY-MM-DD
//
// All non-healthz require X-Auth-InitData header.

(function () {
  "use strict";

  const API_BASE = "";  // same origin
  const state = {
    dateFrom: null,
    dateTo: null,
    foremanFilter: "",
    submissions: [],
  };

  // ---- Date helpers ------------------------------------------------------
  function isoDate(d) {
    return d.toISOString().slice(0, 10);
  }
  function daysAgo(n) {
    const d = new Date();
    d.setDate(d.getDate() - n);
    return d;
  }

  function setRange(range) {
    const today = new Date();
    let from, to;
    if (range === "today") {
      from = to = today;
    } else if (range === "yesterday") {
      from = to = daysAgo(1);
    } else {
      const n = parseInt(range, 10) || 7;
      from = daysAgo(n - 1);
      to = today;
    }
    state.dateFrom = isoDate(from);
    state.dateTo = isoDate(to);
    document.getElementById("date-from").value = state.dateFrom;
    document.getElementById("date-to").value = state.dateTo;
    setActiveChip(range);
    loadSummary();
  }

  function setActiveChip(range) {
    document.querySelectorAll(".chip").forEach((c) => {
      c.classList.toggle("active", c.dataset.range === range);
    });
  }

  // ---- API calls ---------------------------------------------------------
  function getInitData() {
    // MAX WebApp SDK exposes initData — Telegram-compatible.
    // If not running inside the SDK (e.g. local browser dev), use dev header.
    if (window.WebApp && window.WebApp.initData) {
      return window.WebApp.initData;
    }
    // Dev fallback: empty initData — backend will 401 unless MAX_BOT_TOKEN unset.
    return "";
  }

  function authHeaders() {
    return {
      "X-Auth-InitData": getInitData(),
      "Content-Type": "application/json",
    };
  }

  async function apiGet(path) {
    const resp = await fetch(API_BASE + path, { headers: authHeaders() });
    if (resp.status === 401) {
      throw new Error("Unauthorized — open this app from MAX bot");
    }
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    if (resp.headers.get("content-type")?.includes("json")) {
      return await resp.json();
    }
    return resp;
  }

  // ---- Render ------------------------------------------------------------
  function renderStats(subs) {
    document.getElementById("stat-count").textContent = subs.length;
    const totalPeople = subs.reduce((s, x) => s + (x.personnel_total || 0), 0);
    const totalWaste = subs.reduce((s, x) => s + (x.waste_volume || 0), 0);
    const totalMachineHours = subs.reduce((s, x) => {
      return s + (x.machines || []).reduce((m, mach) => {
        const q = Number(mach.quantity) || 0;
        return m + q;
      }, 0);
    }, 0);
    document.getElementById("stat-people").textContent = totalPeople;
    document.getElementById("stat-waste").textContent = totalWaste;
    document.getElementById("stat-machines").textContent = totalMachineHours;
  }

  function renderList(subs) {
    const list = document.getElementById("list");
    list.innerHTML = "";
    if (subs.length === 0) {
      document.getElementById("empty").classList.remove("hidden");
      return;
    }
    document.getElementById("empty").classList.add("hidden");
    subs.forEach((s) => {
      const li = document.createElement("li");
      li.className = "submission-item" + (s.confirmed ? "" : " unconfirmed");
      const status = s.confirmed ? "✅" : "⏳";
      const machineNames = (s.machines || []).map((m) => m.machine_type).join(", ");
      li.innerHTML = `
        <div class="submission-header">
          <span class="submission-date">${escapeHtml(s.date)}</span>
          <span class="submission-object">${escapeHtml(s.object_name || "—")}</span>
          <span class="submission-status">${status}</span>
        </div>
        <div class="submission-foreman">👤 ${escapeHtml(s.foreman || "—")}</div>
        <div class="submission-meta">
          <span>🔧 ${escapeHtml(machineNames || "—")}</span>
          <span>👥 ${s.personnel_total || 0}</span>
          <span>🟫 ${s.waste_volume || 0} м³</span>
        </div>
      `;
      li.addEventListener("click", () => showDetail(s));
      list.appendChild(li);
    });
  }

  function showDetail(s) {
    const modal = document.getElementById("modal");
    const body = document.getElementById("modal-body");
    const machinesHtml = (s.machines || [])
      .map(
        (m) =>
          `<div class="field"><span class="field-label">${escapeHtml(m.machine_type)}</span><span class="field-value">${m.quantity} ${escapeHtml(m.unit)}</span></div>`
      )
      .join("");
    body.innerHTML = `
      <h2>${escapeHtml(s.object_name)} — ${escapeHtml(s.date)}</h2>
      <div class="field"><span class="field-label">Прораб</span><span class="field-value">${escapeHtml(s.foreman)}</span></div>
      ${machinesHtml || '<div class="field"><span class="field-label">Техника</span><span class="field-value">—</span></div>'}
      <div class="field"><span class="field-label">ИТР</span><span class="field-value">${s.personnel.itr || 0}</span></div>
      <div class="field"><span class="field-label">ОПР штатные</span><span class="field-value">${s.personnel.opr_staff || 0}</span></div>
      <div class="field"><span class="field-label">ОПР внештатные</span><span class="field-value">${s.personnel.opr_external || 0}</span></div>
      <div class="field"><span class="field-label">Вывоз грунта</span><span class="field-value">${s.waste_volume} м³</span></div>
      ${s.comment ? `<div class="field"><span class="field-label">Комментарий</span><span class="field-value">${escapeHtml(s.comment)}</span></div>` : ""}
      ${s.final_comment ? `<div class="field"><span class="field-label">Итог</span><span class="field-value">${escapeHtml(s.final_comment)}</span></div>` : ""}
      ${s.screenshot_url ? `<img class="screenshot-img" src="${s.screenshot_url}" alt="Скриншот формы" />` : ""}
      ${s.disk_json_url ? `<div class="field"><span class="field-label">💾 JSON на диске</span><span class="field-value"><a href="${s.disk_json_url}" target="_blank">открыть</a></span></div>` : ""}
    `;
    modal.classList.remove("hidden");
  }

  function escapeHtml(s) {
    if (s == null) return "";
    return String(s)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  // ---- Main flow ---------------------------------------------------------
  async function loadSummary() {
    const loading = document.getElementById("loading");
    const list = document.getElementById("list");
    const cards = document.getElementById("summary-cards");
    loading.classList.remove("hidden");
    list.classList.add("hidden");
    cards.classList.add("hidden");
    try {
      const params = new URLSearchParams({
        date_from: state.dateFrom,
        date_to: state.dateTo,
      });
      if (state.foremanFilter) params.set("foreman", state.foremanFilter);
      const data = await apiGet("/api/summary?" + params.toString());
      state.submissions = data.submissions;
      renderStats(data.submissions);
      renderList(data.submissions);
      cards.classList.remove("hidden");
      if (data.submissions.length > 0) list.classList.remove("hidden");
    } catch (e) {
      loading.textContent = "❌ " + e.message;
      console.error(e);
      return;
    }
    loading.classList.add("hidden");
  }

  async function downloadXlsx() {
    try {
      const date = state.dateTo;
      const resp = await fetch(`${API_BASE}/api/summary.xlsx?date=${date}`, {
        headers: authHeaders(),
      });
      if (!resp.ok) throw new Error("HTTP " + resp.status);
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `summary_${date}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert("❌ Не удалось скачать Excel: " + e.message);
    }
  }

  // ---- Wire up -----------------------------------------------------------
  function init() {
    // Date bar
    document.querySelectorAll(".chip").forEach((c) => {
      c.addEventListener("click", () => setRange(c.dataset.range));
    });
    document.getElementById("apply").addEventListener("click", () => {
      state.dateFrom = document.getElementById("date-from").value;
      state.dateTo = document.getElementById("date-to").value;
      setActiveChip("");
      loadSummary();
    });
    document.getElementById("foreman-filter").addEventListener("input", (e) => {
      state.foremanFilter = e.target.value.trim();
      loadSummary();
    });
    document.getElementById("download-xlsx").addEventListener("click", downloadXlsx);

    // Modal
    document.getElementById("modal-close").addEventListener("click", () => {
      document.getElementById("modal").classList.add("hidden");
    });
    document.getElementById("modal-backdrop").addEventListener("click", () => {
      document.getElementById("modal").classList.add("hidden");
    });

    // Initial range: last 7 days
    setRange("7");
  }

  // MAX WebApp ready hook
  if (window.WebApp && window.WebApp.ready) {
    window.WebApp.ready();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
