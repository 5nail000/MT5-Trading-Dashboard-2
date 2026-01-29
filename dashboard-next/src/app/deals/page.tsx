"use client";

import { useState, useMemo, useEffect } from "react";
import { Deal, Magic, Account } from "@/types/dashboard";
import { api } from "@/lib/api";

type SortField = "position_id" | "symbol" | "magic" | "direction" | "entry_time" | "profit" | "max_drawdown_currency";
type SortOrder = "asc" | "desc";

export default function DealsPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState("");
  const [deals, setDeals] = useState<Deal[]>([]);
  const [magics, setMagics] = useState<Magic[]>([]);
  const [filterMagic, setFilterMagic] = useState<number | null>(null);
  const [filterStatus, setFilterStatus] = useState<"all" | "open" | "closed">("all");
  const [sortField, setSortField] = useState<SortField>("entry_time");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

  useEffect(() => {
    api.listAccounts().then((data) => {
      setAccounts(data);
      if (!selectedAccountId && data[0]) {
        setSelectedAccountId(data[0].account_id);
      }
    });
  }, [selectedAccountId]);

  useEffect(() => {
    if (!selectedAccountId) return;
    const now = new Date();
    const from = new Date(now.getFullYear(), now.getMonth(), 1).toISOString();
    const to = now.toISOString();
    Promise.all([
      api.deals(selectedAccountId, from, to),
      api.listMagics(selectedAccountId),
    ]).then(([dealsData, magicsData]) => {
      setDeals(dealsData);
      setMagics(magicsData);
    });
  }, [selectedAccountId]);

  // Filter and sort deals
  const filteredDeals = useMemo(() => {
    let dealsList = [...deals];

    // Filter by magic
    if (filterMagic !== null) {
      dealsList = dealsList.filter((d) => d.magic === filterMagic);
    }

    // Filter by status
    if (filterStatus !== "all") {
      dealsList = dealsList.filter((d) => d.status === filterStatus);
    }

    // Sort
    dealsList.sort((a, b) => {
      let aVal: string | number | null = a[sortField];
      let bVal: string | number | null = b[sortField];

      // Handle nulls
      if (aVal === null) aVal = sortOrder === "asc" ? Infinity : -Infinity;
      if (bVal === null) bVal = sortOrder === "asc" ? Infinity : -Infinity;

      if (typeof aVal === "string" && typeof bVal === "string") {
        return sortOrder === "asc" ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      }
      
      const diff = (aVal as number) - (bVal as number);
      return sortOrder === "asc" ? diff : -diff;
    });

    return dealsList;
  }, [deals, filterMagic, filterStatus, sortField, sortOrder]);

  // Summary stats
  const summary = useMemo(() => {
    const closedDeals = filteredDeals.filter((d) => d.status === "closed");
    const totalProfit = closedDeals.reduce((sum, d) => sum + d.profit, 0);
    const winCount = closedDeals.filter((d) => d.profit > 0).length;
    const winRate = closedDeals.length > 0 ? (winCount / closedDeals.length) * 100 : 0;
    return { totalProfit, count: closedDeals.length, winRate };
  }, [filteredDeals]);

  const getMagicLabel = (magic: number) => {
    const m = magics.find((am) => am.magic === magic);
    return m ? m.label : `Magic ${magic}`;
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "—";
    return new Date(dateStr).toLocaleString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatProfit = (val: number) =>
    val >= 0 ? `+$${val.toFixed(2)}` : `-$${Math.abs(val).toFixed(2)}`;

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  };

  const getSortIcon = (field: SortField) => {
    if (sortField !== field) return "";
    return sortOrder === "asc" ? " ↑" : " ↓";
  };

  const exportCSV = () => {
    const headers = ["Position ID", "Symbol", "Direction", "Magic", "Volume", "Entry Time", "Entry Price", "Exit Time", "Exit Price", "Profit", "Max DD (pts)", "Max DD ($)", "Status"];
    const rows = filteredDeals.map((d) => [
      d.position_id,
      d.symbol,
      d.direction,
      d.magic,
      d.volume,
      d.entry_time,
      d.entry_price,
      d.exit_time || "",
      d.exit_price || "",
      d.profit,
      d.max_drawdown_points || "",
      d.max_drawdown_currency || "",
      d.status,
    ]);
    
    const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `deals_${selectedAccountId}_${new Date().toISOString().split("T")[0]}.csv`;
    a.click();
  };

  return (
    <div className="min-h-screen bg-background text-textPrimary p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Deals (Aggregated by Position)</h1>
        <button
          onClick={exportCSV}
          className="px-4 py-2 text-sm bg-neutral text-white rounded hover:bg-neutral/80 transition-colors"
        >
          Export CSV
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4 mb-6 p-4 bg-surface rounded border border-border">
        <div className="flex items-center gap-2">
          <label className="text-sm text-textSecondary">Account:</label>
          <select
            value={selectedAccountId}
            onChange={(e) => setSelectedAccountId(e.target.value)}
            className="bg-background border border-border rounded px-3 py-1.5 text-sm focus:outline-none focus:border-neutral"
          >
            {accounts.map((acc) => (
              <option key={acc.account_id} value={acc.account_id}>
                {acc.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-sm text-textSecondary">Magic:</label>
          <select
            value={filterMagic ?? ""}
            onChange={(e) => setFilterMagic(e.target.value ? parseInt(e.target.value) : null)}
            className="bg-background border border-border rounded px-3 py-1.5 text-sm focus:outline-none focus:border-neutral"
          >
            <option value="">All</option>
            {magics.map((m) => (
              <option key={m.magic} value={m.magic}>
                {m.label} (#{m.magic})
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-sm text-textSecondary">Status:</label>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value as "all" | "open" | "closed")}
            className="bg-background border border-border rounded px-3 py-1.5 text-sm focus:outline-none focus:border-neutral"
          >
            <option value="all">All</option>
            <option value="closed">Closed</option>
            <option value="open">Open</option>
          </select>
        </div>
      </div>

      {/* Summary */}
      <div className="flex items-center gap-6 mb-6 p-4 bg-surface rounded border border-border">
        <div>
          <span className="text-sm text-textSecondary">Total P/L: </span>
          <span className={`font-semibold ${summary.totalProfit >= 0 ? "text-positive" : "text-negative"}`}>
            {formatProfit(summary.totalProfit)}
          </span>
        </div>
        <div>
          <span className="text-sm text-textSecondary">Closed Deals: </span>
          <span className="font-semibold">{summary.count}</span>
        </div>
        <div>
          <span className="text-sm text-textSecondary">Win Rate: </span>
          <span className="font-semibold">{summary.winRate.toFixed(1)}%</span>
        </div>
      </div>

      {/* Table */}
      <div className="bg-surface rounded border border-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-surfaceHover border-b border-border">
                <th
                  className="px-4 py-3 text-left font-medium text-textSecondary cursor-pointer hover:text-textPrimary"
                  onClick={() => handleSort("position_id")}
                >
                  Position{getSortIcon("position_id")}
                </th>
                <th
                  className="px-4 py-3 text-left font-medium text-textSecondary cursor-pointer hover:text-textPrimary"
                  onClick={() => handleSort("symbol")}
                >
                  Symbol{getSortIcon("symbol")}
                </th>
                <th
                  className="px-4 py-3 text-left font-medium text-textSecondary cursor-pointer hover:text-textPrimary"
                  onClick={() => handleSort("direction")}
                >
                  Dir{getSortIcon("direction")}
                </th>
                <th
                  className="px-4 py-3 text-left font-medium text-textSecondary cursor-pointer hover:text-textPrimary"
                  onClick={() => handleSort("magic")}
                >
                  Magic{getSortIcon("magic")}
                </th>
                <th className="px-4 py-3 text-right font-medium text-textSecondary">
                  Volume
                </th>
                <th
                  className="px-4 py-3 text-left font-medium text-textSecondary cursor-pointer hover:text-textPrimary"
                  onClick={() => handleSort("entry_time")}
                >
                  Entry{getSortIcon("entry_time")}
                </th>
                <th className="px-4 py-3 text-left font-medium text-textSecondary">
                  Exit
                </th>
                <th
                  className="px-4 py-3 text-right font-medium text-textSecondary cursor-pointer hover:text-textPrimary"
                  onClick={() => handleSort("profit")}
                >
                  Profit{getSortIcon("profit")}
                </th>
                <th
                  className="px-4 py-3 text-right font-medium text-textSecondary cursor-pointer hover:text-textPrimary"
                  onClick={() => handleSort("max_drawdown_currency")}
                >
                  Max DD{getSortIcon("max_drawdown_currency")}
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredDeals.map((deal) => (
                <tr
                  key={deal.position_id}
                  className="border-b border-border hover:bg-surfaceHover transition-colors"
                >
                  <td className="px-4 py-3 font-mono text-xs">{deal.position_id}</td>
                  <td className="px-4 py-3">{deal.symbol}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${
                        deal.direction === "buy"
                          ? "bg-positive/20 text-positive"
                          : "bg-negative/20 text-negative"
                      }`}
                    >
                      {deal.direction.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-textSecondary">
                    <span title={`#${deal.magic}`}>{getMagicLabel(deal.magic)}</span>
                  </td>
                  <td className="px-4 py-3 text-right">{deal.volume}</td>
                  <td className="px-4 py-3 text-xs">{formatDate(deal.entry_time)}</td>
                  <td className="px-4 py-3 text-xs">{formatDate(deal.exit_time)}</td>
                  <td
                    className={`px-4 py-3 text-right font-medium ${
                      deal.profit >= 0 ? "text-positive" : "text-negative"
                    }`}
                  >
                    {formatProfit(deal.profit)}
                  </td>
                  <td className="px-4 py-3 text-right text-textSecondary">
                    {deal.max_drawdown_currency !== null
                      ? `$${deal.max_drawdown_currency.toFixed(2)}`
                      : "—"}
                  </td>
                </tr>
              ))}
              {filteredDeals.length === 0 && (
                <tr>
                  <td colSpan={9} className="px-4 py-8 text-center text-textSecondary">
                    No deals found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
