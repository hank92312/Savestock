// Savestock v2 — ⚙️ 設定、Cloudflare D1 跨裝置 QR 配對、Email 通知與本機備份頁

import React, { useEffect, useState } from 'react';
import QRCode from 'qrcode';
import { useAppStore } from '../store';

export const SettingsPage: React.FC = () => {
  const userDoc = useAppStore((s) => s.userDoc);
  const deviceToken = useAppStore((s) => s.deviceToken);
  const syncStatus = useAppStore((s) => s.syncStatus);
  const lastSyncedAt = useAppStore((s) => s.lastSyncedAt);
  const updateSettings = useAppStore((s) => s.updateSettings);
  const setDeviceToken = useAppStore((s) => s.setDeviceToken);
  const syncWithCloud = useAppStore((s) => s.syncWithCloud);
  const importDocJson = useAppStore((s) => s.importDocJson);

  const [apiUrl, setApiUrl] = useState(userDoc.settings.syncApiUrl || '');
  const [inviteCode, setInviteCode] = useState('HANK-ADMIN');
  const [regNick, setRegNick] = useState(userDoc.settings.nickname || '');
  const [regEmail, setRegEmail] = useState(userDoc.settings.email || '');
  const [pairCodeInput, setPairCodeInput] = useState('');
  const [generatedPairCode, setGeneratedPairCode] = useState<string | null>(null);
  const [qrDataUrl, setQrDataUrl] = useState<string>('');
  const [msg, setMsg] = useState<string>('');
  const [importText, setImportText] = useState('');

  // 若網址帶有 #pair=XXXXXX&api=... 自動填入配對碼
  useEffect(() => {
    const hash = window.location.hash;
    if (hash.includes('pair=')) {
      const params = new URLSearchParams(hash.replace(/^#\/?settings\??/, ''));
      const p = params.get('pair');
      const a = params.get('api');
      if (p) setPairCodeInput(p);
      if (a) setApiUrl(a);
    }
  }, []);

  const handleRegisterWithInvite = async () => {
    const base = apiUrl.trim().replace(/\/+$/, '');
    if (!base) {
      setMsg('請先填入你的 Cloudflare Worker 同步網址');
      return;
    }
    const finalEmail = (regEmail || userDoc.settings.email || '').trim().toLowerCase();
    if (!finalEmail) {
      setMsg('請填寫接收盤後異常警示與除息通知的 Email 信箱');
      return;
    }
    const finalNick = (regNick || userDoc.settings.nickname || '存股夥伴').trim();

    try {
      const res = await fetch(`${base}/v1/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          inviteCode: inviteCode.trim() || 'HANK-ADMIN',
          nickname: finalNick,
          email: finalEmail,
          doc: userDoc,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || '註冊失敗');
      await updateSettings({ nickname: finalNick, email: finalEmail });
      await setDeviceToken(data.token, base);
      setMsg(`✅ 啟用成功！裝置已綁定雲端同步（復原碼：${data.recoveryCode || '已儲存'}）`);
    } catch (e: any) {
      setMsg(`❌ ${e.message}`);
    }
  };

  const handleStartPair = async () => {
    const base = (apiUrl || userDoc.settings.syncApiUrl || '').trim().replace(/\/+$/, '');
    if (!base || !deviceToken) {
      setMsg('請先完成首次雲端啟用後再產生手機配對碼');
      return;
    }
    try {
      const res = await fetch(`${base}/v1/pair/start`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${deviceToken}` },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || '無法產生配對碼');
      setGeneratedPairCode(data.code);
      const pairUrl = `${window.location.origin}${window.location.pathname}#/settings?pair=${data.code}&api=${encodeURIComponent(base)}`;
      const qr = await QRCode.toDataURL(pairUrl, { width: 200, margin: 1 });
      setQrDataUrl(qr);
      setMsg('✅ 已產生 5 分鐘有效的 6 位數配對碼與 QR Code，請用手機掃描！');
    } catch (e: any) {
      setMsg(`❌ ${e.message}`);
    }
  };

  const handleClaimPair = async () => {
    const base = (apiUrl || userDoc.settings.syncApiUrl || '').trim().replace(/\/+$/, '');
    if (!base || !pairCodeInput.trim()) {
      setMsg('請確認同步網址與 6 位數配對碼');
      return;
    }
    try {
      const res = await fetch(`${base}/v1/pair/claim`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: pairCodeInput.trim(), label: navigator.userAgent.slice(0, 40) }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || '配對失敗');
      await setDeviceToken(data.token, base);
      setMsg('✅ 手機與 PC 配對成功！已自動同步最新持股與設定。');
    } catch (e: any) {
      setMsg(`❌ ${e.message}`);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      <div>
        <h1 style={{ fontSize: 22, fontWeight: 700 }}>⚙️ 跨裝置同步、Email 通知與外觀設定</h1>
        <p className="text-muted" style={{ fontSize: 13.5 }}>
          透過 Cloudflare Workers + D1 免費雲端資料庫，在 PC 與外出手機瀏覽器之間零成本即時同步持股。
        </p>
      </div>

      {msg && (
        <div className="card" style={{ borderColor: 'var(--brand)', background: 'var(--brand-soft)', fontWeight: 600 }}>
          {msg}
        </div>
      )}

      <div className="grid-2">
        {/* 1. 跨裝置雲端同步與 QR 配對 */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ fontSize: 17, fontWeight: 700 }}>☁️ PC ↔ 手機 跨裝置雲端同步 (Cloudflare D1)</h2>
            <span className={`badge ${syncStatus === 'synced' ? 'badge-brand' : 'badge-subtle'}`}>
              {syncStatus === 'synced' ? `已同步 (${lastSyncedAt})` : syncStatus === 'syncing' ? '同步中...' : '本機模式'}
            </span>
          </div>

          <div>
            <label style={{ fontSize: 12.5, fontWeight: 600, display: 'block', marginBottom: 4 }}>
              Cloudflare Worker 同步服務網址
            </label>
            <input
              className="input"
              placeholder="https://savestock-sync.<你的帳號>.workers.dev"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
            />
          </div>

          {!deviceToken ? (
            <div style={{ background: 'var(--bg-subtle)', padding: 14, borderRadius: 'var(--radius-md)', display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--brand)' }}>方式 A：首次啟用（自己或朋友獨立帳號）</div>
              <p className="text-muted" style={{ fontSize: 12.5, margin: 0, lineHeight: 1.5 }}>
                每位朋友填寫各自的名字與 Email 點擊啟用，系統會在 D1 自動分配各自獨立的持股記錄，各自保密且每日各別寄信通知！
              </p>

              <div className="grid-2">
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 3 }}>你的暱稱</label>
                  <input
                    className="input"
                    placeholder="例：Hank 或 小王"
                    value={regNick}
                    onChange={(e) => setRegNick(e.target.value)}
                  />
                </div>
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 3 }}>接收通知 Email (必填)</label>
                  <input
                    className="input"
                    placeholder="例：hank92312@gmail.com"
                    value={regEmail}
                    onChange={(e) => setRegEmail(e.target.value)}
                  />
                </div>
              </div>

              <div>
                <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 3 }}>專屬邀請碼</label>
                <div style={{ display: 'flex', gap: 8 }}>
                  <input
                    className="input"
                    placeholder="預設 HANK-ADMIN"
                    value={inviteCode}
                    onChange={(e) => setInviteCode(e.target.value)}
                  />
                  <button className="btn btn-primary" style={{ whiteSpace: 'nowrap' }} onClick={handleRegisterWithInvite}>
                    一鍵啟用雲端同步
                  </button>
                </div>
              </div>

              <div style={{ borderTop: '1px solid var(--border-soft)', paddingTop: 10, marginTop: 4 }}>
                <div style={{ fontWeight: 700, fontSize: 13.5, marginBottom: 4 }}>方式 B：第二台裝置快速配對（手機 ↔ 電腦雙向通用）</div>
                <div className="text-muted" style={{ fontSize: 12, marginBottom: 8 }}>
                  無論您先在「手機」或「電腦」設定，若想在另一台裝置同步，只需輸入另一台已啟用裝置顯示的 6 位數配對碼：
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <input
                    className="input"
                    placeholder="輸入另一台裝置顯示的 6 位數配對碼"
                    value={pairCodeInput}
                    onChange={(e) => setPairCodeInput(e.target.value)}
                  />
                  <button className="btn btn-primary" style={{ whiteSpace: 'nowrap' }} onClick={handleClaimPair}>
                    綁定此裝置
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div style={{ background: 'var(--bg-subtle)', padding: 14, borderRadius: 'var(--radius-md)', display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 600 }}>此裝置已綁定雲端同步</span>
                <div style={{ display: 'flex', gap: 6 }}>
                  <button className="btn" onClick={() => syncWithCloud(true)}>立即同步</button>
                  <button className="btn btn-primary" onClick={handleStartPair}>📱 產生跨裝置配對碼 / QR Code</button>
                </div>
              </div>

              {generatedPairCode && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 8, flexWrap: 'wrap' }}>
                  {qrDataUrl && <img src={qrDataUrl} alt="Pair QR" style={{ width: 130, height: 130, borderRadius: 8 }} />}
                  <div>
                    <div className="text-muted" style={{ fontSize: 12 }}>6 位數配對碼（5 分鐘內有效）：</div>
                    <div style={{ fontSize: 28, fontWeight: 800, letterSpacing: 3, color: 'var(--brand)' }}>
                      {generatedPairCode}
                    </div>
                    <div className="text-muted" style={{ fontSize: 12 }}>
                      在另一台手機或電腦打開設定頁輸入此配對碼（或用手機相機掃描 QR Code），即可瞬間同步！
                    </div>
                  </div>
                </div>
              )}

              <div style={{ marginTop: 4 }}>
                <button
                  className="btn"
                  style={{ fontSize: 12, color: 'var(--danger)' }}
                  onClick={() => setDeviceToken('')}
                >
                  登出此裝置 Token
                </button>
              </div>
            </div>
          )}
        </div>

        {/* 2. 個人資料、Email 推播與外觀主題 */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <h2 style={{ fontSize: 17, fontWeight: 700 }}>✉️ Email 推播通知與個人偏好</h2>

          <div className="grid-2">
            <div>
              <label style={{ fontSize: 12.5, fontWeight: 600, display: 'block', marginBottom: 4 }}>暱稱</label>
              <input
                className="input"
                value={userDoc.settings.nickname}
                onChange={(e) => updateSettings({ nickname: e.target.value })}
              />
            </div>
            <div>
              <label style={{ fontSize: 12.5, fontWeight: 600, display: 'block', marginBottom: 4 }}>
                接收通知 Email（預設 hank92312@gmail.com）
              </label>
              <input
                className="input"
                value={userDoc.settings.email}
                onChange={(e) => updateSettings({ email: e.target.value })}
              />
            </div>
          </div>

          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginTop: 4 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={userDoc.settings.notifyDaily}
                onChange={(e) => updateSettings({ notifyDaily: e.target.checked })}
              />
              <span>每日盤後異常警示與除權息摘要（有事件才寄信）</span>
            </label>

            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={userDoc.settings.notifyWeekly}
                onChange={(e) => updateSettings({ notifyWeekly: e.target.checked })}
              />
              <span>每週六投資組合與股利進度週報</span>
            </label>
          </div>

          <div style={{ marginTop: 8 }}>
            <label style={{ fontSize: 12.5, fontWeight: 600, display: 'block', marginBottom: 6 }}>
              視覺主題配色（低對比溫潤紙感 / 夜間暖黑）
            </label>
            <div style={{ display: 'flex', gap: 8 }}>
              {(['light', 'dark', 'auto'] as const).map((t) => (
                <button
                  key={t}
                  className={`chip ${userDoc.settings.theme === t ? 'active' : ''}`}
                  onClick={() => updateSettings({ theme: t })}
                >
                  {t === 'light' ? '☀️ 溫潤淺色' : t === 'dark' ? '🌙 柔和深色' : '🖥️ 跟隨系統'}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 3. 免伺服器備援：一鍵匯出 / 匯入 JSON 備份 */}
      <div className="card">
        <h2 style={{ fontSize: 16.5, fontWeight: 700, marginBottom: 6 }}>📦 離線備份匯出與匯入</h2>
        <p className="text-muted" style={{ fontSize: 13, marginBottom: 12 }}>
          除了 Cloudflare D1 自動雲端同步外，你也可以隨時將完整持股與設定匯出成 JSON 文字保存或傳給朋友：
        </p>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 10 }}>
          <button
            className="btn"
            onClick={() => {
              navigator.clipboard.writeText(JSON.stringify(userDoc, null, 2));
              setMsg('✅ 已複製完整持股 JSON 到剪貼簿！');
            }}
          >
            複製目前持股 JSON
          </button>
          <button
            className="btn"
            onClick={() => {
              const blob = new Blob([JSON.stringify(userDoc, null, 2)], { type: 'application/json' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `savestock-backup-${new Date().toISOString().slice(0, 10)}.json`;
              a.click();
            }}
          >
            下載備份檔 (.json)
          </button>
        </div>

        <div style={{ display: 'flex', gap: 8 }}>
          <input
            className="input"
            placeholder="貼上備份 JSON 內容以還原或合併持股..."
            value={importText}
            onChange={(e) => setImportText(e.target.value)}
          />
          <button
            className="btn btn-primary"
            onClick={async () => {
              if (!importText.trim()) return;
              try {
                await importDocJson(importText);
                setImportText('');
                setMsg('✅ 匯入並合併持股成功！');
              } catch {
                setMsg('❌ JSON 格式不正確');
              }
            }}
          >
            匯入合併
          </button>
        </div>
      </div>
    </div>
  );
};

