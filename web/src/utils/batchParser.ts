// Savestock v2 — 智慧批次持股匯入引擎（支援：1. 整串文字/Excel/記事本貼上  2. 券商 App 截圖 OCR 自動辨識與價格校正）

import type { SecuritySummary } from '../types';

export interface ParsedHoldingCandidate {
  code: string;
  name: string;
  shares: number;
  avgCost: number;
  currentPrice: number;
  selected: boolean;
  note?: string;
}

// 常見簡稱或舊名對照表（讓朋友就算打簡稱或舊名也能一秒識別）
const NAME_ALIASES: Record<string, string> = {
  台積: '2330',
  鴻海: '2317',
  聯發科: '2454',
  中華電信: '2412',
  台灣50: '0050',
  元大50: '0050',
  高股息: '0056',
  元大高息: '0056',
  國泰高股息: '00878',
  國泰永續: '00878',
  群益高息: '00919',
  復華台灣科技優息: '00929',
  元大台灣價值高息: '00940',
  富邦台50: '006208',
  開發金: '2883',
  凱基金控: '2883',
  台新金: '2887',
  新光金: '2887',
  台新新光: '2887',
  日月光: '3711',
  合庫: '5880',
  合庫金: '5880',
  中信: '2891',
  中信金: '2891',
  兆豐: '2886',
  兆豐金: '2886',
  玉山: '2884',
  玉山金: '2884',
  第一金控: '2892',
  富邦金: '2881',
  國泰金: '2882',
  元大金: '2885',
  永豐金: '2890',
  華南金: '2880',
};

/**
 * 嘗試將單一 Token 識別為合法台股/ETF代號（含 OCR 常見誤判修正，如 007198 -> 00719B）
 */
function resolveCodeToken(rawToken: string, items: Record<string, SecuritySummary>): string | null {
  // 若帶有千分位逗號（例如 1,000、2,000、3,000），代表是「股數」而非股票代號！
  if (rawToken.includes(',')) return null;

  const cleaned = rawToken
    .toUpperCase()
    .replace(/\.TW(O)?$/i, '')
    .replace(/^[([（【]+|[)\]）】:;，,。]+$/g, '')
    .trim();

  if (!cleaned || cleaned.length < 4 || cleaned.length > 6) return null;

  // 把 OCR 常誤判的英文字母 O 轉為數字 0（前4碼）
  const normalizedPrefix = cleaned.slice(0, 4).replace(/O/g, '0') + cleaned.slice(4);

  if (items[normalizedPrefix]) return normalizedPrefix;
  if (items[cleaned]) return cleaned;

  // 針對債券/槓反 ETF 最末碼 B / L / R 被 OCR 誤讀為 8 / 0 / 6 / 5 的自動修復（例如 007198 -> 00719B, 008598 -> 00859B）
  if (normalizedPrefix.length === 6 && normalizedPrefix.startsWith('00') && '80653'.includes(normalizedPrefix[5])) {
    const stem = normalizedPrefix.slice(0, 5);
    for (const suffix of ['B', 'L', 'R']) {
      if (items[stem + suffix]) return stem + suffix;
    }
  }

  return null;
}

/**
 * 在自由格式單行文字中尋找股票代號或中文名稱
 */
function findStockInLine(
  line: string,
  items: Record<string, SecuritySummary>,
  sortedByNameLen: SecuritySummary[],
): { code: string; matchedText: string; isCodeLine: boolean } | null {
  const tokens = line.trim().split(/[\s\t|,;，；、/]+/);
  if (tokens.length === 0) return null;

  // 1. 優先檢查第一個 Token 是否就是股票代號（券商 App 截圖的第二行必定以代號開頭，如 "0050 4,800 34.52 +167.1%"）
  const firstCode = resolveCodeToken(tokens[0], items);
  if (firstCode) {
    return { code: firstCode, matchedText: tokens[0], isCodeLine: true };
  }

  // 2. 檢查該行中是否有明確的中文股票名稱（先移除多餘空白，例如「遠  雄」->「遠雄」）
  const compactLine = line.replace(/\s+/g, '');
  for (const [alias, targetCode] of Object.entries(NAME_ALIASES)) {
    if (compactLine.includes(alias) && items[targetCode]) {
      return { code: targetCode, matchedText: alias, isCodeLine: false };
    }
  }

  for (const sec of sortedByNameLen) {
    const cleanName = sec.name.replace(/\s+/g, '');
    if (cleanName.length >= 2 && compactLine.includes(cleanName)) {
      return { code: sec.code, matchedText: sec.name, isCodeLine: false };
    }
  }

  // 3. 若無中文名稱，檢查行內其他 Token 是否為代號（排除帶有「股/張/元」後綴的數字）
  for (let i = 1; i < tokens.length; i++) {
    const t = tokens[i];
    if (/[股張元%$]/.test(t)) continue;
    const c = resolveCodeToken(t, items);
    if (c) {
      return { code: c, matchedText: t, isCodeLine: false };
    }
  }

  return null;
}

/**
 * 解析使用者貼上的整串文字或 OCR 辨識結果
 */
export function parseHoldingsText(
  rawText: string,
  items: Record<string, SecuritySummary>,
): ParsedHoldingCandidate[] {
  if (!rawText.trim() || !items) return [];

  const sortedByNameLen = Object.values(items).sort((a, b) => b.name.length - a.name.length);
  const rawLines = rawText
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0);

  const resultsMap = new Map<string, ParsedHoldingCandidate>();

  for (let idx = 0; idx < rawLines.length; idx++) {
    const line = rawLines[idx];

    // 跳過明顯的表頭列
    if (/商品名稱|今餘股數|可下單數|成本均價|參考損益|報酬率/.test(line)) {
      continue;
    }

    const found = findStockInLine(line, items, sortedByNameLen);
    if (!found) continue;

    const sec = items[found.code];
    if (!sec) continue;

    const curPrice = sec.price || 0;

    // 把已配對到的股票代號或名稱從該行移除，避免名稱裡的數字（如「元大台灣50」、「美債1-3」、「0-1年」）被當成股數！
    let remainder = line;
    const matchIdx = remainder.indexOf(found.matchedText);
    if (matchIdx >= 0) {
      remainder = remainder.slice(matchIdx + found.matchedText.length);
    } else {
      // 處理像「遠  雄」中間有空白的狀況
      const charsPattern = found.matchedText.split('').join('\\s*');
      remainder = remainder.replace(new RegExp(charsPattern), ' ');
    }

    // 檢查是否有明確寫「X張」或「X股」或「成本/均價X」
    let explicitShares: number | null = null;
    let explicitCost: number | null = null;

    const zhangMatch = remainder.match(/(\d+(?:,\d{3})*(?:\.\d+)?)\s*張/);
    if (zhangMatch) {
      explicitShares = Math.round(parseFloat(zhangMatch[1].replace(/,/g, '')) * 1000);
      remainder = remainder.replace(zhangMatch[0], ' ');
    }

    const guMatch = remainder.match(/(\d+(?:,\d{3})*(?:\.\d+)?)\s*股/);
    if (guMatch && explicitShares === null) {
      explicitShares = Math.round(parseFloat(guMatch[1].replace(/,/g, '')));
      remainder = remainder.replace(guMatch[0], ' ');
    }

    const costLabelMatch = remainder.match(/(?:成本|均價|買價|@|＠)\s*[:：]?\s*(\d+(?:,\d{3})*(?:\.\d+)?)/);
    if (costLabelMatch) {
      explicitCost = parseFloat(costLabelMatch[1].replace(/,/g, ''));
      remainder = remainder.replace(costLabelMatch[0], ' ');
    }

    // 擷取剩餘的純數字 Token（排除百分比 +167.1% 等）
    const rawTokens = remainder.trim().split(/[\s\t|,;，；/]+/);
    const numTokens: { raw: string; val: number }[] = [];

    for (const tok of rawTokens) {
      if (!tok || tok.includes('%') || tok.includes('％')) continue;
      const cleanedTok = tok.replace(/[元$＄]/g, '').replace(/,/g, '');
      if (/^[+-]?\d+(\.\d+)?$/.test(cleanedTok)) {
        const val = parseFloat(cleanedTok);
        if (!isNaN(val) && val >= 0) {
          numTokens.push({ raw: cleanedTok, val });
        }
      }
    }

    let shares = explicitShares !== null ? explicitShares : 0;
    let avgCost = explicitCost !== null ? explicitCost : 0;
    let rawCostStr = '';

    if (explicitShares === null && numTokens.length >= 1) {
      shares = Math.round(numTokens[0].val);
      if (explicitCost === null && numTokens.length >= 2) {
        avgCost = numTokens[1].val;
        rawCostStr = numTokens[1].raw;
      }
    } else if (explicitShares !== null && explicitCost === null && numTokens.length >= 1) {
      avgCost = numTokens[0].val;
      rawCostStr = numTokens[0].raw;
    }

    if (shares <= 0 && explicitShares === null && numTokens.length === 0) {
      // 如果該行只有股票名稱（例如券商截圖中名稱斷行），先跳過等下一行代號行
      if (!found.isCodeLine) continue;
      shares = 1000;
    }

    // 若沒有提供均價，預設帶入最新收盤價
    if (avgCost <= 0) {
      avgCost = curPrice;
    }

    // === 智慧校正 1：若為券商截圖「名稱行」(非代號開頭)，且有 3 個數字 (今餘股數, 現價, 損益)，下一行通常才是真正的 (代號, 可下單數, 成本均價) ===
    // 若下一行是同一個股票的代號行，則會在下一迴圈被代號行精準覆蓋。
    // 但若使用者只貼了名稱行，且第二個數字剛好等於現價，可由第三個數字 (損益) 反推成本！

    // === 智慧校正 2：OCR 小數點遺漏自動修復（例如 34.52 被讀成 3452、9.73 被讀成 973、22.24 被讀成 2224） ===
    if (rawCostStr && !rawCostStr.includes('.') && curPrice > 0 && avgCost > curPrice * 3.5) {
      if (avgCost / 100 <= curPrice * 3 && avgCost / 100 >= curPrice * 0.1) {
        avgCost = Math.round((avgCost / 100) * 100) / 100;
      } else if (avgCost / 10 <= curPrice * 3 && avgCost / 10 >= curPrice * 0.1) {
        avgCost = Math.round((avgCost / 10) * 100) / 100;
      }
    }

    // === 智慧校正 3：結合上方 1~3 行的「今餘股數 / 現價 / 損益」交叉驗證（防止截圖右下角懸浮按鈕遮擋成本，如 00859B） ===
    if (found.isCodeLine && shares > 0 && curPrice > 0) {
      for (let back = 1; back <= 3; back++) {
        if (idx - back < 0) break;
        const upTokens = rawLines[idx - back]
          .split(/[\s\t|,;]+/)
          .filter((t) => !t.includes('%'))
          .map((t) => t.replace(/,/g, ''))
          .filter((t) => /^[+-]?\d+(\.\d+)?$/.test(t))
          .map((t) => parseFloat(t));

        if (upTokens.length >= 3 && Math.round(upTokens[0]) === shares) {
          const pnlAbs = Math.abs(upTokens[2]);
          const feeRate = sec.type === 'etf' ? 0.002425 : 0.00585;
          const impliedGainCost = Math.round((curPrice * (1 - feeRate) - pnlAbs / shares) * 100) / 100;
          const impliedLossCost = Math.round((curPrice * (1 - feeRate) + pnlAbs / shares) * 100) / 100;

          const diffGain = Math.abs(avgCost - impliedGainCost) / curPrice;
          const diffLoss = Math.abs(avgCost - impliedLossCost) / curPrice;

          if (Math.min(diffGain, diffLoss) > 0.25 && impliedGainCost > 0) {
            avgCost = impliedGainCost;
          }
          break;
        }
      }
    }

    // 若同一檔股票在上一行（名稱行）已經被粗略抓過，代號行（isCodeLine = true）有最精準的成本均價，優先覆蓋！
    const existing = resultsMap.get(found.code);
    if (!existing || found.isCodeLine) {
      resultsMap.set(found.code, {
        code: sec.code,
        name: sec.name,
        shares,
        avgCost: Math.round(avgCost * 100) / 100,
        currentPrice: curPrice,
        selected: true,
      });
    }
  }

  return Array.from(resultsMap.values());
}

/**
 * 瀏覽器端辨識單張或多張券商 App 截圖
 */
export async function recognizeScreenshots(
  files: File[],
  items: Record<string, SecuritySummary>,
  onProgress?: (msg: string) => void,
): Promise<{ candidates: ParsedHoldingCandidate[]; rawOcrText: string }> {
  const Tesseract = await import('tesseract.js');
  const allTexts: string[] = [];

  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    onProgress?.(`正在辨識第 ${i + 1} / ${files.length} 張截圖（${file.name}）...`);
    const res = await Tesseract.recognize(file, 'eng');
    allTexts.push(res.data.text || '');
  }

  const combinedText = allTexts.join('\n');
  const candidates = parseHoldingsText(combinedText, items);
  return { candidates, rawOcrText: combinedText };
}

