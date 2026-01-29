"use client";

import { useState, useMemo } from "react";
import { Account, Magic, MagicGroup } from "@/types/dashboard";

interface GroupsDialogProps {
  groups: MagicGroup[];
  magics: Magic[];
  onSave: (groups: MagicGroup[], magicGroupAssignments: Record<number, number[]>) => void;
  accounts: Account[];
  currentAccountId: string;
  onCopyFromAccount: (sourceAccountId: string) => void;
  onClose: () => void;
}

export default function GroupsDialog({
  groups,
  magics,
  onSave,
  accounts,
  currentAccountId,
  onCopyFromAccount,
  onClose,
}: GroupsDialogProps) {
  const [tempGroups, setTempGroups] = useState<MagicGroup[]>(groups);
  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(
    groups.length > 0 ? groups[0].group_id : null
  );
  const [editingGroupId, setEditingGroupId] = useState<number | null>(null);
  const [newGroupName, setNewGroupName] = useState("");
  const [isCreatingGroup, setIsCreatingGroup] = useState(false);
  const donorAccounts = useMemo(
    () => accounts.filter((acc) => acc.account_id !== currentAccountId),
    [accounts, currentAccountId]
  );
  const [donorAccountId, setDonorAccountId] = useState(
    donorAccounts[0]?.account_id || ""
  );

  // Track magic-to-groups assignments
  const [magicAssignments, setMagicAssignments] = useState<Record<number, number[]>>(() => {
    const assignments: Record<number, number[]> = {};
    magics.forEach((m) => {
      assignments[m.magic] = [...m.group_ids];
    });
    return assignments;
  });

  // Sort groups alphabetically
  const sortedGroups = useMemo(() => {
    return [...tempGroups].sort((a, b) => a.name.localeCompare(b.name));
  }, [tempGroups]);

  // Sort magics by number ascending
  const sortedMagics = useMemo(() => {
    return [...magics].sort((a, b) => a.magic - b.magic);
  }, [magics]);

  // Get magics for selected group
  const selectedGroupMagics = useMemo(() => {
    if (!selectedGroupId) return [];
    return magics.filter((m) =>
      magicAssignments[m.magic]?.includes(selectedGroupId)
    );
  }, [selectedGroupId, magics, magicAssignments]);

  // Get magics not in selected group
  const unassignedMagics = useMemo(() => {
    if (!selectedGroupId) return magics;
    return magics.filter(
      (m) => !magicAssignments[m.magic]?.includes(selectedGroupId)
    );
  }, [selectedGroupId, magics, magicAssignments]);

  const handleRenameGroup = (groupId: number, newName: string) => {
    setTempGroups(
      tempGroups.map((g) =>
        g.group_id === groupId ? { ...g, name: newName } : g
      )
    );
    setEditingGroupId(null);
  };

  const handleLabel2Change = (groupId: number, value: string) => {
    setTempGroups(
      tempGroups.map((g) =>
        g.group_id === groupId ? { ...g, label2: value } : g
      )
    );
  };

  const handleGroupColorChange = (groupId: number, key: "font_color" | "fill_color", value: string) => {
    setTempGroups(
      tempGroups.map((g) =>
        g.group_id === groupId ? { ...g, [key]: value } : g
      )
    );
  };

  const handleResetGroupColors = (groupId: number) => {
    setTempGroups(
      tempGroups.map((g) =>
        g.group_id === groupId ? { ...g, font_color: "", fill_color: "" } : g
      )
    );
  };

  const handleDeleteGroup = (groupId: number) => {
    setTempGroups(tempGroups.filter((g) => g.group_id !== groupId));
    // Remove group from all magic assignments
    const newAssignments = { ...magicAssignments };
    Object.keys(newAssignments).forEach((magicKey) => {
      const magicNum = parseInt(magicKey);
      newAssignments[magicNum] = newAssignments[magicNum].filter(
        (gid) => gid !== groupId
      );
    });
    setMagicAssignments(newAssignments);
    if (selectedGroupId === groupId) {
      setSelectedGroupId(tempGroups.length > 1 ? tempGroups[0].group_id : null);
    }
  };

  const handleCreateGroup = () => {
    if (!newGroupName.trim()) return;
    const newId = Math.max(...tempGroups.map((g) => g.group_id), 0) + 1;
    const accountId = groups.length > 0 ? groups[0].account_id : "";
    setTempGroups([
      ...tempGroups,
      {
        group_id: newId,
        account_id: accountId,
        name: newGroupName.trim(),
        label2: "",
        font_color: "",
        fill_color: "",
      },
    ]);
    setNewGroupName("");
    setIsCreatingGroup(false);
    setSelectedGroupId(newId);
  };

  const handleToggleMagicInGroup = (magicNum: number, groupId: number) => {
    const currentGroups = magicAssignments[magicNum] || [];
    if (currentGroups.includes(groupId)) {
      // Remove from group
      setMagicAssignments({
        ...magicAssignments,
        [magicNum]: currentGroups.filter((gid) => gid !== groupId),
      });
    } else {
      // Add to group
      setMagicAssignments({
        ...magicAssignments,
        [magicNum]: [...currentGroups, groupId],
      });
    }
  };

  const handleSave = () => {
    onSave(tempGroups, magicAssignments);
    onClose();
  };

  return (
    <div
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-surface border border-border rounded-lg shadow-2xl w-[700px] max-h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 border-b border-border flex items-center justify-between">
          <h3 className="text-lg font-semibold text-textPrimary">Magic Groups</h3>
          <div className="flex items-center gap-2">
            {donorAccounts.length > 0 && (
              <>
                <select
                  value={donorAccountId}
                  onChange={(e) => setDonorAccountId(e.target.value)}
                  className="bg-background border border-border rounded px-2 py-1 text-textPrimary text-xs focus:outline-none focus:border-neutral"
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
              </>
            )}
            <button
              onClick={onClose}
              className="text-textSecondary hover:text-textPrimary transition-colors"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Groups list */}
          <div className="w-1/3 border-r border-border p-4 flex flex-col">
            <div className="text-xs text-textSecondary uppercase tracking-wider mb-2">
              Groups
            </div>
            <div className="flex-1 overflow-y-auto space-y-1">
              {sortedGroups.map((group) => {
                const isSelected = selectedGroupId === group.group_id;
                const isEditing = editingGroupId === group.group_id;

                return (
                  <div
                    key={group.group_id}
                    className={`flex items-center gap-2 p-2 rounded cursor-pointer transition-colors ${
                      isSelected ? "bg-neutral/30" : "hover:bg-surfaceHover"
                    }`}
                    onClick={() => !isEditing && setSelectedGroupId(group.group_id)}
                  >
                    {isEditing ? (
                      <input
                        type="text"
                        defaultValue={group.name}
                        onBlur={(e) => handleRenameGroup(group.group_id, e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            handleRenameGroup(group.group_id, e.currentTarget.value);
                          }
                          if (e.key === "Escape") setEditingGroupId(null);
                        }}
                        autoFocus
                        className="flex-1 bg-background border border-neutral rounded px-2 py-0.5 text-textPrimary text-sm focus:outline-none"
                        onClick={(e) => e.stopPropagation()}
                      />
                    ) : (
                      <>
                        <span className="flex-1 text-sm text-textPrimary truncate">
                          {group.name}
                        </span>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setEditingGroupId(group.group_id);
                          }}
                          className="text-xs text-textSecondary hover:text-textPrimary"
                          title="Rename"
                        >
                          ✏️
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteGroup(group.group_id);
                          }}
                          className="text-xs text-textSecondary hover:text-negative"
                          title="Delete"
                        >
                          🗑️
                        </button>
                      </>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Create new group */}
            {isCreatingGroup ? (
              <div className="mt-2 flex gap-2">
                <input
                  type="text"
                  placeholder="Group name"
                  value={newGroupName}
                  onChange={(e) => setNewGroupName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleCreateGroup();
                    if (e.key === "Escape") setIsCreatingGroup(false);
                  }}
                  autoFocus
                  className="flex-1 bg-background border border-border rounded px-2 py-1 text-textPrimary text-sm focus:outline-none focus:border-neutral"
                />
                <button
                  onClick={handleCreateGroup}
                  className="px-2 py-1 text-xs bg-positive text-white rounded hover:bg-positive/80"
                >
                  ✓
                </button>
              </div>
            ) : (
              <button
                onClick={() => setIsCreatingGroup(true)}
                className="mt-2 px-3 py-2 text-sm bg-surfaceHover text-textSecondary rounded hover:bg-border transition-colors w-full text-left"
              >
                + Create new group
              </button>
            )}
          </div>

          {/* Assignments */}
          <div className="flex-1 p-4 flex flex-col">
            <div className="text-xs text-textSecondary uppercase tracking-wider mb-2">
              {selectedGroupId
                ? `Magics in "${tempGroups.find((g) => g.group_id === selectedGroupId)?.name}"`
                : "Select a group"}
            </div>

            {selectedGroupId && (
            <div className="flex-1 overflow-y-auto">
              <div className="mb-3">
                <div className="text-xs text-textSecondary mb-1">
                  Group label 2 (номер/код)
                </div>
                <input
                  type="text"
                  value={tempGroups.find((g) => g.group_id === selectedGroupId)?.label2 || ""}
                  onChange={(e) => handleLabel2Change(selectedGroupId, e.target.value)}
                  placeholder="Напр. 101"
                  className="w-full bg-background border border-border rounded px-2 py-1 text-textPrimary text-sm focus:outline-none focus:border-neutral"
                />
              </div>
                <div className="mb-3 grid grid-cols-2 gap-3">
                  <div>
                    <div className="text-xs text-textSecondary mb-1">Цвет шрифта</div>
                    <input
                      type="color"
                      value={tempGroups.find((g) => g.group_id === selectedGroupId)?.font_color || "#e5e7eb"}
                      onChange={(e) => handleGroupColorChange(selectedGroupId, "font_color", e.target.value)}
                      className="w-full h-8 bg-background border border-border rounded"
                    />
                  </div>
                  <div>
                    <div className="text-xs text-textSecondary mb-1">Цвет заливки</div>
                    <input
                      type="color"
                      value={tempGroups.find((g) => g.group_id === selectedGroupId)?.fill_color || "#0b0f14"}
                      onChange={(e) => handleGroupColorChange(selectedGroupId, "fill_color", e.target.value)}
                      className="w-full h-8 bg-background border border-border rounded"
                    />
                  </div>
                </div>
                <div className="mb-3">
                  <button
                    onClick={() => handleResetGroupColors(selectedGroupId)}
                    className="px-3 py-1 text-xs bg-surfaceHover text-textSecondary rounded hover:bg-border transition-colors"
                  >
                    Сбросить цвета
                  </button>
                </div>
                <div className="space-y-1">
                  {sortedMagics.map((magic) => {
                    const isInGroup = magicAssignments[magic.magic]?.includes(selectedGroupId);
                    return (
                      <label
                        key={magic.magic}
                        className="flex items-center gap-3 p-2 rounded hover:bg-surfaceHover cursor-pointer transition-colors"
                      >
                        <input
                          type="checkbox"
                          checked={isInGroup}
                          onChange={() => handleToggleMagicInGroup(magic.magic, selectedGroupId)}
                          className="w-4 h-4 accent-neutral"
                        />
                        <span className="w-12 text-xs text-textSecondary font-mono">
                          #{magic.magic}
                        </span>
                        <span className="text-sm text-textPrimary">{magic.label}</span>
                      </label>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
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
