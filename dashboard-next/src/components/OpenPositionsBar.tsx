"use client";

import { useState } from "react";
import { OpenPositionsSummary } from "@/types/dashboard";

interface OpenPositionsBarProps {
  summary: OpenPositionsSummary | undefined;
  config: {
    range_percent: number;
    center_percent: number;
    positive_color: string;
    negative_color: string;
    neutral_color: string;
    hover_glow: boolean;
  };
  onBarClick: () => void;
}

export default function OpenPositionsBar({
  summary,
  config,
  onBarClick,
}: OpenPositionsBarProps) {
  const [isHovered, setIsHovered] = useState(false);

  if (!summary) {
    return (
      <div className="px-4 py-3 bg-surface border-b border-border text-textSecondary text-sm">
        No open positions data
      </div>
    );
  }

  const { balance, floating_total, floating_percent } = summary;
  const { range_percent, positive_color, negative_color, neutral_color } = config;

  // Calculate bar position (-range_percent to +range_percent maps to 0% to 100%)
  const clampedPercent = Math.max(-range_percent, Math.min(range_percent, floating_percent));
  // Center is 50%, each percent of range is 50/range_percent of width
  const barPosition = 50 + (clampedPercent / range_percent) * 50;
  const barWidth = Math.abs(clampedPercent / range_percent) * 50;

  const isPositive = floating_percent >= 0;
  const barColor = floating_percent === 0 ? neutral_color : isPositive ? positive_color : negative_color;

  const formatCurrency = (val: number) =>
    val >= 0 ? `+$${val.toFixed(2)}` : `-$${Math.abs(val).toFixed(2)}`;

  return (
    <div
      onClick={onBarClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={`relative px-4 py-4 bg-surface border-b border-border cursor-pointer transition-all ${
        isHovered ? "bg-surfaceHover shadow-lg" : ""
      }`}
      style={{
        boxShadow: isHovered ? `0 0 20px ${barColor}40` : "none",
      }}
    >
      {/* Labels */}
      <div className="flex justify-between text-xs text-textSecondary mb-2">
        <span>-{range_percent}%</span>
        <span>0%</span>
        <span>+{range_percent}%</span>
      </div>

      {/* Bar container */}
      <div className="relative h-6 bg-background rounded overflow-hidden">
        {/* Center line */}
        <div className="absolute left-1/2 top-0 bottom-0 w-px bg-border" />

        {/* Filled bar */}
        <div
          className="absolute top-0 bottom-0 transition-all duration-300"
          style={{
            left: isPositive ? "50%" : `${barPosition}%`,
            width: `${barWidth}%`,
            backgroundColor: barColor,
          }}
        />

        {/* Floating value label */}
        <div
          className="absolute top-1/2 -translate-y-1/2 px-2 py-0.5 rounded text-xs font-medium text-white whitespace-nowrap transition-all"
          style={{
            left: `${barPosition}%`,
            transform: `translateX(${isPositive ? "4px" : "-100%"}) translateY(-50%)`,
            marginLeft: isPositive ? 0 : "-4px",
          }}
        >
          {floating_percent >= 0 ? "+" : ""}
          {floating_percent.toFixed(2)}%
        </div>
      </div>

      {/* Summary text */}
      <div className="flex justify-between items-center mt-2 text-sm">
        <span className="text-textSecondary">
          Balance: <span className="text-textPrimary">${balance.toLocaleString()}</span>
        </span>
        <span
          className="font-medium"
          style={{ color: barColor }}
        >
          Floating P/L: {formatCurrency(floating_total)} ({floating_percent >= 0 ? "+" : ""}
          {floating_percent.toFixed(2)}%)
        </span>
        <span className="text-textSecondary text-xs">
          Click for details →
        </span>
      </div>
    </div>
  );
}
