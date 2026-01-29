"use client";

import { useState, useMemo } from "react";
import { OpenPositionsSummary, Magic, MagicGroup } from "@/types/dashboard";

interface OpenPositionsModalProps {
  summary: OpenPositionsSummary | undefined;
  magics: Magic[];
  groups: MagicGroup[];
  onClose: () => void;
}

type SortType = "value" | "magic" | "alpha";

export default function OpenPositionsModal({
  summary,
  magics,
  groups,
  onClose,
}: OpenPositionsModalProps) {
  const [sortBy, setSortBy] = useState<SortType>("value");
  const [sortDesc, setSortDesc] = useState(true);
  const [hoveredMagic, setHoveredMagic] = useState<number | null>(null);

  if (!summary) return null;

  const { balance, floating_total, floating_percent, by_magic } = summary;

  // Sort and enrich data
  const sortedData = useMemo(() => {
    const items = by_magic.map((item) => ({
      ...item,
      label: magics.find((m) => m.magic === item.magic)?.label ?? `Magic ${item.magic}`,
      description: magics.find((m) => m.magic === item.magic)?.description ?? "",
      groupName:
        groups.find((g) =>
          magics.find((m) => m.magic === item.magic)?.group_ids.includes(g.group_id)
        )?.name ?? "—",
    }));

    items.sort((a, b) => {
      let cmp = 0;
      switch (sortBy) {
        case "value":
          cmp = a.floating - b.floating;
          break;
        case "magic":
          cmp = a.magic - b.magic;
          break;
        case "alpha":
          cmp = a.label.localeCompare(b.label);
          break;
      }
      return sortDesc ? -cmp : cmp;
    });

    return items;
  }, [by_magic, magics, groups, sortBy, sortDesc]);

  // Find max absolute value for scaling
  const maxAbsFloating = Math.max(...by_magic.map((m) => Math.abs(m.floating)), 1);
  const formatCurrency = (val: number) =>
    val >= 0 ? `+$${val.toFixed(2)}` : `-$${Math.abs(val).toFixed(2)}`;

  const formatPercent = (val: number) =>
    val >= 0 ? `+${val.toFixed(2)}%` : `${val.toFixed(2)}%`;

  const handleSort = (type: SortType) => {
    if (sortBy === type) {
      setSortDesc(!sortDesc);
    } else {
      setSortBy(type);
      setSortDesc(true);
    }
  };

  const getSortIcon = (type: SortType) => {
    if (sortBy !== type) return "";
    return sortDesc ? " ↓" : " ↑";
  };

  return (
    <div
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-surface border border-border rounded-lg shadow-2xl w-[600px] max-h-[85vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 border-b border-border">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold text-textPrimary">
              Open Positions by Magic
            </h3>
            <button
              onClick={onClose}
              className="text-textSecondary hover:text-textPrimary transition-colors"
            >
              ✕
            </button>
          </div>

          {/* Summary bar */}
          <div className="flex items-center justify-between p-3 bg-background rounded">
            <div className="text-textSecondary text-sm">
              Balance:{" "}
              <span className="text-textPrimary font-medium">
                ${balance.toLocaleString()}
              </span>
            </div>
            <div
              className={`font-semibold ${
                floating_total >= 0 ? "text-positive" : "text-negative"
              }`}
            >
              {formatCurrency(floating_total)}{" "}
              <span className="text-sm opacity-80">
                ({formatPercent(floating_percent)})
              </span>
            </div>
          </div>

          {/* Sort controls */}
          <div className="flex items-center gap-2 mt-3 text-xs">
            <span className="text-textSecondary">Sort by:</span>
            <button
              onClick={() => handleSort("value")}
              className={`px-2 py-1 rounded transition-colors ${
                sortBy === "value"
                  ? "bg-neutral text-white"
                  : "bg-surfaceHover text-textSecondary hover:bg-border"
              }`}
            >
              Value{getSortIcon("value")}
            </button>
            <button
              onClick={() => handleSort("magic")}
              className={`px-2 py-1 rounded transition-colors ${
                sortBy === "magic"
                  ? "bg-neutral text-white"
                  : "bg-surfaceHover text-textSecondary hover:bg-border"
              }`}
            >
              Magic #{getSortIcon("magic")}
            </button>
            <button
              onClick={() => handleSort("alpha")}
              className={`px-2 py-1 rounded transition-colors ${
                sortBy === "alpha"
                  ? "bg-neutral text-white"
                  : "bg-surfaceHover text-textSecondary hover:bg-border"
              }`}
            >
              Name{getSortIcon("alpha")}
            </button>
          </div>
        </div>

        {/* Histogram - scrollable */}
        <div className="flex-1 overflow-y-auto p-4">
          <div className="space-y-2">
            {sortedData.map((item) => {
              const barWidth = (Math.abs(item.floating) / maxAbsFloating) * 100;
              const isPositive = item.floating >= 0;
              const isHovered = hoveredMagic === item.magic;

              return (
                <div
                  key={item.magic}
                  className={`py-2 px-3 bg-background rounded transition-all ${
                    isHovered ? "ring-1 ring-neutral" : ""
                  }`}
                  onMouseEnter={() => setHoveredMagic(item.magic)}
                  onMouseLeave={() => setHoveredMagic(null)}
                >
                  {/* Main row */}
                  <div className="flex items-center gap-3">
                    {/* Label */}
                    <div className="w-28 flex-shrink-0">
                      <div className="text-sm text-textPrimary truncate font-medium">
                        {item.label}
                      </div>
                      <div className="text-xs text-textSecondary">
                        #{item.magic}
                      </div>
                    </div>

                    {/* Bar */}
                    <div className="flex-1 flex items-center h-6 relative">
                      {/* Center line */}
                      <div className="absolute left-1/2 top-0 bottom-0 w-px bg-border z-10" />
                      
                      {/* Negative bar */}
                      {!isPositive && (
                        <div
                          className="absolute top-0 bottom-0 rounded-l transition-all"
                          style={{
                            right: "50%",
                            width: `${barWidth / 2}%`,
                            backgroundColor: isHovered ? "#f87171" : "#ef4444",
                          }}
                        />
                      )}
                      
                      {/* Positive bar */}
                      {isPositive && item.floating !== 0 && (
                        <div
                          className="absolute top-0 bottom-0 rounded-r transition-all"
                          style={{
                            left: "50%",
                            width: `${barWidth / 2}%`,
                            backgroundColor: isHovered ? "#4ade80" : "#22c55e",
                          }}
                        />
                      )}
                    </div>

                    {/* Values */}
                    <div className="w-28 text-right flex-shrink-0">
                      <div
                        className={`text-sm font-semibold ${
                          isPositive ? "text-positive" : "text-negative"
                        }`}
                      >
                        {formatCurrency(item.floating)}
                      </div>
                      <div
                        className={`text-xs ${
                          isPositive ? "text-positive/70" : "text-negative/70"
                        }`}
                      >
                        {formatPercent(item.percent)}
                      </div>
                    </div>
                  </div>

                  {/* Hover details */}
                  {isHovered && item.description && (
                    <div className="mt-2 pt-2 border-t border-border text-xs text-textSecondary">
                      <div className="flex items-center gap-4">
                        <span>Group: {item.groupName}</span>
                        <span className="text-textSecondary/70">{item.description}</span>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}

            {sortedData.length === 0 && (
              <div className="text-center text-textSecondary py-8">
                No open positions
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border">
          <div className="flex items-center justify-between text-xs text-textSecondary">
            <span>{sortedData.length} magic(s) with open positions</span>
            <span>
              Scale: max {formatCurrency(maxAbsFloating)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
