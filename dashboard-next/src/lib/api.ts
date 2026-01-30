import { Account, Magic, MagicGroup, OpenPositionsSummary, Deal } from "@/types/dashboard";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

// Chart Editor Types
export type ChartSection = {
  id: number;
  folder_name: string;
  validation_line1: string;
  validation_line2: string | null;
  param_key: string;
  param_value: string;
  order_index: number;
};

export type ChartSectionCreate = {
  folder_name: string;
  validation_line1: string;
  validation_line2?: string | null;
  param_key: string;
  param_value: string;
};

export type ChartSectionUpdate = {
  validation_line1?: string;
  validation_line2?: string | null;
  param_key?: string;
  param_value?: string;
};

export type ChartValidateRequest = {
  folder_name: string;
  validation_line1: string;
  validation_line2?: string | null;
  param_key: string;
};

export type ChartValidationResult = {
  matched_files: string[];
  matched_file: string | null;
  needs_second_validation: boolean;
  param_found: boolean;
  current_value: string | null;
  status: "ok" | "multiple_files" | "no_match" | "param_not_found" | "error";
};

export type ChartWriteResult = {
  status: "ok" | "error";
  message: string;
  file?: string;
};

export type ChartFolderWriteResult = {
  status: "ok" | "partial";
  success_count: number;
  error_count: number;
  results: Array<{
    section_id: number;
    param_key: string;
    status: string;
    message: string;
    file?: string;
  }>;
};

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `API error: ${res.status}`);
  }
  return res.json();
}

export type SyncResponse = {
  status: "ok" | "needs_credentials";
  account_id?: string;
  new_deals_total?: number;
  new_deals_by_magic?: { magic: number; label: string; count: number }[];
};
export type ActiveAccountResponse = { active: boolean; account_id?: string; server?: string };

export const api = {
  listAccounts: () => apiFetch<Account[]>("/accounts"),
  getActiveAccount: () => apiFetch<ActiveAccountResponse>("/terminal/active"),
  listMagics: (accountId: string) => apiFetch<Magic[]>(`/magics?account_id=${accountId}`),
  listGroups: (accountId: string) => apiFetch<MagicGroup[]>(`/groups?account_id=${accountId}`),
  openPositions: (accountId: string) => apiFetch<OpenPositionsSummary>(`/open-positions?account_id=${accountId}`),
  aggregates: (accountId: string, from: string, to: string) =>
    apiFetch<{ period_profit: number; period_percent: number; by_magic: { magic: number; profit: number }[]; by_group: { group_id: number; profit: number }[] }>(
      `/aggregates?account_id=${accountId}&from_date=${encodeURIComponent(from)}&to_date=${encodeURIComponent(to)}`
    ),
  deals: (accountId: string, from: string, to: string) =>
    apiFetch<Deal[]>(
      `/deals?account_id=${accountId}&from_date=${encodeURIComponent(from)}&to_date=${encodeURIComponent(to)}`
    ),
  syncOpen: (payload: { account_id?: string; use_active?: boolean }) =>
    apiFetch<SyncResponse>("/sync/open", { method: "POST", body: JSON.stringify(payload) }),
  syncHistory: (payload: { account_id?: string; use_active?: boolean; from_date?: string; to_date?: string }) =>
    apiFetch<SyncResponse>("/sync/history", { method: "POST", body: JSON.stringify(payload) }),
  saveCredentials: (accountId: string, payload: { login: string; server: string; password: string }) =>
    apiFetch<{ status: string }>(`/accounts/${accountId}/credentials`, { method: "POST", body: JSON.stringify(payload) }),
  updateAccountLabel: (accountId: string, label: string) =>
    apiFetch<{ status: string }>(`/accounts/${accountId}/label`, { method: "POST", body: JSON.stringify({ label }) }),
  updateHistoryStart: (accountId: string, history_start_date: string | null) =>
    apiFetch<{ status: string }>(`/accounts/${accountId}/history-start`, {
      method: "POST",
      body: JSON.stringify({ history_start_date }),
    }),
  updateMagicLabels: (accountId: string, labels: { magic: number; label: string }[]) =>
    apiFetch<{ status: string }>("/magics/labels", { method: "POST", body: JSON.stringify({ account_id: accountId, labels }) }),
  createGroup: (
    accountId: string,
    name: string,
    label2?: string | null,
    font_color?: string | null,
    fill_color?: string | null
  ) =>
    apiFetch<{
      group_id: number;
      account_id: string;
      name: string;
      label2?: string | null;
      font_color?: string | null;
      fill_color?: string | null;
    }>(
      "/groups",
      { method: "POST", body: JSON.stringify({ account_id: accountId, name, label2, font_color, fill_color }) }
    ),
  renameGroup: (groupId: number, name?: string, label2?: string | null, font_color?: string | null, fill_color?: string | null) =>
    apiFetch<{ status: string }>(
      `/groups/${groupId}`,
      { method: "PUT", body: JSON.stringify({ name, label2, font_color, fill_color }) }
    ),
  deleteGroup: (groupId: number, accountId: string) =>
    apiFetch<{ status: string }>(`/groups/${groupId}?account_id=${accountId}`, { method: "DELETE" }),
  updateGroupAssignments: (groupId: number, accountId: string, magic_ids: number[]) =>
    apiFetch<{ status: string }>(`/groups/${groupId}/assignments`, {
      method: "POST",
      body: JSON.stringify({ account_id: accountId, magic_ids }),
    }),

  // Chart Editor API
  getChartsConfig: () =>
    apiFetch<{ id: number; charts_path: string }>("/charts/config"),
  updateChartsPath: (charts_path: string) =>
    apiFetch<{ id: number; charts_path: string }>("/charts/config", {
      method: "PUT",
      body: JSON.stringify({ charts_path }),
    }),
  listChartFolders: () => apiFetch<string[]>("/charts/folders"),
  listChartSections: (folder_name?: string) =>
    apiFetch<ChartSection[]>(
      folder_name ? `/charts/sections?folder_name=${encodeURIComponent(folder_name)}` : "/charts/sections"
    ),
  createChartSection: (data: ChartSectionCreate) =>
    apiFetch<ChartSection>("/charts/sections", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateChartSection: (sectionId: number, data: ChartSectionUpdate) =>
    apiFetch<ChartSection>(`/charts/sections/${sectionId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  deleteChartSection: (sectionId: number) =>
    apiFetch<{ status: string }>(`/charts/sections/${sectionId}`, { method: "DELETE" }),
  validateChartSection: (data: ChartValidateRequest) =>
    apiFetch<ChartValidationResult>("/charts/validate", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  writeChartSection: (sectionId: number) =>
    apiFetch<ChartWriteResult>(`/charts/write/${sectionId}`, { method: "POST" }),
  writeChartFolder: (folderName: string) =>
    apiFetch<ChartFolderWriteResult>(`/charts/write-folder/${encodeURIComponent(folderName)}`, {
      method: "POST",
    }),
};
