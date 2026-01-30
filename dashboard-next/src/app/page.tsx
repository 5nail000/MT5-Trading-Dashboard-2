"use client";

import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import html2canvas from "html2canvas";
import { LayoutMargins, Period, MagicGroup, Magic, Account, AccountAggregate, OpenPositionsSummary, Deal } from "@/types/dashboard";
import { dashboardConfig } from "@/config/dashboard";
import { api, SyncResponse } from "@/lib/api";
import TopBar from "@/components/TopBar";
import OpenPositionsBar from "@/components/OpenPositionsBar";
import MainResults from "@/components/MainResults";
import Filters from "@/components/Filters";
import SidePanel from "@/components/SidePanel";
import OpenPositionsModal from "@/components/OpenPositionsModal";
import MagicDealsModal from "@/components/MagicDealsModal";
import SettingsDialog from "@/components/SettingsDialog";
import LabelsDialog from "@/components/LabelsDialog";
import GroupsDialog from "@/components/GroupsDialog";

// Local storage key
const STATE_KEY = "mt5_dashboard_state";

interface AccountViewState {
  selectedGroupIds: number[];
  selectedMagicIds: number[];
  viewMode: "grouped" | "individual";
  margins: LayoutMargins;
  sortBy: "value" | "alpha" | "magic";
  sortOrder: "asc" | "desc";
  customPeriod: { from: string; to: string } | null;
  selectedPeriodKey: string;
  groupedGroupIds?: number[];
}

interface SavedState {
  selectedAccountId: string;
  viewsByAccount: Record<string, AccountViewState>;
  accountLabels: Record<string, string>;
  magicLabelsByAccount: Record<string, Record<number, string>>;
}

const defaultView: AccountViewState = {
  selectedGroupIds: [],
  selectedMagicIds: [],
  viewMode: "grouped",
  margins: dashboardConfig.layout.margins,
  sortBy: "value",
  sortOrder: "desc",
  customPeriod: null,
  selectedPeriodKey: "month",
  groupedGroupIds: [],
};

const defaultState: SavedState = {
  selectedAccountId: "",
  viewsByAccount: {},
  accountLabels: {},
  magicLabelsByAccount: {},
};

export default function Home() {
  // Use default state initially to avoid hydration mismatch
  const [state, setState] = useState<SavedState>(defaultState);
  const [isHydrated, setIsHydrated] = useState(false);
  const [syncStatus, setSyncStatus] = useState<"idle" | "syncing_open" | "syncing_history">("idle");
  const [isOpenPosModalOpen, setIsOpenPosModalOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isLabelsOpen, setIsLabelsOpen] = useState(false);
  const [isGroupsOpen, setIsGroupsOpen] = useState(false);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [magicsData, setMagicsData] = useState<Magic[]>([]);
  const [groupsData, setGroupsData] = useState<MagicGroup[]>([]);
  const [openPosSummary, setOpenPosSummary] = useState<OpenPositionsSummary | undefined>(undefined);
  const [accountAggregate, setAccountAggregate] = useState<AccountAggregate | undefined>(undefined);
  const [syncChoice, setSyncChoice] = useState<{ activeAccountId: string } | null>(null);
  const [credDialog, setCredDialog] = useState<{ accountId: string; login: string; server: string; password: string } | null>(null);
  const [pendingSync, setPendingSync] = useState<{ accountId: string; useActive: boolean } | null>(null);
  const [syncToast, setSyncToast] = useState<{ title: string; details?: string } | null>(null);
  const [magicDealsModal, setMagicDealsModal] = useState<{ title: string; magicIds: number[] } | null>(null);
  const [magicDeals, setMagicDeals] = useState<Deal[]>([]);
  const [isMagicDealsLoading, setIsMagicDealsLoading] = useState(false);
  const syncInFlightRef = useRef(false);
  const credPromptedRef = useRef(false);
  const toastTimerRef = useRef<number | null>(null);

  const showSyncToast = useCallback((response: SyncResponse) => {
    if (response.status !== "ok") return;
    const byMagic = response.new_deals_by_magic ?? [];
    const total =
      response.new_deals_total ??
      byMagic.reduce((sum, item) => sum + item.count, 0);
    const details =
      total > 0 && byMagic.length > 0
        ? `От: ${byMagic.map((item) => `${item.label} (${item.count})`).join(", ")}`
        : undefined;
    const title =
      total === 0 ? "Синхронизация: без изменений" : `Синхронизация: +${total} сделок`;

    setSyncToast({ title, details });
    if (toastTimerRef.current) {
      window.clearTimeout(toastTimerRef.current);
    }
    toastTimerRef.current = window.setTimeout(() => setSyncToast(null), 4000);
  }, []);

  useEffect(() => {
    return () => {
      if (toastTimerRef.current) {
        window.clearTimeout(toastTimerRef.current);
      }
    };
  }, []);

  // Load state from localStorage after hydration
  useEffect(() => {
    const saved = localStorage.getItem(STATE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed.viewsByAccount) {
          const normalizedViews: Record<string, AccountViewState> = {};
          Object.entries(parsed.viewsByAccount).forEach(([accountId, view]) => {
            const viewObj = view as Partial<AccountViewState>;
            normalizedViews[accountId] = {
              ...defaultView,
              ...viewObj,
              groupedGroupIds: viewObj.groupedGroupIds,
            };
          });
          const merged: SavedState = {
            ...defaultState,
            ...parsed,
            accountLabels: parsed.accountLabels || {},
            magicLabelsByAccount: parsed.magicLabelsByAccount || {},
            viewsByAccount: normalizedViews,
          };
          setState(merged);
        } else {
          const selectedAccountId = parsed.selectedAccountId || "";
          const legacyView: AccountViewState = {
            selectedGroupIds: parsed.selectedGroupIds || [],
            selectedMagicIds: parsed.selectedMagicIds || [],
            viewMode: parsed.viewMode || defaultView.viewMode,
            margins: parsed.margins || defaultView.margins,
            sortBy: parsed.sortBy || defaultView.sortBy,
            sortOrder: parsed.sortOrder || defaultView.sortOrder,
            customPeriod: parsed.customPeriod || null,
            selectedPeriodKey: parsed.selectedPeriodKey || defaultView.selectedPeriodKey,
            groupedGroupIds: undefined,
          };
          const magicLabelsByAccount: Record<string, Record<number, string>> = {};
          if (selectedAccountId && parsed.magicLabels) {
            magicLabelsByAccount[selectedAccountId] = parsed.magicLabels;
          }
          setState({
            selectedAccountId,
            viewsByAccount: selectedAccountId ? { [selectedAccountId]: legacyView } : {},
            accountLabels: parsed.accountLabels || {},
            magicLabelsByAccount,
          });
        }
      } catch {
        // Invalid JSON, keep defaults
      }
    }
    setIsHydrated(true);
  }, []);

  // Auto-save state to localStorage (only after hydration)
  useEffect(() => {
    if (isHydrated) {
      localStorage.setItem(STATE_KEY, JSON.stringify(state));
    }
  }, [state, isHydrated]);

  // Helper to update state
  const updateState = useCallback((updates: Partial<SavedState>) => {
    setState((prev) => ({ ...prev, ...updates }));
  }, []);

  const currentView = useMemo(() => {
    if (!state.selectedAccountId) {
      return defaultView;
    }
    return state.viewsByAccount[state.selectedAccountId] || defaultView;
  }, [state.selectedAccountId, state.viewsByAccount]);

  const updateView = useCallback((accountId: string, updates: Partial<AccountViewState>) => {
    setState((prev) => {
      const existing = prev.viewsByAccount[accountId] || defaultView;
      const next = { ...existing, ...updates };
      const existingGrouped = existing.groupedGroupIds || [];
      const nextGrouped = next.groupedGroupIds || [];
      const isSame =
        existing.selectedGroupIds.join(",") === next.selectedGroupIds.join(",") &&
        existing.selectedMagicIds.join(",") === next.selectedMagicIds.join(",") &&
        existingGrouped.join(",") === nextGrouped.join(",") &&
        existing.viewMode === next.viewMode &&
        existing.sortBy === next.sortBy &&
        existing.sortOrder === next.sortOrder &&
        existing.selectedPeriodKey === next.selectedPeriodKey &&
        JSON.stringify(existing.customPeriod) === JSON.stringify(next.customPeriod) &&
        existing.margins.left === next.margins.left &&
        existing.margins.right === next.margins.right &&
        existing.margins.top === next.margins.top &&
        existing.margins.bottom === next.margins.bottom &&
        existingGrouped.join(",") === nextGrouped.join(",");
      if (isSame) {
        return prev;
      }
      return {
        ...prev,
        viewsByAccount: {
          ...prev.viewsByAccount,
          [accountId]: next,
        },
      };
    });
  }, []);

  // Derived data
  const accountGroups = groupsData.filter(
    (g) => g.account_id === state.selectedAccountId
  );
  const accountMagics = magicsData.filter(
    (m) => m.account_id === state.selectedAccountId
  );
  const currentMagicLabels =
    state.magicLabelsByAccount[state.selectedAccountId] || {};

  const activeMagicIdSet = useMemo(() => {
    if (!accountAggregate) return new Set<number>();
    return new Set(accountAggregate.by_magic.map((m) => m.magic));
  }, [accountAggregate]);

  const activeMagics = useMemo(
    () => accountMagics.filter((m) => activeMagicIdSet.has(m.magic)),
    [accountMagics, activeMagicIdSet]
  );

  const activeGroupIds = useMemo(() => {
    const ids = new Set<number>();
    accountMagics.forEach((magic) => {
      if (!activeMagicIdSet.has(magic.magic)) return;
      (magic.group_ids || []).forEach((gid) => ids.add(gid));
    });
    return ids;
  }, [accountMagics, activeMagicIdSet]);

  const activeGroups = useMemo(
    () => accountGroups.filter((g) => activeGroupIds.has(g.group_id)),
    [accountGroups, activeGroupIds]
  );

  const buildPeriod = useCallback((key: string, custom?: { from: string; to: string } | null): Period => {
    const toGmtIso = (date: Date) => {
      const offsetMs = date.getTimezoneOffset() * 60000;
      return new Date(date.getTime() - offsetMs).toISOString();
    };
    if (custom) {
      const fromDate = new Date(`${custom.from}T00:00:00`);
      const toDate = new Date(`${custom.to}T00:00:00`);
      return {
        from: toGmtIso(fromDate),
        to: toGmtIso(toDate),
        label: "custom",
      };
    }
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    let from = today;
    let to = now;
    if (key === "today") {
      to = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
    } else if (key === "last3days") {
      from = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 2);
      to = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
    } else if (key === "week") {
      const day = now.getDay() || 7;
      from = new Date(now.getFullYear(), now.getMonth(), now.getDate() - day + 1);
    } else if (key === "month") {
      from = new Date(now.getFullYear(), now.getMonth(), 1);
    } else if (key === "year") {
      from = new Date(now.getFullYear(), 0, 1);
    }
    return {
      from: toGmtIso(from),
      to: toGmtIso(to),
      label: key,
    };
  }, []);

  const [period, setPeriod] = useState<Period>(() =>
    buildPeriod(defaultView.selectedPeriodKey, defaultView.customPeriod)
  );

  useEffect(() => {
    setPeriod(buildPeriod(currentView.selectedPeriodKey, currentView.customPeriod));
  }, [buildPeriod, currentView.customPeriod, currentView.selectedPeriodKey]);

  const handleMagicDealsClick = useCallback(
    async (payload: { label: string; magicIds: number[] }) => {
      if (!payload.magicIds.length) {
        return;
      }
      setMagicDealsModal({ title: payload.label, magicIds: payload.magicIds });
      setIsMagicDealsLoading(true);
      try {
        const deals = (await api.deals(state.selectedAccountId, period.from, period.to)) as Deal[];
        const magicSet = new Set(payload.magicIds);
        const filtered = deals.filter((deal) => magicSet.has(deal.magic));
        setMagicDeals(filtered);
      } finally {
        setIsMagicDealsLoading(false);
      }
    },
    [period.from, period.to, state.selectedAccountId]
  );

  const loadAccounts = useCallback(async () => {
    let data = (await api.listAccounts()) as Account[];
    if (data.length === 0) {
      setSyncStatus("syncing_open");
      await api.syncOpen({ use_active: true });
      data = (await api.listAccounts()) as Account[];
      setSyncStatus("idle");
    }
    setAccounts(data);
    return data;
  }, []);

  const loadAccountData = useCallback(async (accountId: string) => {
    const [magics, groups, summary, aggregates] = (await Promise.all([
      api.listMagics(accountId),
      api.listGroups(accountId),
      api.openPositions(accountId),
      api.aggregates(accountId, period.from, period.to),
    ])) as [
      Magic[],
      MagicGroup[],
      OpenPositionsSummary,
      { period_profit: number; period_percent: number; by_magic: { magic: number; profit: number }[]; by_group: { group_id: number; profit: number }[] }
    ];

    setMagicsData(magics);
    setGroupsData(groups);
    setOpenPosSummary(summary);
    setAccountAggregate({
      account_id: accountId,
      period_profit: aggregates.period_profit,
      period_percent: aggregates.period_percent,
      by_magic: aggregates.by_magic,
      by_group: aggregates.by_group,
    });

    const activeMagicIds = new Set(aggregates.by_magic.map((m) => m.magic));
    const activeGroupIds = new Set<number>();
    magics.forEach((magic) => {
      if (!activeMagicIds.has(magic.magic)) return;
      (magic.group_ids || []).forEach((gid) => activeGroupIds.add(gid));
    });

    const existingGroupIds = new Set(groups.map((g: MagicGroup) => g.group_id));
    const existingMagicIds = new Set(magics.map((m: Magic) => m.magic));

    const hasView = Boolean(state.viewsByAccount[accountId]);
    const view = state.viewsByAccount[accountId] || defaultView;
    const rawGroupedIds = hasView
      ? view.groupedGroupIds ??
        (view.viewMode === "grouped" ? groups.map((g) => g.group_id) : [])
      : view.viewMode === "grouped"
        ? groups.map((g) => g.group_id)
        : [];
    const filteredGroupedIds = rawGroupedIds.filter(
      (id) => existingGroupIds.has(id) && activeGroupIds.has(id)
    );
    const filteredGroupIds = view.selectedGroupIds.filter(
      (id) => existingGroupIds.has(id) && activeGroupIds.has(id)
    );
    const filteredMagicIds = view.selectedMagicIds.filter(
      (id) => existingMagicIds.has(id) && activeMagicIds.has(id)
    );
    const defaultMagicIds = magics
      .filter((m) => activeMagicIds.has(m.magic))
      .map((m) => m.magic);
    const defaultGroupIds = Array.from(activeGroupIds);
    
    // If all previously selected items became inactive but there ARE active items,
    // reset to show all active items (useful when switching periods)
    const shouldResetMagics = filteredMagicIds.length === 0 && defaultMagicIds.length > 0;
    const shouldResetGroups = filteredGroupIds.length === 0 && defaultGroupIds.length > 0;
    
    const nextMagicIds = filteredMagicIds.length > 0 
      ? filteredMagicIds 
      : shouldResetMagics ? defaultMagicIds : [];
    const nextGroupIds = filteredGroupIds.length > 0 
      ? filteredGroupIds 
      : shouldResetGroups ? defaultGroupIds : [];
    const hasChanges =
      filteredGroupedIds.join(",") !== (view.groupedGroupIds || []).join(",") ||
      nextGroupIds.join(",") !== view.selectedGroupIds.join(",") ||
      nextMagicIds.join(",") !== view.selectedMagicIds.join(",");
    if (hasChanges) {
      updateView(accountId, {
        groupedGroupIds: filteredGroupedIds,
        selectedGroupIds: nextGroupIds,
        selectedMagicIds: nextMagicIds,
      });
    }
  }, [period.from, period.to, state.viewsByAccount, updateView]);

  useEffect(() => {
    if (!isHydrated) return;
    loadAccounts().then((data) => {
      const selected =
        data.find((a: Account) => a.account_id === state.selectedAccountId)?.account_id ||
        data[0]?.account_id ||
        "";
      if (selected && selected !== state.selectedAccountId) {
        updateState({ selectedAccountId: selected });
      }
      if (selected) {
        loadAccountData(selected);
      }
    });
  }, [isHydrated, loadAccounts, loadAccountData, state.selectedAccountId, updateState]);

  useEffect(() => {
    if (!state.selectedAccountId) return;
    loadAccountData(state.selectedAccountId);
  }, [period.from, period.to, state.selectedAccountId, loadAccountData]);

  // Handlers
  const handleAccountChange = (accountId: string) => {
    updateState({
      selectedAccountId: accountId,
    });
    if (!state.viewsByAccount[accountId]) {
      const newGroups = groupsData
        .filter((g) => g.account_id === accountId)
        .map((g) => g.group_id);
      const newMagics = magicsData
        .filter((m) => m.account_id === accountId)
        .map((m) => m.magic);
      updateView(accountId, {
        selectedGroupIds: newGroups,
        selectedMagicIds: newMagics,
      });
    }
    loadAccountData(accountId);
  };

  const runSyncHistory = async (accountId: string, useActive: boolean) => {
    if (syncInFlightRef.current) return;
    syncInFlightRef.current = true;
    try {
      setSyncStatus("syncing_history");
      const response = (await api.syncHistory({
        account_id: useActive ? undefined : accountId,
        use_active: useActive,
        from_date: period.from,
        to_date: period.to,
      })) as SyncResponse;
      if (response.status === "needs_credentials") {
        if (!credPromptedRef.current) {
          credPromptedRef.current = true;
          setPendingSync({ accountId, useActive });
          // Get server from account info if available
          const account = accounts.find((a) => a.account_id === accountId);
          setCredDialog({
            accountId,
            login: accountId,
            server: account?.account_info.server || "",
            password: "",
          });
        }
        setSyncStatus("idle");
        return;
      }
      credPromptedRef.current = false;
      await api.syncOpen({
        account_id: useActive ? undefined : accountId,
        use_active: useActive,
      });
      await loadAccounts();
      const targetAccountId = response.account_id || accountId;
      updateState({ selectedAccountId: targetAccountId });
      await loadAccountData(targetAccountId);
      showSyncToast(response);
    } finally {
      setSyncStatus("idle");
      syncInFlightRef.current = false;
    }
  };

  const handleSyncHistory = async () => {
    const active = (await api.getActiveAccount()) as { active: boolean; account_id?: string };
    if (active.active && active.account_id && active.account_id !== state.selectedAccountId) {
      setSyncChoice({ activeAccountId: active.account_id });
      return;
    }
    await runSyncHistory(state.selectedAccountId, false);
  };

  const handleLabelsClick = () => {
    setIsLabelsOpen(true);
  };

  const handleGroupsClick = () => {
    setIsGroupsOpen(true);
  };

  const handleLabelsSave = async (labels: Record<number, string>) => {
    updateState({
      magicLabelsByAccount: {
        ...state.magicLabelsByAccount,
        [state.selectedAccountId]: labels,
      },
    });
    const payload = Object.keys(labels).map((magic) => ({
      magic: Number(magic),
      label: labels[Number(magic)],
    }));
    await api.updateMagicLabels(state.selectedAccountId, payload);
    loadAccountData(state.selectedAccountId);
  };

  const handleGroupsSave = async (
    groups: typeof accountGroups,
    assignments: Record<number, number[]>
  ) => {
    const existingGroups = groupsData.filter((g) => g.account_id === state.selectedAccountId);
    const existingIds = new Set(existingGroups.map((g) => g.group_id));
    const newGroups = groups.filter((g) => !existingIds.has(g.group_id));
    const removedGroups = existingGroups.filter(
      (g) => !groups.find((candidate) => candidate.group_id === g.group_id)
    );

    const idMap = new Map<number, number>();
    for (const group of newGroups) {
      const created = (await api.createGroup(
        state.selectedAccountId,
        group.name,
        group.label2 || null,
        group.font_color ?? null,
        group.fill_color ?? null
      )) as {
        group_id: number;
        account_id: string;
        name: string;
        label2?: string | null;
        font_color?: string | null;
        fill_color?: string | null;
      };
      idMap.set(group.group_id, created.group_id);
    }

    for (const group of groups) {
      const existing = existingGroups.find((g) => g.group_id === group.group_id);
      const mappedId = idMap.get(group.group_id);
      if (mappedId) {
        continue;
      }
      if (
        existing &&
        (existing.name !== group.name ||
          (existing.label2 || "") !== (group.label2 || "") ||
          (existing.font_color || "") !== (group.font_color || "") ||
          (existing.fill_color || "") !== (group.fill_color || ""))
      ) {
        await api.renameGroup(
          group.group_id,
          group.name,
          group.label2 ?? null,
          group.font_color ?? null,
          group.fill_color ?? null
        );
      }
    }

    for (const group of removedGroups) {
      await api.deleteGroup(group.group_id, state.selectedAccountId);
    }

    const assignmentsByGroup: Record<number, number[]> = {};
    Object.entries(assignments).forEach(([magicKey, groupIds]) => {
      const magicId = Number(magicKey);
      groupIds.forEach((gid) => {
        const resolved = idMap.get(gid) || gid;
        assignmentsByGroup[resolved] = assignmentsByGroup[resolved] || [];
        assignmentsByGroup[resolved].push(magicId);
      });
    });

    for (const [groupId, magicIds] of Object.entries(assignmentsByGroup)) {
      await api.updateGroupAssignments(Number(groupId), state.selectedAccountId, magicIds);
    }

    loadAccountData(state.selectedAccountId);
  };

  const handleCopyLabelsFromAccount = useCallback(
    async (sourceAccountId: string) => {
      if (!sourceAccountId || sourceAccountId === state.selectedAccountId) {
        return;
      }
      const sourceMagics = (await api.listMagics(sourceAccountId)) as Magic[];
      const labels: Record<number, string> = {};
      sourceMagics.forEach((magic) => {
        labels[magic.magic] = magic.label || `Magic ${magic.magic}`;
      });
      updateState({
        magicLabelsByAccount: {
          ...state.magicLabelsByAccount,
          [state.selectedAccountId]: labels,
        },
      });
      const payload = Object.keys(labels).map((magic) => ({
        magic: Number(magic),
        label: labels[Number(magic)],
      }));
      await api.updateMagicLabels(state.selectedAccountId, payload);
      loadAccountData(state.selectedAccountId);
    },
    [loadAccountData, state.magicLabelsByAccount, state.selectedAccountId, updateState]
  );

  const handleCopyGroupsFromAccount = useCallback(
    async (sourceAccountId: string) => {
      if (!sourceAccountId || sourceAccountId === state.selectedAccountId) {
        return;
      }
      const [sourceGroups, sourceMagics, targetGroups, targetMagics] = (await Promise.all([
        api.listGroups(sourceAccountId),
        api.listMagics(sourceAccountId),
        api.listGroups(state.selectedAccountId),
        api.listMagics(state.selectedAccountId),
      ])) as [MagicGroup[], Magic[], MagicGroup[], Magic[]];

      for (const group of targetGroups) {
        await api.deleteGroup(group.group_id, state.selectedAccountId);
      }

      const idMap = new Map<number, number>();
      for (const group of sourceGroups) {
        const created = (await api.createGroup(
          state.selectedAccountId,
          group.name,
          group.label2 || null,
          group.font_color ?? null,
          group.fill_color ?? null
        )) as {
          group_id: number;
          account_id: string;
          name: string;
          label2?: string | null;
          font_color?: string | null;
          fill_color?: string | null;
        };
        idMap.set(group.group_id, created.group_id);
      }

      const targetMagicIds = new Set(targetMagics.map((magic) => magic.magic));
      const assignmentsByGroup: Record<number, number[]> = {};
      sourceMagics.forEach((magic) => {
        if (!targetMagicIds.has(magic.magic)) {
          return;
        }
        (magic.group_ids || []).forEach((groupId) => {
          const resolved = idMap.get(groupId);
          if (!resolved) {
            return;
          }
          assignmentsByGroup[resolved] = assignmentsByGroup[resolved] || [];
          assignmentsByGroup[resolved].push(magic.magic);
        });
      });

      for (const [groupId, magicIds] of Object.entries(assignmentsByGroup)) {
        await api.updateGroupAssignments(Number(groupId), state.selectedAccountId, magicIds);
      }

      loadAccountData(state.selectedAccountId);
    },
    [loadAccountData, state.selectedAccountId]
  );

  const handleDealsClick = () => {
    window.open("/deals", "_blank");
  };

  const handleBalanceChartClick = () => {
    window.open("/balance-chart", "_blank");
  };

  const handleChartsClick = () => {
    window.open("/create-charts", "_blank");
  };

  const handleSettingsClick = () => {
    setIsSettingsOpen(true);
  };

  const handleSettingsSave = async (
    newMargins: LayoutMargins,
    accountLabel: string,
    historyStartDate: string | null,
    password?: string
  ) => {
    updateView(state.selectedAccountId, { margins: newMargins });
    updateState({
      accountLabels: {
        ...state.accountLabels,
        [state.selectedAccountId]: accountLabel,
      },
    });
    await api.updateAccountLabel(state.selectedAccountId, accountLabel);
    await api.updateHistoryStart(state.selectedAccountId, historyStartDate);
    
    // Save password if provided
    if (password) {
      const account = accounts.find((a) => a.account_id === state.selectedAccountId);
      const server = account?.account_info.server || "";
      await api.saveCredentials(state.selectedAccountId, {
        login: state.selectedAccountId,
        server,
        password,
      });
    }
    
    loadAccounts();
    loadAccountData(state.selectedAccountId);
  };

  const handlePeriodChange = (periodKey: string, customFrom?: string, customTo?: string) => {
    if (periodKey === "custom" && customFrom && customTo) {
      updateView(state.selectedAccountId, {
        selectedPeriodKey: "custom",
        customPeriod: { from: customFrom, to: customTo },
      });
    } else {
      updateView(state.selectedAccountId, {
        selectedPeriodKey: periodKey,
        customPeriod: null,
      });
    }
  };

  const handleSortChange = (sortBy: "value" | "alpha" | "magic", sortOrder: "asc" | "desc") => {
    updateView(state.selectedAccountId, { sortBy, sortOrder });
  };

  const handleGroupSelectionChange = (ids: number[]) => {
    updateView(state.selectedAccountId, { selectedGroupIds: ids });
  };

  const handleMagicSelectionChange = (ids: number[]) => {
    updateView(state.selectedAccountId, { selectedMagicIds: ids });
  };

  const handleViewModeChange = (mode: "grouped" | "individual") => {
    const nextGrouped =
      mode === "grouped" ? activeGroups.map((g) => g.group_id) : [];
    updateView(state.selectedAccountId, { viewMode: mode, groupedGroupIds: nextGrouped });
  };

  const handleToggleGroupAggregate = (groupId: number) => {
    const current = currentView.groupedGroupIds || [];
    const next = current.includes(groupId)
      ? current.filter((id) => id !== groupId)
      : [...current, groupId];
    updateView(state.selectedAccountId, { groupedGroupIds: next });
  };

  const handleScreenshot = async (element: HTMLDivElement | null) => {
    if (!element) return;
    const computedBg = getComputedStyle(element).backgroundColor;
    const bgColor =
      computedBg && computedBg !== "rgba(0, 0, 0, 0)" && computedBg !== "transparent"
        ? computedBg
        : "#0b0f14";

    const rect = element.getBoundingClientRect();
    const clone = element.cloneNode(true) as HTMLDivElement;

    // Create an offscreen container to avoid scroll/transform issues
    const container = document.createElement("div");
    container.style.position = "fixed";
    container.style.left = "0";
    container.style.top = "0";
    container.style.width = `${rect.width}px`;
    container.style.height = `${rect.height}px`;
    container.style.background = bgColor;
    container.style.zIndex = "-1";
    container.style.overflow = "hidden";
    container.style.pointerEvents = "none";

    clone.style.width = `${rect.width}px`;
    clone.style.height = `${rect.height}px`;
    clone.style.margin = "0";
    clone.style.transform = "none";

    container.appendChild(clone);
    document.body.appendChild(container);

    const canvas = await html2canvas(container, {
      backgroundColor: bgColor,
      scale: 1,
      scrollX: 0,
      scrollY: 0,
      x: 0,
      y: 0,
      width: rect.width,
      height: rect.height,
      windowWidth: rect.width,
      windowHeight: rect.height,
    });

    document.body.removeChild(container);
    const link = document.createElement("a");
    link.href = canvas.toDataURL("image/png");
    link.download = `dashboard_${state.selectedAccountId}_${new Date().toISOString().slice(0, 10)}.png`;
    link.click();
  };

  // Get account label (custom or default)
  const getAccountLabel = (accountId: string) => {
    return (
      state.accountLabels[accountId] ||
      accounts.find((a) => a.account_id === accountId)?.label ||
      accountId
    );
  };

  // Apply margins
  const marginStyle = {
    paddingLeft: `${currentView.margins.left}%`,
    paddingRight: `${currentView.margins.right}%`,
    paddingTop: `${currentView.margins.top}%`,
    paddingBottom: `${currentView.margins.bottom}%`,
  };

  return (
    <div className="flex flex-col h-screen">
      {/* TopBar */}
      <TopBar
        accounts={accounts}
        selectedAccountId={state.selectedAccountId}
        onAccountChange={handleAccountChange}
        period={period}
        syncStatus={syncStatus}
        onSyncHistory={handleSyncHistory}
        selectedPeriodKey={currentView.selectedPeriodKey}
        onPeriodChange={handlePeriodChange}
        getAccountLabel={getAccountLabel}
        onSettingsClick={handleSettingsClick}
        viewMode={currentView.viewMode}
        onViewModeChange={handleViewModeChange}
      />

      {syncToast && (
        <div className="fixed right-6 top-20 z-50 bg-surface border border-border text-textPrimary text-sm rounded-lg shadow-lg px-4 py-3">
          <div className="font-medium">{syncToast.title}</div>
          {syncToast.details && (
            <div className="text-xs text-textSecondary mt-1">{syncToast.details}</div>
          )}
        </div>
      )}

      {/* Main container with margins */}
      <div className="flex-1 flex flex-col overflow-hidden" style={marginStyle}>
        {/* OpenPositionsBar */}
        <OpenPositionsBar
          summary={openPosSummary}
          config={dashboardConfig.open_positions_bar}
          onBarClick={() => setIsOpenPosModalOpen(true)}
        />

        {/* Main content area */}
        <div className="flex flex-1 overflow-hidden">
          {/* MainResults */}
          <MainResults
            accountAggregate={accountAggregate}
            groups={activeGroups}
            magics={activeMagics}
            magicLabels={currentMagicLabels}
            selectedMagicIds={currentView.selectedMagicIds}
            groupedGroupIds={currentView.groupedGroupIds || []}
            period={period}
            onScreenshot={handleScreenshot}
            sortBy={currentView.sortBy}
            sortOrder={currentView.sortOrder}
            onSortChange={handleSortChange}
            onItemClick={handleMagicDealsClick}
          />

          {/* SidePanel */}
          <SidePanel
            groups={activeGroups}
            magics={activeMagics}
            selectedMagicIds={currentView.selectedMagicIds}
            groupedGroupIds={currentView.groupedGroupIds || []}
            onToggleGroupAggregate={handleToggleGroupAggregate}
            onLabelsClick={handleLabelsClick}
            onGroupsClick={handleGroupsClick}
            onDealsClick={handleDealsClick}
            onBalanceChartClick={handleBalanceChartClick}
            onChartsClick={handleChartsClick}
          />
        </div>

        {/* Filters (variant A) */}
        <Filters
          groups={activeGroups}
          magics={activeMagics}
          magicLabels={currentMagicLabels}
          selectedGroupIds={currentView.selectedGroupIds}
          selectedMagicIds={currentView.selectedMagicIds}
          onGroupSelectionChange={handleGroupSelectionChange}
          onMagicSelectionChange={handleMagicSelectionChange}
        />
      </div>

      {/* Open Positions Modal */}
      {isOpenPosModalOpen && (
        <OpenPositionsModal
          summary={openPosSummary}
          magics={accountMagics}
          groups={accountGroups}
          onClose={() => setIsOpenPosModalOpen(false)}
        />
      )}

      {/* Settings Dialog */}
      {isSettingsOpen && (
        <SettingsDialog
          margins={currentView.margins}
          accountLabel={getAccountLabel(state.selectedAccountId)}
          historyStartDate={
            accounts.find((a) => a.account_id === state.selectedAccountId)
              ?.history_start_date || null
          }
          accountServer={
            accounts.find((a) => a.account_id === state.selectedAccountId)
              ?.account_info.server || ""
          }
          onSave={handleSettingsSave}
          onClose={() => setIsSettingsOpen(false)}
        />
      )}

      {/* Labels Dialog */}
      {isLabelsOpen && (
        <LabelsDialog
          magics={accountMagics}
          magicLabels={currentMagicLabels}
          accounts={accounts}
          currentAccountId={state.selectedAccountId}
          onSave={handleLabelsSave}
          onCopyFromAccount={handleCopyLabelsFromAccount}
          onClose={() => setIsLabelsOpen(false)}
        />
      )}

      {/* Groups Dialog */}
      {isGroupsOpen && (
        <GroupsDialog
          groups={accountGroups}
          magics={accountMagics}
          onSave={handleGroupsSave}
          accounts={accounts}
          currentAccountId={state.selectedAccountId}
          onCopyFromAccount={handleCopyGroupsFromAccount}
          onClose={() => setIsGroupsOpen(false)}
        />
      )}

      {magicDealsModal && (
        <MagicDealsModal
          title={magicDealsModal.title}
          deals={magicDeals}
          isLoading={isMagicDealsLoading}
          onClose={() => setMagicDealsModal(null)}
        />
      )}

      {/* Sync choice dialog */}
      {syncChoice && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-surface border border-border rounded-lg shadow-2xl w-[480px] p-5">
            <div className="text-lg font-semibold text-textPrimary mb-2">Sync account mismatch</div>
            <div className="text-sm text-textSecondary mb-4">
              Active terminal account differs from selected. Which one to sync?
            </div>
            <div className="flex gap-2">
              <button
                onClick={async () => {
                  setSyncChoice(null);
                  await runSyncHistory(state.selectedAccountId, false);
                }}
                className="flex-1 px-3 py-2 text-sm bg-neutral text-white rounded hover:bg-neutral/80 transition-colors"
              >
                <div className="font-medium">Selected</div>
                <div className="text-xs opacity-80">
                  {getAccountLabel(state.selectedAccountId)} ({state.selectedAccountId})
                </div>
              </button>
              <button
                onClick={async () => {
                  setSyncChoice(null);
                  await runSyncHistory(syncChoice.activeAccountId, true);
                }}
                className="flex-1 px-3 py-2 text-sm bg-surfaceHover text-textSecondary rounded hover:bg-border transition-colors"
              >
                <div className="font-medium">Active terminal</div>
                <div className="text-xs opacity-80">
                  {accounts.find((a) => a.account_id === syncChoice.activeAccountId)?.label || "Unknown"} ({syncChoice.activeAccountId})
                </div>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Credentials dialog */}
      {credDialog && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-surface border border-border rounded-lg shadow-2xl w-[420px] p-5">
            <div className="text-lg font-semibold text-textPrimary mb-3">Account credentials</div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-textSecondary mb-1">Login</label>
                <input
                  className="w-full bg-background border border-border rounded px-3 py-2 text-sm text-textPrimary"
                  value={credDialog.login}
                  onChange={(e) => setCredDialog({ ...credDialog, login: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-xs text-textSecondary mb-1">Server</label>
                <input
                  className="w-full bg-background border border-border rounded px-3 py-2 text-sm text-textPrimary"
                  value={credDialog.server}
                  onChange={(e) => setCredDialog({ ...credDialog, server: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-xs text-textSecondary mb-1">Password</label>
                <input
                  type="password"
                  className="w-full bg-background border border-border rounded px-3 py-2 text-sm text-textPrimary"
                  value={credDialog.password}
                  onChange={(e) => setCredDialog({ ...credDialog, password: e.target.value })}
                />
              </div>
            </div>
            <div className="flex gap-2 mt-4">
              <button
                onClick={() => {
                  credPromptedRef.current = false;
                  setCredDialog(null);
                }}
                className="flex-1 px-3 py-2 text-sm bg-surfaceHover text-textSecondary rounded hover:bg-border transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  if (!credDialog) return;
                  await api.saveCredentials(credDialog.accountId, {
                    login: credDialog.login,
                    server: credDialog.server,
                    password: credDialog.password,
                  });
                  const pending = pendingSync;
                  credPromptedRef.current = false;
                  setCredDialog(null);
                  if (pending) {
                    setPendingSync(null);
                    await runSyncHistory(pending.accountId, pending.useActive);
                  }
                }}
                className="flex-1 px-3 py-2 text-sm bg-neutral text-white rounded hover:bg-neutral/80 transition-colors"
              >
                Save & Sync
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
