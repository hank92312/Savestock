// Savestock v2 — 🏠 總覽頁：持股總市值、今年股利進度、12個月現金流月曆、即將除權息日程與今日警示

import React, { useMemo } from 'react';
import { useAppStore } from '../store';
import { evaluatePortfolio } from '../calc';
import { MonthlyBarChart } from '../components/Charts';
import { SecurityCard } from '../components/SecurityCard';
import type { SecuritySummary } from '../types';

export const DashboardPage: React.FC<{
  onSelectSecurity: (code: string) => void;
  onQuickEdit: (item: SecuritySummary) => void;
  onNavigateTab: (tab: string) => void;
}> = ({ onSelectSecurity, onQuickEdit, onNavigateTab }) => {
  const meta = useAppStore((s) => s.meta);
  const screener = useAppStore((s) => s.screener);
  const calendar = useAppStore((s) => s.calendar);
  const userDoc = useAppStore((s) => s.userDoc);

  const pf = useMemo(
    () => evaluatePortfolio(userDoc.holdings, screener?.items || {}),
    [userDoc.holdings, screener],
  );

  const myCodes = useMemo(
    () => new Set(Object.values(userDoc.holdings).filter((h) => !h.deleted).map((h) => h.code)),
    [userDoc.holdings],
  );

  const alertsList = useMemo(() => {
    if (!screener) return [];
    const items = Object.values(screener.items).filter((it) => it.alert?.flag);
    // 優先顯示使用者持有或觀察中、其次精選清單
    items.sort((a, b) => {
      const aMine = myCodes.has(a.code) ? 2 : a.curated ? 1 : 0;
      const bMine = myCodes.has(b.code) ? 2 : b.curated ? 1 : 0;
      return bMine - aMine || a.changePct - b.changePct;
    });
    return items.slice(0, 8);
  }, [screener, myCodes]);

  const cheapCurated = useMemo(() => {
    if (!screener) return [];
    return Object.values(screener.items)
      .filter((it) => it.curated && (it.priceBands?.zone === 'cheap' || it.priceBands?.zone === 'fair'))
      .sort((a, b) => b.score.total - a.score.total)
      .slice(0, 6);
  }, [screener]);

  const myEvents = useMemo(() => {
    const mine = calendar.filter((e) => myCodes.has(e.code));
    return (mine.length > 0 ? mine : calendar).slice(0, 8);
  }, [calendar, myCodes]);

  const monthlyAvg = Math.round(pf.totalNetDiv / 12);
  const targetMonthly = userDoc.settings.targetMonthlyDividend || 20000;
  const targetPct = Math.min(100, Math.round((monthlyAvg / Math.max(targetMonthly, 1)) * 100));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* 頂部問候與資料日期橫幅 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: 10 }}>
        <div>
          <h1 style={{ fontSize: 23, fontWeight: 700 }}>
            早安，{userDoc.settings.nickname || '存股夥伴'}
          </h1>
          <p className="text-muted" style={{ fontSize: 13.5 }}>
            全市場靜態極速模式 ‧ 收盤資料基準日：{meta?.marketDate || '--'}（涵蓋上市 {meta?.counts.twse} 檔、上櫃 {meta?.counts.tpex} 檔、完整 ETF {meta?.sources.etfHoldings} 檔）
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn" onClick={() => onNavigateTab('portfolio')}>管理我的持股</button>
          <button className="btn btn-primary" onClick={() => onNavigateTab('explore')}>探索全市場</button>
        </div>
      </div>

      {/* 頂部四大核心總覽指標卡 */}
      <div className="grid-4">
        <div className="card">
          <div className="text-muted" style={{ fontSize: 12.5 }}>持股總市值</div>
          <div style={{ fontSize: 25, fontWeight: 700, marginTop: 4 }}>
            ${pf.totalMarketValue.toLocaleString()}
          </div>
          <div className={pf.totalUnrealizedPnl >= 0 ? 'text-up' : 'text-down'} style={{ fontSize: 12.5, fontWeight: 600, marginTop: 4 }}>
            帳面損益 {pf.totalUnrealizedPnl >= 0 ? '+' : ''}{pf.totalUnrealizedPnl.toLocaleString()} ({pf.totalUnrealizedPnlPct.toFixed(1)}%)
          </div>
        </div>

        <div className="card">
          <div className="text-muted" style={{ fontSize: 12.5 }}>今年預估實領股利（扣補充保費）</div>
          <div style={{ fontSize: 25, fontWeight: 700, color: 'var(--brand)', marginTop: 4 }}>
            ${pf.totalNetDiv.toLocaleString()}
          </div>
          <div className="text-muted" style={{ fontSize: 12, marginTop: 4 }}>
            毛額 ${pf.totalGrossDiv.toLocaleString()} ｜ 二代健保 -${pf.totalNhiSurcharge.toLocaleString()}
          </div>
        </div>

        <div className="card">
          <div className="text-muted" style={{ fontSize: 12.5 }}>組合殖利率 / 成本殖利率</div>
          <div style={{ fontSize: 25, fontWeight: 700, marginTop: 4 }}>
            {pf.portfolioYieldPct.toFixed(2)}%
            <span className="text-brand" style={{ fontSize: 15, marginLeft: 8 }}>
              (成本 {pf.portfolioYieldOnCostPct.toFixed(2)}%)
            </span>
          </div>
          <div className="text-muted" style={{ fontSize: 12, marginTop: 4 }}>
            持有 {pf.activePositions.length} 檔 ‧ 觀察 {pf.watchlist.length} 檔
          </div>
        </div>

        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5 }}>
            <span className="text-muted">月均被動收入目標進度</span>
            <span style={{ fontWeight: 700 }}>{targetPct}%</span>
          </div>
          <div style={{ fontSize: 22, fontWeight: 700, marginTop: 4 }}>
            ${monthlyAvg.toLocaleString()} <span className="text-muted" style={{ fontSize: 13, fontWeight: 400 }}>/ 目標 ${targetMonthly.toLocaleString()}</span>
          </div>
          <div style={{ height: 7, background: 'var(--bg-subtle)', borderRadius: 99, marginTop: 8, overflow: 'hidden' }}>
            <div style={{ width: `${targetPct}%`, height: '100%', background: 'var(--brand)', borderRadius: 99 }} />
          </div>
        </div>
      </div>

      {/* 12 個月股利現金流月曆 + 近期除權息日程 */}
      <div className="grid-2">
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
            <h2 style={{ fontSize: 16.5, fontWeight: 700 }}>📅 12 個月預估股利現金流分佈</h2>
            <span className="badge badge-brand">月均 ${monthlyAvg.toLocaleString()}</span>
          </div>
          <p className="text-muted" style={{ fontSize: 12.5 }}>
            依各檔 ETF 配息月份（季配 1/4/7/10、2/5/8/11、3/6/9/12、月配）與年配股自動攤算
          </p>
          <MonthlyBarChart values={pf.monthlyCashflow} targetLine={targetMonthly} />
        </div>

        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <h2 style={{ fontSize: 16.5, fontWeight: 700 }}>🔔 近期除權息預告日程（證交所 / 櫃買中心）</h2>
            <span className="text-muted" style={{ fontSize: 12 }}>優先顯示持股</span>
          </div>
          {myEvents.length === 0 ? (
            <div className="text-muted" style={{ padding: 20 }}>近期暫無除權息預告事件</div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {myEvents.map((ev, idx) => (
                <div
                  key={`${ev.code}-${ev.date}-${idx}`}
                  onClick={() => onSelectSecurity(ev.code)}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '8px 11px',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--bg-subtle)',
                    cursor: 'pointer',
                  }}
                >
                  <div>
                    <span className="badge badge-brand" style={{ marginRight: 8 }}>{ev.date}</span>
                    <strong>{ev.name}</strong> <span className="text-muted" style={{ fontSize: 12.5 }}>({ev.code})</span>
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 600 }}>
                    {ev.cashDiv > 0 ? `現金 ${ev.cashDiv} 元` : ''}
                    {ev.stockDiv > 0 ? ` 配股 ${ev.stockDiv} 元` : ''}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 今日自適應異常警示區 */}
      {alertsList.length > 0 && (
        <div className="card" style={{ borderColor: 'var(--warn)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div>
              <h2 style={{ fontSize: 16.5, fontWeight: 700 }}>🚨 今日異常波動與下跌爆量防護警示</h2>
              <p className="text-muted" style={{ fontSize: 12.5 }}>
                採用「自適應 60 日波動率門檻 + 產業分級地板」，僅在異常重挫或下跌爆量時觸發，協助避開高殖利率陷阱
              </p>
            </div>
            <span className="badge badge-danger">全市場共 {meta?.counts.alertsToday || alertsList.length} 檔觸發</span>
          </div>
          <div className="grid-3">
            {alertsList.map((item) => (
              <SecurityCard key={item.code} item={item} onSelect={onSelectSecurity} onQuickEdit={onQuickEdit} />
            ))}
          </div>
        </div>
      )}

      {/* 進入便宜 / 合理偏低區的精選高分標的 */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div>
            <h2 style={{ fontSize: 17, fontWeight: 700 }}>🌱 目前位於「便宜 / 合理偏低區」的精選高分存股</h2>
            <p className="text-muted" style={{ fontSize: 13 }}>
              依平均股利反推殖利率 ≥ 5% 且存股健康評分最高之精選清單標的
            </p>
          </div>
          <button className="btn" onClick={() => onNavigateTab('explore')}>查看全部精選清單 →</button>
        </div>
        <div className="grid-3">
          {cheapCurated.map((item) => (
            <SecurityCard key={item.code} item={item} onSelect={onSelectSecurity} onQuickEdit={onQuickEdit} />
          ))}
        </div>
      </div>
    </div>
  );
};

