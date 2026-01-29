"use client";

import { useMemo, useRef, useState, useEffect } from "react";
import { MagicGroup, AccountAggregate, Magic, Period } from "@/types/dashboard";

interface MainResultsProps {
  accountAggregate: AccountAggregate | undefined;
  groups: MagicGroup[];
  magics: Magic[];
  magicLabels: Record<number, string>;
  selectedMagicIds: number[];
  groupedGroupIds: number[];
  period: Period;
  onScreenshot: (element: HTMLDivElement | null) => void;
  sortBy: "value" | "alpha" | "magic";
  sortOrder: "asc" | "desc";
  onSortChange: (sortBy: "value" | "alpha" | "magic", sortOrder: "asc" | "desc") => void;
  onItemClick: (payload: { label: string; magicIds: number[] }) => void;
}

// Minimum row height to keep readable
const MIN_ROW_HEIGHT = 20; // px
const MAX_ROW_HEIGHT = 40; // px

export default function MainResults({
  accountAggregate,
  groups,
  magics,
  magicLabels,
  selectedMagicIds,
  groupedGroupIds,
  period,
  onScreenshot,
  sortBy,
  sortOrder,
  onSortChange,
  onItemClick,
}: MainResultsProps) {
  // Ref for the bars container specifically
  const barsContainerRef = useRef<HTMLDivElement>(null);
  const mainResultsRef = useRef<HTMLDivElement>(null);
  const [barsContainerHeight, setBarsContainerHeight] = useState(0);

  // Measure the actual bars container height
  useEffect(() => {
    const updateHeight = () => {
      if (barsContainerRef.current) {
        setBarsContainerHeight(barsContainerRef.current.clientHeight);
      }
    };

    updateHeight();

    const resizeObserver = new ResizeObserver(updateHeight);
    if (barsContainerRef.current) {
      resizeObserver.observe(barsContainerRef.current);
    }

    return () => resizeObserver.disconnect();
  }, []);

  const safeAggregate = accountAggregate || {
    account_id: "",
    period_profit: 0,
    period_percent: 0,
    by_group: [],
    by_magic: [],
  };
  const { period_profit, period_percent, by_magic } = safeAggregate;

  // Helper to get magic label
  const getMagicLabel = (magicNum: number) => {
    if (magicLabels[magicNum]) return magicLabels[magicNum];
    const m = magics.find((mg) => mg.magic === magicNum);
    return m?.label ?? `Magic ${magicNum}`;
  };

  const getGroupLabel = (groupId: number) => {
    const group = groups.find((gr) => gr.group_id === groupId);
    if (!group) return `Group ${groupId}`;
    const label2 = (group.label2 || "").trim();
    const base = `[ ${group.name} ]`;
    return label2 ? `${base} - ${label2}` : base;
  };

  const formatMagicLabel = (magicNum: number) =>
    `${getMagicLabel(magicNum)} - ${magicNum}`;

  const groupToMagics = useMemo(() => {
    const map = new Map<number, number[]>();
    magics.forEach((m) => {
      (m.group_ids || []).forEach((gid) => {
        const current = map.get(gid) || [];
        current.push(m.magic);
        map.set(gid, current);
      });
    });
    return map;
  }, [magics]);

  const magicToGroups = useMemo(() => {
    const map = new Map<number, number[]>();
    magics.forEach((m) => {
      map.set(m.magic, m.group_ids || []);
    });
    return map;
  }, [magics]);

  const profitByMagic = useMemo(() => {
    const map = new Map<number, number>();
    by_magic.forEach((m) => map.set(m.magic, m.profit));
    return map;
  }, [by_magic]);

  const selectedMagicSet = useMemo(
    () => new Set(selectedMagicIds),
    [selectedMagicIds]
  );

  const groupedSet = useMemo(
    () => new Set(groupedGroupIds),
    [groupedGroupIds]
  );

  const groupById = useMemo(() => {
    const map = new Map<number, MagicGroup>();
    groups.forEach((group) => map.set(group.group_id, group));
    return map;
  }, [groups]);

  const rawItems = useMemo(() => {
    const items: Array<{
      id: number;
      label: string;
      profit: number;
      kind: "group" | "magic";
      label2?: string;
      magicIds?: number[];
      font_color?: string | null;
      fill_color?: string | null;
    }> = [];

    groups.forEach((group) => {
      const magicsInGroup = groupToMagics.get(group.group_id) || [];
      const selectedInGroup = magicsInGroup.filter(
        (id) => selectedMagicSet.has(id) && profitByMagic.has(id)
      );
      if (selectedInGroup.length === 0) return;
      if (!groupedSet.has(group.group_id)) return;
      const profit = selectedInGroup.reduce(
        (sum, id) => sum + (profitByMagic.get(id) || 0),
        0
      );
      items.push({
        id: group.group_id,
        label: getGroupLabel(group.group_id),
        profit,
        kind: "group",
        label2: group.label2 || "",
        magicIds: selectedInGroup,
        font_color: group.font_color || null,
        fill_color: group.fill_color || null,
      });
    });

    selectedMagicIds.forEach((magicId) => {
      if (!selectedMagicSet.has(magicId)) return;
      if (!profitByMagic.has(magicId)) return;
      const groupIds = magicToGroups.get(magicId) || [];
      if (groupIds.some((gid) => groupedSet.has(gid))) {
        return;
      }
      items.push({
        id: magicId,
        label: formatMagicLabel(magicId),
        profit: profitByMagic.get(magicId) || 0,
        kind: "magic",
      });
    });

    return items;
  }, [groups, groupedSet, groupToMagics, magicToGroups, profitByMagic, selectedMagicIds, selectedMagicSet]);

  // Sort items
  const items = useMemo(() => {
    const sorted = [...rawItems];
    if (sortBy === "value") {
      sorted.sort((a, b) => {
        const diff = a.profit - b.profit;
        return sortOrder === "asc" ? diff : -diff;
      });
    } else if (sortBy === "alpha") {
      sorted.sort((a, b) => {
        const diff = a.label.localeCompare(b.label);
        return sortOrder === "asc" ? diff : -diff;
      });
    } else {
      const resolveSortValue = (item: (typeof sorted)[number]) => {
        if (item.kind === "magic") {
          return { type: "num" as const, value: item.id };
        }
        const label2 = (item.label2 || "").trim();
        if (!label2) return { type: "none" as const, value: "" };
        const num = Number(label2);
        if (!Number.isNaN(num)) {
          return { type: "num" as const, value: num };
        }
        return { type: "str" as const, value: label2 };
      };
      sorted.sort((a, b) => {
        const aVal = resolveSortValue(a);
        const bVal = resolveSortValue(b);
        const dir = sortOrder === "asc" ? 1 : -1;
        if (aVal.type === "none" && bVal.type === "none") return 0;
        if (aVal.type === "none") return 1 * dir;
        if (bVal.type === "none") return -1 * dir;
        if (aVal.type === "num" && bVal.type === "num") {
          return (aVal.value - bVal.value) * dir;
        }
        return String(aVal.value).localeCompare(String(bVal.value)) * dir;
      });
    }
    return sorted;
  }, [rawItems, sortBy, sortOrder]);

  // Calculate dynamic row height based on the actual bars container height
  const calculatedRowHeight =
    items.length > 0 && barsContainerHeight > 0
      ? Math.floor(barsContainerHeight / items.length)
      : MAX_ROW_HEIGHT;

  // Clamp between min and max
  const rowHeight = Math.max(MIN_ROW_HEIGHT, Math.min(MAX_ROW_HEIGHT, calculatedRowHeight));

  // Determine if we need scroll (items don't fit even at minimum height)
  const totalRequiredHeight = items.length * MIN_ROW_HEIGHT;
  const needsScroll = barsContainerHeight > 0 && totalRequiredHeight > barsContainerHeight;

  // Determine compact mode based on row height
  const isCompact = rowHeight < 28;
  const isUltraCompact = rowHeight < 24;

  // Find max positive and negative values for dynamic center calculation
  const maxPositive = Math.max(...items.map((i) => (i.profit > 0 ? i.profit : 0)), 0);
  const maxNegative = Math.abs(
    Math.min(...items.map((i) => (i.profit < 0 ? i.profit : 0)), 0)
  );

  // Calculate dynamic center position (0-100%)
  let centerPercent = 50;
  if (maxPositive === 0 && maxNegative === 0) {
    centerPercent = 50;
  } else if (maxNegative === 0) {
    centerPercent = 5;
  } else if (maxPositive === 0) {
    centerPercent = 95;
  } else {
    const total = maxPositive + maxNegative;
    centerPercent = (maxNegative / total) * 100;
    centerPercent = Math.max(5, Math.min(95, centerPercent));
  }

  // Find max absolute value for scaling
  const maxAbsProfit = Math.max(maxPositive, maxNegative, 1);

  const formatProfit = (val: number) =>
    val >= 0 ? `+$${val.toFixed(2)}` : `-$${Math.abs(val).toFixed(2)}`;

  const selectedProfit = items.reduce((sum, item) => sum + item.profit, 0);
  const balanceEstimate =
    period_percent !== 0 ? period_profit / (period_percent / 100) : 0;
  const selectedPercent = balanceEstimate
    ? (selectedProfit / balanceEstimate) * 100
    : 0;

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  };

  const handleSortClick = (newSortBy: "value" | "alpha" | "magic") => {
    if (sortBy === newSortBy) {
      onSortChange(sortBy, sortOrder === "asc" ? "desc" : "asc");
    } else {
      onSortChange(newSortBy, newSortBy === "value" ? "desc" : "asc");
    }
  };

  const getSortIcon = (type: "value" | "alpha" | "magic") => {
    if (sortBy !== type) return "";
    return sortOrder === "asc" ? "↑" : "↓";
  };

  // Dynamic styles based on row height
  const fontSize = isUltraCompact ? "text-xs" : isCompact ? "text-xs" : "text-sm";
  const labelWidth = isUltraCompact ? "w-40" : isCompact ? "w-48" : "w-64";
  const valueWidth = isUltraCompact ? "w-16" : isCompact ? "w-20" : "w-28";
  const barHeightPx = Math.max(8, rowHeight - 12);

  // Calculate bar style considering dynamic center
  const getBarStyle = (profit: number) => {
    const isPositive = profit >= 0;
    const absProfit = Math.abs(profit);

    if (isPositive) {
      const availablePercent = 100 - centerPercent;
      const barWidthPercent = (absProfit / maxAbsProfit) * availablePercent;
      return {
        left: `${centerPercent}%`,
        width: `${barWidthPercent}%`,
        backgroundColor: "#22c55e",
      };
    } else {
      const availablePercent = centerPercent;
      const barWidthPercent = (absProfit / maxAbsProfit) * availablePercent;
      return {
        right: `${100 - centerPercent}%`,
        width: `${barWidthPercent}%`,
        backgroundColor: "#ef4444",
      };
    }
  };

  return (
    <div className="flex-1 flex flex-col p-4 overflow-hidden" ref={mainResultsRef}>
      {/* Info panel with sort controls */}
      <div className="flex items-center justify-between mb-2 p-2 bg-surface rounded border border-border shrink-0">
        <div className="flex items-center gap-3">
          <div className="text-xs text-textSecondary">
            Period Result ({formatDate(period.from)} → {formatDate(period.to)} GMT):
          </div>
          <div
            className={`text-base font-semibold ${
              selectedProfit >= 0 ? "text-positive" : "text-negative"
            }`}
          >
            {formatProfit(selectedProfit)} ({selectedPercent >= 0 ? "+" : ""}
            {selectedPercent.toFixed(2)}%)
          </div>
          <div className="text-xs text-textSecondary">({items.length} items)</div>
        </div>

        {/* Sort controls */}
        <div className="flex items-center gap-1">
          <button
            onClick={() => onScreenshot(mainResultsRef.current)}
            className="inline-flex items-center justify-center px-2 py-1 text-xs leading-none rounded bg-surfaceHover text-textSecondary hover:bg-border transition-colors"
            title="Save dashboard screenshot"
          >
            📷 Screenshot
          </button>
          <span className="text-xs text-textSecondary">Sort:</span>
          <button
            onClick={() => handleSortClick("value")}
            className={`inline-flex items-center justify-center px-2 py-1 text-xs leading-none rounded transition-colors ${
              sortBy === "value"
                ? "bg-neutral text-white"
                : "bg-surfaceHover text-textSecondary hover:bg-border"
            }`}
          >
            Value {getSortIcon("value")}
          </button>
          <button
            onClick={() => handleSortClick("magic")}
            className={`inline-flex items-center justify-center px-2 py-1 text-xs leading-none rounded transition-colors ${
              sortBy === "magic"
                ? "bg-neutral text-white"
                : "bg-surfaceHover text-textSecondary hover:bg-border"
            }`}
          >
            Magic # {getSortIcon("magic")}
          </button>
          <button
            onClick={() => handleSortClick("alpha")}
            className={`inline-flex items-center justify-center px-2 py-1 text-xs leading-none rounded transition-colors ${
              sortBy === "alpha"
                ? "bg-neutral text-white"
                : "bg-surfaceHover text-textSecondary hover:bg-border"
            }`}
          >
            A-Z {getSortIcon("alpha")}
          </button>
        </div>
      </div>

      {/* Bars container with dynamic sizing - this is what we measure */}
      <div
        ref={barsContainerRef}
        className={`flex-1 flex flex-col ${needsScroll ? "overflow-y-auto" : "overflow-hidden"}`}
      >
        {!accountAggregate ? (
          <div className="text-textSecondary text-sm text-center py-8">
            No data available
          </div>
        ) : items.length === 0 ? (
          <div className="text-textSecondary text-sm text-center py-8">
            No groups/magics selected. Use filters below.
          </div>
        ) : (
          items.map((item) => {
            const isPositive = item.profit >= 0;
            const barStyle = getBarStyle(item.profit);
            const isGroupItem = item.kind === "group";
            let inheritedGroup: MagicGroup | undefined;
            if (!isGroupItem) {
              const groupIds = magicToGroups.get(item.id) || [];
              const candidateId = groupIds.find((gid) => {
                if (groupedSet.has(gid)) return false;
                const groupMagics = groupToMagics.get(gid) || [];
                if (groupMagics.length === 0) return false;
                return groupMagics.every((id) => selectedMagicSet.has(id));
              });
              if (candidateId !== undefined) {
                inheritedGroup = groupById.get(candidateId);
              }
            }

            const fontColor = isGroupItem
              ? item.font_color || undefined
              : inheritedGroup?.font_color || undefined;
            const fillColor = isGroupItem
              ? item.fill_color || undefined
              : inheritedGroup?.fill_color || undefined;

            return (
              <div
                key={item.id}
                className="flex items-center gap-1 px-1 bg-surface rounded hover:bg-surfaceHover transition-colors shrink-0 cursor-pointer"
                style={{ height: `${rowHeight}px`, backgroundColor: fillColor || undefined }}
                onClick={() => {
                  const magicIds = item.kind === "group" ? item.magicIds || [] : [item.id];
                  onItemClick({ label: item.label, magicIds });
                }}
              >
                {/* Label */}
                <div
                  className={`${labelWidth} ${fontSize} leading-none flex items-center justify-end h-full text-right text-textPrimary truncate ${
                    isGroupItem ? "font-semibold" : ""
                  }`}
                  title={item.label}
                  style={fontColor ? { color: fontColor } : undefined}
                >
                  {item.label}
                </div>

                {/* Bar container with dynamic center */}
                <div className="flex-1 flex items-center relative" style={{ height: `${barHeightPx}px` }}>
                  {/* Center/zero line */}
                  <div
                    className="absolute top-0 bottom-0 w-px bg-border"
                    style={{ left: `${centerPercent}%` }}
                  />

                  {/* Bar */}
                  {item.profit !== 0 && (
                    <div
                      className={`absolute top-0 bottom-0 transition-all ${
                        isPositive ? "rounded-r" : "rounded-l"
                      }`}
                      style={barStyle}
                    />
                  )}
                </div>

                {/* Value */}
                <div
                  className={`${valueWidth} ${fontSize} leading-none flex items-center justify-end h-full text-right font-medium ${
                    isPositive ? "text-positive" : "text-negative"
                  }`}
                >
                  {formatProfit(item.profit)}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
