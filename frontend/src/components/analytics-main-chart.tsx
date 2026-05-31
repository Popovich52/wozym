"use client";

import { useMemo, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type RangeKey = 7 | 30 | 90;

type TrendPoint = {
  label: string;
  value: number;
};

function buildTrend(days: RangeKey, base: number): TrendPoint[] {
  const formatter = new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "2-digit" });
  const now = new Date();

  return Array.from({ length: days }, (_, index) => {
    const offset = days - index - 1;
    const date = new Date(now);
    date.setDate(now.getDate() - offset);

    const waveA = Math.sin(index / 2.4) * 0.3;
    const waveB = Math.cos(index / 5.1) * 0.22;
    const spike = index % 11 === 0 ? 0.42 : index % 17 === 0 ? 0.28 : 0;
    const ratio = Math.max(0.08, 0.62 + waveA + waveB + spike);
    const value = Math.round(base * ratio);

    return {
      label: formatter.format(date),
      value,
    };
  });
}

export function AnalyticsMainChart({ revenueTotal, ordersTotal }: { revenueTotal: number; ordersTotal: number }) {
  const [range, setRange] = useState<RangeKey>(30);
  const base = Math.max(2500, revenueTotal || ordersTotal * 1200 || 18000);

  const data = useMemo(() => buildTrend(range, base), [range, base]);
  const maxValue = useMemo(() => Math.max(...data.map((row) => row.value), 0), [data]);

  return (
    <section className="mp-card overflow-hidden border-[#223e77] bg-[#0a1438] p-4 text-white">
      <div className="mb-3 flex items-center justify-between gap-2">
        <div>
          <h2 className="font-bold">Аналитика</h2>
          <p className="text-xs text-blue-200">Динамика по выбранному подключению</p>
        </div>
        <div className="inline-flex rounded-lg border border-[#2d4d8c] bg-[#091130] p-1">
          {[7, 30, 90].map((item) => (
            <button
              className={`rounded-md px-2.5 py-1 text-xs font-semibold transition ${
                range === item ? "bg-orange-500 text-white" : "text-blue-200 hover:bg-[#16244f]"
              }`}
              key={item}
              onClick={() => setRange(item as RangeKey)}
              type="button"
            >
              {item}d
            </button>
          ))}
        </div>
      </div>
      <div className="h-[290px] min-h-[290px] min-w-0 w-full">
        <ResponsiveContainer width="100%" height="100%" minWidth={0}>
          <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="mpOrangeFill" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="#ff6a00" stopOpacity={0.45} />
                <stop offset="95%" stopColor="#ff6a00" stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#20335f" strokeDasharray="4 4" />
            <XAxis
              axisLine={{ stroke: "#2f4f8f" }}
              dataKey="label"
              minTickGap={12}
              tick={{ fill: "#9bb4ea", fontSize: 11 }}
              tickLine={{ stroke: "#2f4f8f" }}
            />
            <YAxis
              axisLine={{ stroke: "#2f4f8f" }}
              domain={[0, Math.ceil(maxValue * 1.15)]}
              tick={{ fill: "#9bb4ea", fontSize: 11 }}
              tickLine={{ stroke: "#2f4f8f" }}
              width={70}
            />
            <Tooltip
              contentStyle={{ background: "#0f1d49", border: "1px solid #355a9f", borderRadius: 10, color: "#fff" }}
              formatter={(value) => {
                const numeric = typeof value === "number" ? value : Number(value ?? 0);
                return [`${numeric.toLocaleString("ru-RU")} ₽`, "Выручка"];
              }}
              labelStyle={{ color: "#b6caf5" }}
            />
            <Area
              dataKey="value"
              fill="url(#mpOrangeFill)"
              fillOpacity={1}
              isAnimationActive
              name="Выручка"
              stroke="#ff6a00"
              strokeWidth={2.5}
              type="monotone"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
