export interface Account {
  account_id: string;
  label: string;
  history_start_date?: string | null;
  account_info: {
    account_number: string;
    leverage: number;
    server: string;
  };
  has_credentials?: boolean;
}

export interface MagicGroup {
  group_id: number;
  account_id: string;
  name: string;
  label2?: string | null;
  font_color?: string | null;
  fill_color?: string | null;
}

export interface Magic {
  account_id: string;
  magic: number;
  label: string;
  description: string;
  group_ids: number[];
}

export interface OpenPositionsSummary {
  account_id: string;
  balance: number;
  floating_total: number;
  floating_percent: number;
  by_magic: { magic: number; floating: number; percent: number }[];
}

export interface GroupAggregate {
  group_id: number;
  profit: number;
}

export interface MagicAggregate {
  magic: number;
  profit: number;
}

export interface AccountAggregate {
  account_id: string;
  period_profit: number;
  period_percent: number;
  by_magic: MagicAggregate[];
  by_group: GroupAggregate[];
}

export interface LayoutMargins {
  left: number;
  right: number;
  top: number;
  bottom: number;
}

export interface Period {
  from: string;
  to: string;
  label: string;
}

export interface Deal {
  position_id: number;
  account_id: string;
  magic: number;
  symbol: string;
  direction: "buy" | "sell";
  volume: number;
  entry_time: string;
  entry_price: number;
  exit_time: string | null;
  exit_price: number | null;
  profit: number;
  max_drawdown_points: number | null;
  max_drawdown_currency: number | null;
  status: "open" | "closed";
  comment?: string | null;
}
