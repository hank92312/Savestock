// Savestock v2 — 🧠 ETF 追蹤與進階分析頁（存股與 ETF 共用同款視覺與卡片，整合完整成分股、穿透持股、重疊矩陣、共識股、隱藏強勢股、熱力圖與共識動能評分）

import React, { useEffect, useMemo, useState } from 'react';
import { useAppStore } from '../store';
import { SecurityCard } from '../components/SecurityCard';
import { calcLookthroughExposure, evaluatePortfolio } from '../calc';
import type { SecuritySummary } from '../types';

const GROUP_TABS = [
  { id: 'all', label: '全部精選 ETF' },
  { id: 'high_dividend', label: '💰 高股息 ETF' },
  { id: 'market_cap', label: '🏛️ 市值型 ETF' },
  { id: 'tech_ai', label: '🤖 科技 / AI 主題' },
  { id: 'bond', label: '🛡️ 債券型 ETF' },
  { id: 'global', label: '🌎 海外主題 ETF' },
  { id: 'custom', label: '➕ 自訂追蹤' },
];

export const EtfPage: React.FC<{
  onSelectSecurity: (code: string) => void;
  onQuickEdit: (item: SecuritySummary) => void;
}> = ({ onSelectSecurity, onQuickEdit }) => {
  const screener = useAppStore((s) => s.screener);
  const userDoc = useAppStore((s) => s.userDoc);
  const etfAnalytics = useAppStore((s) => s.etfAnalytics);
  const loadEtfAnalytics = useAppStore((s) => s.loadEtfAnalytics);
  const addCustomEtf = useAppStore((s) => s.addCustomEtf);
  const removeCustomEtf = useAppStore((s) => s.removeCustomEtf);

  const [mode, setMode] = useState<'list' | 'lookthrough' | 'overlap' | 'consensus' | 'hidden' | 'heatmap' | 'factor'>('list');
  const [group, setGroup] = useState<string>('all');
  const [customInput, setCustomInput] = useState('');

  useEffect(() => {
    loadEtfAnalytics();
  }, [loadEtfAnalytics]);

  const etfItems = useMemo(() => {
    if (!screener) return [];
    const curatedSet = new Set(screener.curatedEtfCodes || []);
    const customSet = new Set(userDoc.customEtfs || []);

    return Object.values(screener.items).filter((it) => {
      if (it.type !== 'etf') return false;
      if (group === 'custom') return customSet.has(it.code);
      if (!curatedSet.has(it.code) && !customSet.has(it.code)) return false;
      if (group === 'all') return true;
      return it.etfGroup === group;
    });
  }, [screener, userDoc.customEtfs, group]);

  const pf = useMemo(
    () => evaluatePortfolio(userDoc.holdings, screener?.items || {}),
    [userDoc.holdings, screener],
  );

  const lookthroughRows = useMemo(() => {
    if (!etfAnalytics) return [];
    return calcLookthroughExposure(pf.activePositions, etfAnalytics.holdingsByEtf || {});
  }, [pf.activePositions, etfAnalytics]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700 }}>🧠 ETF 完整成分股追蹤與智慧分析</h1>
          <p className="text-muted" style={{ fontSize: 13.5 }}>
            突破舊版僅前 10 大持股限制，全面串接 30～60 檔完整成分股、即時折溢價、內扣總費用率與含息報酬，並與存股追蹤共享同一套介面。
          </p>
        </div>

        {/* 自訂新增任意台股 ETF */}
        <div style={{ display: 'flex', gap: 6 }}>
          <input
            className="input"
            style={{ width: 180 }}
            placeholder="輸入 ETF 代號 (如 00712)"
            value={customInput}
            onChange={(e) => setCustomInput(e.target.value)}
          />
          <button
            className="btn btn-primary"
            onClick={async () => {
              const c = customInput.trim().toUpperCase();
              if (!c) return;
              await addCustomEtf(c);
              setCustomInput('');
              setGroup('custom');
            }}
          >
            + 加入自訂 ETF
          </button>
        </div>
      </div>

      {/* 功能模組切換列 */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {[
          { id: 'list', label: '📊 ETF 六大分群總覽' },
          { id: 'lookthrough', label: '🔍 我的組合穿透持股 (Look-through)' },
          { id: 'overlap', label: '🧩 ETF 兩兩重疊度矩陣' },
          { id: 'consensus', label: '🤝 機構重疊共識股' },
          { id: 'hidden', label: '💎 隱藏強勢股挖掘' },
          { id: 'heatmap', label: '🔥 權重交叉熱力圖' },
          { id: 'factor', label: '⚡ 共識動能三因子評分' },
        ].map((m) => (
          <button
            key={m.id}
            className={`chip ${mode === m.id ? 'active' : ''}`}
            onClick={() => setMode(m.id as any)}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* 模式 1：ETF 分群清單 */}
      {mode === 'list' && (
        <>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {GROUP_TABS.map((g) => (
              <button
                key={g.id}
                className={`btn ${group === g.id ? 'btn-primary' : ''}`}
                style={{ padding: '5px 12px', fontSize: 12.5 }}
                onClick={() => setGroup(g.id)}
              >
                {g.label}
              </button>
            ))}
          </div>

          <div className="grid-3">
            {etfItems.map((item) => (
              <div key={item.code} style={{ position: 'relative' }}>
                <SecurityCard item={item} onSelect={onSelectSecurity} onQuickEdit={onQuickEdit} />
                {group === 'custom' && (
                  <button
                    className="btn"
                    style={{ position: 'absolute', top: 12, right: 12, fontSize: 11, padding: '2px 8px' }}
                    onClick={() => removeCustomEtf(item.code)}
                  >
                    移除自訂
                  </button>
                )}
              </div>
            ))}
          </div>
        </>
      )}

      {/* 模式 2：我的組合穿透持股 */}
      {mode === 'lookthrough' && (
        <div className="card">
          <h2 style={{ fontSize: 17, fontWeight: 700, marginBottom: 6 }}>
            🔍 我的投資組合穿透持股分析（Look-through Exposure）
          </h2>
          <p className="text-muted" style={{ fontSize: 13, marginBottom: 14 }}>
            將你持有的每一檔 ETF 依其最新完整成分股權重拆解，並與你直接持有的個股加總，揭露你真正重壓的底層公司：
          </p>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>排名</th>
                  <th>底層標的</th>
                  <th>穿透總曝險金額</th>
                  <th>占總組合比重</th>
                  <th>來源拆解（來自哪些 ETF 或直接持有）</th>
                </tr>
              </thead>
              <tbody>
                {lookthroughRows.slice(0, 35).map((r, idx) => (
                  <tr key={r.code} style={{ cursor: 'pointer' }} onClick={() => onSelectSecurity(r.code)}>
                    <td>#{idx + 1}</td>
                    <td>
                      <strong>{r.name}</strong> <span className="text-muted">({r.code})</span>
                    </td>
                    <td style={{ fontWeight: 700 }}>${r.exposedValue.toLocaleString()}</td>
                    <td>
                      <span className="badge badge-brand">{r.portfolioPct}%</span>
                    </td>
                    <td style={{ fontSize: 12.5 }} className="text-muted">
                      {r.sources.map((s) => `${s.from} ($${s.value.toLocaleString()})`).join(' ＋ ')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 模式 3：ETF 兩兩重疊度矩陣 */}
      {mode === 'overlap' && etfAnalytics && (
        <div className="card">
          <h2 style={{ fontSize: 17, fontWeight: 700, marginBottom: 6 }}>
            🧩 熱門高股息與科技 ETF 兩兩權重重疊度矩陣（%）
          </h2>
          <p className="text-muted" style={{ fontSize: 13, marginBottom: 14 }}>
            數值為兩檔 ETF 共同成分股之最低重疊權重總和（Σ min(w_A, w_B)）。若重疊度超過 50%，同時買進兩檔的分散效果有限。
          </p>
          <div className="table-wrap">
            <table className="data-table" style={{ fontSize: 12 }}>
              <thead>
                <tr>
                  <th>ETF</th>
                  {etfAnalytics.pairwiseOverlap.etfs.slice(0, 14).map((eid) => (
                    <th key={eid}>{eid}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {etfAnalytics.pairwiseOverlap.etfs.slice(0, 14).map((rowEtf, rIdx) => (
                  <tr key={rowEtf}>
                    <td style={{ fontWeight: 700 }}>{rowEtf} {screener?.items[rowEtf]?.name}</td>
                    {etfAnalytics.pairwiseOverlap.matrix[rIdx].slice(0, 14).map((val, cIdx) => (
                      <td
                        key={cIdx}
                        style={{
                          background:
                            rIdx === cIdx
                              ? 'var(--bg-subtle)'
                              : val >= 45
                              ? 'var(--up-bg)'
                              : val >= 25
                              ? 'var(--brand-soft)'
                              : 'transparent',
                          fontWeight: val >= 30 && rIdx !== cIdx ? 700 : 400,
                        }}
                      >
                        {rIdx === cIdx ? '—' : `${val.toFixed(0)}%`}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 模式 4：機構共識股 */}
      {mode === 'consensus' && etfAnalytics && (
        <div className="card">
          <h2 style={{ fontSize: 17, fontWeight: 700, marginBottom: 6 }}>
            🤝 跨 ETF 機構共識股（被最多檔 ETF 同時納入之核心標的）
          </h2>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>標的</th>
                  <th>納入 ETF 檔數</th>
                  <th>跨 ETF 權重加總 (%)</th>
                  <th>平均單檔權重 (%)</th>
                  <th>持有它的 ETF 清單</th>
                </tr>
              </thead>
              <tbody>
                {etfAnalytics.consensus.map((row) => (
                  <tr key={row.stock_id} style={{ cursor: 'pointer' }} onClick={() => onSelectSecurity(row.stock_id)}>
                    <td>
                      <strong>{row.name}</strong> <span className="text-muted">({row.stock_id})</span>
                    </td>
                    <td><span className="badge badge-brand">{row.etf_count} 檔 ETF</span></td>
                    <td style={{ fontWeight: 700 }}>{row.total_weight.toFixed(2)}%</td>
                    <td>{row.avg_weight.toFixed(2)}%</td>
                    <td style={{ fontSize: 12 }} className="text-muted">{row.etf_list.join(', ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 模式 5：隱藏強勢股 */}
      {mode === 'hidden' && etfAnalytics && (
        <div className="card">
          <h2 style={{ fontSize: 17, fontWeight: 700, marginBottom: 6 }}>
            💎 隱藏強勢股挖掘（廣泛被多檔 ETF 建倉、但單一權重尚未過度擁擠）
          </h2>
          <p className="text-muted" style={{ fontSize: 13, marginBottom: 14 }}>
            公式：Hidden Score = ETF 檔數 × (1 / 平均權重)（僅統計被 ≥ 3 檔 ETF 共同持有之成分股）
          </p>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>標的</th>
                  <th>隱藏強度分數</th>
                  <th>持有 ETF 數</th>
                  <th>平均權重 (%)</th>
                  <th>持有 ETF</th>
                </tr>
              </thead>
              <tbody>
                {etfAnalytics.hiddenWinners.map((row) => (
                  <tr key={row.stock_id} style={{ cursor: 'pointer' }} onClick={() => onSelectSecurity(row.stock_id)}>
                    <td>
                      <strong>{row.name}</strong> <span className="text-muted">({row.stock_id})</span>
                    </td>
                    <td className="text-brand" style={{ fontWeight: 700 }}>{row.hidden_score.toFixed(2)}</td>
                    <td>{row.etf_count} 檔</td>
                    <td>{row.avg_weight.toFixed(2)}%</td>
                    <td style={{ fontSize: 12 }} className="text-muted">{row.etf_list.join(', ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 模式 6：權重交叉熱力圖 */}
      {mode === 'heatmap' && etfAnalytics && (
        <div className="card">
          <h2 style={{ fontSize: 17, fontWeight: 700, marginBottom: 10 }}>
            🔥 ETF × 核心成分股 權重交叉熱力圖（%）
          </h2>
          <div className="table-wrap">
            <table className="data-table" style={{ fontSize: 12 }}>
              <thead>
                <tr>
                  <th>成分股 \ ETF</th>
                  {etfAnalytics.heatmap.etfs.slice(0, 15).map((eid) => (
                    <th key={eid}>{eid}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {etfAnalytics.heatmap.stocks.map((st, rIdx) => (
                  <tr key={st.stock_id} style={{ cursor: 'pointer' }} onClick={() => onSelectSecurity(st.stock_id)}>
                    <td style={{ fontWeight: 700 }}>{st.name} ({st.stock_id})</td>
                    {etfAnalytics.heatmap.matrix[rIdx].slice(0, 15).map((w, cIdx) => (
                      <td
                        key={cIdx}
                        style={{
                          background:
                            w >= 10
                              ? 'var(--up-bg)'
                              : w >= 4
                              ? 'var(--brand-soft)'
                              : w > 0
                              ? 'var(--bg-subtle)'
                              : 'transparent',
                          fontWeight: w >= 5 ? 700 : 400,
                        }}
                      >
                        {w > 0 ? w.toFixed(1) : ''}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 模式 7：共識動能三因子評分 */}
      {mode === 'factor' && etfAnalytics && (
        <div className="card">
          <h2 style={{ fontSize: 17, fontWeight: 700, marginBottom: 6 }}>
            ⚡ 共識動能三因子量化評分（Top 25）
          </h2>
          <p className="text-muted" style={{ fontSize: 13, marginBottom: 14 }}>
            綜合「ETF 共識度（持有檔數）」、「隱藏強度」與「價格動能」三因子標準化加權排名（僅供量化參考，非投資建議）：
          </p>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>排名</th>
                  <th>標的</th>
                  <th>綜合評分</th>
                  <th>持有 ETF 數</th>
                  <th>隱藏強度</th>
                  <th>近期動能 (%)</th>
                  <th>納入 ETF</th>
                </tr>
              </thead>
              <tbody>
                {etfAnalytics.factorRanking.map((row) => (
                  <tr key={row.stock_id} style={{ cursor: 'pointer' }} onClick={() => onSelectSecurity(row.stock_id)}>
                    <td><strong>#{row.rank}</strong></td>
                    <td>
                      <strong>{row.name}</strong> <span className="text-muted">({row.stock_id})</span>
                    </td>
                    <td className="text-brand" style={{ fontWeight: 700 }}>{(row.ai_score * 100).toFixed(1)}</td>
                    <td>{row.etf_count} 檔</td>
                    <td>{row.hidden_score.toFixed(2)}</td>
                    <td className={row.momentum >= 0 ? 'text-up' : 'text-down'}>
                      {row.momentum >= 0 ? `+${row.momentum}` : row.momentum}%
                    </td>
                    <td style={{ fontSize: 12 }} className="text-muted">{row.etf_list.join(', ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
