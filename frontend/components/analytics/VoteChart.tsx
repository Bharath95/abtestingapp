// frontend/components/analytics/VoteChart.tsx
"use client";

import { useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from "recharts";
import type { OptionAnalytics } from "@/lib/types";

const COLORS = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"];

interface VoteChartProps {
  options: OptionAnalytics[];
  questionTitle: string;
}

export default function VoteChart({ options, questionTitle }: VoteChartProps) {
  const [view, setView] = useState<"bar" | "pie">("bar");

  const data = options.map((o) => ({
    name: o.label,
    votes: o.votes,
    percentage: o.percentage,
  }));

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-base font-semibold text-gray-900">{questionTitle}</h3>
        <div className="flex gap-1 bg-gray-100 rounded-lg p-0.5">
          <button
            onClick={() => setView("bar")}
            className={`px-3 py-1 text-xs rounded-md font-medium transition-colors ${
              view === "bar" ? "bg-white shadow text-gray-900" : "text-gray-500"
            }`}
          >
            Bar
          </button>
          <button
            onClick={() => setView("pie")}
            className={`px-3 py-1 text-xs rounded-md font-medium transition-colors ${
              view === "pie" ? "bg-white shadow text-gray-900" : "text-gray-500"
            }`}
          >
            Pie
          </button>
        </div>
      </div>

      {view === "bar" ? (
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis allowDecimals={false} />
            <Tooltip
              formatter={(value: unknown, _name: unknown, props: unknown) => {
                const p = props as { payload?: { percentage?: number } };
                const percentage = p.payload?.percentage ?? 0;
                return [`${value} votes (${percentage}%)`, "Votes"];
              }}
            />
            <Bar dataKey="votes" fill="#3B82F6" radius={[4, 4, 0, 0]}>
              {data.map((_, index) => (
                <Cell key={index} fill={COLORS[index % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={data}
              dataKey="votes"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={100}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              label={((props: any) => `${props.name}: ${props.percentage}%`) as any}
            >
              {data.map((_, index) => (
                <Cell key={index} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
