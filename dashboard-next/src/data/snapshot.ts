// Data snapshot for dashboard (imported from design/sample_snapshot.json)

export interface Account {
  account_id: string;
  label: string;
  account_info: {
    account_number: string;
    leverage: number;
    server: string;
  };
}

export interface MagicGroup {
  group_id: number;
  account_id: string;
  name: string;
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

export interface UIState {
  last_view: {
    account_id: string;
    period_key: string;
    view_mode: "grouped" | "individual";
    selected_groups: number[];
    selected_magics: number[];
    filters_open: boolean;
  };
}

export interface LayoutMargins {
  left: number;   // percent
  right: number;  // percent
  top: number;    // percent
  bottom: number; // percent
}

export interface Config {
  open_positions_bar: {
    range_percent: number;
    center_percent: number;
    positive_color: string;
    negative_color: string;
    neutral_color: string;
    hover_glow: boolean;
  };
  thresholds: {
    warning_percent: number;
    critical_percent: number;
  };
  ui: {
    theme: string;
    default_view_mode: string;
    compact_filters: boolean;
  };
  layout: {
    margins: LayoutMargins;
  };
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
}

export interface Snapshot {
  schema_version: string;
  generated_at: string;
  periods: { default: Period };
  config: Config;
  accounts: Account[];
  magics: Magic[];
  magic_groups: MagicGroup[];
  open_positions_summary: OpenPositionsSummary[];
  deals: Deal[];
  aggregates: {
    by_account: AccountAggregate[];
    by_magic: { account_id: string; magic: number; profit: number; count_closed: number }[];
    by_group: { account_id: string; group_id: number; profit: number; count_closed: number }[];
  };
  ui_state: UIState;
}

// Snapshot data
export const snapshot: Snapshot = {
  schema_version: "0.1",
  generated_at: "2026-01-27T10:00:00Z",
  periods: {
    default: {
      from: "2026-01-01T00:00:00+03:00",
      to: "2026-01-27T23:59:59+03:00",
      label: "this_month",
    },
  },
  config: {
    open_positions_bar: {
      range_percent: 10,
      center_percent: 0,
      positive_color: "#22c55e",
      negative_color: "#ef4444",
      neutral_color: "#3a3a3a",
      hover_glow: true,
    },
    thresholds: {
      warning_percent: -12,
      critical_percent: -20,
    },
    ui: {
      theme: "dark",
      default_view_mode: "grouped",
      compact_filters: true,
    },
    layout: {
      margins: {
        left: 10,
        right: 10,
        top: 0,
        bottom: 0,
      },
    },
  },
  accounts: [
    {
      account_id: "1001001",
      label: "Main USD",
      account_info: {
        account_number: "1001001",
        leverage: 200,
        server: "MetaQuotes-Demo",
      },
    },
    {
      account_id: "2002002",
      label: "Hedge EUR",
      account_info: {
        account_number: "2002002",
        leverage: 100,
        server: "Broker-Live",
      },
    },
  ],
  magics: [
    // Account 1001001 - 15 magics
    { account_id: "1001001", magic: 101, label: "Trend Alpha", description: "XAUUSD intraday trend", group_ids: [1] },
    { account_id: "1001001", magic: 102, label: "Scalp Beta", description: "M5 scalping", group_ids: [1] },
    { account_id: "1001001", magic: 103, label: "Gold Swing", description: "H4 swing trading", group_ids: [1] },
    { account_id: "1001001", magic: 104, label: "XAU Breakout", description: "London session breakout", group_ids: [1] },
    { account_id: "1001001", magic: 201, label: "Mean Rev EUR", description: "EURUSD mean reversion", group_ids: [2] },
    { account_id: "1001001", magic: 202, label: "EUR Scalper", description: "M1 EUR scalper", group_ids: [2] },
    { account_id: "1001001", magic: 203, label: "EUR News", description: "News trading EUR", group_ids: [2] },
    { account_id: "1001001", magic: 301, label: "GBP Trend", description: "GBPUSD trend following", group_ids: [5] },
    { account_id: "1001001", magic: 302, label: "Cable Swing", description: "GBPUSD swing", group_ids: [5] },
    { account_id: "1001001", magic: 401, label: "JPY Carry", description: "Yen carry trade", group_ids: [6] },
    { account_id: "1001001", magic: 402, label: "JPY Reversal", description: "Mean reversion JPY", group_ids: [6] },
    { account_id: "1001001", magic: 501, label: "Index DAX", description: "DAX scalping", group_ids: [7] },
    { account_id: "1001001", magic: 502, label: "Index SP500", description: "SP500 swing", group_ids: [7] },
    { account_id: "1001001", magic: 503, label: "Index NAS", description: "Nasdaq momentum", group_ids: [7] },
    { account_id: "1001001", magic: 601, label: "Oil WTI", description: "WTI trend", group_ids: [8] },
    // Account 2002002 - 10 magics
    { account_id: "2002002", magic: 1001, label: "Breakout FX", description: "London breakout", group_ids: [3] },
    { account_id: "2002002", magic: 1002, label: "Asian Range", description: "Asian session range", group_ids: [3] },
    { account_id: "2002002", magic: 1003, label: "NY Open", description: "New York open strategy", group_ids: [3] },
    { account_id: "2002002", magic: 2001, label: "Carry Basket", description: "Swap carry basket", group_ids: [4] },
    { account_id: "2002002", magic: 2002, label: "Crypto Grid", description: "BTCUSD grid", group_ids: [4] },
    { account_id: "2002002", magic: 2003, label: "ETH Momentum", description: "ETHUSD momentum", group_ids: [4] },
    { account_id: "2002002", magic: 3001, label: "Multi Trend", description: "Multi-pair trend", group_ids: [9] },
    { account_id: "2002002", magic: 3002, label: "Correlation", description: "Correlation trading", group_ids: [9] },
    { account_id: "2002002", magic: 3003, label: "Hedge Master", description: "Hedging strategy", group_ids: [9] },
    { account_id: "2002002", magic: 3004, label: "Risk Parity", description: "Risk parity portfolio", group_ids: [9] },
  ],
  magic_groups: [
    // Account 1001001 - 8 groups
    { group_id: 1, account_id: "1001001", name: "Gold Systems" },
    { group_id: 2, account_id: "1001001", name: "EURUSD Core" },
    { group_id: 5, account_id: "1001001", name: "GBP Strategies" },
    { group_id: 6, account_id: "1001001", name: "JPY Pairs" },
    { group_id: 7, account_id: "1001001", name: "Indices" },
    { group_id: 8, account_id: "1001001", name: "Commodities" },
    // Account 2002002 - 3 groups
    { group_id: 3, account_id: "2002002", name: "FX Intraday" },
    { group_id: 4, account_id: "2002002", name: "Multi-Asset" },
    { group_id: 9, account_id: "2002002", name: "Portfolio" },
  ],
  open_positions_summary: [
    {
      account_id: "1001001",
      balance: 12450.0,
      floating_total: 34.9,
      floating_percent: 0.28,
      by_magic: [{ magic: 201, floating: 34.9, percent: 0.28 }],
    },
    {
      account_id: "2002002",
      balance: 19500.0,
      floating_total: -81.2,
      floating_percent: -0.42,
      by_magic: [{ magic: 302, floating: -81.2, percent: -0.42 }],
    },
  ],
  deals: [
    // Account 1001001 - closed deals
    { position_id: 10001, account_id: "1001001", magic: 101, symbol: "XAUUSD", direction: "buy", volume: 0.5, entry_time: "2026-01-05T09:30:00Z", entry_price: 2045.50, exit_time: "2026-01-05T14:22:00Z", exit_price: 2051.20, profit: 285.00, max_drawdown_points: 45, max_drawdown_currency: 22.50, status: "closed" },
    { position_id: 10002, account_id: "1001001", magic: 101, symbol: "XAUUSD", direction: "sell", volume: 0.3, entry_time: "2026-01-10T11:15:00Z", entry_price: 2068.30, exit_time: "2026-01-10T16:45:00Z", exit_price: 2072.10, profit: -114.00, max_drawdown_points: 82, max_drawdown_currency: 24.60, status: "closed" },
    { position_id: 10003, account_id: "1001001", magic: 102, symbol: "XAUUSD", direction: "buy", volume: 0.1, entry_time: "2026-01-12T08:00:00Z", entry_price: 2055.00, exit_time: "2026-01-12T08:12:00Z", exit_price: 2054.40, profit: -6.00, max_drawdown_points: 15, max_drawdown_currency: 1.50, status: "closed" },
    { position_id: 10004, account_id: "1001001", magic: 103, symbol: "XAUUSD", direction: "buy", volume: 0.5, entry_time: "2026-01-08T06:00:00Z", entry_price: 2040.00, exit_time: "2026-01-15T18:00:00Z", exit_price: 2078.90, profit: 194.50, max_drawdown_points: 120, max_drawdown_currency: 60.00, status: "closed" },
    { position_id: 10005, account_id: "1001001", magic: 202, symbol: "EURUSD", direction: "buy", volume: 1.0, entry_time: "2026-01-18T10:00:00Z", entry_price: 1.0850, exit_time: "2026-01-18T15:30:00Z", exit_price: 1.0858, profit: 80.00, max_drawdown_points: 12, max_drawdown_currency: 12.00, status: "closed" },
    { position_id: 10006, account_id: "1001001", magic: 301, symbol: "GBPUSD", direction: "sell", volume: 0.8, entry_time: "2026-01-20T14:00:00Z", entry_price: 1.2720, exit_time: "2026-01-21T09:00:00Z", exit_price: 1.2675, profit: 360.00, max_drawdown_points: 25, max_drawdown_currency: 20.00, status: "closed" },
    { position_id: 10007, account_id: "1001001", magic: 401, symbol: "USDJPY", direction: "buy", volume: 1.5, entry_time: "2026-01-15T03:00:00Z", entry_price: 148.50, exit_time: "2026-01-22T12:00:00Z", exit_price: 152.30, profit: 570.00, max_drawdown_points: 180, max_drawdown_currency: 180.00, status: "closed" },
    { position_id: 10008, account_id: "1001001", magic: 502, symbol: "US500", direction: "buy", volume: 0.2, entry_time: "2026-01-10T15:30:00Z", entry_price: 4850.0, exit_time: "2026-01-24T20:00:00Z", exit_price: 4920.0, profit: 460.00, max_drawdown_points: 45, max_drawdown_currency: 90.00, status: "closed" },
    // Account 1001001 - open deal
    { position_id: 10009, account_id: "1001001", magic: 201, symbol: "EURUSD", direction: "buy", volume: 0.5, entry_time: "2026-01-26T09:00:00Z", entry_price: 1.0820, exit_time: null, exit_price: null, profit: 34.90, max_drawdown_points: null, max_drawdown_currency: null, status: "open" },
    // Account 2002002 - closed deals
    { position_id: 20001, account_id: "2002002", magic: 1001, symbol: "EURUSD", direction: "buy", volume: 2.0, entry_time: "2026-01-03T08:00:00Z", entry_price: 1.0920, exit_time: "2026-01-03T16:00:00Z", exit_price: 1.0892, profit: -560.00, max_drawdown_points: 35, max_drawdown_currency: 70.00, status: "closed" },
    { position_id: 20002, account_id: "2002002", magic: 1002, symbol: "GBPUSD", direction: "sell", volume: 1.0, entry_time: "2026-01-08T07:30:00Z", entry_price: 1.2680, exit_time: "2026-01-08T10:00:00Z", exit_price: 1.2656, profit: 240.00, max_drawdown_points: 18, max_drawdown_currency: 18.00, status: "closed" },
    { position_id: 20003, account_id: "2002002", magic: 2002, symbol: "BTCUSD", direction: "buy", volume: 0.1, entry_time: "2026-01-05T00:00:00Z", entry_price: 42500, exit_time: "2026-01-20T12:00:00Z", exit_price: 48650, profit: 615.00, max_drawdown_points: 3500, max_drawdown_currency: 350.00, status: "closed" },
    { position_id: 20004, account_id: "2002002", magic: 2002, symbol: "BTCUSD", direction: "buy", volume: 0.15, entry_time: "2026-01-12T06:00:00Z", entry_price: 44200, exit_time: "2026-01-25T18:00:00Z", exit_price: 48200, profit: 600.00, max_drawdown_points: 2800, max_drawdown_currency: 420.00, status: "closed" },
    { position_id: 20005, account_id: "2002002", magic: 3001, symbol: "EURUSD", direction: "sell", volume: 0.5, entry_time: "2026-01-22T11:00:00Z", entry_price: 1.0870, exit_time: "2026-01-24T14:00:00Z", exit_price: 1.0832, profit: 190.00, max_drawdown_points: 22, max_drawdown_currency: 11.00, status: "closed" },
    // Account 2002002 - open deal
    { position_id: 20006, account_id: "2002002", magic: 302, symbol: "AUDJPY", direction: "sell", volume: 0.8, entry_time: "2026-01-25T04:00:00Z", entry_price: 97.50, exit_time: null, exit_price: null, profit: -81.20, max_drawdown_points: null, max_drawdown_currency: null, status: "open" },
  ],
  aggregates: {
    by_account: [
      {
        account_id: "1001001",
        period_profit: 1847.5,
        period_percent: 14.8,
        by_magic: [
          { magic: 101, profit: 253.2 },
          { magic: 102, profit: -6.0 },
          { magic: 103, profit: 189.5 },
          { magic: 104, profit: -45.3 },
          { magic: 201, profit: 0.0 },
          { magic: 202, profit: 78.4 },
          { magic: 203, profit: -12.7 },
          { magic: 301, profit: 345.6 },
          { magic: 302, profit: -89.2 },
          { magic: 401, profit: 567.8 },
          { magic: 402, profit: 123.4 },
          { magic: 501, profit: -234.5 },
          { magic: 502, profit: 456.7 },
          { magic: 503, profit: 178.9 },
          { magic: 601, profit: 41.7 },
        ],
        by_group: [
          { group_id: 1, profit: 391.4 },
          { group_id: 2, profit: 65.7 },
          { group_id: 5, profit: 256.4 },
          { group_id: 6, profit: 691.2 },
          { group_id: 7, profit: 401.1 },
          { group_id: 8, profit: 41.7 },
        ],
      },
      {
        account_id: "2002002",
        period_profit: 1892.3,
        period_percent: 9.7,
        by_magic: [
          { magic: 1001, profit: -555.7 },
          { magic: 1002, profit: 234.5 },
          { magic: 1003, profit: 123.4 },
          { magic: 2001, profit: 0.0 },
          { magic: 2002, profit: 1213.2 },
          { magic: 2003, profit: 345.6 },
          { magic: 3001, profit: 189.3 },
          { magic: 3002, profit: -78.9 },
          { magic: 3003, profit: 234.5 },
          { magic: 3004, profit: 186.4 },
        ],
        by_group: [
          { group_id: 3, profit: -197.8 },
          { group_id: 4, profit: 1558.8 },
          { group_id: 9, profit: 531.3 },
        ],
      },
    ],
    by_magic: [
      // Account 1001001
      { account_id: "1001001", magic: 101, profit: 253.2, count_closed: 5 },
      { account_id: "1001001", magic: 102, profit: -6.0, count_closed: 2 },
      { account_id: "1001001", magic: 103, profit: 189.5, count_closed: 3 },
      { account_id: "1001001", magic: 104, profit: -45.3, count_closed: 1 },
      { account_id: "1001001", magic: 201, profit: 0.0, count_closed: 0 },
      { account_id: "1001001", magic: 202, profit: 78.4, count_closed: 4 },
      { account_id: "1001001", magic: 203, profit: -12.7, count_closed: 1 },
      { account_id: "1001001", magic: 301, profit: 345.6, count_closed: 6 },
      { account_id: "1001001", magic: 302, profit: -89.2, count_closed: 2 },
      { account_id: "1001001", magic: 401, profit: 567.8, count_closed: 8 },
      { account_id: "1001001", magic: 402, profit: 123.4, count_closed: 3 },
      { account_id: "1001001", magic: 501, profit: -234.5, count_closed: 4 },
      { account_id: "1001001", magic: 502, profit: 456.7, count_closed: 7 },
      { account_id: "1001001", magic: 503, profit: 178.9, count_closed: 5 },
      { account_id: "1001001", magic: 601, profit: 41.7, count_closed: 2 },
      // Account 2002002
      { account_id: "2002002", magic: 1001, profit: -555.7, count_closed: 3 },
      { account_id: "2002002", magic: 1002, profit: 234.5, count_closed: 4 },
      { account_id: "2002002", magic: 1003, profit: 123.4, count_closed: 2 },
      { account_id: "2002002", magic: 2001, profit: 0.0, count_closed: 0 },
      { account_id: "2002002", magic: 2002, profit: 1213.2, count_closed: 12 },
      { account_id: "2002002", magic: 2003, profit: 345.6, count_closed: 5 },
      { account_id: "2002002", magic: 3001, profit: 189.3, count_closed: 3 },
      { account_id: "2002002", magic: 3002, profit: -78.9, count_closed: 2 },
      { account_id: "2002002", magic: 3003, profit: 234.5, count_closed: 4 },
      { account_id: "2002002", magic: 3004, profit: 186.4, count_closed: 3 },
    ],
    by_group: [
      // Account 1001001
      { account_id: "1001001", group_id: 1, profit: 391.4, count_closed: 11 },
      { account_id: "1001001", group_id: 2, profit: 65.7, count_closed: 5 },
      { account_id: "1001001", group_id: 5, profit: 256.4, count_closed: 8 },
      { account_id: "1001001", group_id: 6, profit: 691.2, count_closed: 11 },
      { account_id: "1001001", group_id: 7, profit: 401.1, count_closed: 16 },
      { account_id: "1001001", group_id: 8, profit: 41.7, count_closed: 2 },
      // Account 2002002
      { account_id: "2002002", group_id: 3, profit: -197.8, count_closed: 9 },
      { account_id: "2002002", group_id: 4, profit: 1558.8, count_closed: 17 },
      { account_id: "2002002", group_id: 9, profit: 531.3, count_closed: 12 },
    ],
  },
  ui_state: {
    last_view: {
      account_id: "1001001",
      period_key: "default",
      view_mode: "grouped",
      selected_groups: [1, 2, 5, 6, 7, 8],
      selected_magics: [101, 102, 103, 104, 201, 202, 203, 301, 302, 401, 402, 501, 502, 503, 601],
      filters_open: false,
    },
  },
};
