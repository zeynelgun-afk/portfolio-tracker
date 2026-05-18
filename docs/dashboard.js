// Finzora AI Dashboard
// Renders the system map and overlays live workflow status from GitHub Actions API.
// Public repo → no token needed.

const REPO_OWNER = "zeynelgun-afk";
const REPO_NAME  = "portfolio-tracker";

// ---- Color palette per node category (must match HTML legend) ----
const CATEGORY_COLORS = {
  workflow:    "#a371f7",
  script:      "#3fb950",
  module:      "#58a6ff",
  "module-core": "#1f6feb",
  agent:       "#bc8cff",   // pastel mor — AI/agent kategorisi (ai_gate, vb.)
  data:        "#d29922",
  external:    "#8b949e",
};

// Status colors (border tint for workflows)
const STATUS_COLORS = {
  ok:      "#3fb950",
  warn:    "#d29922",
  err:     "#f85149",
  gray:    "#6e7681",
  railway: "#1f6feb",  // mavi — GitHub'da görünmeyen, Railway subprocess
};

// ---- Helpers ----
function timeAgoTR(isoDate) {
  if (!isoDate) return "—";
  const diff = (Date.now() - new Date(isoDate).getTime()) / 1000;
  if (diff < 60)        return `${Math.floor(diff)}sn önce`;
  if (diff < 3600)      return `${Math.floor(diff / 60)}dk önce`;
  if (diff < 86400)     return `${Math.floor(diff / 3600)}sa önce`;
  if (diff < 86400*7)   return `${Math.floor(diff / 86400)}g önce`;
  return `${Math.floor(diff / 86400)}g önce`;
}

function classifyStatus(run) {
  if (!run) return "gray";
  const conclusion = run.conclusion;        // success, failure, cancelled, skipped, null (in_progress)
  const updated = new Date(run.updated_at).getTime();
  const ageHours = (Date.now() - updated) / 3600000;

  if (conclusion === null || run.status === "in_progress") return "warn";
  if (conclusion === "failure") return "err";
  if (conclusion === "cancelled") return "warn";
  if (conclusion === "success") {
    if (ageHours > 36) return "warn";   // stale success
    return "ok";
  }
  return "gray";
}

// ---- Load system map ----
async function loadMap() {
  // Cache busting: GitHub Pages CDN + browser cache'i bypass et
  // (system_map.json güncellemelerinin anında yansıması için)
  const res = await fetch("system_map.json?v=" + Date.now(), {
    cache: "no-cache",
  });
  if (!res.ok) throw new Error("system_map.json yüklenemedi");
  return await res.json();
}

// ---- Fetch live workflow runs ----
async function fetchWorkflowRuns() {
  const url = `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/workflows`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("GitHub API hatası: " + res.status);
  const data = await res.json();

  // For each workflow, fetch latest run
  const map = {};
  await Promise.all(data.workflows.map(async (wf) => {
    const fileName = wf.path.split("/").pop();
    try {
      const runRes = await fetch(
        `https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/actions/workflows/${wf.id}/runs?per_page=1`
      );
      if (!runRes.ok) { map[fileName] = null; return; }
      const runData = await runRes.json();
      map[fileName] = runData.workflow_runs[0] || null;
    } catch (e) {
      map[fileName] = null;
    }
  }));
  return map;
}

// ---- Build Cytoscape elements ----
function buildElements(systemMap, statusByWorkflow) {
  const elements = [];

  systemMap.nodes.forEach((n) => {
    let statusClass = "gray";
    let lastRunInfo = null;
    if (n.category === "workflow" && n.workflow_file) {
      const run = statusByWorkflow[n.workflow_file];
      statusClass = classifyStatus(run);
      lastRunInfo = run;
    } else if (n.category === "workflow" && !n.workflow_file) {
      // Workflow node'u var ama GitHub Actions'tan dispatch edilmiyor
      // (Railway subprocess olarak çalışıyor) — özel durum
      statusClass = "railway";
    }
    elements.push({
      data: {
        id: n.id,
        label: n.label,
        category: n.category,
        color: CATEGORY_COLORS[n.category] || "#888",
        statusColor: STATUS_COLORS[statusClass] || STATUS_COLORS.gray,
        statusClass: statusClass,
        meta: n,
        run: lastRunInfo,
      },
    });
  });

  systemMap.edges.forEach((e) => {
    elements.push({
      data: {
        id: `${e.source}__${e.target}`,
        source: e.source,
        target: e.target,
      },
    });
  });

  return elements;
}

// ---- Status report generator ----
let _latestState = null;  // {systemMap, statusByWorkflow, elements, generatedAt}

function generateStatusReport(state) {
  if (!state) return "# Henüz veri yüklenmedi.\n";

  const { systemMap, statusByWorkflow, elements, generatedAt } = state;
  const counts = { ok: 0, warn: 0, err: 0, gray: 0, railway: 0 };
  const rows = [];
  const problems = [];

  systemMap.nodes
    .filter(n => n.category === "workflow")
    .forEach(n => {
      // Railway-managed (no workflow_file) — özel durum
      if (!n.workflow_file) {
        counts.railway++;
        rows.push(
          `| ${n.label} | 🔵 RAILWAY | Railway subprocess | ${n.schedule || "—"} | — |`
        );
        return;
      }
      const run = statusByWorkflow[n.workflow_file];
      const status = classifyStatus(run);
      counts[status] = (counts[status] || 0) + 1;
      const conclusion = run ? (run.conclusion || run.status || "—") : "hiç çalışmamış";
      const updated = run ? new Date(run.updated_at).toLocaleString("tr-TR") : "—";
      const ago = run ? timeAgoTR(run.updated_at) : "—";
      const url = run && run.html_url ? run.html_url : "";
      const emoji = { ok: "✅", warn: "⏳", err: "❌", gray: "—" }[status];

      rows.push(
        `| ${n.label} | ${emoji} ${status.toUpperCase()} | ${conclusion} | ${updated} | ${ago} |`
      );

      if (status === "err" || status === "warn") {
        problems.push({
          label: n.label,
          status,
          conclusion,
          updated,
          ago,
          url,
          schedule: n.schedule || "—",
        });
      }
    });

  const totalWf = counts.ok + counts.warn + counts.err + counts.gray + counts.railway;
  const lines = [];
  lines.push("# Finzora AI — Sistem Durum Raporu");
  lines.push("");
  lines.push(`**Oluşturulma:** ${generatedAt.toLocaleString("tr-TR")}`);
  lines.push(`**Repo:** https://github.com/${REPO_OWNER}/${REPO_NAME}`);
  lines.push(`**Dashboard:** https://${REPO_OWNER}.github.io/${REPO_NAME}/dashboard.html`);
  lines.push("");
  lines.push("## Özet");
  lines.push("");
  lines.push(`- ✅ Başarılı: **${counts.ok}** / ${totalWf}`);
  lines.push(`- ⏳ Bekliyor / eski: **${counts.warn}** / ${totalWf}`);
  lines.push(`- ❌ Hata: **${counts.err}** / ${totalWf}`);
  lines.push(`- 🔵 Railway-managed: **${counts.railway}** / ${totalWf}`);
  lines.push(`- — Bilinmiyor: **${counts.gray}** / ${totalWf}`);
  lines.push("");

  if (problems.length > 0) {
    lines.push("## ⚠️ Dikkat gerektiren workflow'lar");
    lines.push("");
    problems.forEach(p => {
      const icon = p.status === "err" ? "❌" : "⏳";
      lines.push(`### ${icon} ${p.label}`);
      lines.push(`- **Durum:** ${p.status.toUpperCase()} (${p.conclusion})`);
      lines.push(`- **Son çalışma:** ${p.updated} (${p.ago})`);
      lines.push(`- **Zamanlama:** ${p.schedule}`);
      if (p.url) lines.push(`- **GitHub run:** ${p.url}`);
      lines.push("");
    });
  } else {
    lines.push("## ✅ Sorun bulunmadı");
    lines.push("");
    lines.push("Tüm workflow'lar başarılı veya henüz çalıştırılmamış.");
    lines.push("");
  }

  lines.push("## Tüm Workflow'lar");
  lines.push("");
  lines.push("| Workflow | Durum | Conclusion | Son çalışma (TR) | Önce |");
  lines.push("|---|---|---|---|---|");
  rows.forEach(r => lines.push(r));
  lines.push("");

  lines.push("## Sistem Haritası");
  lines.push("");
  const byCat = {};
  systemMap.nodes.forEach(n => {
    byCat[n.category] = (byCat[n.category] || 0) + 1;
  });
  lines.push(`- Toplam **${systemMap.nodes.length}** node, **${systemMap.edges.length}** edge`);
  Object.entries(byCat).forEach(([cat, n]) => {
    lines.push(`  - ${cat}: ${n}`);
  });
  lines.push("");

  lines.push("---");
  lines.push(`*Bu rapor Finzora AI dashboard'undan otomatik üretildi.*`);
  return lines.join("\n");
}

function downloadReport() {
  if (!_latestState) {
    alert("Önce veriler yüklensin (sayfayı yenile veya 'Yenile' bas).");
    return;
  }
  const md = generateStatusReport(_latestState);
  const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  const filename = `finzora_status_${ts}.md`;
  const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ---- Cytoscape style ----
const cyStyle = [
  {
    selector: "node",
    style: {
      "background-color": "data(color)",
      "label": "data(label)",
      "color": "#e6edf3",
      "font-size": "11px",
      "text-valign": "bottom",
      "text-halign": "center",
      "text-margin-y": 6,
      "text-outline-width": 2,
      "text-outline-color": "#0d1117",
      "width": 30,
      "height": 30,
      "border-width": 0,
    },
  },
  {
    selector: "node[category = 'workflow']",
    style: {
      "shape": "round-rectangle",
      "width": 50,
      "height": 30,
      "border-width": 3,
      "border-color": "data(statusColor)",
      "font-size": "12px",
      "font-weight": 600,
    },
  },
  {
    selector: "node[category = 'module-core']",
    style: {
      "width": 38,
      "height": 38,
      "border-width": 2,
      "border-color": "#58a6ff",
    },
  },
  {
    selector: "node[category = 'external']",
    style: {
      "shape": "diamond",
      "width": 32,
      "height": 32,
    },
  },
  {
    selector: "node[category = 'data']",
    style: {
      "shape": "barrel",
      "width": 40,
      "height": 28,
    },
  },
  {
    selector: "edge",
    style: {
      "width": 1.2,
      "line-color": "#30363d",
      "target-arrow-color": "#30363d",
      "target-arrow-shape": "triangle",
      "curve-style": "bezier",
      "arrow-scale": 0.8,
      "opacity": 0.7,
    },
  },
  {
    selector: "node:selected",
    style: {
      "border-width": 4,
      "border-color": "#58a6ff",
    },
  },
  {
    selector: "edge.highlighted",
    style: {
      "line-color": "#58a6ff",
      "target-arrow-color": "#58a6ff",
      "width": 2,
      "opacity": 1,
    },
  },
];

// ---- Detail panel ----
function renderDetail(nodeData) {
  const meta = nodeData.meta;
  const run = nodeData.run;
  const parts = [`<h2>${meta.label}</h2>`];

  parts.push(`<div class="field"><span class="k">ID</span><span class="v">${meta.id}</span></div>`);
  parts.push(`<div class="field"><span class="k">Kategori</span><span class="v">${meta.category}</span></div>`);

  if (meta.schedule) {
    parts.push(`<div class="field"><span class="k">Zamanlama</span><span class="v">${meta.schedule}</span></div>`);
  }
  if (meta.url) {
    parts.push(`<div class="field"><span class="k">URL</span><span class="v"><a href="${meta.url}" target="_blank">${meta.url}</a></span></div>`);
  }
  if (meta.tag) {
    parts.push(`<div class="field"><span class="k">Etiket</span><span class="v">${meta.tag}</span></div>`);
  }

  if (meta.category === "workflow") {
    if (nodeData.statusClass === "railway") {
      parts.push(`<div class="status-line ok">🔵 Railway tarafından subprocess olarak çalıştırılır</div>`);
      parts.push(`<div class="field"><span class="k">Tetikleyici</span><span class="v">${meta.schedule || "—"}</span></div>`);
      parts.push(`<div class="field"><span class="k">Not</span><span class="v">GitHub Actions'ta görünmez — son çalışma data dosyaları üzerinden takip edilir</span></div>`);
    } else if (run) {
      const statusText = {
        ok:   `✅ Son çalışma başarılı`,
        warn: `⏳ Devam ediyor veya eski`,
        err:  `❌ Son çalışma BAŞARISIZ`,
        gray: `— Bilinmiyor`,
      }[nodeData.statusClass];
      parts.push(`<div class="status-line ${nodeData.statusClass}">${statusText}</div>`);
      parts.push(`<div class="field"><span class="k">Son durum</span><span class="v">${run.conclusion || run.status || "—"}</span></div>`);
      parts.push(`<div class="field"><span class="k">Son çalışma</span><span class="v">${timeAgoTR(run.updated_at)}</span></div>`);
      if (run.html_url) {
        parts.push(`<div class="field"><span class="k">Detay</span><span class="v"><a href="${run.html_url}" target="_blank">GitHub'da aç</a></span></div>`);
      }
    } else {
      parts.push(`<div class="status-line gray">Henüz çalıştırılmamış</div>`);
    }
  }

  document.getElementById("detail").innerHTML = parts.join("\n");
}

// ---- Status counts ----
function updateStats(elements, systemMap) {
  const counts = { ok: 0, warn: 0, err: 0, gray: 0, railway: 0 };
  elements.forEach((el) => {
    if (el.data.category === "workflow") {
      counts[el.data.statusClass] = (counts[el.data.statusClass] || 0) + 1;
    }
  });
  document.getElementById("ok-count").textContent   = counts.ok;
  document.getElementById("warn-count").textContent = counts.warn;
  document.getElementById("err-count").textContent  = counts.err;
  // Railway-managed olanlar gray sayılmasın — kendi sayacı olsun
  document.getElementById("gray-count").textContent = counts.gray + " / " + counts.railway + " Railway";
  // Harita versiyonu: node/edge sayısı (cache durumunu görmek için)
  if (systemMap) {
    const v = document.getElementById("map-version");
    if (v) v.textContent = `${systemMap.nodes.length}n / ${systemMap.edges.length}e`;
  }
}

// ---- Main render ----
let cy;
async function render() {
  const btn = document.getElementById("refresh");
  btn.disabled = true;
  btn.textContent = "Yükleniyor…";

  try {
    const systemMap = await loadMap();
    const statusByWorkflow = await fetchWorkflowRuns();
    const elements = buildElements(systemMap, statusByWorkflow);

    if (cy) {
      cy.elements().remove();
      cy.add(elements);
      cy.layout({ name: "cose", animate: false, padding: 30, nodeRepulsion: 12000 }).run();
    } else {
      cy = cytoscape({
        container: document.getElementById("cy"),
        elements: elements,
        style: cyStyle,
        layout: {
          name: "cose",
          animate: false,
          padding: 30,
          nodeRepulsion: 12000,
          idealEdgeLength: 80,
          edgeElasticity: 100,
        },
        wheelSensitivity: 0.2,
      });

      cy.on("tap", "node", (e) => {
        const n = e.target;
        cy.elements("edge.highlighted").removeClass("highlighted");
        n.connectedEdges().addClass("highlighted");
        renderDetail(n.data());
      });
      cy.on("tap", (e) => {
        if (e.target === cy) {
          cy.elements("edge.highlighted").removeClass("highlighted");
        }
      });
    }

    updateStats(elements, systemMap);
    _latestState = {
      systemMap,
      statusByWorkflow,
      elements,
      generatedAt: new Date(),
    };
    document.getElementById("last-update").textContent =
      "Son güncelleme: " + new Date().toLocaleString("tr-TR");
  } catch (err) {
    console.error(err);
    document.getElementById("last-update").textContent =
      "HATA: " + err.message;
  } finally {
    btn.disabled = false;
    btn.textContent = "Yenile";
  }
}

document.getElementById("refresh").addEventListener("click", render);
document.getElementById("download").addEventListener("click", downloadReport);
render();
