// Savestock v2 — 💼 我的持股頁：整合持有中 + 觀察清單 + 年度股利試算（含二代健保補充保費）+ 目標月領與複利模擬

import React, { useMemo, useState } from 'react';
import { useAppStore } from '../store';
import { evaluatePortfolio, simulateCompoundGrowth } from '../calc';
import { SecurityCard } from '../components/SecurityCard';
import { BatchImportModal } from '../components/BatchImportModal';
import type { SecuritySummary } from '../types';

export const PortfolioPage: React.FC<{
  onSelectSecurity: (code: string) => void;
  onQuickEdit: (item: SecuritySummary) => void;
}> = ({ onSelectSecurity, onQuickEdit }) => {
  const screener = useAppStore((s) => s.screener);
  const userDoc = useAppStore((s) => s.userDoc);
  const updateSettings = useAppStore((s) => s.updateSettings);
  const clearAllHoldings = useAppStore((s) => s.clearAllHoldings);
  const removeHolding = useAppStore((s) => s.removeHolding);

  const [subTab, setSubTab] = useState<'holdings' | 'watchlist' | 'simulator'>('holdings');
  const [searchAdd, setSearchAdd] = useState('');
  const [batchModalMode, setBatchModalMode] = useState<'screenshot' | 'text' | null>(null);
  const [monthlySave, setMonthlySave] = useState(15000);
  const [simYield, setSimYield] = useState(5.8);
  const [simYears, setSimYears] = useState(15);

  const pf = useMemo(
    () => evaluatePortfolio(userDoc.holdings, screener?.items || {}),
    [userDoc.holdings, screener],
  );

  const searchCandidates = useMemo(() => {
    const q = searchAdd.trim().toUpperCase();
    if (!q || !screener) return [];
    return Object.values(screener.items)
      .filter((it) => it.code.startsWith(q) || it.name.includes(q))
      .slice(0, 8);
  }, [searchAdd, screener]);

  const simTimeline = useMemo(
    () => simulateCompoundGrowth(pf.totalMarketValue || 500000, monthlySave, simYield, simYears),
    [pf.totalMarketValue, monthlySave, simYield, simYears],
  );

  const targetMonthly = userDoc.settings.targetMonthlyDividend || 20000;
  const requiredCapitalForTarget = pf.portfolioYieldPct > 0
    ? Math.round((targetMonthly * 12) / (pf.portfolioYieldPct / 100))
    : Math.round((targetMonthly * 12) / 0.055);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700 }}>💼 我的持股與年度股利試算</h1>
          <p className="text-muted" style={{ fontSize: 13.5 }}>
            支援「📸 券商 App 庫存截圖自動辨識」、「📋 整串文字貼上」或單筆搜尋加入。自動試算全年配息與二代健保補充保費（單筆 ≥ 2 萬扣 2.11%）。
          </p>
        </div>

        {/* 快速批次匯入與單筆搜尋 */}
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            className="btn btn-primary"
            onClick={() => setBatchModalMode('screenshot')}
          >
            📸 券商 App 截圖匯入
          </button>
          <button
            className="btn"
            onClick={() => setBatchModalMode('text')}
          >
            📋 貼上整串文字匯入
          </button>

          <div style={{ position: 'relative', minWidth: 230 }}>
            <input
              className="input"
              placeholder="🔍 單筆搜尋代號或名稱..."
              value={searchAdd}
              onChange={(e) => setSearchAdd(e.target.value)}
            />
            {searchCandidates.length > 0 && (
              <div
                className="card"
                style={{
                  position: 'absolute',
                  top: '105%',
                  left: 0,
                  right: 0,
                  zIndex: 40,
                  padding: 6,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 4,
                }}
              >
                {searchCandidates.map((c) => (
                  <div
                    key={c.code}
                    style={{
                      padding: '7px 10px',
                      borderRadius: 'var(--radius-sm)',
                      cursor: 'pointer',
                      display: 'flex',
                      justifyContent: 'space-between',
                    }}
                    onClick={() => {
                      setSearchAdd('');
                      onQuickEdit(c);
                    }}
                  >
                    <span><strong>{c.name}</strong> ({c.code})</span>
                    <span className="text-muted">{c.price} 元 · 殖利率 {c.yield1y}%</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 頂部切換籤 */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button className={`chip ${subTab === 'holdings' ? 'active' : ''}`} onClick={() => setSubTab('holdings')}>
          持有中明細與股利試算 ({pf.activePositions.length})
        </button>
        <button className={`chip ${subTab === 'watchlist' ? 'active' : ''}`} onClick={() => setSubTab('watchlist')}>
          純觀察清單 ({pf.watchlist.length})
        </button>
        <button className={`chip ${subTab === 'simulator' ? 'active' : ''}`} onClick={() => setSubTab('simulator')}>
          🎯 目標月領與股利再投入複利模擬
        </button>
      </div>

      {subTab === 'holdings' && (
        <div>
          {pf.activePositions.length === 0 ? (
            <div className="card" style={{ padding: '36px 20px', textAlign: 'center', background: 'var(--bg-subtle)' }}>
              <div style={{ fontSize: 32, marginBottom: 10 }}>🌱</div>
              <h3 style={{ fontSize: 17, marginBottom: 6 }}>目前持股清單為空 — 選擇您最順手的方式新增股票：</h3>
              <p className="text-muted" style={{ fontSize: 13.5, maxWidth: 540, margin: '0 auto 18px', lineHeight: 1.6 }}>
                股票或零股很多嗎？不用一檔一檔查！直接上傳手機券商 App 的庫存截圖，或是貼上整理好的文字清單，3 秒鐘一次匯入全部持股！
              </p>
              <div style={{ display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap' }}>
                <button className="btn btn-primary" style={{ padding: '10px 18px', fontSize: 14.5 }} onClick={() => setBatchModalMode('screenshot')}>
                  📸 上傳券商 App 截圖（自動辨識）
                </button>
                <button className="btn" style={{ padding: '10px 18px', fontSize: 14.5 }} onClick={() => setBatchModalMode('text')}>
                  📋 貼上整串文字一次匯入
                </button>
              </div>
            </div>
          ) : (
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, flexWrap: 'wrap', gap: 10 }}>
                <div>
                  <span className="text-muted" style={{ fontSize: 13 }}>全年預估總毛額：</span>
                  <strong style={{ fontSize: 18, marginRight: 16 }}>${pf.totalGrossDiv.toLocaleString()}</strong>
                  <span className="text-muted" style={{ fontSize: 13 }}>預估二代健保補充保費：</span>
                  <strong className="text-warn" style={{ fontSize: 16, marginRight: 16 }}>-${pf.totalNhiSurcharge.toLocaleString()}</strong>
                  <span className="text-muted" style={{ fontSize: 13 }}>全年實領股利：</span>
                  <strong className="text-brand" style={{ fontSize: 20 }}>${pf.totalNetDiv.toLocaleString()}</strong>
                </div>

                <button
                  className="btn"
                  style={{ fontSize: 12, color: 'var(--danger)' }}
                  onClick={async () => {
                    if (window.confirm('確定要清空目前清單中的所有股票（包含預設範例），從零開始記錄您自己的持股嗎？')) {
                      await clearAllHoldings();
                    }
                  }}
                >
                  🗑️ 清空所有標的，從零開始記錄
                </button>
              </div>

              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>標的</th>
                      <th>股數</th>
                      <th>均價 / 現價</th>
                      <th>市值 / 帳面損益</th>
                      <th>每股配息 (口徑)</th>
                      <th>殖利率 / 成本殖利率</th>
                      <th>全年毛額 / 補充保費 / 實領</th>
                      <th>健康分</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pf.activePositions.map((row) => {
                      const sec = screener?.items[row.code];
                      return (
                        <tr key={row.code}>
                          <td style={{ cursor: 'pointer' }} onClick={() => onSelectSecurity(row.code)}>
                            <div style={{ fontWeight: 700 }}>{row.name}</div>
                            <div className="text-muted" style={{ fontSize: 12 }}>{row.code} · {row.sector}</div>
                          </td>
                          <td>{row.shares.toLocaleString()} 股</td>
                          <td>
                            <div>{row.avgCost > 0 ? row.avgCost.toFixed(2) : '--'}</div>
                            <div style={{ fontWeight: 600 }}>{row.price.toFixed(2)}</div>
                          </td>
                          <td>
                            <div style={{ fontWeight: 600 }}>${row.marketValue.toLocaleString()}</div>
                            <div className={row.unrealizedPnl >= 0 ? 'text-up' : 'text-down'} style={{ fontSize: 12 }}>
                              {row.unrealizedPnl >= 0 ? '+' : ''}{row.unrealizedPnl.toLocaleString()} ({row.unrealizedPnlPct.toFixed(1)}%)
                            </div>
                          </td>
                          <td>
                            <span style={{ fontWeight: 700 }}>{row.perShareDiv.toFixed(2)} 元</span>{' '}
                            <span className={`badge ${row.divSource === 'announced' ? 'badge-brand' : 'badge-subtle'}`}>
                              {row.divSource === 'announced' ? '已公告' : row.divSource === '5y' ? '5年均' : '近1年'}
                            </span>
                          </td>
                          <td>
                            <div>現價 {row.currentYieldPct.toFixed(2)}%</div>
                            <div className="text-brand" style={{ fontWeight: 600, fontSize: 12.5 }}>
                              成本 {row.yieldOnCostPct.toFixed(2)}%
                            </div>
                          </td>
                          <td>
                            <div>毛額 ${row.annualGrossDiv.toLocaleString()}</div>
                            <div style={{ fontSize: 12 }} className="text-muted">
                              健保 -${row.nhiSurcharge.toLocaleString()} → <strong className="text-brand">實領 ${row.annualNetDiv.toLocaleString()}</strong>
                            </div>
                          </td>
                          <td>
                            <span className="badge badge-brand">{row.score} ({row.grade})</span>
                          </td>
                          <td>
                            <div style={{ display: 'flex', gap: 6 }}>
                              {sec && (
                                <button className="btn" style={{ padding: '4px 10px', fontSize: 12 }} onClick={() => onQuickEdit(sec)}>
                                  編輯
                                </button>
                              )}
                              <button
                                className="btn"
                                style={{ padding: '4px 8px', fontSize: 12, color: 'var(--danger)' }}
                                onClick={async () => {
                                  if (window.confirm(`確定要移除 ${row.name} (${row.code}) 嗎？`)) {
                                    await removeHolding(row.code);
                                  }
                                }}
                              >
                                移除
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {subTab === 'watchlist' && (
        <div>
          {pf.watchlist.length === 0 ? (
            <div className="card text-muted" style={{ padding: 28, textAlign: 'center' }}>
              目前沒有純觀察標的。你可以在上方搜尋框或任一股票卡片點擊「+ 持股/觀察」並將股數設為 0。
            </div>
          ) : (
            <div className="grid-3">
              {pf.watchlist.map((item) => (
                <SecurityCard key={item.code} item={item} onSelect={onSelectSecurity} onQuickEdit={onQuickEdit} />
              ))}
            </div>
          )}
        </div>
      )}

      {subTab === 'simulator' && (
        <div className="grid-2">
          <div className="card">
            <h2 style={{ fontSize: 17, fontWeight: 700, marginBottom: 8 }}>🎯 目標月領被動收入試算</h2>
            <p className="text-muted" style={{ fontSize: 13, marginBottom: 14 }}>
              根據你目前的組合殖利率（{pf.portfolioYieldPct.toFixed(2)}%），推算達成目標月領股利所需的總部位規模：
            </p>
            <div style={{ marginBottom: 14 }}>
              <label style={{ fontSize: 13, fontWeight: 600, display: 'block', marginBottom: 4 }}>
                設定目標每月平均實領股利（元）
              </label>
              <input
                type="number"
                className="input"
                value={targetMonthly}
                onChange={(e) => updateSettings({ targetMonthlyDividend: Number(e.target.value) || 10000 })}
                step={5000}
              />
            </div>

            <div style={{ background: 'var(--bg-subtle)', padding: 14, borderRadius: 'var(--radius-md)', display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-muted">目標年領股利總額：</span>
                <strong>${(targetMonthly * 12).toLocaleString()} / 年</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-muted">所需總本金規模：</span>
                <strong className="text-brand" style={{ fontSize: 17 }}>${requiredCapitalForTarget.toLocaleString()}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-muted">距離目標尚需投入：</span>
                <strong>${Math.max(0, requiredCapitalForTarget - pf.totalMarketValue).toLocaleString()}</strong>
              </div>
            </div>
          </div>

          <div className="card">
            <h2 style={{ fontSize: 17, fontWeight: 700, marginBottom: 8 }}>📈 定期定額 + 股利再投入複利模擬</h2>
            <div className="grid-3" style={{ marginBottom: 14 }}>
              <div>
                <label style={{ fontSize: 12 }} className="text-muted">每月新投入 (元)</label>
                <input type="number" className="input" value={monthlySave} onChange={(e) => setMonthlySave(Number(e.target.value) || 0)} step={5000} />
              </div>
              <div>
                <label style={{ fontSize: 12 }} className="text-muted">預估年化殖利率 (%)</label>
                <input type="number" className="input" value={simYield} onChange={(e) => setSimYield(Number(e.target.value) || 5)} step={0.5} />
              </div>
              <div>
                <label style={{ fontSize: 12 }} className="text-muted">模擬年數 (年)</label>
                <input type="number" className="input" value={simYears} onChange={(e) => setSimYears(Math.min(35, Math.max(1, Number(e.target.value) || 10)))} />
              </div>
            </div>

            <div className="table-wrap" style={{ maxHeight: 240 }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>年度</th>
                    <th>累積投入本金</th>
                    <th>期末總資產</th>
                    <th>當年度可領股利</th>
                    <th>月均股利</th>
                  </tr>
                </thead>
                <tbody>
                  {simTimeline.filter((_, i) => (i + 1) % 3 === 0 || i === simTimeline.length - 1).map((row) => (
                    <tr key={row.year}>
                      <td>第 {row.year} 年</td>
                      <td>${row.invested.toLocaleString()}</td>
                      <td style={{ fontWeight: 700 }}>${row.balance.toLocaleString()}</td>
                      <td className="text-brand" style={{ fontWeight: 700 }}>${row.annualDividend.toLocaleString()}</td>
                      <td>${Math.round(row.annualDividend / 12).toLocaleString()}/月</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {batchModalMode && (
        <BatchImportModal
          initialMode={batchModalMode}
          onClose={() => setBatchModalMode(null)}
        />
      )}
    </div>
  );
};

