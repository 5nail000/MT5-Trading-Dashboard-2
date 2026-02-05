"use client";

import { useMemo } from "react";
import { Magic, MagicGroup } from "@/types/dashboard";

interface SidePanelProps {
  groups: MagicGroup[];
  magics: Magic[];
  selectedMagicIds: number[];
  groupedGroupIds: number[];
  onToggleGroupAggregate: (groupId: number) => void;
  onLabelsClick: () => void;
  onGroupsClick: () => void;
  onDealsClick: () => void;
  onBalanceChartClick: () => void;
  onChartsClick: () => void;
  onCompareClick: () => void;
}

const panelItems = [
  { id: "labels", label: "Labels (magic)", icon: "🏷️" },
  { id: "groups", label: "Groups (magic)", icon: "📁" },
  { id: "deals", label: "Deals", icon: "📊", newWindow: true },
  { id: "balance", label: "Balance Chart", icon: "📈", newWindow: true },
  { id: "charts", label: "Create Charts", icon: "⚙️", newWindow: true },
  { id: "compare", label: "Compare Accounts", icon: "⚖️", newWindow: true },
];

export default function SidePanel({
  groups,
  magics,
  selectedMagicIds,
  groupedGroupIds,
  onToggleGroupAggregate,
  onLabelsClick,
  onGroupsClick,
  onDealsClick,
  onBalanceChartClick,
  onChartsClick,
  onCompareClick,
}: SidePanelProps) {
  const visibleGroups = useMemo(() => {
    const selectedSet = new Set(selectedMagicIds);
    return groups.filter((group) =>
      magics.some(
        (magic) =>
          selectedSet.has(magic.magic) &&
          (magic.group_ids || []).includes(group.group_id)
      )
    );
  }, [groups, magics, selectedMagicIds]);

  const handleClick = (id: string) => {
    switch (id) {
      case "labels":
        onLabelsClick();
        break;
      case "groups":
        onGroupsClick();
        break;
      case "deals":
        onDealsClick();
        break;
      case "balance":
        onBalanceChartClick();
        break;
      case "charts":
        onChartsClick();
        break;
      case "compare":
        onCompareClick();
        break;
    }
  };

  return (
    <div className="w-56 flex flex-col gap-4 p-3 bg-surface border-l border-border">
      <div>
        <h4 className="text-xs text-textSecondary uppercase tracking-wider mb-2">
          Actions
        </h4>
        {panelItems.map((item) => (
          <button
            key={item.id}
            onClick={() => handleClick(item.id)}
            className="flex items-center gap-2 px-3 py-2 text-sm text-textPrimary bg-surfaceHover rounded hover:bg-border transition-colors text-left w-full"
          >
            <span>{item.icon}</span>
            <span className="flex-1">{item.label}</span>
            {item.newWindow && (
              <span className="text-textSecondary text-xs">↗</span>
            )}
          </button>
        ))}
      </div>

      {visibleGroups.length > 0 && (
        <div>
          <h4 className="text-xs text-textSecondary uppercase tracking-wider mb-2">
            Groups
          </h4>
          <div className="flex flex-col gap-2">
            {visibleGroups.map((group) => {
              const isGrouped = groupedGroupIds.includes(group.group_id);
              const label2 = (group.label2 || "").trim();
              const label = label2 ? `${group.name} - ${label2}` : group.name;
              return (
                <button
                  key={group.group_id}
                  onClick={() => onToggleGroupAggregate(group.group_id)}
                  className={`px-3 py-2 text-sm rounded text-left transition-colors ${
                    isGrouped
                      ? "bg-neutral text-white"
                      : "bg-surfaceHover text-textSecondary hover:bg-border"
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
