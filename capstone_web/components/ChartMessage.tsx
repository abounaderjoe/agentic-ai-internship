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
  const options = {
    responsive: true,
    plugins: {
      title: { display: !!spec.title, text: spec.title ?? "" },
    },
  };

  return (
    <div className="max-w-md rounded-lg border border-black/10 bg-white p-4 dark:border-white/10 dark:bg-neutral-900">
      {spec.type === "bar" && <Bar data={data} options={options} />}
      {spec.type === "pie" && <Pie data={data} options={options} />}
      {spec.type === "line" && <Line data={data} options={options} />}
    </div>
  );
}
