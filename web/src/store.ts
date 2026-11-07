// Savestock v2 — 全域狀態、靜態 JSON 載入快取、IndexedDB 持久化與 Cloudflare D1 跨裝置同步引擎

import { create } from 'zustand';
import { openDB } from 'idb';
import type {
  MetaData,
  ScreenerPayload,
  SecuritySummary,
  SecurityDetail,
  CalendarEvent,
  EtfAnalyticsPayload,
  UserHolding,
  UserSettings,
  UserSyncDoc,
} from './types';

const DB_NAME = 'savestock_v2';
const STORE_NAME = 'kv';
const DOC_KEY = 'user_sync_doc';
const TOKEN_KEY = 'sync_device_token';

async function getIdb() {
  return openDB(DB_NAME, 1, {
    upgrade(db) {
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME);
      }
    },
  });
}

// 預設把精選高息股與中華電放進初始體驗清單，讓首次開啟就有豐富畫面（updatedAt: 0 確保雲端任何實際持股皆可優先覆蓋）
const DEFAULT_HOLDINGS: Record<string, UserHolding> = {
  '0056': { code: '0056', shares: 5000, avgCost: 36.8, basis: '1y', updatedAt: 0 },
  '00878': { code: '00878', shares: 6000, avgCost: 21.5, basis: '1y', updatedAt: 0 },
  '00919': { code: '00919', shares: 4000, avgCost: 24.2, basis: '1y', updatedAt: 0 },
  '2412': { code: '2412', shares: 2000, avgCost: 118.0, basis: '1y', updatedAt: 0 },
  '2892': { code: '2892', shares: 3000, avgCost: 26.5, basis: '1y', updatedAt: 0 },
  '2886': { code: '2886', shares: 0, avgCost: 0, basis: '1y', updatedAt: 0 }, // 0 股 = 觀察清單
};

const PROD_SYNC_URL = 'https://savestock-sync.hank92312.workers.dev';

const DEFAULT_SETTINGS: UserSettings = {
  theme: 'light',
  notifyDaily: true,
  notifyWeekly: true,
  email: '',
  nickname: '存股夥伴',
  targetMonthlyDividend: 20000,
  syncApiUrl: localStorage.getItem('savestock_sync_api') || PROD_SYNC_URL,
};

export function mergeUserDocs(local: UserSyncDoc, remote: UserSyncDoc): UserSyncDoc {
  const mergedHoldings: Record<string, UserHolding> = { ...remote.holdings };
  for (const [code, lh] of Object.entries(local.holdings)) {
    const rh = mergedHoldings[code];
    if (!rh || (lh.updatedAt || 0) >= (rh.updatedAt || 0)) {
      mergedHoldings[code] = lh;
    }
  }
  const customSet = Array.from(new Set([...(remote.customEtfs || []), ...(local.customEtfs || [])]));
  const newerSettings = (local.updatedAt || 0) >= (remote.updatedAt || 0) ? local.settings : remote.settings;
  return {
    version: Math.max(local.version || 0, remote.version || 0) + 1,
    holdings: mergedHoldings,
    customEtfs: customSet,
    settings: { ...DEFAULT_SETTINGS, ...newerSettings },
    updatedAt: Date.now(),
  };
}

interface AppState {
  // 市場靜態資料
  loading: boolean;
  error: string | null;
  meta: MetaData | null;
  screener: ScreenerPayload | null;
  calendar: CalendarEvent[];
  etfAnalytics: EtfAnalyticsPayload | null;
  detailsCache: Record<string, SecurityDetail>;

  // 使用者跨裝置同步狀態
  userDoc: UserSyncDoc;
  deviceToken: string;
  syncStatus: 'idle' | 'syncing' | 'synced' | 'offline';
  lastSyncedAt: string | null;

  // Actions
  initApp: () => Promise<void>;
  fetchDetail: (code: string) => Promise<SecurityDetail | null>;
  loadEtfAnalytics: () => Promise<EtfAnalyticsPayload | null>;
  upsertHolding: (code: string, shares: number, avgCost: number, basis?: '1y' | '5y') => Promise<void>;
  removeHolding: (code: string) => Promise<void>;
  clearAllHoldings: () => Promise<void>;
  addCustomEtf: (code: string) => Promise<void>;
  removeCustomEtf: (code: string) => Promise<void>;
  updateSettings: (patch: Partial<UserSettings>) => Promise<void>;
  setDeviceToken: (token: string, apiUrl?: string) => Promise<void>;
  syncWithCloud: (forcePull?: boolean) => Promise<boolean>;
  importDocJson: (rawJson: string) => Promise<void>;
}

const baseUrl = import.meta.env.BASE_URL || '/';

export const useAppStore = create<AppState>((set, get) => ({
  loading: true,
  error: null,
  meta: null,
  screener: null,
  calendar: [],
  etfAnalytics: null,
  detailsCache: {},

  userDoc: {
    version: 1,
    holdings: DEFAULT_HOLDINGS,
    customEtfs: [],
    settings: DEFAULT_SETTINGS,
    updatedAt: Date.now(),
  },
  deviceToken: localStorage.getItem(TOKEN_KEY) || '',
  syncStatus: 'idle',
  lastSyncedAt: null,

  initApp: async () => {
    try {
      // 1. 先從 IndexedDB 載入本機持股與設定（0ms 呈現）
      const db = await getIdb();
      const savedDoc = (await db.get(STORE_NAME, DOC_KEY)) as UserSyncDoc | undefined;
      if (savedDoc && savedDoc.holdings) {
        const merged = {
          ...savedDoc,
          settings: { ...DEFAULT_SETTINGS, ...savedDoc.settings },
        };
        set({ userDoc: merged });
        applyTheme(merged.settings.theme);
      } else {
        await db.put(STORE_NAME, get().userDoc, DOC_KEY);
        applyTheme(DEFAULT_SETTINGS.theme);
      }

      // 2. 載入靜態 meta.json + screener.json + calendar.json
      const metaRes = await fetch(`${baseUrl}data/meta.json?t=${Date.now()}`, { cache: 'no-store' });
      if (!metaRes.ok) throw new Error('無法讀取市場資料 meta.json');
      const meta: MetaData = await metaRes.json();
      const v = meta.version;

      const [scrRes, calRes] = await Promise.all([
        fetch(`${baseUrl}data/screener.json?v=${v}`),
        fetch(`${baseUrl}data/calendar.json?v=${v}`),
      ]);
      const screener: ScreenerPayload = await scrRes.json();
      const calPayload = calRes.ok ? await calRes.json() : { events: [] };

      set({
        meta,
        screener,
        calendar: calPayload.events || [],
        loading: false,
        error: null,
      });

      // 3. 若已綁定 Cloudflare Worker Token，背景執行跨裝置同步
      if (get().deviceToken && get().userDoc.settings.syncApiUrl) {
        get().syncWithCloud(true);
      }
    } catch (e: any) {
      set({ loading: false, error: e?.message || '載入資料失敗' });
    }
  },

  fetchDetail: async (code: string) => {
    const clean = code.replace('.TW', '').replace('.TWO', '').toUpperCase();
    const cached = get().detailsCache[clean];
    if (cached) return cached;

    const v = get().meta?.version || '';
    try {
      const res = await fetch(`${baseUrl}data/s/${clean}.json?v=${v}`);
      if (res.ok) {
        const detail: SecurityDetail = await res.json();
        set((s) => ({ detailsCache: { ...s.detailsCache, [clean]: detail } }));
        return detail;
      }
    } catch {
      // Fallback: 用 screener summary 動態合成輕量詳情（全市場 2,370 檔皆可開啟詳情頁！）
    }

    const sum: SecuritySummary | undefined = get().screener?.items[clean];
    if (!sum) return null;

    const fallbackDetail: SecurityDetail = {
      code: sum.code,
      name: sum.name,
      market: sum.market,
      type: sum.type,
      sector: sum.sector,
      updatedAt: get().meta?.marketDate || '',
      summary: sum,
      scoreBreakdown: {
        total: sum.score.total,
        grade: sum.score.grade,
        dimensions: [
          { key: 'dividend', label: '股利品質', score: Math.round(sum.score.total * 0.35), max: 35 },
          { key: 'valuation', label: '估值與成本', score: Math.round(sum.score.total * 0.25), max: 25 },
          { key: 'fundamentals', label: '基本面趨勢', score: Math.round(sum.score.total * 0.25), max: 25 },
          { key: 'chips_risk', label: '籌碼與風險', score: Math.round(sum.score.total * 0.15), max: 15 },
        ],
        positives: sum.score.positives,
        cautions: sum.score.cautions,
      },
      prices: [{ date: get().meta?.marketDate || '', close: sum.price, volume: sum.volume }],
      dividends: sum.div1y > 0 ? [{
        year: new Date().getFullYear(),
        exDate: get().meta?.marketDate || '',
        payDate: '-',
        cash: sum.div1y,
        stock: 0,
        total: sum.div1y,
      }] : [],
      valuationHistory: [],
      fundamentals: {
        revYm: sum.revYm,
        revYoY: sum.revYoY,
        revMoM: sum.revMoM,
        epsTtm: sum.epsTtm,
        payoutRatio: sum.payoutRatio,
      },
      chips: {
        largeHolder1000Pct: sum.largeHolder1000Pct,
        largeHolder400Pct: sum.largeHolder400Pct,
        shareholders: sum.shareholders,
      },
      risk: {
        adaptive_drop_threshold: sum.alert.thresholdPct,
        alert_flag: sum.alert.flag,
        alert_reasons: sum.alert.reasons,
        vol_info: sum.alert.volInfo,
      },
      etfInfo: sum.etf ? {
        ...sum.etf,
        completeness: 'summary',
        holdings: [],
      } : null,
    };
    set((s) => ({ detailsCache: { ...s.detailsCache, [clean]: fallbackDetail } }));
    return fallbackDetail;
  },

  loadEtfAnalytics: async () => {
    const existing = get().etfAnalytics;
    if (existing) return existing;
    const v = get().meta?.version || '';
    try {
      const res = await fetch(`${baseUrl}data/etf/analytics.json?v=${v}`);
      if (res.ok) {
        const data: EtfAnalyticsPayload = await res.json();
        set({ etfAnalytics: data });
        return data;
      }
    } catch {
      // ignore
    }
    return null;
  },

  upsertHolding: async (code, shares, avgCost, basis = '1y') => {
    const clean = code.replace('.TW', '').replace('.TWO', '').toUpperCase();
    const doc = get().userDoc;
    const nextDoc: UserSyncDoc = {
      ...doc,
      version: (doc.version || 1) + 1,
      updatedAt: Date.now(),
      holdings: {
        ...doc.holdings,
        [clean]: {
          code: clean,
          shares: Math.max(0, Math.round(shares)),
          avgCost: Math.max(0, Number(avgCost) || 0),
          basis,
          updatedAt: Date.now(),
          deleted: false,
        },
      },
    };
    set({ userDoc: nextDoc });
    const db = await getIdb();
    await db.put(STORE_NAME, nextDoc, DOC_KEY);
    get().syncWithCloud(false);
  },

  removeHolding: async (code) => {
    const clean = code.replace('.TW', '').replace('.TWO', '').toUpperCase();
    const doc = get().userDoc;
    const nextHoldings = { ...doc.holdings };
    if (nextHoldings[clean]) {
      nextHoldings[clean] = { ...nextHoldings[clean], deleted: true, updatedAt: Date.now() };
    }
    const nextDoc: UserSyncDoc = {
      ...doc,
      version: (doc.version || 1) + 1,
      updatedAt: Date.now(),
      holdings: nextHoldings,
    };
    set({ userDoc: nextDoc });
    const db = await getIdb();
    await db.put(STORE_NAME, nextDoc, DOC_KEY);
    get().syncWithCloud(false);
  },

  clearAllHoldings: async () => {
    const doc = get().userDoc;
    const nextHoldings: Record<string, UserHolding> = {};
    for (const [code, h] of Object.entries(doc.holdings)) {
      nextHoldings[code] = { ...h, deleted: true, updatedAt: Date.now() };
    }
    const nextDoc: UserSyncDoc = {
      ...doc,
      version: (doc.version || 1) + 1,
      updatedAt: Date.now(),
      holdings: nextHoldings,
    };
    set({ userDoc: nextDoc });
    const db = await getIdb();
    await db.put(STORE_NAME, nextDoc, DOC_KEY);
    get().syncWithCloud(false);
  },

  addCustomEtf: async (code) => {
    const clean = code.replace('.TW', '').replace('.TWO', '').toUpperCase();
    const doc = get().userDoc;
    if (doc.customEtfs.includes(clean)) return;
    const nextDoc: UserSyncDoc = {
      ...doc,
      version: (doc.version || 1) + 1,
      updatedAt: Date.now(),
      customEtfs: [...doc.customEtfs, clean],
    };
    set({ userDoc: nextDoc });
    const db = await getIdb();
    await db.put(STORE_NAME, nextDoc, DOC_KEY);
    get().syncWithCloud(false);
  },

  removeCustomEtf: async (code) => {
    const clean = code.replace('.TW', '').replace('.TWO', '').toUpperCase();
    const doc = get().userDoc;
    const nextDoc: UserSyncDoc = {
      ...doc,
      version: (doc.version || 1) + 1,
      updatedAt: Date.now(),
      customEtfs: doc.customEtfs.filter((c) => c !== clean),
    };
    set({ userDoc: nextDoc });
    const db = await getIdb();
    await db.put(STORE_NAME, nextDoc, DOC_KEY);
    get().syncWithCloud(false);
  },

  updateSettings: async (patch) => {
    const doc = get().userDoc;
    const nextSettings = { ...doc.settings, ...patch };
    if (patch.syncApiUrl !== undefined) {
      localStorage.setItem('savestock_sync_api', patch.syncApiUrl.trim());
    }
    if (patch.theme) {
      applyTheme(patch.theme);
    }
    const nextDoc: UserSyncDoc = {
      ...doc,
      version: (doc.version || 1) + 1,
      updatedAt: Date.now(),
      settings: nextSettings,
    };
    set({ userDoc: nextDoc });
    const db = await getIdb();
    await db.put(STORE_NAME, nextDoc, DOC_KEY);
    get().syncWithCloud(false);
  },

  setDeviceToken: async (token, apiUrl) => {
    localStorage.setItem(TOKEN_KEY, token.trim());
    if (apiUrl) {
      localStorage.setItem('savestock_sync_api', apiUrl.trim());
      await get().updateSettings({ syncApiUrl: apiUrl.trim() });
    }
    set({ deviceToken: token.trim() });
    if (token.trim()) {
      await get().syncWithCloud(true);
    }
  },

  syncWithCloud: async (forcePull = false) => {
    const token = get().deviceToken;
    const apiUrl = (get().userDoc.settings.syncApiUrl || '').replace(/\/+$/, '');
    if (!token || !apiUrl) return false;

    set({ syncStatus: 'syncing' });
    try {
      const headers = {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      };

      if (forcePull) {
        const res = await fetch(`${apiUrl}/v1/doc`, { headers });
        if (res.ok) {
          const remoteWrap = await res.json();
          if (remoteWrap && remoteWrap.doc) {
            // 若為強制拉取且雲端已有版本，直接以雲端為準（避免新裝置初始範例污染）
            const nextDoc = (remoteWrap.doc.version || 0) > 1 ? remoteWrap.doc : mergeUserDocs(get().userDoc, remoteWrap.doc);
            set({ userDoc: nextDoc });
            const db = await getIdb();
            await db.put(STORE_NAME, nextDoc, DOC_KEY);
            applyTheme(nextDoc.settings?.theme || 'light');
          }
        }
      }

      const pushRes = await fetch(`${apiUrl}/v1/doc`, {
        method: 'PUT',
        headers,
        body: JSON.stringify({ doc: get().userDoc }),
      });
      if (pushRes.status === 409) {
        const conflict = await pushRes.json();
        if (conflict.serverDoc) {
          const merged = mergeUserDocs(get().userDoc, conflict.serverDoc);
          set({ userDoc: merged });
          const db = await getIdb();
          await db.put(STORE_NAME, merged, DOC_KEY);
          await fetch(`${apiUrl}/v1/doc`, {
            method: 'PUT',
            headers,
            body: JSON.stringify({ doc: merged, force: true }),
          });
        }
      }

      const nowStr = new Date().toLocaleTimeString('zh-TW', { hour12: false });
      set({ syncStatus: 'synced', lastSyncedAt: nowStr });
      return true;
    } catch {
      set({ syncStatus: 'offline' });
      return false;
    }
  },

  importDocJson: async (rawJson: string) => {
    const parsed = JSON.parse(rawJson) as UserSyncDoc;
    const merged = mergeUserDocs(get().userDoc, parsed);
    set({ userDoc: merged });
    const db = await getIdb();
    await db.put(STORE_NAME, merged, DOC_KEY);
    applyTheme(merged.settings.theme);
    await get().syncWithCloud(false);
  },
}));

function applyTheme(theme: 'light' | 'dark' | 'auto') {
  if (theme === 'auto') {
    const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
  } else {
    document.documentElement.setAttribute('data-theme', theme);
  }
}

// 當使用者從手機或 PC 切回瀏覽器分頁時，自動拉取最新雲端持股
if (typeof document !== 'undefined') {
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      const st = useAppStore.getState();
      if (st.deviceToken && st.userDoc.settings.syncApiUrl) {
        st.syncWithCloud(true);
      }
    }
  });
}

