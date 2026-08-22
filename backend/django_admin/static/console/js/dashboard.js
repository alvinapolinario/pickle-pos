function readJson(id) {
  const node = document.getElementById(id);
  return node ? JSON.parse(node.textContent) : null;
}

function doughnutCenterPlugin(text, sub) {
  return {
    id: "centerText",
    afterDraw(chart) {
      const { ctx, chartArea } = chart;
      if (!chartArea) return;
      ctx.save();
      ctx.fillStyle = "#122033";
      ctx.font = "700 22px Inter, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(text, (chartArea.left + chartArea.right) / 2, (chartArea.top + chartArea.bottom) / 2 - 8);
      ctx.fillStyle = "#6b7c90";
      ctx.font = "500 12px Inter, sans-serif";
      ctx.fillText(sub, (chartArea.left + chartArea.right) / 2, (chartArea.top + chartArea.bottom) / 2 + 14);
      ctx.restore();
    },
  };
}

document.addEventListener("DOMContentLoaded", () => {
  const overview = readJson("sales-overview-data");
  const payments = readJson("payments-data");
  const occupancy = readJson("occupancy-data");
  if (!window.Chart) return;

  if (overview) {
    new Chart(document.getElementById("salesOverviewChart"), {
      type: "line",
      data: {
        labels: overview.labels,
        datasets: [
          { label: "Total Sales", data: overview.total, borderColor: "#2563eb", backgroundColor: "rgba(37,99,235,0.08)", fill: true, tension: 0.35, borderWidth: 2.5, pointRadius: 3 },
          { label: "Canteen Sales", data: overview.canteen, borderColor: "#16a34a", backgroundColor: "transparent", tension: 0.35, borderWidth: 2.5, pointRadius: 3 },
          { label: "Court Revenue", data: overview.court, borderColor: "#7c3aed", backgroundColor: "transparent", tension: 0.35, borderWidth: 2.5, pointRadius: 3 },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: { legend: { position: "bottom", labels: { boxWidth: 10, usePointStyle: true, pointStyle: "circle", padding: 16 } } },
        scales: {
          x: { grid: { display: false } },
          y: { ticks: { callback: (value) => `₱${Number(value) / 1000}k` }, grid: { color: "#eef2f7" } },
        },
      },
    });
  }

  if (payments) {
    new Chart(document.getElementById("paymentsChart"), {
      type: "doughnut",
      data: {
        labels: payments.slices.map((item) => item.label),
        datasets: [{ data: payments.slices.map((item) => item.value), backgroundColor: payments.slices.map((item) => item.color), borderWidth: 0 }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "72%",
        plugins: { legend: { display: false } },
      },
    });
  }

  if (occupancy) {
    new Chart(document.getElementById("occupancyChart"), {
      type: "doughnut",
      data: {
        labels: occupancy.slices.map((item) => item.label),
        datasets: [{ data: occupancy.slices.map((item) => item.value), backgroundColor: occupancy.slices.map((item) => item.color), borderWidth: 0 }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "72%",
        plugins: { legend: { display: false } },
      },
      plugins: [doughnutCenterPlugin(`${occupancy.percent}%`, "Occupied")],
    });
  }
});
