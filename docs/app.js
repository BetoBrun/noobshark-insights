async function loadJson(path) {
  const response = await fetch(path + `?v=${Date.now()}`);
  if (!response.ok) throw new Error(`Erro ao carregar ${path}`);
  return response.json();
}

function fmtNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return Number(value).toLocaleString("pt-BR", { maximumFractionDigits: digits });
}

function fmtPct(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const num = Number(value);
  const sign = num > 0 ? "+" : "";
  return `${sign}${num.toLocaleString("pt-BR", { maximumFractionDigits: digits })}%`;
}

function scoreLabel(score) {
  if (score >= 70) return "Forte / euforia";
  if (score >= 55) return "Construtivo";
  if (score >= 40) return "Neutro / cautela";
  if (score >= 25) return "Defensivo";
  return "Risco elevado";
}

function corrLabel(value) {
  if (value >= 0.5) return "Positiva forte";
  if (value >= 0.25) return "Positiva moderada";
  if (value <= -0.5) return "Negativa forte";
  if (value <= -0.25) return "Negativa moderada";
  return "Sem relação clara";
}

function dotClass(color) {
  if (color === "green") return "dot-green";
  if (color === "yellow") return "dot-yellow";
  if (color === "red") return "dot-red";
  return "dot-black";
}

function renderDashboard(data, history) {
  document.getElementById("updatedAt").textContent = `DATA: ${data.updated_at_brt || data.updated_at}`;
  document.getElementById("modelPosture").textContent = data.model_posture || "Modelo neutro";

  const trafficDot = document.getElementById("trafficDot");
  if (trafficDot) {
    trafficDot.className = `traffic-dot ${dotClass(data.traffic_light.color)}`;
    document.getElementById("trafficLabel").textContent = data.traffic_light.label;
    document.getElementById("trafficText").textContent = data.traffic_light.text;
  }

  const headline = document.getElementById("headline");
  if (headline) headline.textContent = data.headline;
  
  const executiveSummary = document.getElementById("executiveSummary");
  if (executiveSummary) executiveSummary.textContent = data.executive_summary;

  const regimeTags = document.getElementById("regimeTags");
  if (regimeTags) {
    const tags = [data.market_regime, data.btc_regime, data.altseason_regime].filter(Boolean);
    regimeTags.innerHTML = tags.map(t => `<span class="tag">${t}</span>`).join("");
  }

  const globalRisk = document.getElementById("globalRisk");
  if (globalRisk) {
    globalRisk.textContent = fmtNumber(data.scores.global_risk, 0);
    document.getElementById("globalRiskLabel").textContent = scoreLabel(data.scores.global_risk);

    document.getElementById("btcCycle").textContent = fmtNumber(data.scores.btc_cycle, 0);
    document.getElementById("btcCycleLabel").textContent = scoreLabel(data.scores.btc_cycle);

    document.getElementById("altseason").textContent = fmtNumber(data.scores.altseason_window, 0);
    document.getElementById("altseasonLabel").textContent = scoreLabel(data.scores.altseason_window);

    document.getElementById("techCorr").textContent = fmtNumber(data.scores.tech_correlation, 2);
    document.getElementById("techCorrLabel").textContent = corrLabel(data.scores.tech_correlation);
  }

  const correlationTable = document.getElementById("correlationTable");
  if (correlationTable) {
    const rows = Object.entries(data.correlations.current || {});
    correlationTable.innerHTML = rows.map(([key, value]) => `
      <tr>
        <td><strong>${key}</strong></td>
        <td>${fmtNumber(value, 3)}</td>
        <td style="color: var(--text-muted)">${corrLabel(value)}</td>
      </tr>
    `).join("");
  }

  const marketGrid = document.getElementById("marketGrid");
  if (marketGrid) {
    marketGrid.innerHTML = Object.entries(data.markets || {}).map(([key, item]) => {
      const pct = Number(item.change_30d_pct);
      const color = pct > 0 ? "var(--green)" : pct < 0 ? "var(--red)" : "var(--text)";
      return `
      <tr>
        <td>${item.name || key}</td>
        <td><strong>${fmtNumber(item.last, 2)}</strong></td>
        <td style="color: ${color}; text-align: right;">${fmtPct(item.change_30d_pct)} 30D</td>
      </tr>
    `}).join("");
  }

  const insightsFeed = document.getElementById("insightsFeed");
  if (insightsFeed) {
    insightsFeed.innerHTML = (data.insights || []).map(item => `
      <div class="feed-item">
        <strong>${item.title}</strong>
        <p>${item.text}</p>
      </div>
    `).join("");
  }

  const historyTable = document.getElementById("historyTable");
  if (historyTable) {
    historyTable.innerHTML = (history || []).slice(-15).reverse().map(item => `
      <tr>
        <td>${item.date.split(" ")[0]}</td>
        <td><span class="tag">${item.traffic_light}</span></td>
        <td>${fmtNumber(item.global_risk, 0)}</td>
        <td>${fmtNumber(item.btc_cycle, 0)}</td>
        <td>${fmtNumber(item.altseason_window, 0)}</td>
        <td>${fmtNumber(item.btc_price, 0)}</td>
      </tr>
    `).join("");
  }

  renderCorrelationChart(data);
}

function renderCorrelationChart(data) {
  const ctx = document.getElementById("correlationChart");
  if (!ctx) return;
  
  const series = data.correlations.series || [];
  const labels = series.map(x => x.date);

  const datasets = [
    ["GOLD", "gold", "#f5b041"],
    ["SPX", "spx", "#3498db"],
    ["DXY", "dxy", "#e74c3c"],
    ["NASDAQ", "nasdaq", "#00ff87"],
    ["IGV", "igv", "#00d2ff"]
  ].map(([label, key, color]) => ({
    label,
    data: series.map(x => x[key]),
    tension: 0.25,
    borderWidth: 2,
    borderColor: color,
    pointRadius: 0
  }));

  new Chart(ctx, {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { labels: { color: "#828a99", font: { family: "'Inter', sans-serif" } } }
      },
      scales: {
        x: { ticks: { color: "#828a99", maxTicksLimit: 8 }, grid: { color: "rgba(255,255,255,0.05)" } },
        y: { min: -1, max: 1, ticks: { color: "#828a99" }, grid: { color: "rgba(255,255,255,0.05)" } }
      }
    }
  });
}

async function main() {
  try {
    const [dashboard, history] = await Promise.all([
      loadJson("./data/dashboard.json"),
      loadJson("./data/history.json")
    ]);
    renderDashboard(dashboard, history);
  } catch (err) {
    console.error(err);
    const executiveSummary = document.getElementById("executiveSummary");
    if (executiveSummary) {
      executiveSummary.textContent =
        "Não foi possível carregar os dados. Verifique a conectividade com as fontes de dados.";
    }
  }
}

main();
