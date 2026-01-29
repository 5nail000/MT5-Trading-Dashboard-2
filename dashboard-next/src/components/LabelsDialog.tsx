"use client";

import { useState, useMemo } from "react";
import { Account, Magic } from "@/types/dashboard";

interface LabelsDialogProps {
  magics: Magic[];
  magicLabels: Record<number, string>;
  accounts: Account[];
  currentAccountId: string;
  onSave: (labels: Record<number, string>) => void;
  onCopyFromAccount: (sourceAccountId: string) => void;
  onClose: () => void;
}

export default function LabelsDialog({
  magics,
  magicLabels,
  accounts,
  currentAccountId,
  onSave,
  onCopyFromAccount,
  onClose,
}: LabelsDialogProps) {
  const [tempLabels, setTempLabels] = useState<Record<number, string>>(magicLabels || {});
  const [searchQuery, setSearchQuery] = useState("");
  const [editingMagic, setEditingMagic] = useState<number | null>(null);
  const donorAccounts = useMemo(
    () => accounts.filter((acc) => acc.account_id !== currentAccountId),
    [accounts, currentAccountId]
  );
  const [donorAccountId, setDonorAccountId] = useState(
    donorAccounts[0]?.account_id || ""
  );

  // Filter magics by search
  const filteredMagics = useMemo(() => {
    if (!searchQuery) return magics;
    const query = searchQuery.toLowerCase();
    return magics.filter(
      (m) =>
        m.magic.toString().includes(query) ||
        m.label.toLowerCase().includes(query) ||
        (tempLabels[m.magic] || "").toLowerCase().includes(query)
    );
  }, [magics, searchQuery, tempLabels]);

  // Sort by magic number ascending
  const sortedMagics = useMemo(() => {
    return [...filteredMagics].sort((a, b) => a.magic - b.magic);
  }, [filteredMagics]);

  const getDisplayLabel = (magic: Magic) => {
    return tempLabels?.[magic.magic] || magic.label;
  };

  const handleLabelChange = (magicNum: number, newLabel: string) => {
    setTempLabels({ ...tempLabels, [magicNum]: newLabel });
  };

  const handleClear = (magicNum: number, defaultLabel: string) => {
    const newLabels = { ...tempLabels };
    delete newLabels[magicNum];
    setTempLabels(newLabels);
  };

  const handleSave = () => {
    onSave(tempLabels);
    onClose();
  };

  return (
    <div
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-surface border border-border rounded-lg shadow-2xl w-[500px] max-h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 border-b border-border">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold text-textPrimary">Magic Labels</h3>
            <button
              onClick={onClose}
              className="text-textSecondary hover:text-textPrimary transition-colors"
            >
              ✕
            </button>
          </div>
          <input
            type="text"
            placeholder="Search magics..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-background border border-border rounded px-3 py-2 text-textPrimary text-sm focus:outline-none focus:border-neutral"
          />
          {donorAccounts.length > 0 && (
            <div className="flex items-center gap-2 mt-3">
              <select
                value={donorAccountId}
                onChange={(e) => setDonorAccountId(e.target.value)}
                className="flex-1 bg-background border border-border rounded px-2 py-1 text-textPrimary text-xs focus:outline-none focus:border-neutral"
              >
                {donorAccounts.map((account) => (
                  <option key={account.account_id} value={account.account_id}>
                    {account.label} ({account.account_id})
                  </option>
                ))}
              </select>
              <button
                onClick={() => onCopyFromAccount(donorAccountId)}
                className="px-3 py-1 text-xs bg-surfaceHover text-textSecondary rounded hover:bg-border transition-colors"
                disabled={!donorAccountId}
              >
                Копировать
              </button>
            </div>
          )}
        </div>

        {/* Magic list - scrollable */}
        <div className="flex-1 overflow-y-auto p-4">
          <div className="space-y-2">
            {sortedMagics.map((magic) => {
              const isEditing = editingMagic === magic.magic;
              const displayLabel = getDisplayLabel(magic);
              const hasCustomLabel = tempLabels[magic.magic] !== undefined;

              return (
                <div
                  key={magic.magic}
                  className="flex items-center gap-3 p-2 rounded bg-surfaceHover hover:bg-border transition-colors"
                >
                  <div className="w-16 text-xs text-textSecondary font-mono">
                    #{magic.magic}
                  </div>

                  {isEditing ? (
                    <input
                      type="text"
                      value={displayLabel}
                      onChange={(e) => handleLabelChange(magic.magic, e.target.value)}
                      onBlur={() => setEditingMagic(null)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") setEditingMagic(null);
                        if (e.key === "Escape") setEditingMagic(null);
                      }}
                      autoFocus
                      className="flex-1 bg-background border border-neutral rounded px-2 py-1 text-textPrimary text-sm focus:outline-none"
                    />
                  ) : (
                    <div className="flex-1 text-sm text-textPrimary truncate">
                      {displayLabel}
                      {hasCustomLabel && (
                        <span className="ml-2 text-xs text-textSecondary">
                          (custom)
                        </span>
                      )}
                    </div>
                  )}

                  <button
                    onClick={() => setEditingMagic(magic.magic)}
                    className="px-2 py-1 text-xs bg-neutral text-white rounded hover:bg-neutral/80 transition-colors"
                  >
                    Rename
                  </button>
                  <button
                    onClick={() => handleClear(magic.magic, magic.label)}
                    disabled={!hasCustomLabel}
                    className={`px-2 py-1 text-xs rounded transition-colors ${
                      hasCustomLabel
                        ? "bg-surfaceHover text-textSecondary hover:bg-border"
                        : "bg-surfaceHover text-textSecondary/50 cursor-not-allowed"
                    }`}
                  >
                    Clear
                  </button>
                </div>
              );
            })}

            {sortedMagics.length === 0 && (
              <div className="text-center text-textSecondary py-8">
                No magics found
              </div>
            )}
          </div>
        </div>

        {/* Footer - fixed */}
        <div className="p-4 border-t border-border flex justify-end gap-2">
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
