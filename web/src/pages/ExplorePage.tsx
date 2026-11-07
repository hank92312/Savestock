// Savestock v2 — 🔍 探索頁：全市場 2,370 檔（含上市、上櫃、ETF）極速搜尋、精選 25 檔存股清單與多維策略篩選器

import React, { useMemo, useState } from 'react';
import { useAppStore } from '../store';
import { SecurityCard } from '../components/SecurityCard';
import type { SecuritySummary } from '../types';

type PresetKey = 'curated25' | 'safe_high_yield' | 'cheap_zone' | 'rev_growth' | 'large_holder' | 'all';

export const ExplorePage: React.FC<{
  onSelectSecurity: (code: string) => void;
  onQuickEdit: (item: SecuritySummary) => void;
}> = ({ onSelectSecurity, onQuickEdit }) => {
  const screener = useAppStore((s) => s.screener);
  const [query, setQuery] = useState('');
  const [preset, setPreset] = useState<PresetKey>('curated25');
  const [marketFilter, setMarketFilter] = useState<'ALL' | 'TWSE' | 'TPEX'>('ALL');
  const [minYield, setMinYield] = useState<number>(0);
  const [sortBy, setSortBy] = useState<'yield1y' | 'score' | 'large1000' | 'revYoY'>('yield1y');

  const filteredList = useMemo(() => {
    if (!screener) return [];
    const q = query.trim().toUpperCase();
    const curatedSet = new Set(screener.curatedStockCodes || []);

    let arr = Object.values(screener.items);

    // 若有輸入關鍵字，直接搜尋全市場 2,370 檔
    if (q) {
      arr = arr.filter(
        (it) =>
          it.code.toUpperCase().includes(q) ||
          it.name.toUpperCase().includes(q) ||
          (it.sector || '').includes(q),
      );
    } else {
      switch (preset) {
        case 'curated25':
          arr = arr.filter((it) => curatedSet.has(it.code));
          break;
        case 'safe_high_yield':
          arr = arr.filter(
            (it) =>
              it.yield1y >= 5.0 &&
              it.score.total >= 68 &&
              (!it.payoutRatio || it.payoutRatio <= 100) &&
              !it.alert.flag,
          );
          break;
        case 'cheap_zone':
          arr = arr.filter(
            (it) =>
              (it.priceBands?.zone === 'cheap' || it.priceBands?.zone === 'fair') &&
              it.score.total >= 65 &&
              it.volume >= 200,
          );
          break;
        case 'rev_growth':
          arr = arr.filter(
            (it) =>
              (it.revYoY || 0) >= 15 &&
              it.yield1y >= 3.5 &&
              (it.pe || 99) <= 22 &&
              it.volume >= 300,
          );
          break;
        case 'large_holder':
          arr = arr.filter(
            (it) =>
              (it.largeHolder1000Pct || 0) >= 65 &&
              it.yield1y >= 4.0 &&
              it.volume >= 200,
          );
          break;
        case 'all':
        default:
          arr = arr.filter((it) => it.volume >= 100);
          break;
      }
    }

    if (marketFilter !== 'ALL') {
      arr = arr.filter((it) => it.market === marketFilter);
    }
    if (minYield > 0) {
      arr = arr.filter((it) => (it.yield1y || 0) >= minYield);
    }

    arr.sort((a, b) => {
      if (sortBy === 'score') return b.score.total - a.score.total;
      if (sortBy === 'large1000') return (b.largeHolder1000Pct || 0) - (a.largeHolder1000Pct || 0);
      if (sortBy === 'revYoY') return (b.revYoY || -999) - (a.revYoY || -999);
      return (b.yield1y || 0) - (a.yield1y || 0);
    });

    return arr.slice(0, 90);
  }, [screener, query, preset, marketFilter, minYield, sortBy]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      <div>
        <h1 style={{ fontSize: 22, fontWeight: 700 }}>🔍 探索全市場與精選存股清單</h1>
        <p className="text-muted" style={{ fontSize: 13.5 }}>
          涵蓋全部上市、上櫃與 ETF 共 {Object.keys(screener?.items || {}).length} 檔證券，所有指標與健康分數皆已預先算好，搜尋與篩選零等待。
        </p>
      </div>

      {/* 搜尋與過濾控制列 */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <input
            className="input"
            style={{ flex: 1, minWidth: 240 }}
            placeholder="輸入股票代號、中文名稱或產業（如：2412、金融、上櫃、00679B）..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <select
            className="input"
            style={{ width: 'auto' }}
            value={marketFilter}
            onChange={(e) => setMarketFilter(e.target.value as any)}
          >
            <option value="ALL">全部市場 (上市+上櫃)</option>
            <option value="TWSE">僅上市 (TWSE)</option>
            <option value="TPEX">僅上櫃 (TPEx)</option>
          </select>
          <select
            className="input"
            style={{ width: 'auto' }}
            value={minYield}
            onChange={(e) => setMinYield(Number(e.target.value))}
          >
            <option value={0}>不限殖利率</option>
            <option value={4}>殖利率 ≥ 4%</option>
            <option value={5}>殖利率 ≥ 5%</option>
            <option value={6}>殖利率 ≥ 6%</option>
          </select>
          <select
            className="input"
            style={{ width: 'auto' }}
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
          >
            <option value="yield1y">依近1年殖利率排序</option>
            <option value="score">依存股健康分數排序</option>
            <option value="large1000">依千張大戶比例排序</option>
            <option value="revYoY">依月營收年增率排序</option>
          </select>
        </div>

        {/* 預設選股策略膠囊 */}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {[
            { id: 'curated25', label: '⭐ 精選 25 檔存股清單' },
            { id: 'safe_high_yield', label: '🛡️ 高息且安全 (≥5% · 非超額配息)' },
            { id: 'cheap_zone', label: '💰 進入便宜/合理區高分股' },
            { id: 'rev_growth', label: '🚀 營收成長 + 低本益比' },
            { id: 'large_holder', label: '🐋 千張大戶高集中度 (≥65%)' },
            { id: 'all', label: '📋 全市場瀏覽' },
          ].map((p) => (
            <button
              key={p.id}
              className={`chip ${!query && preset === p.id ? 'active' : ''}`}
              onClick={() => {
                setQuery('');
                setPreset(p.id as PresetKey);
              }}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* 結果卡片網格 */}
      <div className="grid-3">
        {filteredList.map((item) => (
          <SecurityCard
            key={item.code}
            item={item}
            onSelect={onSelectSecurity}
            onQuickEdit={onQuickEdit}
          />
        ))}
      </div>
    </div>
  );
};

