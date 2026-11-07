// Savestock v2 — 前端與靜態資料型別定義

export interface MetaData {
  version: string;
  marketDate: string;
  updatedAt: string;
  counts: {
    total: number;
    twse: number;
    tpex: number;
    curatedStocks: number;
    curatedEtfs: number;
    alertsToday: number;
  };
  sources: {
    twseDaily: string;
    tpexDaily: string;
    etfHoldings: string;
    tdccDate: string;
  };
}

export type PriceZone = 'cheap' | 'fair' | 'warm' | 'expensive' | 'unknown';

export interface SecuritySummary {
  code: string;
  name: string;
  market: 'TWSE' | 'TPEX' | string;
  type: 'stock' | 'etf';
  sector: string;
  etfGroup?: string | null;
  tags: string[];
  curated: boolean;
  price: number;
  change: number;
  changePct: number;
  volume: number;
  yield1y: number;
  yield2y: number;
  yield5y: number;
  div1y: number;
  div2y: number;
  div5y: number;
  paidThisYear: number;
  announcedDiv?: number | null;
  pe?: number | null;
  pb?: number | null;
  pePercentile5y?: number | null;
  yieldPercentile5y?: number | null;
  consecDivYears: number;
  divCv5y?: number | null;
  divCagr5y?: number | null;
  payoutRatio?: number | null;
  revYm?: string | null;
  revYoY?: number | null;
  revMoM?: number | null;
  epsTtm?: number | null;
  largeHolder1000Pct?: number | null;
  largeHolder400Pct?: number | null;
  shareholders?: number | null;
  priceBands: {
    cheap?: number | null;
    fair?: number | null;
    expensive?: number | null;
    zone: PriceZone;
  };
  score: {
    total: number;
    grade: string;
    positives: string[];
    cautions: string[];
  };
  alert: {
    flag: boolean;
    reasons: string[];
    volInfo?: string | null;
    thresholdPct: number;
  };
  etf?: {
    nav?: number | null;
    discountPct?: number | null;
    expenseRatioPct?: number | null;
    aumHundredMillions?: number | null;
    holdersCount?: number | null;
    divFrequency?: string | null;
    issuer?: string | null;
    returns: {
      m1?: number | null;
      m3?: number | null;
      m6?: number | null;
      y1?: number | null;
      y3?: number | null;
      y5?: number | null;
    };
    holdingsCount: number;
  } | null;
}

export interface ScreenerPayload {
  version: string;
  marketDate: string;
  curatedStockCodes: string[];
  curatedEtfCodes: string[];
  items: Record<string, SecuritySummary>;
}

export interface CalendarEvent {
  date: string;
  code: string;
  name: string;
  eventType: 'ex_date' | 'pay_date' | string;
  cashDiv: number;
  stockDiv: number;
  note: string;
}

export interface EtfHoldingItem {
  stock_id: string;
  name: string;
  weight: number;
  shares?: number;
  price?: number | null;
  changePct?: number | null;
  yield1y?: number | null;
}

export interface SecurityDetail {
  code: string;
  name: string;
  market: string;
  type: 'stock' | 'etf';
  sector: string;
  updatedAt: string;
  summary: SecuritySummary;
  scoreBreakdown: {
    total: number;
    grade: string;
    dimensions: { key: string; label: string; score: number; max: number }[];
    positives: string[];
    cautions: string[];
  };
  prices: { date: string; close: number; volume: number }[];
  dividends: {
    year: number;
    exDate: string;
    payDate: string;
    cash: number;
    stock: number;
    total: number;
    annualizedYieldPct?: number | null;
  }[];
  valuationHistory: { date: string; pe?: number | null; pb?: number | null; yield?: number | null }[];
  fundamentals: {
    revYm?: string | null;
    rev?: number | null;
    revYoY?: number | null;
    revMoM?: number | null;
    cumYoY?: number | null;
    epsTtm?: number | null;
    payoutRatio?: number | null;
  };
  chips: {
    tdccDate?: string;
    largeHolder1000Pct?: number | null;
    largeHolder400Pct?: number | null;
    shareholders?: number | null;
  };
  risk: {
    volatility_1y?: number | null;
    max_drawdown_1y?: number | null;
    adaptive_drop_threshold: number;
    alert_flag: boolean;
    alert_reasons: string[];
    vol_info?: string | null;
  };
  etfInfo?: {
    nav?: number | null;
    discountPct?: number | null;
    expenseRatioPct?: number | null;
    aumHundredMillions?: number | null;
    holdersCount?: number | null;
    divFrequency?: string | null;
    issuer?: string | null;
    trackingIndex?: string | null;
    listingDate?: string | null;
    completeness: string;
    returns: Record<string, number | null>;
    holdings: EtfHoldingItem[];
  } | null;
}

export interface EtfAnalyticsPayload {
  version: string;
  marketDate: string;
  consensus: {
    stock_id: string;
    name: string;
    etf_count: number;
    total_weight: number;
    avg_weight: number;
    etf_list: string[];
  }[];
  hiddenWinners: {
    stock_id: string;
    name: string;
    etf_count: number;
    avg_weight: number;
    total_weight: number;
    etf_list: string[];
    hidden_score: number;
  }[];
  heatmap: {
    etfs: string[];
    stocks: { stock_id: string; name: string }[];
    matrix: number[][];
  };
  factorRanking: {
    rank: number;
    stock_id: string;
    name: string;
    etf_count: number;
    hidden_score: number;
    momentum: number;
    ai_score: number;
    etf_list: string[];
  }[];
  pairwiseOverlap: {
    etfs: string[];
    matrix: number[][];
  };
  holdingsByEtf: Record<string, EtfHoldingItem[]>;
}

// ── 使用者跨裝置同步文件（D1 & IndexedDB 共用）─────────────────────────
export interface UserHolding {
  code: string;
  shares: number;      // 股數（0 代表僅觀察）
  avgCost: number;     // 平均買進成本（元/股）
  basis: '1y' | '5y';  // 未公告配息時的估算基準
  note?: string;
  updatedAt: number;
  deleted?: boolean;
}

export interface UserSettings {
  theme: 'light' | 'dark' | 'auto';
  notifyDaily: boolean;
  notifyWeekly: boolean;
  email: string;
  nickname: string;
  targetMonthlyDividend: number;
  syncApiUrl: string;
}

export interface UserSyncDoc {
  version: number;
  holdings: Record<string, UserHolding>;
  customEtfs: string[];
  settings: UserSettings;
  updatedAt: number;
}
