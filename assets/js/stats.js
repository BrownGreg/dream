// Graphiques du tableau de bord (Chart.js 4, hébergé localement).
// Couleurs lues dans les variables CSS de .viz-root : la palette validée vit à un seul endroit.
(() => {
  "use strict";
  const source = document.getElementById("chart-data");
  if (!source || !window.Chart) return;
  const data = JSON.parse(source.textContent);
  const root = document.querySelector(".viz-root");
  const css = (name) => getComputedStyle(root).getPropertyValue(name).trim();
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  Chart.defaults.color = css("--text-secondary");
  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  Chart.defaults.animation = reduced ? false : { duration: 300 };
  Chart.defaults.plugins.tooltip.backgroundColor = "#0b1020";
  Chart.defaults.plugins.tooltip.titleColor = css("--text-primary");
  Chart.defaults.plugins.tooltip.bodyColor = css("--text-primary");
  Chart.defaults.plugins.tooltip.borderColor = css("--grid");
  Chart.defaults.plugins.tooltip.borderWidth = 1;

  const grid = { color: css("--grid"), drawTicks: false };
  const integerAxis = { beginAtZero: true, ticks: { precision: 0, padding: 6 }, grid, border: { display: false } };
  const categoryAxis = { grid: { display: false }, border: { color: css("--grid") } };
  // Barres fines (≤ 24 px), extrémité arrondie de 4 px, base carrée.
  const bar = { maxBarThickness: 24, borderRadius: 4, borderSkipped: "start" };

  const draw = (name, config) => {
    const canvas = document.querySelector(`[data-chart="${name}"]`);
    if (canvas) new Chart(canvas, config);
  };

  draw("weeks", {
    type: "bar",
    data: {
      labels: data.weeks.labels,
      datasets: [{ label: "Rêves", data: data.weeks.values, backgroundColor: css("--sequential"), ...bar }],
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { title: (items) => `Semaine du ${items[0].label}` } } },
      scales: { x: { ...categoryAxis, ticks: { maxRotation: 0, autoSkip: true } }, y: integerAxis },
    },
  });

  draw("distribution", {
    type: "bar",
    data: {
      labels: data.distribution.labels,
      datasets: [{ label: "Rêves", data: data.distribution.values, backgroundColor: css("--sequential"), ...bar }],
    },
    options: {
      indexAxis: "y",
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { x: integerAxis, y: { ...categoryAxis, ticks: { color: css("--text-primary") } } },
    },
  });

  draw("evolution", {
    type: "bar",
    data: {
      labels: data.evolution.labels,
      datasets: data.evolution.series.map((s) => ({
        label: s.label,
        data: s.values,
        backgroundColor: css(`--emotion-${s.key}`),
        // Écart de 2 px couleur fond entre segments empilés (pas de contour coloré).
        borderColor: css("--surface-1"),
        borderWidth: 2,
        maxBarThickness: 24,
        borderRadius: 4,
        borderSkipped: "start",
      })),
    },
    options: {
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { position: "bottom", labels: { usePointStyle: true, pointStyle: "rectRounded", color: css("--text-primary") } },
        tooltip: { filter: (item) => item.raw > 0 },
      },
      scales: { x: { ...categoryAxis, stacked: true, ticks: { maxRotation: 0, autoSkip: true } }, y: { ...integerAxis, stacked: true } },
    },
  });
})();
