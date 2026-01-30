"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  api,
  ChartSection,
  ChartValidationResult,
} from "@/lib/api";

// Temporary section for UI (not yet saved to DB)
interface TempSection {
  tempId: string;
  validation_line1: string;
  validation_line2: string;
  param_key: string;
  param_value: string;
}

// Validation state per section
interface ValidationState {
  [key: string]: ChartValidationResult | null;
}

// LocalStorage key for state persistence
const STORAGE_KEY = "create_charts_state";

interface PersistedState {
  chartsPath: string;
  tempSections: Record<string, TempSection[]>;
}

export default function CreateChartsPage() {
  const [chartsPath, setChartsPath] = useState("");
  const [pathInput, setPathInput] = useState("");
  const [folders, setFolders] = useState<string[]>([]);
  const [sections, setSections] = useState<Record<string, ChartSection[]>>({});
  const [tempSections, setTempSections] = useState<Record<string, TempSection[]>>({});
  const [validationState, setValidationState] = useState<Record<string, ValidationState>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [writeResults, setWriteResults] = useState<Record<string, string>>({});
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isInitializedRef = useRef(false);

  // Save state to localStorage
  const saveToStorage = useCallback((path: string, temps: Record<string, TempSection[]>) => {
    if (!isInitializedRef.current) return;
    const state: PersistedState = { chartsPath: path, tempSections: temps };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }, []);

  // Debounced save
  const debouncedSave = useCallback((path: string, temps: Record<string, TempSection[]>) => {
    if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
    saveTimeoutRef.current = setTimeout(() => saveToStorage(path, temps), 300);
  }, [saveToStorage]);

  // Load from localStorage
  const loadFromStorage = (): PersistedState | null => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) return JSON.parse(stored);
    } catch (e) {
      console.error("Failed to load from storage:", e);
    }
    return null;
  };

  // Load initial data
  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const config = await api.getChartsConfig();
      const storedState = loadFromStorage();
      
      const effectivePath = storedState?.chartsPath || config.charts_path;
      setChartsPath(effectivePath);
      setPathInput(effectivePath);

      const folderList = await api.listChartFolders();
      setFolders(folderList);

      // Load sections for each folder
      const allSections = await api.listChartSections();
      const grouped: Record<string, ChartSection[]> = {};
      const temps: Record<string, TempSection[]> = {};

      folderList.forEach((folder) => {
        grouped[folder] = allSections.filter((s) => s.folder_name === folder);
        // Restore temp sections from storage or create empty
        temps[folder] = storedState?.tempSections?.[folder]?.length 
          ? storedState.tempSections[folder]
          : [createEmptyTempSection()];
      });

      setSections(grouped);
      setTempSections(temps);
      isInitializedRef.current = true;

      // Validate all existing sections
      for (const folder of folderList) {
        for (const section of grouped[folder] || []) {
          validateSection(folder, section.id.toString(), section);
        }
        // Validate temp sections too
        for (const temp of temps[folder] || []) {
          if (temp.validation_line1) {
            validateSection(folder, temp.tempId, temp);
          }
        }
      }
    } catch (error) {
      console.error("Failed to load data:", error);
    }
    setIsLoading(false);
  };

  const createEmptyTempSection = (): TempSection => ({
    tempId: `temp-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    validation_line1: "",
    validation_line2: "",
    param_key: "",
    param_value: "",
  });

  // Normalize value: replace comma with dot only between digits (decimal separator)
  const normalizeValue = (value: string): string => {
    // Replace comma between digits: "0,02" → "0.02", "1,5" → "1.5"
    // But keep comma in text: "Hello, world" stays unchanged
    return value.replace(/(\d),(\d)/g, "$1.$2");
  };

  const handlePathApply = async () => {
    try {
      await api.updateChartsPath(pathInput);
      setChartsPath(pathInput);
      await loadData();
    } catch (error) {
      console.error("Failed to update path:", error);
    }
  };

  const validateSection = useCallback(
    async (
      folder: string,
      sectionKey: string,
      section: { validation_line1: string; validation_line2?: string; param_key: string }
    ) => {
      if (!section.validation_line1 || !section.param_key) {
        setValidationState((prev) => ({
          ...prev,
          [folder]: { ...prev[folder], [sectionKey]: null },
        }));
        return;
      }

      try {
        const result = await api.validateChartSection({
          folder_name: folder,
          validation_line1: section.validation_line1,
          validation_line2: section.validation_line2 || undefined,
          param_key: section.param_key,
        });

        setValidationState((prev) => ({
          ...prev,
          [folder]: { ...prev[folder], [sectionKey]: result },
        }));
      } catch (error) {
        console.error("Validation error:", error);
      }
    },
    []
  );

  const handleTempSectionChange = useCallback((
    folder: string,
    tempId: string,
    field: keyof TempSection,
    value: string
  ) => {
    setTempSections((prev) => {
      const updated = { ...prev };
      const sectionIndex = updated[folder]?.findIndex((s) => s.tempId === tempId);
      if (sectionIndex !== undefined && sectionIndex >= 0) {
        updated[folder] = [...updated[folder]];
        updated[folder][sectionIndex] = {
          ...updated[folder][sectionIndex],
          [field]: value,
        };
      }
      // Auto-save to localStorage
      debouncedSave(chartsPath, updated);
      return updated;
    });

    // Debounced validation
    setTempSections((prev) => {
      const section = prev[folder]?.find((s) => s.tempId === tempId);
      if (section) {
        const updatedSection = { ...section, [field]: value };
        setTimeout(() => {
          validateSection(folder, tempId, updatedSection);
        }, 300);
      }
      return prev;
    });
  }, [chartsPath, debouncedSave, validateSection]);

  const handleSavedSectionChange = async (
    folder: string,
    sectionId: number,
    field: keyof ChartSection,
    value: string
  ) => {
    // Update local state
    setSections((prev) => {
      const updated = { ...prev };
      const sectionIndex = updated[folder]?.findIndex((s) => s.id === sectionId);
      if (sectionIndex !== undefined && sectionIndex >= 0) {
        updated[folder] = [...updated[folder]];
        updated[folder][sectionIndex] = {
          ...updated[folder][sectionIndex],
          [field]: value,
        };
      }
      return updated;
    });

    // Update on server
    try {
      await api.updateChartSection(sectionId, { [field]: value });
    } catch (error) {
      console.error("Failed to update section:", error);
    }

    // Re-validate
    const section = sections[folder]?.find((s) => s.id === sectionId);
    if (section) {
      const updatedSection = { ...section, [field]: value };
      setTimeout(() => {
        validateSection(folder, sectionId.toString(), updatedSection);
      }, 300);
    }
  };

  const handleSaveTemp = async (folder: string, tempId: string) => {
    const temp = tempSections[folder]?.find((s) => s.tempId === tempId);
    if (!temp || !temp.validation_line1 || !temp.param_key || !temp.param_value) {
      return;
    }

    try {
      const created = await api.createChartSection({
        folder_name: folder,
        validation_line1: temp.validation_line1,
        validation_line2: temp.validation_line2 || undefined,
        param_key: temp.param_key,
        param_value: temp.param_value,
      });

      // Move from temp to saved
      setSections((prev) => ({
        ...prev,
        [folder]: [...(prev[folder] || []), created],
      }));

      // Replace temp with new empty one
      setTempSections((prev) => {
        const updated = {
          ...prev,
          [folder]: prev[folder]
            .filter((s) => s.tempId !== tempId)
            .concat([createEmptyTempSection()]),
        };
        debouncedSave(chartsPath, updated);
        return updated;
      });

      // Copy validation state
      setValidationState((prev) => ({
        ...prev,
        [folder]: {
          ...prev[folder],
          [created.id.toString()]: prev[folder]?.[tempId] || null,
        },
      }));

      // Validate new section
      await validateSection(folder, created.id.toString(), created);
    } catch (error) {
      console.error("Failed to save section:", error);
    }
  };

  const handleDeleteSection = async (folder: string, sectionId: number) => {
    try {
      await api.deleteChartSection(sectionId);
      setSections((prev) => ({
        ...prev,
        [folder]: prev[folder]?.filter((s) => s.id !== sectionId) || [],
      }));
    } catch (error) {
      console.error("Failed to delete section:", error);
    }
  };

  const handleDeleteTemp = (folder: string, tempId: string) => {
    setTempSections((prev) => {
      const remaining = prev[folder]?.filter((s) => s.tempId !== tempId) || [];
      // Always keep at least one empty section
      if (remaining.length === 0) {
        remaining.push(createEmptyTempSection());
      }
      const updated = { ...prev, [folder]: remaining };
      debouncedSave(chartsPath, updated);
      return updated;
    });
  };

  const handleWriteFolder = async (folder: string) => {
    setWriteResults((prev) => ({ ...prev, [folder]: "Writing..." }));
    try {
      const result = await api.writeChartFolder(folder);
      const message =
        result.status === "ok"
          ? `Success: ${result.success_count} sections written`
          : `Partial: ${result.success_count} success, ${result.error_count} errors`;
      setWriteResults((prev) => ({ ...prev, [folder]: message }));

      // Clear message after 5 seconds
      setTimeout(() => {
        setWriteResults((prev) => ({ ...prev, [folder]: "" }));
      }, 5000);

      // Re-validate all sections
      for (const section of sections[folder] || []) {
        await validateSection(folder, section.id.toString(), section);
      }
    } catch (error) {
      setWriteResults((prev) => ({ ...prev, [folder]: `Error: ${error}` }));
    }
  };

  const isSectionComplete = (validation: ChartValidationResult | null | undefined): boolean => {
    return validation?.status === "ok" && validation?.param_found === true;
  };

  const isSectionSameValue = (
    validation: ChartValidationResult | null | undefined,
    paramValue: string
  ): boolean => {
    return (
      validation?.status === "ok" &&
      validation?.current_value === paramValue
    );
  };

  // Validation Line 1 is green if file(s) found, yellow if multiple files need Line 2
  const getValidation1Class = (validation: ChartValidationResult | null | undefined): string => {
    if (!validation) return "border-gray-600";
    if (validation.status === "multiple_files" || validation.needs_second_validation) return "border-yellow-500";
    if (validation.matched_file || validation.matched_files?.length > 0) return "border-green-500";
    if (validation.status === "no_match") return "border-red-500";
    return "border-green-500"; // ok status
  };

  const getValidation2Class = (validation: ChartValidationResult | null | undefined): string => {
    if (!validation) return "border-gray-600";
    if (validation.matched_file) return "border-green-500";
    if (validation.matched_files?.length > 1) return "border-yellow-500";
    return "border-gray-600";
  };

  const getParamKeyClass = (validation: ChartValidationResult | null | undefined): string => {
    if (!validation) return "border-gray-600";
    if (validation.param_found) return "border-green-500";
    if (validation.matched_file && !validation.param_found) return "border-red-500";
    return "border-gray-600";
  };

  const showValidation2 = (validation: ChartValidationResult | null | undefined, line2: string | null): boolean => {
    return !!(validation?.needs_second_validation || validation?.matched_files?.length > 1 || line2);
  };

  const getSectionBgClass = (
    validation: ChartValidationResult | null | undefined,
    paramValue: string
  ): string => {
    if (isSectionSameValue(validation, paramValue)) {
      return "bg-yellow-900/30";
    }
    return "bg-gray-800";
  };

  const canWriteFolder = (folder: string): boolean => {
    const folderSections = sections[folder] || [];
    return folderSections.some((s) => {
      const validation = validationState[folder]?.[s.id.toString()];
      return isSectionComplete(validation);
    });
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 text-white p-4 flex items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  // Compact section renderer
  const renderSection = (
    folder: string,
    sectionKey: string,
    data: { validation_line1: string; validation_line2: string | null; param_key: string; param_value: string },
    validation: ChartValidationResult | null | undefined,
    isTemp: boolean,
    onUpdate: (field: string, value: string) => void,
    onDelete: () => void,
    onSave?: () => void
  ) => {
    const bgClass = !isTemp ? getSectionBgClass(validation, data.param_value) : "bg-gray-800/50";
    const borderClass = isTemp ? "border-dashed border-gray-600" : "border-gray-700";
    const isComplete = data.validation_line1 && data.param_key && data.param_value && isSectionComplete(validation);

    return (
      <div key={sectionKey} className={`px-3 py-2 rounded ${bgClass} border ${borderClass}`}>
        <div className="flex items-start gap-2">
          {/* Validation Line 1 */}
          <div className="flex-[2] min-w-0">
            <input
              type="text"
              value={data.validation_line1}
              onChange={(e) => onUpdate("validation_line1", e.target.value)}
              className={`w-full px-2 py-1 text-sm bg-gray-700 border-2 rounded ${getValidation1Class(validation)}`}
              placeholder="Validation Line 1"
            />
          </div>

          {/* Validation Line 2 - only show if needed */}
          {showValidation2(validation, data.validation_line2) && (
            <div className="flex-[2] min-w-0">
              <input
                type="text"
                value={data.validation_line2 || ""}
                onChange={(e) => onUpdate("validation_line2", e.target.value)}
                className={`w-full px-2 py-1 text-sm bg-gray-700 border-2 rounded ${getValidation2Class(validation)}`}
                placeholder="Validation Line 2"
              />
            </div>
          )}

          {/* Param Key */}
          <div className="flex-1 min-w-0">
            <input
              type="text"
              value={data.param_key}
              onChange={(e) => onUpdate("param_key", e.target.value)}
              className={`w-full px-2 py-1 text-sm bg-gray-700 border-2 rounded ${getParamKeyClass(validation)}`}
              placeholder="Param="
            />
          </div>

          {/* Value */}
          <div className="flex-1 min-w-0">
            <input
              type="text"
              value={data.param_value}
              onChange={(e) => onUpdate("param_value", normalizeValue(e.target.value))}
              className="w-full px-2 py-1 text-sm bg-gray-700 border border-gray-600 rounded"
              placeholder="Value"
            />
          </div>

          {/* File indicator */}
          <div className="w-24 text-xs truncate pt-1.5">
            {validation?.matched_file ? (
              <span className="text-green-400" title={validation.matched_file}>
                {validation.matched_file}
              </span>
            ) : validation?.matched_files?.length > 1 ? (
              <span className="text-yellow-400" title={validation.matched_files.join(", ")}>
                {validation.matched_files.length} files
              </span>
            ) : validation?.status === "no_match" ? (
              <span className="text-red-400">no match</span>
            ) : null}
          </div>

          {/* Current value indicator */}
          <div className="w-16 text-xs text-gray-400 truncate pt-1.5" title={validation?.current_value || ""}>
            {validation?.current_value && `(${validation.current_value})`}
          </div>

          {/* Actions */}
          <div className="flex gap-1">
            {isTemp && onSave && (
              <button
                onClick={onSave}
                disabled={!isComplete}
                className="px-2 py-1 text-xs text-green-400 hover:bg-green-900/30 rounded disabled:text-gray-600"
                title="Save"
              >
                ✓
              </button>
            )}
            <button
              onClick={onDelete}
              className="px-2 py-1 text-xs text-red-400 hover:bg-red-900/30 rounded"
              title="Delete"
            >
              ✕
            </button>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-4">
      <h1 className="text-xl font-bold mb-4">Create Charts - Parameter Editor</h1>

      {/* Path Configuration - compact */}
      <div className="mb-4 p-3 bg-gray-800 rounded-lg">
        <div className="flex gap-2 items-center">
          <span className="text-sm text-gray-400">Path:</span>
          <input
            type="text"
            value={pathInput}
            onChange={(e) => setPathInput(e.target.value)}
            className="flex-1 px-2 py-1 text-sm bg-gray-700 border border-gray-600 rounded text-white"
          />
          <button
            onClick={handlePathApply}
            disabled={pathInput === chartsPath}
            className="px-3 py-1 text-sm bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded"
          >
            Apply
          </button>
        </div>
      </div>

      {/* Folders/Panels */}
      {folders.length === 0 ? (
        <div className="text-center text-gray-400 py-4">No folders found</div>
      ) : (
        <div className="space-y-4">
          {folders.map((folder) => (
            <div key={folder} className="bg-gray-800 rounded-lg overflow-hidden">
              {/* Panel Header - compact */}
              <div className="px-3 py-2 bg-gray-700 border-b border-gray-600 flex justify-between items-center">
                <h2 className="font-semibold">{folder}</h2>
                <div className="flex items-center gap-2">
                  {writeResults[folder] && (
                    <span className={`text-xs ${
                      writeResults[folder].startsWith("Success") ? "text-green-400" :
                      writeResults[folder].startsWith("Error") ? "text-red-400" : "text-yellow-400"
                    }`}>
                      {writeResults[folder]}
                    </span>
                  )}
                  <button
                    onClick={() => handleWriteFolder(folder)}
                    disabled={!canWriteFolder(folder)}
                    className="px-3 py-1 text-sm bg-green-600 hover:bg-green-700 disabled:bg-gray-600 rounded"
                  >
                    Write
                  </button>
                </div>
              </div>

              {/* Sections - compact list */}
              <div className="p-2 space-y-1">
                {/* Column headers */}
                <div className="flex items-center gap-2 px-3 py-1 text-xs text-gray-500">
                  <div className="flex-[2]">Validation Line 1</div>
                  {(sections[folder] || []).some(s => showValidation2(validationState[folder]?.[s.id.toString()], s.validation_line2)) && (
                    <div className="flex-[2]">Validation Line 2</div>
                  )}
                  <div className="flex-1">Parameter</div>
                  <div className="flex-1">Value</div>
                  <div className="w-24">File</div>
                  <div className="w-16">Current</div>
                  <div className="w-14"></div>
                </div>

                {/* Saved Sections */}
                {(sections[folder] || []).map((section) =>
                  renderSection(
                    folder,
                    section.id.toString(),
                    section,
                    validationState[folder]?.[section.id.toString()],
                    false,
                    (field, value) => handleSavedSectionChange(folder, section.id, field as keyof ChartSection, value),
                    () => handleDeleteSection(folder, section.id)
                  )
                )}

                {/* Temp Sections */}
                {(tempSections[folder] || []).map((temp) =>
                  renderSection(
                    folder,
                    temp.tempId,
                    temp,
                    validationState[folder]?.[temp.tempId],
                    true,
                    (field, value) => handleTempSectionChange(folder, temp.tempId, field as keyof TempSection, value),
                    () => handleDeleteTemp(folder, temp.tempId),
                    () => handleSaveTemp(folder, temp.tempId)
                  )
                )}

                {/* Add button */}
                <button
                  onClick={() => setTempSections((prev) => {
                    const updated = {
                      ...prev,
                      [folder]: [...(prev[folder] || []), createEmptyTempSection()],
                    };
                    debouncedSave(chartsPath, updated);
                    return updated;
                  })}
                  className="w-full py-1 text-sm border border-dashed border-gray-600 rounded text-gray-400 hover:text-gray-300"
                >
                  + Add
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
