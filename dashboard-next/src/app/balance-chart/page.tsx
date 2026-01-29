"use client";

import { useState, useMemo, useEffect } from "react";
import { Deal, Account, OpenPositionsSummary } from "@/types/dashboard";
import { api } from "@/lib/api";

interface BalancePoint {
  time: Date;
  balance: number;
  equity: number;
}

export default function BalanceChartPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState("");
  const [deals, setDeals] = useState<Deal[]>([]);
  const [openPosSummary, setOpenPosSummary] = useState<OpenPositionsSummary | undefined>(undefined);
  const [showBalance, setShowBalance] = useState(true);
  const [showEquity, setShowEquity] = useState(true);
  const [isRecalculating, setIsRecalculating] = useState(false);

  useEffect(() => {
    api.listAccounts().then((data) => {
      setAccounts(data);
      if (!selectedAccountId && data[0]) {
        setSelectedAccountId(data[0].account_id);
      }
    });
  }, [selectedAccountId]);

  useEffect(() => {
    if (!selectedAccountId) return;
    const now = new Date();
    const from = new Date(now.getFullYear(), now.getMonth(), 1).toISOString();
    const to = now.toISOString();
    Promise.all([
      api.deals(selectedAccountId, from, to),
      api.openPositions(selectedAccountId),
    ]).then(([dealsData, summary]) => {
      setDeals(dealsData);
      setOpenPosSummary(summary);
    });
  }, [selectedAccountId]);

  // Generate balance history from deals (simulated)
  const balanceHistory = useMemo(() => {
    // Start with an initial balance (derived from current balance minus profits)
    const closedDeals = deals.filter((d) => d.status === "closed");
    const totalProfit = closedDeals.reduce((sum, d) => sum + d.profit, 0);
    const currentBalance = openPosSummary?.balance || 10000;
    const startingBalance = currentBalance - totalProfit;

    // Sort deals by exit time
    const sortedDeals = [...closedDeals]
      .filter((d) => d.exit_time)
      .sort((a, b) => new Date(a.exit_time!).getTime() - new Date(b.exit_time!).getTime());

    const points: BalancePoint[] = [];
    let runningBalance = startingBalance;

    // Starting point
    if (sortedDeals.length > 0) {
      const firstDealTime = new Date(sortedDeals[0].entry_time);
      points.push({
        time: new Date(firstDealTime.getTime() - 24 * 60 * 60 * 1000), // day before first deal
        balance: runningBalance,
        equity: runningBalance,
      });
    }

    // Add points for each closed deal
    sortedDeals.forEach((deal) => {
      runningBalance += deal.profit;
      points.push({
        time: new Date(deal.exit_time!),
        balance: runningBalance,
        equity: runningBalance + (Math.random() * 200 - 100), // simulate equity fluctuation
      });
    });

    // Current point
    if (points.length > 0) {
      points.push({
        time: new Date(),
        balance: currentBalance,
        equity: currentBalance + (openPosSummary?.floating_total || 0),
      });
    }

    return points;
  }, [deals, openPosSummary]);

  const handleRecalculate = () => {
    setIsRecalculating(true);
    setTimeout(() => setIsRecalculating(false), 1500);
  };

  // Chart dimensions
  const chartWidth = 800;
  const chartHeight = 400;
  const padding = { top: 40, right: 60, bottom: 50, left: 80 };

  // Calculate scales
  const chartData = useMemo(() => {
    if (balanceHistory.length < 2) return null;

    const times = balanceHistory.map((p) => p.time.getTime());
    const minTime = Math.min(...times);
    const maxTime = Math.max(...times);

    const allValues: number[] = [];
    if (showBalance) allValues.push(...balanceHistory.map((p) => p.balance));
    if (showEquity) allValues.push(...balanceHistory.map((p) => p.equity));
    if (allValues.length === 0) return null;

    const minValue = Math.min(...allValues);
    const maxValue = Math.max(...allValues);
    const valueRange = maxValue - minValue || 1;
    const paddedMin = minValue - valueRange * 0.05;
    const paddedMax = maxValue + valueRange * 0.05;

    const scaleX = (time: number) => {
      return padding.left + ((time - minTime) / (maxTime - minTime)) * (chartWidth - padding.left - padding.right);
    };

    const scaleY = (value: number) => {
      return chartHeight - padding.bottom - ((value - paddedMin) / (paddedMax - paddedMin)) * (chartHeight - padding.top - padding.bottom);
    };

    // Generate path
    const balancePath = balanceHistory
      .map((p, i) => `${i === 0 ? "M" : "L"} ${scaleX(p.time.getTime())} ${scaleY(p.balance)}`)
      .join(" ");

    const equityPath = balanceHistory
      .map((p, i) => `${i === 0 ? "M" : "L"} ${scaleX(p.time.getTime())} ${scaleY(p.equity)}`)
      .join(" ");

    // Grid lines
    const yTicks: number[] = [];
    const yStep = (paddedMax - paddedMin) / 5;
    for (let i = 0; i <= 5; i++) {
      yTicks.push(paddedMin + i * yStep);
    }

    return { scaleX, scaleY, balancePath, equityPath, yTicks, minTime, maxTime, paddedMin, paddedMax };
  }, [balanceHistory, showBalance, showEquity]);

  const formatDate = (timestamp: number) => {
    return new Date(timestamp).toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit" });
  };

  const formatValue = (val: number) => `$${val.toFixed(0)}`;

  return (
    <div className="min-h-screen bg-background text-textPrimary p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Balance Change Chart</h1>
        <button
          onClick={handleRecalculate}
          disabled={isRecalculating}
          className={`px-4 py-2 text-sm rounded transition-colors ${
            isRecalculating
              ? "bg-surfaceHover text-textSecondary cursor-not-allowed"
              : "bg-neutral text-white hover:bg-neutral/80"
          }`}
        >
          {isRecalculating ? "Recalculating..." : "Recalculate"}
        </button>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-6 mb-6 p-4 bg-surface rounded border border-border">
        <div className="flex items-center gap-2">
          <label className="text-sm text-textSecondary">Account:</label>
          <select
            value={selectedAccountId}
            onChange={(e) => setSelectedAccountId(e.target.value)}
            className="bg-background border border-border rounded px-3 py-1.5 text-sm focus:outline-none focus:border-neutral"
          >
            {accounts.map((acc) => (
              <option key={acc.account_id} value={acc.account_id}>
                {acc.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showBalance}
              onChange={(e) => setShowBalance(e.target.checked)}
              className="w-4 h-4 accent-positive"
            />
            <span className="text-sm text-positive">Balance</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showEquity}
              onChange={(e) => setShowEquity(e.target.checked)}
              className="w-4 h-4 accent-blue-500"
            />
            <span className="text-sm text-blue-400">Equity</span>
          </label>
        </div>
      </div>

      {/* Chart */}
      <div className="bg-surface rounded border border-border p-6 overflow-x-auto">
        {chartData && balanceHistory.length >= 2 ? (
          <svg width={chartWidth} height={chartHeight} className="mx-auto">
            {/* Grid lines */}
            {chartData.yTicks.map((tick, i) => (
              <g key={i}>
                <line
                  x1={padding.left}
                  y1={chartData.scaleY(tick)}
                  x2={chartWidth - padding.right}
                  y2={chartData.scaleY(tick)}
                  stroke="#333"
                  strokeDasharray="4 4"
                />
                <text
                  x={padding.left - 10}
                  y={chartData.scaleY(tick)}
                  textAnchor="end"
                  alignmentBaseline="middle"
                  fill="#888"
                  fontSize={12}
                >
                  {formatValue(tick)}
                </text>
              </g>
            ))}

            {/* X axis labels */}
            {[0, 0.25, 0.5, 0.75, 1].map((pct, i) => {
              const time = chartData.minTime + pct * (chartData.maxTime - chartData.minTime);
              const x = chartData.scaleX(time);
              return (
                <text
                  key={i}
                  x={x}
                  y={chartHeight - padding.bottom + 25}
                  textAnchor="middle"
                  fill="#888"
                  fontSize={12}
                >
                  {formatDate(time)}
                </text>
              );
            })}

            {/* Balance line */}
            {showBalance && (
              <path
                d={chartData.balancePath}
                fill="none"
                stroke="#22c55e"
                strokeWidth={2}
                strokeLinejoin="round"
              />
            )}

            {/* Equity line */}
            {showEquity && (
              <path
                d={chartData.equityPath}
                fill="none"
                stroke="#3b82f6"
                strokeWidth={2}
                strokeDasharray="6 3"
                strokeLinejoin="round"
              />
            )}

            {/* Data points */}
            {showBalance &&
              balanceHistory.map((p, i) => (
                <circle
                  key={`bal-${i}`}
                  cx={chartData.scaleX(p.time.getTime())}
                  cy={chartData.scaleY(p.balance)}
                  r={4}
                  fill="#22c55e"
                />
              ))}

            {/* Legend */}
            <g transform={`translate(${chartWidth - padding.right - 120}, ${padding.top})`}>
              {showBalance && (
                <>
                  <line x1={0} y1={10} x2={20} y2={10} stroke="#22c55e" strokeWidth={2} />
                  <text x={25} y={14} fill="#22c55e" fontSize={12}>
                    Balance
                  </text>
                </>
              )}
              {showEquity && (
                <>
                  <line
                    x1={0}
                    y1={showBalance ? 30 : 10}
                    x2={20}
                    y2={showBalance ? 30 : 10}
                    stroke="#3b82f6"
                    strokeWidth={2}
                    strokeDasharray="6 3"
                  />
                  <text x={25} y={showBalance ? 34 : 14} fill="#3b82f6" fontSize={12}>
                    Equity
                  </text>
                </>
              )}
            </g>
          </svg>
        ) : (
          <div className="text-center text-textSecondary py-20">
            Not enough data to display chart
          </div>
        )}
      </div>

      {/* Stats */}
      {balanceHistory.length >= 2 && (
        <div className="mt-6 flex items-center gap-6 p-4 bg-surface rounded border border-border">
          <div>
            <span className="text-sm text-textSecondary">Starting Balance: </span>
            <span className="font-semibold">${balanceHistory[0].balance.toFixed(2)}</span>
          </div>
          <div>
            <span className="text-sm text-textSecondary">Current Balance: </span>
            <span className="font-semibold">${balanceHistory[balanceHistory.length - 1].balance.toFixed(2)}</span>
          </div>
          <div>
            <span className="text-sm text-textSecondary">Change: </span>
            <span
              className={`font-semibold ${
                balanceHistory[balanceHistory.length - 1].balance - balanceHistory[0].balance >= 0
                  ? "text-positive"
                  : "text-negative"
              }`}
            >
              {(balanceHistory[balanceHistory.length - 1].balance - balanceHistory[0].balance >= 0 ? "+" : "") +
                (balanceHistory[balanceHistory.length - 1].balance - balanceHistory[0].balance).toFixed(2)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
