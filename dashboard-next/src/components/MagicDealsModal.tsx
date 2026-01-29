"use client";

import { useMemo, useState } from "react";
import { Deal } from "@/types/dashboard";

interface MagicDealsModalProps {
   title: string;
   deals: Deal[];
   isLoading: boolean;
   onClose: () => void;
 }
 
 const formatDateTime = (value: string | null) => {
   if (!value) return "-";
   const date = new Date(value);
   return date.toLocaleString("ru-RU", {
     day: "2-digit",
     month: "2-digit",
     year: "numeric",
     hour: "2-digit",
     minute: "2-digit",
   });
 };
 
const formatProfit = (val: number) =>
  val >= 0 ? `+$${val.toFixed(2)}` : `-$${Math.abs(val).toFixed(2)}`;

const formatPrice = (val: number | null) => {
  if (val === null || val === undefined) return "-";
  return val.toFixed(5);
};
 
 export default function MagicDealsModal({
   title,
   deals,
   isLoading,
   onClose,
 }: MagicDealsModalProps) {
  const [sortKey, setSortKey] = useState<string>("exit_time");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const totalProfit = useMemo(
    () => deals.reduce((sum, deal) => sum + (deal.profit || 0), 0),
    [deals]
  );

  const sortedDeals = useMemo(() => {
    const sorted = [...deals];
    sorted.sort((a, b) => {
      const getVal = (deal: Deal) => {
        switch (sortKey) {
          case "magic":
            return deal.magic;
          case "symbol":
            return deal.symbol;
          case "direction":
            return deal.direction;
          case "volume":
            return deal.volume;
          case "entry_time":
            return deal.entry_time || "";
          case "exit_time":
            return deal.exit_time || "";
          case "entry_price":
            return deal.entry_price ?? 0;
          case "exit_price":
            return deal.exit_price ?? 0;
          case "profit":
            return deal.profit ?? 0;
          case "comment":
            return deal.comment || "";
          case "position_id":
            return deal.position_id;
          default:
            return "";
        }
      };
      const aVal = getVal(a);
      const bVal = getVal(b);
      if (typeof aVal === "number" && typeof bVal === "number") {
        return sortDir === "asc" ? aVal - bVal : bVal - aVal;
      }
      const cmp = String(aVal).localeCompare(String(bVal));
      return sortDir === "asc" ? cmp : -cmp;
    });
    return sorted;
  }, [deals, sortDir, sortKey]);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

   return (
     <div
       className="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
       onClick={onClose}
     >
      <div
        className="bg-surface border border-border rounded-lg shadow-2xl w-[95vw] max-w-[1100px] max-h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-4 border-b border-border flex items-center justify-between">
          <div>
            <div className="text-lg font-semibold text-textPrimary">{title}</div>
            <div className="text-xs text-textSecondary mt-1">
              Сделки по выбранным магикам
            </div>
            <div
              className={`text-sm font-medium mt-2 ${
                totalProfit >= 0 ? "text-positive" : "text-negative"
              }`}
            >
              Итог: {formatProfit(totalProfit)} ({deals.length})
            </div>
          </div>
           <button
             onClick={onClose}
             className="text-textSecondary hover:text-textPrimary transition-colors"
           >
             ✕
           </button>
         </div>
 
         <div className="flex-1 overflow-y-auto p-4">
           {isLoading ? (
             <div className="text-textSecondary text-sm">Загрузка...</div>
           ) : deals.length === 0 ? (
             <div className="text-textSecondary text-sm">Нет сделок за период</div>
          ) : (
            <div className="space-y-2">
              <div className="grid grid-cols-[60px_60px_110px_110px_70px_70px_60px_60px_80px_80px_1fr] gap-2 items-center text-[10px] uppercase tracking-wide text-textSecondary px-1">
                <button onClick={() => handleSort("magic")} className="text-left">
                  Magic
                </button>
                <button onClick={() => handleSort("symbol")} className="text-left">
                  Symbol
                </button>
                <button onClick={() => handleSort("entry_time")} className="text-left">
                  Entry time
                </button>
                <button onClick={() => handleSort("exit_time")} className="text-left">
                  Exit time
                </button>
                <button onClick={() => handleSort("entry_price")} className="text-left">
                  Entry px
                </button>
                <button onClick={() => handleSort("exit_price")} className="text-left">
                  Exit px
                </button>
                <button onClick={() => handleSort("direction")} className="text-left">
                  Side
                </button>
                <button onClick={() => handleSort("volume")} className="text-left">
                  Volume
                </button>
                <button onClick={() => handleSort("profit")} className="text-left">
                  P/L
                </button>
                <button onClick={() => handleSort("position_id")} className="text-left">
                  Ticket
                </button>
                <button onClick={() => handleSort("comment")} className="text-left">
                  Comment
                </button>
              </div>
              {sortedDeals.map((deal) => {
                const profitClass =
                  deal.profit >= 0 ? "text-positive" : "text-negative";
                return (
                  <div
                    key={`${deal.account_id}-${deal.position_id}-${deal.entry_time}`}
                    className="grid grid-cols-[60px_60px_110px_110px_70px_70px_60px_60px_80px_80px_1fr] gap-2 items-center text-[11px] leading-tight bg-surfaceHover rounded px-1 py-2"
                  >
                    <div className="text-textSecondary">{deal.magic}</div>
                    <div className="text-textPrimary">{deal.symbol}</div>
                    <div className="text-textSecondary">
                      {formatDateTime(deal.entry_time)}
                    </div>
                    <div className="text-textSecondary">
                      {formatDateTime(deal.exit_time)}
                    </div>
                    <div className="text-textSecondary">
                      {formatPrice(deal.entry_price)}
                    </div>
                    <div className="text-textSecondary">
                      {formatPrice(deal.exit_price)}
                    </div>
                    <div className="text-textSecondary">{deal.direction}</div>
                    <div className="text-textSecondary">
                      {deal.volume.toFixed(2)}
                    </div>
                    <div className={`font-medium ${profitClass}`}>
                      {formatProfit(deal.profit)}
                    </div>
                    <div className="text-textSecondary">
                      #{deal.position_id}
                    </div>
                    <div className="text-textSecondary">
                      {deal.comment || "-"}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
         </div>
 
         <div className="p-4 border-t border-border flex justify-end">
           <button
             onClick={onClose}
             className="px-4 py-2 text-sm bg-surfaceHover text-textSecondary rounded hover:bg-border transition-colors"
           >
             Закрыть
           </button>
         </div>
       </div>
     </div>
   );
 }
