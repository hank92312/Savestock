// Savestock v2 — 📊 證券詳情頁（個股與 ETF 完全共用同款版型與元件）

import React, { useEffect, useState } from 'react';
import { useAppStore } from '../store';
import { PriceBandChart } from '../components/Charts';
import { zoneLabel } from '../components/SecurityCard';
import type { SecurityDetail, SecuritySummary } from '../types';

export const SecurityDetailPage: React.FC<{
  code: string;
  onBack: () => void;
  onSelectSecurity: (code: string) => void;
  onQuickEdit: (item: SecuritySummary) => void;
}> = ({ code, onBack, onSelectSecurity, onQuickEdit }) => {
  const fetchDetail = useAppStore((s) => s.fetchDetail);
  const holdings = useAppStore((s) => s.userDoc.holdings);
  const [detail, setDetail] = useState<SecurityDetail | null>(null);
  const [tab, setTab] = useState<'overview' | 'dividend' | 'fundamentals' | 'holdings'>('overview');

  useEffect(() => {
    let mounted = true;
    fetchDetail(code).then((d) => {
      if (mounted) {
        setDetail(d);
        setTab('overview');
      }
    });
    return () => {
      mounted = false;
    };
  }, [code, fetchDetail]);

  if (!detail) {
    return (
      <div className="card" style={{ padding: 32 }}>
        <button className="btn" onClick={onBack} style={{ marginBottom: 14 }}>← 返回</button>
        <div>正在載入 {code} 詳情...</div>
      </div>
    );
  }

  const s = detail.summary;
  const held = holdings[s.code];
  const isUp = s.changePct > 0;
  const isDown = s.changePct < 0;
  const z = zoneLabel(s.priceBands?.zone);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      {/* 頂部導覽與標題列 */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <button className="btn" onClick={onBack} style={{ padding: '4px 10px', fontSize: 12.5, marginBottom: 10 }}>
              ← 返回上一頁
            </button>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <h1 style={{ fontSize: 24, fontWeight: 700 }}>{s.name}</h1>
              <span className="text-muted" style={{ fontSize: 17 }}>{s.code}</span>
              <span className="badge badge-subtle">{s.market} · {s.sector}</span>
              {z && <span className={`badge ${z.cls}`}>{z.text}</span>}
              {held && !held.deleted && (
                <span className="badge badge-brand">
                  {held.shares > 0 ? `已持有 ${held.shares.toLocaleString()} 股 (均價 ${held.avgCost})` : '觀察清單中'}
                </span>
              )}
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 28, fontWeight: 700 }}>{s.price.toFixed(2)}</div>
              <div className={isUp ? 'text-up' : isDown ? 'text-down' : 'text-muted'} style={{ fontWeight: 600, fontSize: 14 }}>
                {isUp ? '▲' : isDown ? '▼' : ''} {s.change > 0 ? `+${s.change}` : s.change} ({s.changePct > 0 ? `+${s.changePct}` : s.changePct}%)
              </div>
            </div>
            <button className="btn btn-primary" onClick={() => onQuickEdit(s)}>
              {held && !held.deleted ? '調整持股/觀察' : '+ 加入持股/觀察'}
            </button>
          </div>
        </div>

        {/* 異常警示橫幅 */}
        {s.alert?.flag && (
          <div
            style={{
              marginTop: 14,
              padding: '10px 14px',
              background: 'var(--danger-bg)',
              color: 'var(--danger)',
              borderRadius: 'var(--radius-md)',
              fontWeight: 600,
              fontSize: 13.5,
            }}
          >
            🚨 防護警示：{s.alert.reasons.join('、')}（自適應跌幅門檻 -{s.alert.thresholdPct}%）
          </div>
        )}
      </div>

      {/* 存股健康分數診斷卡 + 關鍵指標六宮格 */}
      <div className="grid-2">
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div>
              <h2 style={{ fontSize: 16.5, fontWeight: 700 }}>🩺 存股健康診斷評分</h2>
              <p className="text-muted" style={{ fontSize: 12 }}>綜合股利品質、估值位階、基本面與風險</p>
            </div>
            <div style={{ textAlign: 'right' }}>
              <span style={{ fontSize: 28, fontWeight: 800, color: 'var(--brand)' }}>{detail.scoreBreakdown.total}</span>
              <span className="badge badge-brand" style={{ marginLeft: 6, fontSize: 14 }}>{detail.scoreBreakdown.grade} 級</span>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8, marginBottom: 12 }}>
            {detail.scoreBreakdown.dimensions.map((d) => (
              <div key={d.key} style={{ background: 'var(--bg-subtle)', padding: '7px 10px', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5 }}>
                  <span>{d.label}</span>
                  <strong>{d.score} / {d.max}</strong>
                </div>
                <div style={{ height: 5, background: 'var(--border-soft)', borderRadius: 99, marginTop: 4 }}>
                  <div style={{ width: `${(d.score / d.max) * 100}%`, height: '100%', background: 'var(--brand)', borderRadius: 99 }} />
                </div>
              </div>
            ))}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 13 }}>
            {detail.scoreBreakdown.positives.map((p, i) => (
              <div key={i} className="text-down">✅ {p}</div>
            ))}
            {detail.scoreBreakdown.cautions.map((c, i) => (
              <div key={i} className="text-warn">⚠️ {c}</div>
            ))}
          </div>
        </div>

        <div className="card">
          <h2 style={{ fontSize: 16.5, fontWeight: 700, marginBottom: 12 }}>📌 核心投資參考數據</h2>
          <div className="grid-3">
            <div>
              <div className="text-muted" style={{ fontSize: 12 }}>近 1 年殖利率</div>
              <div style={{ fontSize: 19, fontWeight: 700 }} className="text-up">{s.yield1y.toFixed(2)}%</div>
              <div className="text-muted" style={{ fontSize: 11.5 }}>每股 {s.div1y} 元</div>
            </div>
            <div>
              <div className="text-muted" style={{ fontSize: 12 }}>近 2 年平均殖利率</div>
              <div style={{ fontSize: 19, fontWeight: 700 }}>{s.yield2y.toFixed(2)}%</div>
              <div className="text-muted" style={{ fontSize: 11.5 }}>均息 {s.div2y} 元</div>
            </div>
            <div>
              <div className="text-muted" style={{ fontSize: 12 }}>近 5 年平均殖利率</div>
              <div style={{ fontSize: 19, fontWeight: 700 }}>{s.yield5y.toFixed(2)}%</div>
              <div className="text-muted" style={{ fontSize: 11.5 }}>均息 {s.div5y} 元</div>
            </div>

            {s.type === 'etf' ? (
              <>
                <div>
                  <div className="text-muted" style={{ fontSize: 12 }}>最新淨值 / 折溢價</div>
                  <div style={{ fontSize: 16, fontWeight: 700 }}>
                    {s.etf?.nav ? `${s.etf.nav.toFixed(2)}` : '--'}{' '}
                    <span className={(s.etf?.discountPct || 0) > 0.5 ? 'text-up' : 'text-brand'}>
                      ({s.etf?.discountPct ? `${s.etf.discountPct > 0 ? '+' : ''}${s.etf.discountPct}%` : '--'})
                    </span>
                  </div>
                </div>
                <div>
                  <div className="text-muted" style={{ fontSize: 12 }}>內扣總費用率 / 配息</div>
                  <div style={{ fontSize: 16, fontWeight: 700 }}>
                    {s.etf?.expenseRatioPct ? `${s.etf.expenseRatioPct}%` : '--'} · {s.etf?.divFrequency || '季配'}
                  </div>
                </div>
                <div>
                  <div className="text-muted" style={{ fontSize: 12 }}>基金規模 / 受益人</div>
                  <div style={{ fontSize: 15, fontWeight: 700 }}>
                    {s.etf?.aumHundredMillions ? `${s.etf.aumHundredMillions.toLocaleString()} 億` : '--'}
                  </div>
                  <div className="text-muted" style={{ fontSize: 11.5 }}>
                    {s.etf?.holdersCount ? `${s.etf.holdersCount.toLocaleString()} 人` : ''}
                  </div>
                </div>
              </>
            ) : (
              <>
                <div>
                  <div className="text-muted" style={{ fontSize: 12 }}>本益比 / 股價淨值比</div>
                  <div style={{ fontSize: 16, fontWeight: 700 }}>
                    PE {s.pe || '--'} / PB {s.pb || '--'}
                  </div>
                  <div className="text-muted" style={{ fontSize: 11.5 }}>
                    {s.pePercentile5y ? `5年位階 ${s.pePercentile5y}%` : '官方收盤估值'}
                  </div>
                </div>
                <div>
                  <div className="text-muted" style={{ fontSize: 12 }}>連續配息 / 盈餘配發率</div>
                  <div style={{ fontSize: 16, fontWeight: 700 }}>
                    {s.consecDivYears} 年 / {s.payoutRatio ? `${s.payoutRatio}%` : '--'}
                  </div>
                </div>
                <div>
                  <div className="text-muted" style={{ fontSize: 12 }}>千張大戶持股比例</div>
                  <div style={{ fontSize: 16, fontWeight: 700 }}>
                    {s.largeHolder1000Pct ? `${s.largeHolder1000Pct}%` : '--'}
                  </div>
                  <div className="text-muted" style={{ fontSize: 11.5 }}>
                    股東 {s.shareholders ? `${s.shareholders.toLocaleString()} 人` : '--'}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* 子分頁切換 */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button className={`chip ${tab === 'overview' ? 'active' : ''}`} onClick={() => setTab('overview')}>
          📈 價格走勢與殖利率價格帶
        </button>
        <button className={`chip ${tab === 'dividend' ? 'active' : ''}`} onClick={() => setTab('dividend')}>
          💰 歷年股利與配息紀錄 ({detail.dividends.length})
        </button>
        <button className={`chip ${tab === 'fundamentals' ? 'active' : ''}`} onClick={() => setTab('fundamentals')}>
          📊 {s.type === 'etf' ? '含息總報酬與風險' : '基本面營收、籌碼與風險'}
        </button>
        {s.type === 'etf' && detail.etfInfo?.holdings && detail.etfInfo.holdings.length > 0 && (
          <button className={`chip ${tab === 'holdings' ? 'active' : ''}`} onClick={() => setTab('holdings')}>
            🧩 完整成分股清單 ({detail.etfInfo.holdings.length} 檔)
          </button>
        )}
      </div>

      {tab === 'overview' && (
        <div className="card">
          <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 10 }}>
            歷史收盤價與殖利率法三段價格帶（便宜 6% / 合理 5% / 昂貴 4%）
          </h3>
          <PriceBandChart data={detail.prices} bands={s.priceBands} />
        </div>
      )}

      {tab === 'dividend' && (
        <div className="card">
          <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 10 }}>歷次除權息與配息金額明細</h3>
          {detail.dividends.length === 0 ? (
            <div className="text-muted">暫無歷史除權息明細</div>
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>年度</th>
                    <th>除息交易日</th>
                    <th>股利發放日</th>
                    <th>現金股利 (元)</th>
                    <th>股票股利 (元)</th>
                    <th>合計股利 (元)</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.dividends.map((dv, idx) => (
                    <tr key={idx}>
                      <td>{dv.year}</td>
                      <td>{dv.exDate}</td>
                      <td>{dv.payDate || '--'}</td>
                      <td>{dv.cash.toFixed(3)}</td>
                      <td>{dv.stock.toFixed(3)}</td>
                      <td style={{ fontWeight: 700 }} className="text-brand">{dv.total.toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {tab === 'fundamentals' && (
        <div className="grid-2">
          {s.type === 'etf' ? (
            <div className="card">
              <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>ETF 含息累積總報酬率（考慮配息再投入）</h3>
              <div className="grid-3">
                {[
                  { k: 'm1', label: '近 1 個月' },
                  { k: 'm3', label: '近 3 個月' },
                  { k: 'm6', label: '近 6 個月' },
                  { k: 'y1', label: '近 1 年' },
                  { k: 'y3', label: '近 3 年' },
                  { k: 'y5', label: '近 5 年' },
                ].map((r) => {
                  const v = detail.etfInfo?.returns?.[r.k];
                  return (
                    <div key={r.k} style={{ background: 'var(--bg-subtle)', padding: 12, borderRadius: 'var(--radius-md)' }}>
                      <div className="text-muted" style={{ fontSize: 12 }}>{r.label}</div>
                      <div
                        style={{ fontSize: 18, fontWeight: 700, marginTop: 4 }}
                        className={v && v > 0 ? 'text-up' : v && v < 0 ? 'text-down' : ''}
                      >
                        {v !== undefined && v !== null ? `${v > 0 ? '+' : ''}${v}%` : '--'}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="card">
              <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>基本面月營收與獲利能力</h3>
              <div className="grid-2">
                <div style={{ background: 'var(--bg-subtle)', padding: 12, borderRadius: 'var(--radius-md)' }}>
                  <div className="text-muted" style={{ fontSize: 12 }}>最新月營收 ({detail.fundamentals.revYm || '--'})</div>
                  <div style={{ fontSize: 18, fontWeight: 700, marginTop: 4 }}>
                    年增率 YoY：{detail.fundamentals.revYoY !== undefined && detail.fundamentals.revYoY !== null ? `${detail.fundamentals.revYoY > 0 ? '+' : ''}${detail.fundamentals.revYoY.toFixed(1)}%` : '--'}
                  </div>
                  <div className="text-muted" style={{ fontSize: 12, marginTop: 4 }}>
                    月增率 MoM：{detail.fundamentals.revMoM !== undefined && detail.fundamentals.revMoM !== null ? `${detail.fundamentals.revMoM.toFixed(1)}%` : '--'}
                  </div>
                </div>
                <div style={{ background: 'var(--bg-subtle)', padding: 12, borderRadius: 'var(--radius-md)' }}>
                  <div className="text-muted" style={{ fontSize: 12 }}>近四季 EPS 與盈餘配發率</div>
                  <div style={{ fontSize: 18, fontWeight: 700, marginTop: 4 }}>
                    EPS {detail.fundamentals.epsTtm ?? '--'} 元
                  </div>
                  <div className="text-muted" style={{ fontSize: 12, marginTop: 4 }}>
                    配發率：{detail.fundamentals.payoutRatio ? `${detail.fundamentals.payoutRatio}%` : '--'}
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="card">
            <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>籌碼集中度與波動風險指標</h3>
            <div className="grid-2">
              <div style={{ background: 'var(--bg-subtle)', padding: 12, borderRadius: 'var(--radius-md)' }}>
                <div className="text-muted" style={{ fontSize: 12 }}>TDCC 集保大戶持股 ({detail.chips.tdccDate || '最新'})</div>
                <div style={{ fontSize: 17, fontWeight: 700, marginTop: 4 }}>
                  千張大戶：{detail.chips.largeHolder1000Pct ?? '--'}%
                </div>
                <div className="text-muted" style={{ fontSize: 12, marginTop: 4 }}>
                  400張以上：{detail.chips.largeHolder400Pct ?? '--'}% · 總股東 {detail.chips.shareholders?.toLocaleString() ?? '--'} 人
                </div>
              </div>
              <div style={{ background: 'var(--bg-subtle)', padding: 12, borderRadius: 'var(--radius-md)' }}>
                <div className="text-muted" style={{ fontSize: 12 }}>波動度與回撤風險</div>
                <div style={{ fontSize: 17, fontWeight: 700, marginTop: 4 }}>
                  年化波動：{detail.risk.volatility_1y ?? s.etf?. discountPct ?? '--'}%
                </div>
                <div className="text-muted" style={{ fontSize: 12, marginTop: 4 }}>
                  近1年最大回撤：{detail.risk.max_drawdown_1y ?? '--'}% · 警示門檻 -{detail.risk.adaptive_drop_threshold}%
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {tab === 'holdings' && detail.etfInfo?.holdings && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h3 style={{ fontSize: 16, fontWeight: 700 }}>
              🧩 {s.name} ({s.code}) 完整成分股權重清單（共 {detail.etfInfo.holdings.length} 檔）
            </h3>
            <span className="badge badge-brand">
              {detail.etfInfo.completeness === 'full' ? '完整持股揭露' : '前十大核心持股'}
            </span>
          </div>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>排名</th>
                  <th>成分股代號與名稱</th>
                  <th>權重 (%)</th>
                  <th>持有股數</th>
                  <th>最新收盤價</th>
                  <th>當日漲跌</th>
                  <th>近1年殖利率</th>
                </tr>
              </thead>
              <tbody>
                {detail.etfInfo.holdings.map((h, i) => (
                  <tr
                    key={`${h.stock_id}-${i}`}
                    style={{ cursor: 'pointer' }}
                    onClick={() => onSelectSecurity(h.stock_id)}
                  >
                    <td>#{i + 1}</td>
                    <td>
                      <strong>{h.name}</strong> <span className="text-muted">({h.stock_id})</span>
                    </td>
                    <td style={{ fontWeight: 700 }} className="text-brand">{h.weight.toFixed(2)}%</td>
                    <td>{h.shares ? h.shares.toLocaleString() : '--'}</td>
                    <td>{h.price ? h.price.toFixed(2) : '--'}</td>
                    <td className={(h.changePct || 0) > 0 ? 'text-up' : (h.changePct || 0) < 0 ? 'text-down' : ''}>
                      {h.changePct !== undefined && h.changePct !== null ? `${h.changePct > 0 ? '+' : ''}${h.changePct}%` : '--'}
                    </td>
                    <td>{h.yield1y ? `${h.yield1y.toFixed(2)}%` : '--'}</td>
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
