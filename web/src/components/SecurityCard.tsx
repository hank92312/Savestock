// Savestock v2 — 存股與 ETF 完全共用的證券卡片與持股新增彈窗

import React, { useState } from 'react';
import type { SecuritySummary } from '../types';
import { useAppStore } from '../store';

export function zoneLabel(zone?: string) {
  switch (zone) {
    case 'cheap':
      return { text: '便宜區 (≥6%)', cls: 'badge-down' };
    case 'fair':
      return { text: '合理偏低 (5~6%)', cls: 'badge-brand' };
    case 'warm':
      return { text: '合理偏高 (4~5%)', cls: 'badge-subtle' };
    case 'expensive':
      return { text: '偏貴區 (<4%)', cls: 'badge-warn' };
    default:
      return null;
  }
}

export const SecurityCard: React.FC<{
  item: SecuritySummary;
  onSelect: (code: string) => void;
  onQuickEdit?: (item: SecuritySummary) => void;
}> = ({ item, onSelect, onQuickEdit }) => {
  const holdings = useAppStore((s) => s.userDoc.holdings);
  const held = holdings[item.code];
  const isUp = item.changePct > 0;
  const isDown = item.changePct < 0;
  const z = zoneLabel(item.priceBands?.zone);

  return (
    <div className="card card-clickable" onClick={() => onSelect(item.code)} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 700, fontSize: 16 }}>{item.name}</span>
            <span className="text-muted" style={{ fontSize: 13 }}>{item.code}</span>
            <span className="badge badge-subtle">{item.sector}</span>
            {held && !held.deleted && (
              <span className="badge badge-brand">
                {held.shares > 0 ? `持有 ${held.shares.toLocaleString()} 股` : '觀察中'}
              </span>
            )}
          </div>
          {item.tags && item.tags.length > 0 && (
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
              {item.tags.slice(0, 3).map((t) => (
                <span key={t} style={{ fontSize: 11, color: 'var(--text-muted)' }}>#{t}</span>
              ))}
            </div>
          )}
        </div>

        <div style={{ textAlign: 'right' }}>
          <div style={{ fontWeight: 700, fontSize: 18 }}>
            {item.price.toFixed(2)}
          </div>
          <div className={isUp ? 'text-up' : isDown ? 'text-down' : 'text-muted'} style={{ fontSize: 12.5, fontWeight: 600 }}>
            {isUp ? '▲' : isDown ? '▼' : ''} {item.change > 0 ? `+${item.change}` : item.change} ({item.changePct > 0 ? `+${item.changePct}` : item.changePct}%)
          </div>
        </div>
      </div>

      {/* 核心指標四格（個股與 ETF 同款結構） */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, background: 'var(--bg-subtle)', padding: '9px 11px', borderRadius: 'var(--radius-md)', fontSize: 12.5 }}>
        <div>
          <div className="text-muted" style={{ fontSize: 11 }}>近1年殖利率</div>
          <div style={{ fontWeight: 700, fontSize: 14.5 }} className={item.yield1y >= 5 ? 'text-up' : ''}>
            {item.yield1y ? `${item.yield1y.toFixed(2)}%` : '--'}
          </div>
        </div>
        <div>
          <div className="text-muted" style={{ fontSize: 11 }}>
            {item.type === 'etf' ? '折溢價' : '近5年均息'}
          </div>
          <div style={{ fontWeight: 600 }}>
            {item.type === 'etf'
              ? item.etf?.discountPct !== undefined && item.etf?.discountPct !== null
                ? `${item.etf.discountPct > 0 ? '+' : ''}${item.etf.discountPct.toFixed(2)}%`
                : '--'
              : item.div5y
              ? `${item.div5y.toFixed(2)}元`
              : '--'}
          </div>
        </div>
        <div>
          <div className="text-muted" style={{ fontSize: 11 }}>
            {item.type === 'etf' ? '內扣費用率' : '連續配息'}
          </div>
          <div style={{ fontWeight: 600 }}>
            {item.type === 'etf'
              ? item.etf?.expenseRatioPct
                ? `${item.etf.expenseRatioPct.toFixed(2)}%`
                : '--'
              : `${item.consecDivYears || 0} 年`}
          </div>
        </div>
        <div>
          <div className="text-muted" style={{ fontSize: 11 }}>健康評分</div>
          <div style={{ fontWeight: 700, color: 'var(--brand)' }}>
            {item.score.total} 分 ({item.score.grade})
          </div>
        </div>
      </div>

      {/* 底部狀態列：價格位階 + 警示 + 快速操作 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
          {z && <span className={`badge ${z.cls}`}>{z.text}</span>}
          {item.announcedDiv && <span className="badge badge-brand">已公告 {item.announcedDiv}元</span>}
          {item.alert?.flag && (
            <span className="badge badge-danger">⚠️ {item.alert.reasons[0]}</span>
          )}
        </div>

        {onQuickEdit && (
          <button
            className="btn"
            style={{ padding: '4px 10px', fontSize: 12 }}
            onClick={(e) => {
              e.stopPropagation();
              onQuickEdit(item);
            }}
          >
            {held && !held.deleted ? '調整持股' : '+ 持股/觀察'}
          </button>
        )}
      </div>
    </div>
  );
};

export const HoldingModal: React.FC<{
  item: SecuritySummary | null;
  onClose: () => void;
}> = ({ item, onClose }) => {
  const holdings = useAppStore((s) => s.userDoc.holdings);
  const upsertHolding = useAppStore((s) => s.upsertHolding);
  const removeHolding = useAppStore((s) => s.removeHolding);

  if (!item) return null;
  const existing = holdings[item.code];

  // eslint-disable-next-line react-hooks/rules-of-hooks
  const [shares, setShares] = useState<string>(existing && !existing.deleted ? String(existing.shares) : '1000');
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const [cost, setCost] = useState<string>(existing && !existing.deleted && existing.avgCost > 0 ? String(existing.avgCost) : String(item.price));
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const [basis, setBasis] = useState<'1y' | '5y'>(existing?.basis || '1y');

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.45)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 16,
        zIndex: 100,
      }}
      onClick={onClose}
    >
      <div className="card" style={{ maxWidth: 420, width: '100%' }} onClick={(e) => e.stopPropagation()}>
        <h3 style={{ fontSize: 18, marginBottom: 4 }}>
          設定持股或觀察 — {item.name} ({item.code})
        </h3>
        <p className="text-muted" style={{ fontSize: 13, marginBottom: 14 }}>
          最新收盤價 {item.price} 元 ‧ 近1年股利 {item.div1y} 元（殖利率 {item.yield1y}%）。<br />
          若只加入「觀察清單」，請將股數設為 <strong>0</strong>。
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div>
            <label style={{ fontSize: 13, fontWeight: 600, display: 'block', marginBottom: 4 }}>
              持有股數（支援整張與零股，0 = 僅觀察）
            </label>
            <div style={{ display: 'flex', gap: 6 }}>
              <input
                type="number"
                className="input"
                value={shares}
                onChange={(e) => setShares(e.target.value)}
                min={0}
                step={100}
              />
              <button className="btn" onClick={() => setShares('0')}>僅觀察</button>
              <button className="btn" onClick={() => setShares(String((Number(shares) || 0) + 1000))}>+1張</button>
            </div>
          </div>

          <div>
            <label style={{ fontSize: 13, fontWeight: 600, display: 'block', marginBottom: 4 }}>
              平均買進成本（元/股，用於計算成本殖利率與損益）
            </label>
            <input
              type="number"
              className="input"
              value={cost}
              onChange={(e) => setCost(e.target.value)}
              min={0}
              step={0.1}
            />
          </div>

          <div>
            <label style={{ fontSize: 13, fontWeight: 600, display: 'block', marginBottom: 4 }}>
              未公告配息時之全年股利估算基準
            </label>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                className={`chip ${basis === '1y' ? 'active' : ''}`}
                onClick={() => setBasis('1y')}
              >
                近 1 年滾動股利 ({item.div1y} 元)
              </button>
              <button
                className={`chip ${basis === '5y' ? 'active' : ''}`}
                onClick={() => setBasis('5y')}
              >
                近 5 年平均 ({item.div5y} 元)
              </button>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 20, gap: 8 }}>
          {existing && !existing.deleted ? (
            <button
              className="btn"
              style={{ color: 'var(--danger)' }}
              onClick={async () => {
                await removeHolding(item.code);
                onClose();
              }}
            >
              移除追蹤
            </button>
          ) : <div />}

          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn" onClick={onClose}>取消</button>
            <button
              className="btn btn-primary"
              onClick={async () => {
                await upsertHolding(item.code, Number(shares) || 0, Number(cost) || 0, basis);
                onClose();
              }}
            >
              儲存並同步
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
