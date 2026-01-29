"use client";

import { useState, useMemo } from "react";
import { MagicGroup, Magic } from "@/types/dashboard";

interface FiltersProps {
  groups: MagicGroup[];
  magics: Magic[];
  magicLabels: Record<number, string>;
  selectedGroupIds: number[];
  selectedMagicIds: number[];
  onGroupSelectionChange: (ids: number[]) => void;
  onMagicSelectionChange: (ids: number[]) => void;
}

export default function Filters({
  groups,
  magics,
  magicLabels,
  selectedGroupIds,
  selectedMagicIds,
  onGroupSelectionChange,
  onMagicSelectionChange,
}: FiltersProps) {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [tempGroupSelection, setTempGroupSelection] = useState<number[]>(selectedGroupIds);
  const [tempMagicSelection, setTempMagicSelection] = useState<number[]>(selectedMagicIds);

  // Sort groups alphabetically
  const sortedGroups = useMemo(() => {
    return [...groups].sort((a, b) => a.name.localeCompare(b.name));
  }, [groups]);

  const getMagicLabel = (magicNum: number) => {
    if (magicLabels[magicNum]) return magicLabels[magicNum];
    const m = magics.find((mg) => mg.magic === magicNum);
    return m?.label ?? `Magic ${magicNum}`;
  };

  const sortedMagics = useMemo(() => {
    return [...magics].sort((a, b) => a.magic - b.magic);
  }, [magics]);

  const groupToMagics = useMemo(() => {
    const map = new Map<number, number[]>();
    magics.forEach((magic) => {
      (magic.group_ids || []).forEach((groupId) => {
        const existing = map.get(groupId) || [];
        existing.push(magic.magic);
        map.set(groupId, existing);
      });
    });
    return map;
  }, [magics]);

  const handleShowAll = () => {
    onGroupSelectionChange(groups.map((g) => g.group_id));
    onMagicSelectionChange(magics.map((m) => m.magic));
  };

  const handleHideAll = () => {
    onGroupSelectionChange([]);
    onMagicSelectionChange([]);
  };

  const openDialog = () => {
    setTempGroupSelection(selectedGroupIds);
    setTempMagicSelection(selectedMagicIds);
    setIsDialogOpen(true);
  };

  const closeDialog = () => {
    setIsDialogOpen(false);
  };

  const saveDialog = () => {
    onGroupSelectionChange(tempGroupSelection);
    onMagicSelectionChange(tempMagicSelection);
    setIsDialogOpen(false);
  };

  const toggleGroup = (groupId: number) => {
    const groupMagics = groupToMagics.get(groupId) || [];
    if (tempGroupSelection.includes(groupId)) {
      setTempGroupSelection(tempGroupSelection.filter((id) => id !== groupId));
      if (groupMagics.length > 0) {
        setTempMagicSelection(
          tempMagicSelection.filter((id) => !groupMagics.includes(id))
        );
      }
    } else {
      setTempGroupSelection([...tempGroupSelection, groupId]);
      if (groupMagics.length > 0) {
        const merged = new Set([...tempMagicSelection, ...groupMagics]);
        setTempMagicSelection([...merged]);
      }
    }
  };

  const toggleMagic = (magicId: number) => {
    if (tempMagicSelection.includes(magicId)) {
      setTempMagicSelection(tempMagicSelection.filter((id) => id !== magicId));
    } else {
      setTempMagicSelection([...tempMagicSelection, magicId]);
    }
  };

  const handleDialogSelectAll = () => {
    setTempGroupSelection(groups.map((g) => g.group_id));
    setTempMagicSelection(magics.map((m) => m.magic));
  };

  const handleDialogDeselectAll = () => {
    setTempGroupSelection([]);
    setTempMagicSelection([]);
  };

  return (
    <>
      {/* Filter bar (variant A) */}
      <div className="flex items-center justify-between px-4 py-3 bg-surface border-t border-border">
        <div className="flex items-center gap-2">
          <button
            onClick={handleShowAll}
            className="px-3 py-1.5 text-sm bg-surfaceHover text-textSecondary rounded hover:bg-border transition-colors"
          >
            Show All
          </button>
          <button
            onClick={handleHideAll}
            className="px-3 py-1.5 text-sm bg-surfaceHover text-textSecondary rounded hover:bg-border transition-colors"
          >
            Hide All
          </button>
          <button
            onClick={openDialog}
            className="px-3 py-1.5 text-sm bg-neutral text-white rounded hover:bg-neutral/80 transition-colors"
          >
            Configure...
          </button>
        </div>
        <div className="text-sm text-textSecondary">
          {`Groups: ${selectedGroupIds.length} / ${groups.length} · Magics: ${selectedMagicIds.length} / ${magics.length}`}
        </div>
      </div>

      {/* Dialog overlay */}
      {isDialogOpen && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-surface border border-border rounded-lg shadow-2xl w-96 max-h-[80vh] flex flex-col">
            {/* Header */}
            <div className="p-4 border-b border-border flex items-center justify-between">
              <h3 className="text-lg font-semibold text-textPrimary">
                Configure Filters
              </h3>
              <div className="flex gap-2">
                <button
                  onClick={handleDialogSelectAll}
                  className="px-2 py-1 text-xs bg-surfaceHover text-textSecondary rounded hover:bg-border transition-colors"
                >
                  All
                </button>
                <button
                  onClick={handleDialogDeselectAll}
                  className="px-2 py-1 text-xs bg-surfaceHover text-textSecondary rounded hover:bg-border transition-colors"
                >
                  None
                </button>
              </div>
            </div>

            {/* Scrollable checkboxes - sorted alphabetically */}
            <div className="flex-1 overflow-y-auto p-4">
              <div className="space-y-2">
                <>
                  <div className="text-xs text-textSecondary uppercase tracking-wider px-1 pt-1">
                    Groups
                  </div>
                  {sortedGroups.map((group) => {
                    const isSelected = tempGroupSelection.includes(group.group_id);
                    return (
                      <label
                        key={group.group_id}
                        className="flex items-center gap-3 p-2 rounded hover:bg-surfaceHover cursor-pointer transition-colors"
                      >
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleGroup(group.group_id)}
                          className="w-4 h-4 accent-neutral"
                        />
                        <span className="text-textPrimary">{group.name}</span>
                      </label>
                    );
                  })}
                  <div className="text-xs text-textSecondary uppercase tracking-wider px-1 pt-3">
                    Magics
                  </div>
                </>

                {sortedMagics.map((magic) => {
                  const isSelected = tempMagicSelection.includes(magic.magic);
                  return (
                    <label
                      key={magic.magic}
                      className="flex items-center gap-3 p-2 rounded hover:bg-surfaceHover cursor-pointer transition-colors"
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleMagic(magic.magic)}
                        className="w-4 h-4 accent-neutral"
                      />
                      <span className="w-16 text-xs text-textSecondary font-mono">
                        #{magic.magic}
                      </span>
                      <span className="text-textPrimary">
                        {getMagicLabel(magic.magic)}
                      </span>
                    </label>
                  );
                })}
              </div>
            </div>

            {/* Fixed footer with actions */}
            <div className="p-4 border-t border-border flex justify-end gap-2">
              <button
                onClick={closeDialog}
                className="px-4 py-2 text-sm bg-surfaceHover text-textSecondary rounded hover:bg-border transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={saveDialog}
                className="px-4 py-2 text-sm bg-neutral text-white rounded hover:bg-neutral/80 transition-colors"
              >
                Apply
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
