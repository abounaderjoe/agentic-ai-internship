"use client";

import {
  ArcElement,
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  Title,
  Tooltip,
} from "chart.js";
import { Bar, Line, Pie } from "react-chartjs-2";
import type { ChartSpec } from "@/lib/types";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend
);

const COLORS = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#06b6d4", "#a855f7", "#eab308", "#f43f5e"];

export function ChartMessage({ spec }: { spec: ChartSpec }) {
  const data = {
    labels: spec.labels,
    datasets: [
      {
        label: spec.title ?? "",
        data: spec.data,
        backgroundColor: COLORS,
        borderColor: spec.type === "line" ? COLORS[0] : undefined,
      },
    ],
  };
  // Chart.js defaults to black text, invisible on our dark background --
  // explicitly light-color the title, legend, and axis ticks/grid.
  const options = {
    responsive: true,
    color: "#d4d4d4",
    plugins: {
      title: { display: !!spec.title, text: spec.title ?? "", color: "#e5e5e5" },
      legend: { labels: { color: "#d4d4d4" } },
    },
    scales:
      spec.type === "pie"
        ? undefined
        : {
            x: { ticks: { color: "#d4d4d4" }, grid: { color: "rgba(255,255,255,0.08)" } },
            y: { ticks: { color: "#d4d4d4" }, grid: { color: "rgba(255,255,255,0.08)" } },
          },
  };

  return (
    <div className="max-w-md rounded-xl border border-neutral-700 bg-neutral-800 p-4">
      {spec.type === "bar" && <Bar data={data} options={options} />}
      {spec.type === "pie" && <Pie data={data} options={options} />}
      {spec.type === "line" && <Line data={data} options={options} />}
    </div>
  );
}
