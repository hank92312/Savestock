// Savestock v2 — 前端股利試算、二代健保補充保費（2.11%）、月度現金流分攤、複利試算與穿透持股計算

import type { SecuritySummary, UserHolding, EtfHoldingItem } from './types';

export const NHI_THRESHOLD = 20000;
export const NHI_RATE = 0.0211;

export interface PortfolioRowCalc {
  code: string;
  name: string;
  type: 'stock' | 'etf';
  sector: string;
  shares: number;
  avgCost: number;
  price: number;
  changePct: number;
  marketValue: number;
  costValue: number;
  unrealizedPnl: number;
  unrealizedPnlPct: number;
  perShareDiv: number;
  divSource: 'announced' | '1y' | '5y';
  annualGrossDiv: number;
  nhiSurcharge: number;
  annualNetDiv: number;
  currentYieldPct: number;
  yieldOnCostPct: number;
  paidThisYearAmt: number;
  score: number;
  grade: string;
  alertFlag: boolean;
  alertReasons: string[];
}

export function estimatePayoutFreq(sec: SecuritySummary): number {
  const freq = sec.etf?.divFrequency || '';
  const tags = (sec.tags || []).join(',');
  if (freq.includes('月') || tags.includes('月配')) return 12;
  if (freq.includes('季') || tags.includes('季配')) return 4;
  if (freq.includes('半年') || tags.includes('半年配')) return 2;
  return 1;
}

export function getActivePayoutMonths(sec: SecuritySummary): number[] {
  const tags = (sec.tags || []).join(',');
  if (tags.includes('月配') || (sec.etf?.divFrequency || '').includes('月')) {
    return [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
  }
  if (tags.includes('1/4/7/10')) return [1, 4, 7, 10];
  if (tags.includes('2/5/8/11')) return [2, 5, 8, 11];
  if (tags.includes('3/6/9/12')) return [3, 6, 9, 12];
  if ((sec.etf?.divFrequency || '').includes('季')) return [2, 5, 8, 11];
  if ((sec.etf?.divFrequency || '').includes('半年') || tags.includes('半年配')) return [1, 7];
  // 一般台股年配息主要集中在 7～8 月除息發放
  return [7];
}

export function evaluatePortfolio(
  holdings: Record<string, UserHolding>,
  screenerItems: Record<string, SecuritySummary>,
) {
  const activePositions: PortfolioRowCalc[] = [];
  const watchlist: SecuritySummary[] = [];

  let totalMarketValue = 0;
  let totalCostValue = 0;
  let totalGrossDiv = 0;
  let totalNhiSurcharge = 0;
  let totalNetDiv = 0;
  let totalPaidThisYear = 0;
  const monthlyCashflow = Array(12).fill(0) as number[];

  for (const h of Object.values(holdings)) {
    if (h.deleted) continue;
    const sec = screenerItems[h.code];
    if (!sec) continue;

    if (h.shares <= 0) {
      watchlist.push(sec);
      continue;
    }

    const marketValue = Math.round(h.shares * sec.price);
    const costValue = h.avgCost > 0 ? Math.round(h.shares * h.avgCost) : marketValue;
    const unrealizedPnl = h.avgCost > 0 ? marketValue - costValue : 0;
    const unrealizedPnlPct = h.avgCost > 0 && costValue > 0 ? (unrealizedPnl / costValue) * 100 : 0;

    // 三層口徑：今年已公告全年配息 > 使用者指定之 1y 或 5y
    let perShareDiv = sec.div1y;
    let divSource: 'announced' | '1y' | '5y' = '1y';
    if (sec.announcedDiv && sec.announcedDiv > 0) {
      perShareDiv = sec.announcedDiv;
      divSource = 'announced';
    } else if (h.basis === '5y' && sec.div5y > 0) {
      perShareDiv = sec.div5y;
      divSource = '5y';
    }

    const annualGrossDiv = Math.round(h.shares * perShareDiv);
    const freq = estimatePayoutFreq(sec);
    const singlePayout = annualGrossDiv / freq;
    const singleNhi = singlePayout >= NHI_THRESHOLD ? Math.round(singlePayout * NHI_RATE) : 0;
    const nhiSurcharge = singleNhi * freq;
    const annualNetDiv = annualGrossDiv - nhiSurcharge;
    const paidThisYearAmt = Math.round(h.shares * (sec.paidThisYear || 0));

    const currentYieldPct = sec.price > 0 ? (perShareDiv / sec.price) * 100 : 0;
    const yieldOnCostPct = h.avgCost > 0 ? (perShareDiv / h.avgCost) * 100 : currentYieldPct;

    // 分配到 12 個月現金流
    const months = getActivePayoutMonths(sec);
    const perMonthAmt = Math.round(annualNetDiv / months.length);
    for (const m of months) {
      monthlyCashflow[m - 1] += perMonthAmt;
    }

    totalMarketValue += marketValue;
    totalCostValue += costValue;
    totalGrossDiv += annualGrossDiv;
    totalNhiSurcharge += nhiSurcharge;
    totalNetDiv += annualNetDiv;
    totalPaidThisYear += paidThisYearAmt;

    activePositions.push({
      code: sec.code,
      name: sec.name,
      type: sec.type,
      sector: sec.sector,
      shares: h.shares,
      avgCost: h.avgCost,
      price: sec.price,
      changePct: sec.changePct,
      marketValue,
      costValue,
      unrealizedPnl,
      unrealizedPnlPct,
      perShareDiv,
      divSource,
      annualGrossDiv,
      nhiSurcharge,
      annualNetDiv,
      currentYieldPct,
      yieldOnCostPct,
      paidThisYearAmt,
      score: sec.score.total,
      grade: sec.score.grade,
      alertFlag: sec.alert.flag,
      alertReasons: sec.alert.reasons,
    });
  }

  activePositions.sort((a, b) => b.marketValue - a.marketValue);
  watchlist.sort((a, b) => b.yield1y - a.yield1y);

  const portfolioYieldPct = totalMarketValue > 0 ? (totalGrossDiv / totalMarketValue) * 100 : 0;
  const portfolioYieldOnCostPct = totalCostValue > 0 ? (totalGrossDiv / totalCostValue) * 100 : 0;

  return {
    activePositions,
    watchlist,
    totalMarketValue,
    totalCostValue,
    totalUnrealizedPnl: totalMarketValue - totalCostValue,
    totalUnrealizedPnlPct: totalCostValue > 0 ? ((totalMarketValue - totalCostValue) / totalCostValue) * 100 : 0,
    totalGrossDiv,
    totalNhiSurcharge,
    totalNetDiv,
    totalPaidThisYear,
    portfolioYieldPct,
    portfolioYieldOnCostPct,
    monthlyCashflow,
  };
}

export function calcLookthroughExposure(
  positions: PortfolioRowCalc[],
  holdingsByEtf: Record<string, EtfHoldingItem[]>,
) {
  const totalVal = positions.reduce((acc, p) => acc + p.marketValue, 0);
  if (totalVal <= 0) return [];

  const map: Record<
    string,
    { code: string; name: string; exposedValue: number; sources: { from: string; weightPct: number; value: number }[] }
  > = {};

  for (const pos of positions) {
    const etfHoldings = holdingsByEtf[pos.code];
    if (etfHoldings && etfHoldings.length > 0) {
      for (const h of etfHoldings) {
        const sid = h.stock_id.replace('.TW', '').replace('.TWO', '');
        const w = (h.weight || 0) / 100;
        const val = pos.marketValue * w;
        if (val <= 0) continue;
        if (!map[sid]) {
          map[sid] = { code: sid, name: h.name || sid, exposedValue: 0, sources: [] };
        }
        map[sid].exposedValue += val;
        map[sid].sources.push({ from: pos.code, weightPct: h.weight, value: Math.round(val) });
      }
    } else {
      if (!map[pos.code]) {
        map[pos.code] = { code: pos.code, name: pos.name, exposedValue: 0, sources: [] };
      }
      map[pos.code].exposedValue += pos.marketValue;
      map[pos.code].sources.push({ from: '直接持有', weightPct: 100, value: pos.marketValue });
    }
  }

  return Object.values(map)
    .map((r) => ({
      ...r,
      exposedValue: Math.round(r.exposedValue),
      portfolioPct: Number(((r.exposedValue / totalVal) * 100).toFixed(2)),
    }))
    .sort((a, b) => b.exposedValue - a.exposedValue);
}

export function simulateCompoundGrowth(
  initialPrincipal: number,
  monthlyContribution: number,
  annualYieldPct: number,
  years: number,
) {
  const r = annualYieldPct / 100;
  let balance = initialPrincipal;
  let invested = initialPrincipal;
  const timeline: { year: number; invested: number; balance: number; annualDividend: number }[] = [];

  for (let y = 1; y <= years; y++) {
    for (let m = 0; m < 12; m++) {
      balance += monthlyContribution;
      invested += monthlyContribution;
      balance *= 1 + r / 12;
    }
    const annualDividend = Math.round(balance * r);
    timeline.push({
      year: y,
      invested: Math.round(invested),
      balance: Math.round(balance),
      annualDividend,
    });
  }
  return timeline;
}

