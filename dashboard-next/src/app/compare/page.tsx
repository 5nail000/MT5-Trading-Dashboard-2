"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import { Account, Magic, CompareResult, CompareDealPair } from "@/types/dashboard";
import { api } from "@/lib/api";

const periodPresets = ["today", "last3days", "week", "month", "year"];

const periodLabels: Record<string, string> = {
  today: "Today",
  last3days: "3 Days",
  week: "Week",
  month: "Month",
  year: "Year",
};

export default function ComparePage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [account1Id, setAccount1Id] = useState("");
  const [account2Id, setAccount2Id] = useState("");
  const [magics1, setMagics1] = useState<Magic[]>([]);
  const [magics2, setMagics2] = useState<Magic[]>([]);
  const [selectedMagic, setSelectedMagic] = useState<number | null>(null);
  const [periodKey, setPeriodKey] = useState("week");
  const [toleranceSeconds, setToleranceSeconds] = useState(1);
  const [compareResult, setCompareResult] = useState<CompareResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Build period from key
  const buildPeriod = useCallback((key: string): { from: string; to: string } => {
    const toGmtIso = (date: Date) => {
      const offsetMs = date.getTimezoneOffset() * 60000;
      return new Date(date.getTime() - offsetMs).toISOString();
    };
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

    return { from: toGmtIso(from), to: toGmtIso(to) };
  }, []);

  const period = useMemo(() => buildPeriod(periodKey), [buildPeriod, periodKey]);

  // Load accounts
  useEffect(() => {
    api.listAccounts().then((data) => {
      setAccounts(data);
      if (data.length >= 2) {
        setAccount1Id(data[0].account_id);
        setAccount2Id(data[1].account_id);
      } else if (data.length === 1) {
        setAccount1Id(data[0].account_id);
        setAccount2Id(data[0].account_id);
      }
    });
  }, []);

  // Load magics for both accounts
  useEffect(() => {
    if (account1Id) {
      api.listMagics(account1Id).then(setMagics1);
    }
  }, [account1Id]);

  useEffect(() => {
    if (account2Id) {
      api.listMagics(account2Id).then(setMagics2);
    }
  }, [account2Id]);

  // Get common magics between accounts
  const commonMagics = useMemo(() => {
    const magic1Ids = new Set(magics1.map((m) => m.magic));
    return magics2.filter((m) => magic1Ids.has(m.magic));
  }, [magics1, magics2]);

  // Load comparison data
  const loadComparison = useCallback(async () => {
    if (!account1Id || !account2Id || selectedMagic === null) {
      setCompareResult(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await api.compareDeals(
        account1Id,
        account2Id,
        selectedMagic,
        period.from,
        period.to,
        toleranceSeconds
      );
      setCompareResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load comparison");
      setCompareResult(null);
    } finally {
      setLoading(false);
    }
  }, [account1Id, account2Id, selectedMagic, period, toleranceSeconds]);

  // Auto-load when params change
  useEffect(() => {
    if (selectedMagic !== null) {
      loadComparison();
    }
  }, [loadComparison, selectedMagic]);

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "—";
    return new Date(dateStr).toLocaleString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  };

  const formatProfit = (val: number) =>
    val >= 0 ? `+$${val.toFixed(2)}` : `-$${Math.abs(val).toFixed(2)}`;

  const getAccountLabel = (id: string) => {
    const acc = accounts.find((a) => a.account_id === id);
    return acc?.label || id;
  };

  const getMagicLabel = (magic: number) => {
    const m = magics1.find((am) => am.magic === magic) || magics2.find((am) => am.magic === magic);
    return m ? m.label : `Magic ${magic}`;
  };

  const getRowClass = (pair: CompareDealPair) => {
    if (!pair.deal1 && pair.deal2) return "bg-negative/10";
    if (pair.deal1 && !pair.deal2) return "bg-warning/10";
    return "";
  };

  return (
    <div className="min-h-screen bg-background text-textPrimary p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Compare Accounts</h1>
      </div>

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-4 mb-6 p-4 bg-surface rounded border border-border">
        {/* Account 1 */}
        <div className="flex items-center gap-2">
          <label className="text-sm text-textSecondary">Account 1:</label>
          <select
            value={account1Id}
            onChange={(e) => setAccount1Id(e.target.value)}
            className="bg-background border border-border rounded px-3 py-1.5 text-sm focus:outline-none focus:border-neutral"
          >
            {accounts.map((acc) => (
              <option key={acc.account_id} value={acc.account_id}>
                {acc.label}
              </option>
            ))}
          </select>
        </div>

        {/* Account 2 */}
        <div className="flex items-center gap-2">
          <label className="text-sm text-textSecondary">Account 2:</label>
          <select
            value={account2Id}
            onChange={(e) => setAccount2Id(e.target.value)}
            className="bg-background border border-border rounded px-3 py-1.5 text-sm focus:outline-none focus:border-neutral"
          >
            {accounts.map((acc) => (
              <option key={acc.account_id} value={acc.account_id}>
                {acc.label}
              </option>
            ))}
          </select>
        </div>

        {/* Period */}
        <div className="flex items-center gap-2">
          <label className="text-sm text-textSecondary">Period:</label>
          <select
            value={periodKey}
            onChange={(e) => setPeriodKey(e.target.value)}
            className="bg-background border border-border rounded px-3 py-1.5 text-sm focus:outline-none focus:border-neutral"
          >
            {periodPresets.map((p) => (
              <option key={p} value={p}>
                {periodLabels[p]}
              </option>
            ))}
          </select>
        </div>

        {/* Magic */}
        <div className="flex items-center gap-2">
          <label className="text-sm text-textSecondary">Magic:</label>
          <select
            value={selectedMagic ?? ""}
            onChange={(e) => setSelectedMagic(e.target.value ? parseInt(e.target.value) : null)}
            className="bg-background border border-border rounded px-3 py-1.5 text-sm focus:outline-none focus:border-neutral"
          >
            <option value="">-- Select Magic --</option>
            {commonMagics.map((m) => (
              <option key={m.magic} value={m.magic}>
                {m.label} (#{m.magic})
              </option>
            ))}
          </select>
        </div>

        {/* Tolerance */}
        <div className="flex items-center gap-2">
          <label className="text-sm text-textSecondary">Tolerance (sec):</label>
          <input
            type="number"
            min={0}
            max={300}
            value={toleranceSeconds}
            onChange={(e) => setToleranceSeconds(parseInt(e.target.value) || 1)}
            className="bg-background border border-border rounded px-3 py-1.5 text-sm w-20 focus:outline-none focus:border-neutral"
          />
        </div>
      </div>

      {/* No magic selected */}
      {selectedMagic === null && (
        <div className="p-8 text-center text-textSecondary bg-surface rounded border border-border">
          Select a magic number to compare deals between accounts
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="p-8 text-center text-textSecondary bg-surface rounded border border-border">
          Loading...
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="p-4 mb-6 bg-negative/10 text-negative rounded border border-negative/30">
          {error}
        </div>
      )}

      {/* Results */}
      {compareResult && !loading && (
        <>
          {/* Summary */}
          <div className="flex flex-wrap items-center gap-6 mb-6 p-4 bg-surface rounded border border-border">
            <div>
              <span className="text-sm text-textSecondary">Matched: </span>
              <span className="font-semibold text-positive">{compareResult.summary.matched}</span>
            </div>
            <div>
              <span className="text-sm text-textSecondary">Only {getAccountLabel(account1Id)}: </span>
              <span className="font-semibold text-warning">{compareResult.summary.account1_only}</span>
            </div>
            <div>
              <span className="text-sm text-textSecondary">Only {getAccountLabel(account2Id)}: </span>
              <span className="font-semibold text-negative">{compareResult.summary.account2_only}</span>
            </div>
            <div className="border-l border-border pl-6">
              <span className="text-sm text-textSecondary">{getAccountLabel(account1Id)} P/L: </span>
              <span className={`font-semibold ${compareResult.summary.total_profit1 >= 0 ? "text-positive" : "text-negative"}`}>
                {formatProfit(compareResult.summary.total_profit1)}
              </span>
            </div>
            <div>
              <span className="text-sm text-textSecondary">{getAccountLabel(account2Id)} P/L: </span>
              <span className={`font-semibold ${compareResult.summary.total_profit2 >= 0 ? "text-positive" : "text-negative"}`}>
                {formatProfit(compareResult.summary.total_profit2)}
              </span>
            </div>
          </div>

          {/* Legend */}
          <div className="flex items-center gap-4 mb-4 text-sm text-textSecondary">
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 bg-warning/20 rounded"></span>
              Only in {getAccountLabel(account1Id)}
            </span>
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 bg-negative/20 rounded"></span>
              Only in {getAccountLabel(account2Id)}
            </span>
          </div>

          {/* Table */}
          <div className="bg-surface rounded border border-border overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-surfaceHover border-b border-border">
                    <th className="px-3 py-3 text-left font-medium text-textSecondary">Entry Time</th>
                    <th className="px-3 py-3 text-left font-medium text-textSecondary">Symbol</th>
                    {/* Account 1 columns */}
                    <th className="px-3 py-3 text-center font-medium text-textSecondary border-l border-border" colSpan={5}>
                      {getAccountLabel(account1Id)}
                    </th>
                    {/* Account 2 columns */}
                    <th className="px-3 py-3 text-center font-medium text-textSecondary border-l border-border" colSpan={5}>
                      {getAccountLabel(account2Id)}
                    </th>
                  </tr>
                  <tr className="bg-surfaceHover border-b border-border text-xs">
                    <th className="px-3 py-2"></th>
                    <th className="px-3 py-2"></th>
                    {/* Account 1 sub-headers */}
                    <th className="px-2 py-2 text-center text-textSecondary border-l border-border">Dir</th>
                    <th className="px-2 py-2 text-right text-textSecondary">Vol</th>
                    <th className="px-2 py-2 text-right text-textSecondary">Entry $</th>
                    <th className="px-2 py-2 text-left text-textSecondary">Exit</th>
                    <th className="px-2 py-2 text-right text-textSecondary">P/L</th>
                    {/* Account 2 sub-headers */}
                    <th className="px-2 py-2 text-center text-textSecondary border-l border-border">Dir</th>
                    <th className="px-2 py-2 text-right text-textSecondary">Vol</th>
                    <th className="px-2 py-2 text-right text-textSecondary">Entry $</th>
                    <th className="px-2 py-2 text-left text-textSecondary">Exit</th>
                    <th className="px-2 py-2 text-right text-textSecondary">P/L</th>
                  </tr>
                </thead>
                <tbody>
                  {compareResult.pairs.map((pair, idx) => (
                    <tr
                      key={idx}
                      className={`border-b border-border hover:bg-surfaceHover transition-colors ${getRowClass(pair)}`}
                    >
                      <td className="px-3 py-2 text-xs whitespace-nowrap">{formatDate(pair.entry_time)}</td>
                      <td className="px-3 py-2">{pair.symbol}</td>

                      {/* Account 1 data */}
                      {pair.deal1 ? (
                        <>
                          <td className="px-2 py-2 text-center border-l border-border">
                            <span
                              className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                                pair.deal1.direction === "buy"
                                  ? "bg-positive/20 text-positive"
                                  : "bg-negative/20 text-negative"
                              }`}
                            >
                              {pair.deal1.direction.toUpperCase()}
                            </span>
                          </td>
                          <td className="px-2 py-2 text-right text-xs">{pair.deal1.volume}</td>
                          <td className="px-2 py-2 text-right text-xs">{pair.deal1.entry_price?.toFixed(5)}</td>
                          <td className="px-2 py-2 text-xs whitespace-nowrap">{formatDate(pair.deal1.exit_time)}</td>
                          <td className={`px-2 py-2 text-right font-medium ${pair.deal1.profit >= 0 ? "text-positive" : "text-negative"}`}>
                            {formatProfit(pair.deal1.profit)}
                          </td>
                        </>
                      ) : (
                        <td colSpan={5} className="px-2 py-2 text-center text-textSecondary border-l border-border">—</td>
                      )}

                      {/* Account 2 data */}
                      {pair.deal2 ? (
                        <>
                          <td className="px-2 py-2 text-center border-l border-border">
                            <span
                              className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                                pair.deal2.direction === "buy"
                                  ? "bg-positive/20 text-positive"
                                  : "bg-negative/20 text-negative"
                              }`}
                            >
                              {pair.deal2.direction.toUpperCase()}
                            </span>
                          </td>
                          <td className="px-2 py-2 text-right text-xs">{pair.deal2.volume}</td>
                          <td className="px-2 py-2 text-right text-xs">{pair.deal2.entry_price?.toFixed(5)}</td>
                          <td className="px-2 py-2 text-xs whitespace-nowrap">{formatDate(pair.deal2.exit_time)}</td>
                          <td className={`px-2 py-2 text-right font-medium ${pair.deal2.profit >= 0 ? "text-positive" : "text-negative"}`}>
                            {formatProfit(pair.deal2.profit)}
                          </td>
                        </>
                      ) : (
                        <td colSpan={5} className="px-2 py-2 text-center text-textSecondary border-l border-border">—</td>
                      )}
                    </tr>
                  ))}
                  {compareResult.pairs.length === 0 && (
                    <tr>
                      <td colSpan={12} className="px-4 py-8 text-center text-textSecondary">
                        No deals found for the selected period and magic
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
