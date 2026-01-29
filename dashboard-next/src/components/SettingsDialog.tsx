"use client";

import { useState } from "react";
import { LayoutMargins } from "@/types/dashboard";

interface SettingsDialogProps {
  margins: LayoutMargins;
  accountLabel: string;
  historyStartDate: string | null;
  accountServer: string;
  onSave: (margins: LayoutMargins, accountLabel: string, historyStartDate: string | null, password?: string) => void;
  onClose: () => void;
}

export default function SettingsDialog({
  margins,
  accountLabel,
  historyStartDate,
  accountServer,
  onSave,
  onClose,
}: SettingsDialogProps) {
  const [tempMargins, setTempMargins] = useState<LayoutMargins>(margins);
  const [tempLabel, setTempLabel] = useState(accountLabel);
  const [tempHistoryStart, setTempHistoryStart] = useState(historyStartDate || "");
  const [tempPassword, setTempPassword] = useState("");

  const handleSave = () => {
    onSave(tempMargins, tempLabel, tempHistoryStart || null, tempPassword || undefined);
    onClose();
  };

  return (
    <div
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-surface border border-border rounded-lg p-6 w-[400px] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-textPrimary">Settings</h3>
          <button
            onClick={onClose}
            className="text-textSecondary hover:text-textPrimary transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Account Label */}
        <div className="mb-6">
          <label className="block text-sm text-textSecondary mb-2">
            Account Label
          </label>
          <input
            type="text"
            value={tempLabel}
            onChange={(e) => setTempLabel(e.target.value)}
            className="w-full bg-background border border-border rounded px-3 py-2 text-textPrimary text-sm focus:outline-none focus:border-neutral"
            placeholder="Enter account label"
          />
        </div>

        {/* MT5 Password */}
        <div className="mb-6">
          <label className="block text-sm text-textSecondary mb-2">
            MT5 Password
          </label>
          <div className="text-xs text-textSecondary mb-2">
            Server: <span className="text-textPrimary">{accountServer || "—"}</span>
          </div>
          <input
            type="password"
            value={tempPassword}
            onChange={(e) => setTempPassword(e.target.value)}
            className="w-full bg-background border border-border rounded px-3 py-2 text-textPrimary text-sm focus:outline-none focus:border-neutral"
            placeholder="Оставьте пустым, если не менять"
          />
        </div>

        {/* Layout Margins */}
        <div className="mb-6">
          <label className="block text-sm text-textSecondary mb-3">
            Layout Margins (%)
          </label>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-textSecondary mb-1">Left</label>
              <input
                type="number"
                min="0"
                max="30"
                value={tempMargins.left}
                onChange={(e) =>
                  setTempMargins({ ...tempMargins, left: Number(e.target.value) })
                }
                className="w-full bg-background border border-border rounded px-3 py-2 text-textPrimary text-sm focus:outline-none focus:border-neutral"
              />
            </div>
            <div>
              <label className="block text-xs text-textSecondary mb-1">Right</label>
              <input
                type="number"
                min="0"
                max="30"
                value={tempMargins.right}
                onChange={(e) =>
                  setTempMargins({ ...tempMargins, right: Number(e.target.value) })
                }
                className="w-full bg-background border border-border rounded px-3 py-2 text-textPrimary text-sm focus:outline-none focus:border-neutral"
              />
            </div>
            <div>
              <label className="block text-xs text-textSecondary mb-1">Top</label>
              <input
                type="number"
                min="0"
                max="30"
                value={tempMargins.top}
                onChange={(e) =>
                  setTempMargins({ ...tempMargins, top: Number(e.target.value) })
                }
                className="w-full bg-background border border-border rounded px-3 py-2 text-textPrimary text-sm focus:outline-none focus:border-neutral"
              />
            </div>
            <div>
              <label className="block text-xs text-textSecondary mb-1">Bottom</label>
              <input
                type="number"
                min="0"
                max="30"
                value={tempMargins.bottom}
                onChange={(e) =>
                  setTempMargins({ ...tempMargins, bottom: Number(e.target.value) })
                }
                className="w-full bg-background border border-border rounded px-3 py-2 text-textPrimary text-sm focus:outline-none focus:border-neutral"
              />
            </div>
          </div>
        </div>

        {/* History window */}
        <div className="mb-6">
          <label className="block text-sm text-textSecondary mb-2">
            History start date
          </label>
          <input
            type="date"
            value={tempHistoryStart}
            onChange={(e) => setTempHistoryStart(e.target.value)}
            className="w-full bg-background border border-border rounded px-3 py-2 text-textPrimary text-sm focus:outline-none focus:border-neutral"
          />
          <div className="text-xs text-textSecondary mt-2">
            Если не задано, берётся окно за последний месяц
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm bg-surfaceHover text-textSecondary rounded hover:bg-border transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 text-sm bg-neutral text-white rounded hover:bg-neutral/80 transition-colors"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
