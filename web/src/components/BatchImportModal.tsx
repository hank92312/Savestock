// Savestock v2 — 📸 券商 App 截圖辨識 & 📋 整串文字快速匯入持股視窗

import React, { useEffect, useRef, useState } from 'react';
import { useAppStore } from '../store';
import {
  parseHoldingsText,
  recognizeScreenshots,
  type ParsedHoldingCandidate,
} from '../utils/batchParser';

export const BatchImportModal: React.FC<{
  initialMode?: 'screenshot' | 'text';
  onClose: () => void;
}> = ({ initialMode = 'screenshot', onClose }) => {
  const screener = useAppStore((s) => s.screener);
  const batchUpsertHoldings = useAppStore((s) => s.batchUpsertHoldings);

  const [mode, setMode] = useState<'screenshot' | 'text'>(initialMode);
  const [rawText, setRawText] = useState('');
  const [candidates, setCandidates] = useState<ParsedHoldingCandidate[]>([]);
  const [replaceAll, setReplaceAll] = useState(false);
  const [recognizing, setRecognizing] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string>('');
  const [previews, setPreviews] = useState<string[]>([]);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // 當使用者在「貼上整串文字」模式輸入或貼上時，即時自動解析
  useEffect(() => {
    if (mode === 'text' && screener?.items) {
      const parsed = parseHoldingsText(rawText, screener.items);
      setCandidates(parsed);
    }
  }, [rawText, mode, screener]);

  // 支援在視窗開啟時直接按 Ctrl+V 貼上剪貼簿裡的截圖圖片！
  useEffect(() => {
    const handlePaste = (e: ClipboardEvent) => {
      const items = e.clipboardData?.items;
      if (!items) return;
      const imageFiles: File[] = [];
      for (let i = 0; i < items.length; i++) {
        if (items[i].type.startsWith('image/')) {
          const f = items[i].getAsFile();
          if (f) imageFiles.push(f);
        }
      }
      if (imageFiles.length > 0) {
        e.preventDefault();
        setMode('screenshot');
        handleFilesSelected(imageFiles);
      }
    };
    window.addEventListener('paste', handlePaste);
    return () => window.removeEventListener('paste', handlePaste);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [screener]);

  const handleFilesSelected = async (files: File[]) => {
    if (!files.length || !screener?.items) return;
    setRecognizing(true);
    setStatusMsg('正在準備辨識截圖...');

    const urls = files.map((f) => URL.createObjectURL(f));
    setPreviews((prev) => [...prev, ...urls]);

    try {
      const { candidates: found } = await recognizeScreenshots(files, screener.items, (msg) => {
        setStatusMsg(msg);
      });

      // 與目前預覽表中的結果合併（支援一次或分批上傳多張截圖！）
      setCandidates((prev) => {
        const mergedMap = new Map<string, ParsedHoldingCandidate>();
        for (const p of prev) mergedMap.set(p.code, p);
        for (const n of found) mergedMap.set(n.code, n);
        return Array.from(mergedMap.values());
      });

      if (found.length > 0) {
        setStatusMsg(`✅ 成功從截圖辨識出 ${found.length} 檔股票！請在下方確認股數與成本均價（可直接點擊修改）：`);
      } else {
        setStatusMsg('⚠️ 未能在截圖中找到清楚的股票代號，請確認截圖包含 4~6 碼台股代號，或改用「貼上整串文字」模式。');
      }
    } catch (e: any) {
      setStatusMsg(`❌ 截圖辨識發生錯誤：${e?.message || '請重試'}`);
    } finally {
      setRecognizing(false);
    }
  };

  const updateCandidate = (code: string, patch: Partial<ParsedHoldingCandidate>) => {
    setCandidates((prev) =>
      prev.map((c) => (c.code === code ? { ...c, ...patch } : c)),
    );
  };

  const selectedList = candidates.filter((c) => c.selected && c.shares >= 0);

  const handleConfirmImport = async () => {
    if (selectedList.length === 0) return;
    await batchUpsertHoldings(
      selectedList.map((c) => ({
        code: c.code,
        shares: c.shares,
        avgCost: c.avgCost,
      })),
      replaceAll,
    );
    onClose();
  };

  const fillDemoText = () => {
    setRawText(
      [
        '0050 4800 34.52',
        '元大高股息 1000股 47.68',
        '富邦公司治理 1張 27.28',
        '00719B 2000 30.26',
        '00859B 3000 39.82',
        '凱基金 2,020 9.73',
        '台新新光金 3,194 13.65',
        '第一金 6,303 22.24',
        '日月光投控 30 617',
        '遠雄 72 45.18',
      ].join('\n'),
    );
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.52)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 16,
        zIndex: 120,
      }}
      onClick={onClose}
    >
      <div
        className="card"
        style={{
          maxWidth: 740,
          width: '100%',
          maxHeight: '90vh',
          overflowY: 'auto',
          padding: 22,
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* 標題列 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
          <div>
            <h2 style={{ fontSize: 19, fontWeight: 700 }}>
              ⚡ 快速批次匯入持股（支援截圖辨識 & 整串文字貼上）
            </h2>
            <p className="text-muted" style={{ fontSize: 13.5, marginTop: 4 }}>
              不用一檔一檔慢慢查！您可以直接上傳手機券商 App 的庫存截圖，或是把整理好的股票文字整串貼上，一次匯入全部整張與零股。
            </p>
          </div>
          <button className="btn" style={{ padding: '4px 10px' }} onClick={onClose}>
            ✕
          </button>
        </div>

        {/* 模式切換籤 */}
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button
            className={`chip ${mode === 'screenshot' ? 'active' : ''}`}
            style={{ padding: '9px 16px', fontSize: 14, fontWeight: 700 }}
            onClick={() => setMode('screenshot')}
          >
            📸 方式一：上傳券商 App 截圖（自動辨識）
          </button>
          <button
            className={`chip ${mode === 'text' ? 'active' : ''}`}
            style={{ padding: '9px 16px', fontSize: 14, fontWeight: 700 }}
            onClick={() => setMode('text')}
          >
            📋 方式二：貼上整串文字（記事本 / Excel / Line）
          </button>
        </div>

        {/* 方式一：上傳券商 App 截圖 */}
        {mode === 'screenshot' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div
              style={{
                border: '2px dashed var(--brand)',
                background: 'var(--brand-soft)',
                borderRadius: 'var(--radius-md)',
                padding: '24px 16px',
                textAlign: 'center',
                cursor: 'pointer',
              }}
              onClick={() => fileInputRef.current?.click()}
            >
              <div style={{ fontSize: 32, marginBottom: 6 }}>📱</div>
              <div style={{ fontWeight: 700, fontSize: 15.5, color: 'var(--brand)' }}>
                點此選擇手機券商 App 的「庫存 / 帳務截圖」（可一次選多張圖片！）
              </div>
              <div className="text-muted" style={{ fontSize: 13, marginTop: 4 }}>
                支援元大、凱基、富邦、國泰、永豐、台新、玉山、群益、第一金等各大券商庫存畫面，或在電腦上直接按 <strong>Ctrl + V</strong> 貼上截圖
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                multiple
                style={{ display: 'none' }}
                onChange={(e) => {
                  const files = Array.from(e.target.files || []);
                  handleFilesSelected(files);
                  e.target.value = '';
                }}
              />
            </div>

            {previews.length > 0 && (
              <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 4 }}>
                {previews.map((src, i) => (
                  <img
                    key={i}
                    src={src}
                    alt={`screenshot-${i}`}
                    style={{ height: 90, borderRadius: 8, border: '1px solid var(--border-soft)' }}
                  />
                ))}
              </div>
            )}

            {recognizing && (
              <div className="card" style={{ padding: 16, textAlign: 'center', background: 'var(--bg-subtle)' }}>
                <div style={{ fontWeight: 700, color: 'var(--brand)' }}>🔍 {statusMsg}</div>
                <div className="text-muted" style={{ fontSize: 12.5, marginTop: 4 }}>
                  正在比對全市場 2,370 檔台股代號、零股股數與成本均價...
                </div>
              </div>
            )}

            {!recognizing && statusMsg && (
              <div
                style={{
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-sm)',
                  background: 'var(--bg-subtle)',
                  fontSize: 13.5,
                  fontWeight: 600,
                }}
              >
                {statusMsg}
              </div>
            )}
          </div>
        )}

        {/* 方式二：貼上整串文字 */}
        {mode === 'text' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
              <span style={{ fontSize: 13.5, fontWeight: 600 }}>
                請在下方貼上您的股票清單（寫「股票代號」或「中文名稱」、寫「股數」或「幾張」都可以，一行一檔）：
              </span>
              <button className="btn" style={{ fontSize: 12, padding: '4px 10px' }} onClick={fillDemoText}>
                ✨ 帶入範例格式試試看
              </button>
            </div>

            <textarea
              className="input"
              rows={6}
              style={{ fontFamily: 'monospace', fontSize: 14, lineHeight: 1.6, resize: 'vertical' }}
              placeholder={`範例（空白、逗號或 Tab 分隔皆可）：\n0050 4800 34.52\n元大高股息 1000股 47.68\n凱基金 2020 9.73\n第一金 6,303 22.24\n日月光投控 30 617\n台積電 2張 850`}
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
            />
          </div>
        )}

        {/* 預覽與微調表格 */}
        {candidates.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
              <div style={{ fontWeight: 700, fontSize: 15, color: 'var(--brand)' }}>
                📋 已辨識出 {candidates.length} 檔股票（可直接修改下方股數或均價，確認無誤後點擊下方匯入）：
              </div>
              <button
                className="btn"
                style={{ fontSize: 12, padding: '3px 10px' }}
                onClick={() => {
                  setCandidates([]);
                  setPreviews([]);
                  setStatusMsg('');
                }}
              >
                清空重選
              </button>
            </div>

            <div className="table-wrap" style={{ maxHeight: 280, overflowY: 'auto', border: '1px solid var(--border-soft)', borderRadius: 'var(--radius-sm)' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th style={{ width: 42 }}>匯入</th>
                    <th>股票名稱 (代號)</th>
                    <th>持有股數（整張+零股）</th>
                    <th>成本均價（元）</th>
                    <th>目前市價</th>
                  </tr>
                </thead>
                <tbody>
                  {candidates.map((c) => (
                    <tr key={c.code}>
                      <td>
                        <input
                          type="checkbox"
                          style={{ width: 16, height: 16 }}
                          checked={c.selected}
                          onChange={(e) => updateCandidate(c.code, { selected: e.target.checked })}
                        />
                      </td>
                      <td>
                        <div style={{ fontWeight: 700 }}>{c.name}</div>
                        <div className="text-muted" style={{ fontSize: 12 }}>{c.code}</div>
                      </td>
                      <td>
                        <input
                          type="number"
                          className="input"
                          style={{ width: 115, padding: '5px 8px' }}
                          value={c.shares}
                          min={0}
                          onChange={(e) => updateCandidate(c.code, { shares: Math.max(0, Number(e.target.value) || 0) })}
                        />
                      </td>
                      <td>
                        <input
                          type="number"
                          className="input"
                          style={{ width: 110, padding: '5px 8px' }}
                          value={c.avgCost}
                          min={0}
                          step={0.01}
                          onChange={(e) => updateCandidate(c.code, { avgCost: Math.max(0, Number(e.target.value) || 0) })}
                        />
                      </td>
                      <td className="text-muted">{c.currentPrice} 元</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 13.5, marginTop: 2 }}>
              <input
                type="checkbox"
                checked={replaceAll}
                onChange={(e) => setReplaceAll(e.target.checked)}
              />
              <span>清空我原本的舊清單，只保留這次匯入的 {selectedList.length} 檔股票（若不勾選則會與現有持股合併）</span>
            </label>
          </div>
        )}

        {/* 底部確認列 */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, paddingTop: 10, borderTop: '1px solid var(--border-soft)' }}>
          <button className="btn" onClick={onClose}>
            取消
          </button>
          <button
            className="btn btn-primary"
            style={{ padding: '10px 22px', fontSize: 15, fontWeight: 700 }}
            disabled={selectedList.length === 0 || recognizing}
            onClick={handleConfirmImport}
          >
            ✅ 確認一鍵匯入 ({selectedList.length} 檔持股)
          </button>
        </div>
      </div>
    </div>
  );
};

