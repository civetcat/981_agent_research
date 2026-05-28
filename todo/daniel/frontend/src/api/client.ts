import axios from "axios";

export const api = axios.create({
  baseURL: "/api",
  timeout: 60000,
});

export interface StockInfo {
  symbol: string;
  name?: string;
  market?: string;
  sector?: string;
  industry?: string;
  currency?: string;
  exchange?: string;
  market_cap?: number;
  pe?: number;
  pb?: number;
  dividend_yield?: number;
  eps?: number;
  summary?: string;
}

export interface OHLCVRow {
  date: string;
  open?: number;
  high?: number;
  low?: number;
  close?: number;
  volume?: number;
  [key: string]: any;
}

export interface BacktestMetrics {
  total_return: number | null;
  annual_return: number | null;
  max_drawdown: number | null;
  sharpe: number | null;
  sortino: number | null;
  win_rate: number | null;
  trades: number;
  best_trade: number | null;
  worst_trade: number | null;
  exposure: number | null;
}

export interface BacktestResult {
  symbol: string;
  strategy: string;
  params: Record<string, any>;
  start: string;
  end: string;
  init_cash: number;
  metrics: BacktestMetrics;
  equity_curve: { date: string; value: number }[];
  benchmark_curve: { date: string; value: number }[];
  trades: any[];
}

export const stocksApi = {
  search: (q: string) => api.get(`/stocks/search`, { params: { q } }).then((r) => r.data),
  info: (symbol: string) => api.get<StockInfo>(`/stocks/${symbol}`).then((r) => r.data),
  ohlcv: (symbol: string, period = "1y") =>
    api
      .get<{ symbol: string; data: OHLCVRow[] }>(`/stocks/${symbol}/ohlcv`, { params: { period } })
      .then((r) => r.data),
  indicators: (symbol: string, period = "1y", types = "sma_5,sma_20,sma_60,rsi_14,macd,bb") =>
    api
      .get<{ symbol: string; data: OHLCVRow[] }>(`/stocks/${symbol}/indicators`, {
        params: { period, types },
      })
      .then((r) => r.data),
  fundamentals: (symbol: string) =>
    api.get(`/stocks/${symbol}/fundamentals`).then((r) => r.data),
  ask: (
    symbol: string,
    question: string,
    history: { role: "user" | "assistant"; content: string }[] = [],
  ) =>
    api
      .post<{
        answer: string;
        source: "grok" | "rule" | "error";
        model?: string;
        symbol: string;
      }>(`/stocks/${symbol}/ask`, { question, history }, { timeout: 120000 })
      .then((r) => r.data),
};

export const screenerApi = {
  run: (body: {
    market?: string;
    symbols?: string[];
    conditions?: { fundamental?: any; technical?: any };
    limit?: number;
  }) => api.post(`/screener/run`, body).then((r) => r.data),
};

export interface Position {
  symbol: string;
  qty: number;
  avg_cost: number;
  last_price: number | null;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pct: number | null;
  weight: number;
}

export interface PortfolioState {
  id: number;
  name: string;
  initial_cash: number;
  total_invested: number;
  cash: number;
  market_value: number;
  total_equity: number;
  total_cost: number;
  unrealized_pnl: number;
  realized_pnl: number;
  total_return_pct: number;
  positions: Position[];
  transactions: any[];
}

export interface PortfolioSummary {
  cash: number;
  market_value: number;
  total_equity: number;
  total_invested: number;
  total_return_pct: number;
  positions_count: number;
}

export const portfolioApi = {
  get: () => api.get<PortfolioState>(`/portfolio`).then((r) => r.data),
  summary: () => api.get<PortfolioSummary>(`/portfolio/summary`).then((r) => r.data),
  transact: (body: {
    symbol: string;
    side: "BUY" | "SELL";
    qty: number;
    price?: number;
    note?: string;
  }) => api.post(`/portfolio/transactions`, body).then((r) => r.data),
  deposit: (amount: number, note?: string) =>
    api.post(`/portfolio/deposit`, { amount, note }).then((r) => r.data),
  withdraw: (amount: number, note?: string) =>
    api.post(`/portfolio/withdraw`, { amount, note }).then((r) => r.data),
  reset: (initial_cash: number) =>
    api.post(`/portfolio/reset`, { initial_cash }).then((r) => r.data),
};

export interface RecommendItem {
  symbol: string;
  name: string | null;
  market: string | null;
  horizon: number;
  strategy: string;
  signal_date: string;
  last_close: number;
  win_rate: number;
  avg_win_pct: number;
  avg_loss_pct: number;
  expected_return_pct: number;
  n_trades: number;
  max_drawdown_pct: number;
  target_high?: number;
  target_low?: number;
  risk_reward_ratio?: number;
}

export interface RecommendRun {
  id: number;
  status: "pending" | "running" | "done" | "failed";
  started_at: string;
  finished_at: string | null;
  scanned: number;
  matched: number;
  total: number;
  universe: string;
  error?: string | null;
}

export interface StrategyCatalogItem {
  key: string;
  name: string;
  category: "trend" | "reversion" | "breakout" | "passive";
  horizon_days: number[];
  indicators: string[];
  default_params: Record<string, number>;
  param_tips: Record<string, string>;
  signal_rule: string;
  when_to_use: string;
  best_for: string[];
  pros: string[];
  cons: string[];
  tune_tips: string;
  use_in: "backtest" | "recommend";
}

export interface StrategyCatalog {
  categories: { key: string; label: string }[];
  items: StrategyCatalogItem[];
  scenarios: { scenario: string; recommend: string; reason: string }[];
}

export const strategiesApi = {
  catalog: (category?: string) =>
    api
      .get<StrategyCatalog>(`/strategies/catalog`, {
        params: category ? { category } : {},
      })
      .then((r) => r.data),
  get: (key: string) =>
    api.get<StrategyCatalogItem>(`/strategies/${key}`).then((r) => r.data),
};

export const recommendApi = {
  horizons: () => api.get<{ horizon: number; strategy: string }[]>(`/recommend/horizons`).then((r) => r.data),
  latest: (horizon: number, limit = 30) =>
    api
      .get<{ horizon: number; run: RecommendRun | null; results: RecommendItem[] }>(
        `/recommend/latest`,
        { params: { horizon, limit } }
      )
      .then((r) => r.data),
  scan: (horizon: number, universe: "top500" | "tw" | "us" | "all" = "top500") =>
    api
      .post<{ run_id: number; status: string }>(`/recommend/scan`, { horizon, universe })
      .then((r) => r.data),
  scanStatus: (runId: number) =>
    api.get<RecommendRun>(`/recommend/scan/${runId}`).then((r) => r.data),
  seedUniverse: (full: boolean) =>
    api.post(`/recommend/seed-universe`, { full }).then((r) => r.data),
};

export interface PredictionItem {
  horizon: number;
  strategy: string;
  n_trades: number;
  win_rate?: number;
  avg_win_pct?: number;
  avg_loss_pct?: number;
  expected_return_pct?: number;
  has_signal_now?: boolean;
  signal_date?: string | null;
  entry?: number;
  target_high?: number;
  target_low?: number;
  upside_pct?: number;
  downside_pct?: number;
  atr?: number;
  atr_pct?: number;
  atr_high?: number;
  atr_low?: number;
  risk_reward_ratio?: number;
  warning?: string;
}

export interface PredictionResponse {
  symbol: string;
  last_close?: number;
  atr?: number;
  predictions: PredictionItem[];
  error?: string;
}

export const predictionApi = {
  forStock: (symbol: string) =>
    api.get<PredictionResponse>(`/predictions/${encodeURIComponent(symbol)}`).then((r) => r.data),
};

export interface VerdictComponent {
  key: string;
  label: string;
  raw_score: number;
  weight: number;
  weighted: number;
  detail: Record<string, any>;
}

export type VerdictEntryMode = "conservative" | "balanced" | "aggressive" | "sma_pullback";

export interface VerdictSuggestion {
  entry_price: number;
  entry_mode?: VerdictEntryMode;
  entry_mode_label?: string;
  buy_low: number;
  buy_high: number;
  target_price: number;
  stop_loss: number;
  upside_pct: number;
  downside_pct: number;
  risk_reward_ratio: number | null;
  action: string;
  hint: string;
  n_strategies_used: number;
}

export interface VerdictResponse {
  symbol: string;
  market: string;
  score: number;
  level: "strong_buy" | "buy" | "hold" | "avoid" | "strong_avoid";
  level_label: string;
  color: string;
  weight_used: number;
  components: VerdictComponent[];
  suggestion: VerdictSuggestion | null;
}

export const verdictApi = {
  forStock: (symbol: string, entryMode: VerdictEntryMode = "balanced") =>
    api
      .get<VerdictResponse>(`/verdict/${encodeURIComponent(symbol)}`, {
        params: { entry_mode: entryMode },
      })
      .then((r) => r.data),
};

export interface EtfRow {
  symbol: string;
  name: string;
  category: string;
  market: string;
  last_close: number;
  currency: string | null;
  aum: number | null;
  expense_ratio: number | null;
  dividend_yield: number | null;
  fund_family: string | null;
  return_1m: number | null;
  return_3m: number | null;
  return_6m: number | null;
  return_1y: number | null;
  inst_net_5d: number | null;
  inst_net_20d: number | null;
}

export interface AiPickStock {
  symbol: string;
  name: string;
  thesis: string;
  risks?: string;
}

export interface AiPickTheme {
  name: string;
  category: string;
  heat_level: "high" | "medium" | "low" | string;
  summary: string;
  drivers: string[];
  stocks: AiPickStock[];
}

export interface AiPicksResponse {
  as_of_date?: string;
  themes: AiPickTheme[];
  source?: string;
  model?: string;
  citations?: string[];
  web_search_used?: boolean;
  generated_at?: string;
  from_cache?: boolean;
  error?: string;
  raw_excerpt?: string;
  top_n?: number;
  theme_hint?: string;
}

export const aiPicksApi = {
  get: (refresh = false, top_n = 10, theme_hint = "") =>
    api
      .get<AiPicksResponse>(`/ai-picks`, {
        params: { refresh, top_n, theme_hint },
        timeout: 600000,
      })
      .then((r) => r.data),
};

export interface AiEtfPickItem {
  symbol: string;
  name: string;
  expense_ratio_hint?: string;
  thesis: string;
  risks?: string;
  off_whitelist?: boolean;
}

export interface AiEtfPickTheme {
  name: string;
  category: string;
  heat_level: "high" | "medium" | "low" | string;
  summary: string;
  drivers: string[];
  etfs: AiEtfPickItem[];
}

export interface AiEtfPicksResponse {
  as_of_date?: string;
  themes: AiEtfPickTheme[];
  source?: string;
  model?: string;
  citations?: string[];
  web_search_used?: boolean;
  generated_at?: string;
  from_cache?: boolean;
  error?: string;
  raw_excerpt?: string;
  top_n?: number;
  theme_hint?: string;
}

export const aiEtfPicksApi = {
  get: (refresh = false, top_n = 8, theme_hint = "") =>
    api
      .get<AiEtfPicksResponse>(`/ai-etf-picks`, {
        params: { refresh, top_n, theme_hint },
        timeout: 600000,
      })
      .then((r) => r.data),
};

export const etfApi = {
  categories: () =>
    api.get<{ key: string; label: string }[]>(`/etfs/categories`).then((r) => r.data),
  ranking: (params: { market?: string; category?: string } = {}) =>
    api
      .get<{ count: number; items: EtfRow[] }>(`/etfs/ranking`, { params })
      .then((r) => r.data),
};

export interface MultiBacktestResult {
  strategy: string;
  scanned: number;
  succeeded: number;
  failed: number;
  summary: {
    avg_total_return: number;
    avg_sharpe: number;
    avg_max_drawdown: number;
    profit_ratio: number;
  };
  results: Array<{
    symbol: string;
    ok: boolean;
    total_return: number;
    annual_return: number;
    max_drawdown: number;
    sharpe: number;
    win_rate: number;
    trades: number;
  }>;
  failures: Array<{ symbol: string; error: string }>;
}

export interface TwInstitutionalRow {
  date: string;
  foreign: number;
  trust: number;
  dealer: number;
  net: number;
}

export interface InsiderRow {
  date: string | null;
  insider: string | null;
  position: string | null;
  transaction: string | null;
  shares: number | null;
  value: number | null;
}

export interface InstitutionalHolder {
  holder: string | null;
  shares: number | null;
  value: number | null;
  pct_held: number | null;
  date_reported: string | null;
}

export interface MoneyFlowIndicatorRow {
  date: string;
  close: number | null;
  volume: number | null;
  mfi: number | null;
  obv: number | null;
  vol_ma20: number | null;
  vol_z: number | null;
}

export interface FundFlowPayload {
  symbol: string;
  market: "TW" | "US";
  indicators: MoneyFlowIndicatorRow[];
  tw_institutional?: TwInstitutionalRow[];
  us_insider?: InsiderRow[];
  us_institutional?: InstitutionalHolder[];
  warnings?: string[];
}

export interface FundFlowAnalysis {
  symbol: string;
  analysis?: string;
  source?: "grok" | "rule";
  model?: string;
  cached?: boolean;
}

export const fundFlowApi = {
  get: (symbol: string) =>
    api.get<FundFlowPayload>(`/fund-flow/${symbol}`).then((r) => r.data),
  analysis: (symbol: string, refresh = false) =>
    api
      .get<FundFlowAnalysis>(`/fund-flow/${symbol}/analysis`, {
        params: refresh ? { refresh: true } : {},
      })
      .then((r) => r.data),
  analysisCheck: (symbol: string) =>
    api
      .get<FundFlowAnalysis>(`/fund-flow/${symbol}/analysis`, {
        params: { check_only: true },
      })
      .then((r) => r.data),
};

export const backtestApi = {
  strategies: () => api.get(`/backtest/strategies`).then((r) => r.data),
  run: (body: {
    symbol: string;
    strategy: string;
    params?: Record<string, any>;
    start?: string;
    end?: string;
    init_cash?: number;
  }) => api.post<BacktestResult>(`/backtest/run`, body).then((r) => r.data),
  runMulti: (body: {
    symbols: string[];
    strategy: string;
    params?: Record<string, any>;
    start?: string;
    end?: string;
    init_cash?: number;
  }) => api.post<MultiBacktestResult>(`/backtest/run-multi`, body).then((r) => r.data),
};
