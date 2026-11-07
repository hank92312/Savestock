// Savestock v2 — 輕量 SVG 圖表元件（零外部圖表包袱，首屏 JS < 100KB，與暖色深淺主題無縫融合）

import React, { useState } from 'react';

interface PricePoint {
  date: string;
  close: number;
  volume?: number;
}

export const PriceBandChart: React.FC<{
  data: PricePoint[];
  bands?: { cheap?: number | null; fair?: number | null; expensive?: number | null };
}> = ({ data, bands }) => {
  const [range, setRange] = useState<'30d' | '180d' | 'all'>('all');
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  if (!data || data.length === 0) {
    return <div className="text-muted" style={{ padding: 24 }}>暫無歷史價格走勢</div>;
  }

  const sliceLen = range === '30d' ? 22 : range === '180d' ? 125 : data.length;
  const pts = data.slice(-sliceLen);

  const values = pts.map((p) => p.close);
  if (bands?.cheap) values.push(bands.cheap);
  if (bands?.expensive) values.push(bands.expensive);

  const minV = Math.min(...values) * 0.96;
  const maxV = Math.max(...values) * 1.04;
  const span = Math.max(maxV - minV, 0.01);

  const W = 720;
  const H = 230;
  const padL = 48;
  const padR = 18;
  const padT = 18;
  const padB = 28;
  const plotW = W - padL - padR;
  const plotH = H - padT - padB;

  const toX = (i: number) => padL + (pts.length <= 1 ? plotW / 2 : (i / (pts.length - 1)) * plotW);
  const toY = (v: number) => padT + plotH - ((v - minV) / span) * plotH;

  const pathD = pts
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${toX(i).toFixed(1)} ${toY(p.close).toFixed(1)}`)
    .join(' ');
  const areaD = `${pathD} L ${toX(pts.length - 1).toFixed(1)} ${(padT + plotH).toFixed(1)} L ${toX(0).toFixed(1)} ${(padT + plotH).toFixed(1)} Z`;

  const active = hoverIdx !== null && pts[hoverIdx] ? pts[hoverIdx] : pts[pts.length - 1];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10, flexWrap: 'wrap', gap: 8 }}>
        <div style={{ fontSize: 13 }}>
          <span className="text-muted">{active.date} 收盤：</span>
          <strong style={{ fontSize: 16 }}>{active.close.toFixed(2)} 元</strong>
          {bands?.cheap && (
            <span style={{ marginLeft: 12, fontSize: 12 }} className="text-muted">
              便宜價 <strong className="text-down">{bands.cheap}</strong> ｜ 合理價 <strong>{bands.fair}</strong> ｜ 昂貴價 <strong className="text-up">{bands.expensive}</strong>
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {(['30d', '180d', 'all'] as const).map((k) => (
            <button
              key={k}
              className={`chip ${range === k ? 'active' : ''}`}
              style={{ padding: '3px 10px', fontSize: 12 }}
              onClick={() => setRange(k)}
            >
              {k === '30d' ? '近 1 月' : k === '180d' ? '近半年' : '近 1 年'}
            </button>
          ))}
        </div>
      </div>

      <svg
        viewBox={`0 0 ${W} ${H}`}
        style={{ width: '100%', height: 'auto', overflow: 'visible', cursor: 'crosshair' }}
        onMouseMove={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          const relX = ((e.clientX - rect.left) / rect.width) * W - padL;
          const ratio = Math.max(0, Math.min(1, relX / plotW));
          setHoverIdx(Math.round(ratio * (pts.length - 1)));
        }}
        onMouseLeave={() => setHoverIdx(null)}
      >
        <defs>
          <linearGradient id="priceArea" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--brand)" stopOpacity="0.24" />
            <stop offset="100%" stopColor="var(--brand)" stopOpacity="0.0" />
          </linearGradient>
        </defs>

        {/* Y 軸參考線 */}
        {[0, 0.5, 1].map((t) => {
          const val = minV + span * t;
          const y = toY(val);
          return (
            <g key={t}>
              <line x1={padL} y1={y} x2={W - padR} y2={y} stroke="var(--border-soft)" strokeDasharray="3 3" />
              <text x={padL - 6} y={y + 4} textAnchor="end" fontSize="11" fill="var(--text-muted)">
                {val.toFixed(0)}
              </text>
            </g>
          );
        })}

        {/* 殖利率法便宜價 / 合理價 / 昂貴價參考帶 */}
        {bands?.cheap && bands.cheap >= minV && bands.cheap <= maxV && (
          <line x1={padL} y1={toY(bands.cheap)} x2={W - padR} y2={toY(bands.cheap)} stroke="var(--down)" strokeWidth="1.2" strokeDasharray="5 4" />
        )}
        {bands?.fair && bands.fair >= minV && bands.fair <= maxV && (
          <line x1={padL} y1={toY(bands.fair)} x2={W - padR} y2={toY(bands.fair)} stroke="var(--warn)" strokeWidth="1.2" strokeDasharray="5 4" />
        )}
        {bands?.expensive && bands.expensive >= minV && bands.expensive <= maxV && (
          <line x1={padL} y1={toY(bands.expensive)} x2={W - padR} y2={toY(bands.expensive)} stroke="var(--up)" strokeWidth="1.2" strokeDasharray="5 4" />
        )}

        <path d={areaD} fill="url(#priceArea)" />
        <path d={pathD} fill="none" stroke="var(--brand)" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round" />

        {hoverIdx !== null && pts[hoverIdx] && (
          <g>
            <line x1={toX(hoverIdx)} y1={padT} x2={toX(hoverIdx)} y2={padT + plotH} stroke="var(--text-muted)" strokeDasharray="2 2" />
            <circle cx={toX(hoverIdx)} cy={toY(pts[hoverIdx].close)} r="4.5" fill="var(--brand)" stroke="#fff" strokeWidth="1.5" />
          </g>
        )}

        <text x={padL} y={H - 6} fontSize="11" fill="var(--text-muted)">{pts[0].date}</text>
        <text x={W - padR} y={H - 6} textAnchor="end" fontSize="11" fill="var(--text-muted)">{pts[pts.length - 1].date}</text>
      </svg>
    </div>
  );
};

export const MonthlyBarChart: React.FC<{
  values: number[];
  targetLine?: number;
}> = ({ values, targetLine }) => {
  const maxVal = Math.max(...values, targetLine || 0, 1000);

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: 8, alignItems: 'end', height: 150, paddingTop: 18 }}>
        {values.map((v, idx) => {
          const pct = Math.max(4, Math.min(100, (v / maxVal) * 100));
          return (
            <div key={idx} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', justifyContent: 'flex-end' }}>
              <div style={{ fontSize: 10.5, color: 'var(--text-secondary)', marginBottom: 4 }}>
                {v > 0 ? `${(v / 1000).toFixed(1)}k` : '-'}
              </div>
              <div
                style={{
                  width: '100%',
                  maxWidth: 34,
                  height: `${pct}%`,
                  background: v >= (targetLine || Infinity) ? 'var(--up)' : 'var(--brand)',
                  opacity: v > 0 ? 0.88 : 0.18,
                  borderRadius: '6px 6px 3px 3px',
                  transition: 'height 0.2s ease',
                }}
                title={`${idx + 1} 月預估實領：${v.toLocaleString()} 元`}
              />
              <div style={{ fontSize: 11.5, color: 'var(--text-secondary)', marginTop: 6 }}>{idx + 1}月</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

