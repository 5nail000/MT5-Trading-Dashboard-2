"use client";

import { useState } from "react";
import { Account, Period } from "@/types/dashboard";

interface TopBarProps {
  accounts: Account[];
  selectedAccountId: string;
  onAccountChange: (accountId: string) => void;
  period: Period;
  syncStatus: "idle" | "syncing_open" | "syncing_history";
  onSyncHistory: () => void;
  selectedPeriodKey: string;
  onPeriodChange: (periodKey: string, customFrom?: string, customTo?: string) => void;
  getAccountLabel: (accountId: string) => string;
  onSettingsClick: () => void;
  viewMode: "grouped" | "individual";
  onViewModeChange: (mode: "grouped" | "individual") => void;
}

const periodPresets = ["today", "last3days", "week", "month", "year", "custom"];

const periodLabels: Record<string, string> = {
  today: "Today",
  last3days: "3 Days",
  week: "Week",
  month: "Month",
  year: "Year",
  custom: "Custom",
};

export default function TopBar({
  accounts,
  selectedAccountId,
  onAccountChange,
  period,
  syncStatus,
  onSyncHistory,
  selectedPeriodKey,
  onPeriodChange,
  getAccountLabel,
  onSettingsClick,
  viewMode,
  onViewModeChange,
}: TopBarProps) {
  const [isCustomOpen, setIsCustomOpen] = useState(false);
  const [customFrom, setCustomFrom] = useState("");
  const [customTo, setCustomTo] = useState("");

  const selectedAccount = accounts.find((a) => a.account_id === selectedAccountId);

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric" });
  };

  const getSyncLabel = () => {
    switch (syncStatus) {
      case "syncing_open":
        return "Syncing positions...";
      case "syncing_history":
        return "Syncing history...";
      default:
        return "Idle";
    }
  };

  const handlePresetClick = (preset: string) => {
    if (preset === "custom") {
      setIsCustomOpen(true);
    } else {
      onPeriodChange(preset);
      setIsCustomOpen(false);
    }
  };

  const handleCustomApply = () => {
    if (customFrom && customTo) {
      onPeriodChange("custom", customFrom, customTo);
      setIsCustomOpen(false);
    }
  };

  return (
    <div className="flex items-center justify-between px-4 py-3 bg-surface border-b border-border">
      {/* Account Selector */}
      <div className="flex items-center gap-4">
        <label className="text-textSecondary text-sm">Account:</label>
        <select
          value={selectedAccountId}
          onChange={(e) => onAccountChange(e.target.value)}
          className="bg-background border border-border rounded px-3 py-1.5 text-textPrimary text-sm focus:outline-none focus:border-neutral"
        >
          {accounts.map((acc) => (
            <option key={acc.account_id} value={acc.account_id}>
              {getAccountLabel(acc.account_id)} ({acc.account_info.account_number})
            </option>
          ))}
        </select>
        {selectedAccount && (
          <span className="text-textSecondary text-xs">
            1:{selectedAccount.account_info.leverage} · {selectedAccount.account_info.server}
          </span>
        )}
      </div>

      {/* View Mode Toggle */}
      <div className="flex items-center gap-2">
        <span className="text-textSecondary text-xs">View:</span>
        <div className="flex rounded overflow-hidden border border-border">
          <button
            onClick={() => onViewModeChange("grouped")}
            className={`px-3 py-1 text-xs transition-colors ${
              viewMode === "grouped"
                ? "bg-neutral text-white"
                : "bg-surfaceHover text-textSecondary hover:bg-border"
            }`}
          >
            Groups
          </button>
          <button
            onClick={() => onViewModeChange("individual")}
            className={`px-3 py-1 text-xs transition-colors ${
              viewMode === "individual"
                ? "bg-neutral text-white"
                : "bg-surfaceHover text-textSecondary hover:bg-border"
            }`}
          >
            Magics
          </button>
        </div>
      </div>

      {/* Period Presets */}
      <div className="flex items-center gap-2 relative">
        {periodPresets.map((preset) => (
          <button
            key={preset}
            onClick={() => handlePresetClick(preset)}
            className={`px-3 py-1 text-sm rounded transition-colors ${
              selectedPeriodKey === preset
                ? "bg-neutral text-white"
                : "bg-surfaceHover text-textSecondary hover:bg-border"
            }`}
          >
            {periodLabels[preset] || preset}
          </button>
        ))}
        <span className="text-textSecondary text-xs ml-2">
          {formatDate(period.from)} → {formatDate(period.to)} GMT
        </span>

        {/* Custom Period Popup */}
        {isCustomOpen && (
          <div className="absolute top-full mt-2 right-0 bg-surface border border-border rounded-lg p-4 shadow-lg z-50">
            <div className="flex flex-col gap-3">
              <div>
                <label className="block text-xs text-textSecondary mb-1">From</label>
                <input
                  type="date"
                  value={customFrom}
                  onChange={(e) => setCustomFrom(e.target.value)}
                  className="bg-background border border-border rounded px-3 py-1.5 text-textPrimary text-sm focus:outline-none focus:border-neutral"
                />
              </div>
              <div>
                <label className="block text-xs text-textSecondary mb-1">To</label>
                <input
                  type="date"
                  value={customTo}
                  onChange={(e) => setCustomTo(e.target.value)}
                  className="bg-background border border-border rounded px-3 py-1.5 text-textPrimary text-sm focus:outline-none focus:border-neutral"
                />
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setIsCustomOpen(false)}
                  className="flex-1 px-3 py-1.5 text-sm bg-surfaceHover text-textSecondary rounded hover:bg-border transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCustomApply}
                  className="flex-1 px-3 py-1.5 text-sm bg-neutral text-white rounded hover:bg-neutral/80 transition-colors"
                >
                  Apply
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Sync Status & Actions */}
      <div className="flex items-center gap-3">
        <div
          className={`flex items-center gap-2 px-3 py-1 rounded text-xs ${
            syncStatus === "idle"
              ? "bg-positive/20 text-positive"
              : "bg-warning/20 text-warning"
          }`}
        >
          <span
            className={`w-2 h-2 rounded-full ${
              syncStatus === "idle" ? "bg-positive" : "bg-warning animate-pulse"
            }`}
          />
          {getSyncLabel()}
        </div>
        <button
          onClick={onSyncHistory}
          disabled={syncStatus !== "idle"}
          className={`px-3 py-1 text-sm rounded transition-colors ${
            syncStatus === "idle"
              ? "bg-neutral text-white hover:bg-neutral/80"
              : "bg-surfaceHover text-textSecondary cursor-not-allowed"
          }`}
        >
          Sync History
        </button>
        <button
          onClick={onSettingsClick}
          className="px-3 py-1 text-sm bg-surfaceHover text-textSecondary rounded hover:bg-border transition-colors"
          title="Settings"
        >
          ⚙️
        </button>
      </div>
    </div>
  );
}
