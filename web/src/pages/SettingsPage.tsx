// Savestock v2 — ⚙️ 零門檻小白友善設定頁（一鍵 Email 雲端同步、掃碼自動配對、深淺主題與一鍵檔案備份）

import React, { useEffect, useRef, useState } from 'react';
import QRCode from 'qrcode';
import { PROD_SYNC_URL, useAppStore } from '../store';

export const SettingsPage: React.FC = () => {
  const userDoc = useAppStore((s) => s.userDoc);
  const deviceToken = useAppStore((s) => s.deviceToken);
  const syncStatus = useAppStore((s) => s.syncStatus);
  const lastSyncedAt = useAppStore((s) => s.lastSyncedAt);
  const updateSettings = useAppStore((s) => s.updateSettings);
  const setDeviceToken = useAppStore((s) => s.setDeviceToken);
  const syncWithCloud = useAppStore((s) => s.syncWithCloud);
  const importDocJson = useAppStore((s) => s.importDocJson);

  const [regNick, setRegNick] = useState(
    userDoc.settings.nickname && userDoc.settings.nickname !== '存股夥伴'
      ? userDoc.settings.nickname
      : '',
  );
  const [regEmail, setRegEmail] = useState(userDoc.settings.email || '');
  const [submitting, setSubmitting] = useState(false);

  const [showPairInput, setShowPairInput] = useState(false);
  const [pairCodeInput, setPairCodeInput] = useState('');
  const [generatedPairCode, setGeneratedPairCode] = useState<string | null>(null);
  const [qrDataUrl, setQrDataUrl] = useState<string>('');
  const [msg, setMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const getBaseApiUrl = () => {
    return ((userDoc.settings.syncApiUrl || '').trim() || PROD_SYNC_URL).replace(/\/+$/, '');
  };

  // 若手機掃描 QR Code 進來帶有 #/settings?pair=XXXXXX，自動完成配對綁定！
  useEffect(() => {
    const hash = window.location.hash;
    if (hash.includes('pair=')) {
      const qIndex = hash.indexOf('?');
      const params = new URLSearchParams(qIndex >= 0 ? hash.slice(qIndex + 1) : '');
      const p = params.get('pair');
      const a = params.get('api') || getBaseApiUrl();
      if (p) {
        setPairCodeInput(p);
        setShowPairInput(true);
        handleClaimPairCode(p, a);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 當雲端資料拉取完成後，同步更新輸入框顯示
  useEffect(() => {
    if (userDoc.settings.email) setRegEmail(userDoc.settings.email);
    if (userDoc.settings.nickname && userDoc.settings.nickname !== '存股夥伴') {
      setRegNick(userDoc.settings.nickname);
    }
  }, [userDoc.settings.email, userDoc.settings.nickname]);

  const handleOneClickSetup = async () => {
    const finalEmail = regEmail.trim().toLowerCase();
    if (!finalEmail || !finalEmail.includes('@')) {
      setMsg({ type: 'err', text: '⚠️ 請輸入有效的 Email 信箱（例如：name@gmail.com），才能為您保存持股與寄送通知喔！' });
      return;
    }
    const finalNick = regNick.trim() || finalEmail.split('@')[0] || '存股夥伴';
    const base = getBaseApiUrl();

    setSubmitting(true);
    setMsg(null);
    try {
      const updatedDoc = {
        ...userDoc,
        settings: {
          ...userDoc.settings,
          nickname: finalNick,
          email: finalEmail,
          syncApiUrl: base,
        },
      };

      const res = await fetch(`${base}/v1/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          inviteCode: 'HANK-ADMIN',
          nickname: finalNick,
          email: finalEmail,
          doc: updatedDoc,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || '連線雲端失敗，請稍後再試');

      await updateSettings({ nickname: finalNick, email: finalEmail, syncApiUrl: base });
      await setDeviceToken(data.token, base);
      setMsg({
        type: 'ok',
        text: `🎉 設定完成！已為「${finalNick} (${finalEmail})」開啟自動雲端保存與信箱通知！日後換手機或換電腦，只要輸入同一個 Email 就能自動帶入持股。`,
      });
    } catch (e: any) {
      setMsg({ type: 'err', text: `❌ 設定失敗：${e.message}` });
    } finally {
      setSubmitting(false);
    }
  };

  const handleSaveProfileUpdate = async () => {
    const finalEmail = regEmail.trim().toLowerCase();
    if (!finalEmail || !finalEmail.includes('@')) {
      setMsg({ type: 'err', text: '⚠️ 請填入正確的 Email 格式' });
      return;
    }
    const finalNick = regNick.trim() || '存股夥伴';
    await updateSettings({ nickname: finalNick, email: finalEmail });
    await syncWithCloud(false);
    setMsg({ type: 'ok', text: '✅ 已儲存您的稱呼與通知設定，並同步至雲端！' });
  };

  const handleStartPair = async () => {
    const base = getBaseApiUrl();
    if (!deviceToken) {
      setMsg({ type: 'err', text: '請先完成上方 Email 啟用後，再產生配對碼' });
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
      const pairUrl = `${window.location.origin}${window.location.pathname}#/settings?pair=${data.code}`;
      const qr = await QRCode.toDataURL(pairUrl, { width: 220, margin: 1 });
      setQrDataUrl(qr);
      setMsg({ type: 'ok', text: '📱 已產生手機配對 QR Code！請直接拿手機相機掃描下方條碼，手機打開就會自動綁定完成！' });
    } catch (e: any) {
      setMsg({ type: 'err', text: `❌ ${e.message}` });
    }
  };

  const handleClaimPairCode = async (codeOverride?: string, apiOverride?: string) => {
    const base = (apiOverride || getBaseApiUrl()).replace(/\/+$/, '');
    const code = (codeOverride ?? pairCodeInput).trim();
    if (!code) {
      setMsg({ type: 'err', text: '請輸入 6 位數配對碼' });
      return;
    }
    setSubmitting(true);
    try {
      const res = await fetch(`${base}/v1/pair/claim`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, label: navigator.userAgent.slice(0, 40) }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || '配對碼無效或已過期');
      await setDeviceToken(data.token, base);
      // 清除網址上的 pair 參數避免重複觸發
      if (window.location.hash.includes('pair=')) {
        window.history.replaceState(null, '', `${window.location.pathname}#/settings`);
      }
      setMsg({ type: 'ok', text: '🎉 裝置配對成功！已自動從雲端載入您的全部持股與設定！' });
    } catch (e: any) {
      setMsg({ type: 'err', text: `❌ ${e.message}` });
    } finally {
      setSubmitting(false);
    }
  };

  const handleFileRestore = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (ev) => {
      try {
        const content = String(ev.target?.result || '');
        await importDocJson(content);
        setMsg({ type: 'ok', text: '✅ 備份檔案還原成功！已恢復您的持股清單。' });
      } catch {
        setMsg({ type: 'err', text: '❌ 備份檔案格式不正確，請選擇從本網站下載的 .json 備份檔。' });
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div>
        <h1 style={{ fontSize: 22, fontWeight: 700 }}>⚙️ 帳號同步、信箱通知與畫面設定</h1>
        <p className="text-muted" style={{ fontSize: 14, marginTop: 4 }}>
          免註冊密碼！只要填寫您的稱呼與 Email，系統就會自動把您的持股保存在雲端，換手機或換電腦都能隨時接續查看。
        </p>
      </div>

      {msg && (
        <div
          className="card"
          style={{
            borderColor: msg.type === 'ok' ? 'var(--brand)' : 'var(--danger)',
            background: msg.type === 'ok' ? 'var(--brand-soft)' : 'var(--danger-soft)',
            color: msg.type === 'ok' ? 'var(--text-primary)' : 'var(--danger)',
            fontWeight: 600,
            fontSize: 14,
            lineHeight: 1.6,
          }}
        >
          {msg.text}
        </div>
      )}

      {/* 主卡片：根據是否已綁定雲端，顯示「3步輕鬆啟用」或「已開啟同步狀態」 */}
      {!deviceToken ? (
        <div className="card" style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 18 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
            <div>
              <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--brand)' }}>
                ☁️ 第一步：開啟您的專屬雲端保存與除息通知
              </h2>
              <p className="text-muted" style={{ fontSize: 13.5, marginTop: 4 }}>
                每位朋友填寫自己的 Email 後，系統會自動建立各自獨立保密的持股空間，不會與其他人混在一起。
              </p>
            </div>
            <span className="badge badge-subtle">目前為本機暫存模式</span>
          </div>

          <div className="grid-2" style={{ gap: 14 }}>
            <div>
              <label style={{ fontSize: 13.5, fontWeight: 700, display: 'block', marginBottom: 6 }}>
                1. 您的稱呼（怎麼稱呼您？）
              </label>
              <input
                className="input"
                style={{ fontSize: 15, padding: '10px 12px' }}
                placeholder="例如：阿明、小美、Hank"
                value={regNick}
                onChange={(e) => setRegNick(e.target.value)}
              />
            </div>

            <div>
              <label style={{ fontSize: 13.5, fontWeight: 700, display: 'block', marginBottom: 6 }}>
                2. 您的 Email 信箱（必填，找回持股與收通知用）
              </label>
              <input
                type="email"
                className="input"
                style={{ fontSize: 15, padding: '10px 12px' }}
                placeholder="例如：yourname@gmail.com"
                value={regEmail}
                onChange={(e) => setRegEmail(e.target.value)}
              />
            </div>
          </div>

          <div style={{ background: 'var(--bg-subtle)', padding: 14, borderRadius: 'var(--radius-md)', display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontSize: 13.5, fontWeight: 700 }}>3. 選擇您想收到的免費信箱提醒：</div>
            <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', fontSize: 14 }}>
              <input
                type="checkbox"
                style={{ width: 17, height: 17 }}
                checked={userDoc.settings.notifyDaily}
                onChange={(e) => updateSettings({ notifyDaily: e.target.checked })}
              />
              <span><strong>每日盤後異常波動與除權息提醒</strong>（平時安靜不打擾，只有持股大跌或即將除息才寄信）</span>
            </label>

            <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', fontSize: 14 }}>
              <input
                type="checkbox"
                style={{ width: 17, height: 17 }}
                checked={userDoc.settings.notifyWeekly}
                onChange={(e) => updateSettings({ notifyWeekly: e.target.checked })}
              />
              <span><strong>每週六投資組合與股利進度週報</strong></span>
            </label>
          </div>

          <button
            className="btn btn-primary"
            style={{ padding: '13px 20px', fontSize: 16, fontWeight: 700, width: '100%' }}
            onClick={handleOneClickSetup}
            disabled={submitting}
          >
            {submitting ? '正在為您連接雲端...' : '🚀 立即儲存並開啟雲端同步'}
          </button>

          <div style={{ borderTop: '1px solid var(--border-soft)', paddingTop: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10 }}>
            <span className="text-muted" style={{ fontSize: 13 }}>
              💡 <strong>換手機或換電腦嗎？</strong> 直接在上方輸入您之前設定過的<strong>同一個 Email</strong> 按下按鈕，就會自動載入您的持股！
            </span>
            <button
              className="btn"
              style={{ fontSize: 12.5, padding: '5px 12px' }}
              onClick={() => setShowPairInput(!showPairInput)}
            >
              {showPairInput ? '收起配對碼輸入' : '📱 或輸入 6 位數配對碼'}
            </button>
          </div>

          {showPairInput && (
            <div style={{ background: 'var(--bg-subtle)', padding: 14, borderRadius: 'var(--radius-md)', display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
              <input
                className="input"
                style={{ maxWidth: 260 }}
                placeholder="輸入另一台裝置顯示的 6 位數配對碼"
                value={pairCodeInput}
                onChange={(e) => setPairCodeInput(e.target.value)}
              />
              <button
                className="btn btn-primary"
                onClick={() => handleClaimPairCode()}
                disabled={submitting}
              >
                連接裝置
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="card" style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 18 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10, paddingBottom: 14, borderBottom: '1px solid var(--border-soft)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ width: 42, height: 42, borderRadius: '50%', background: 'var(--brand-soft)', color: 'var(--brand)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20, fontWeight: 800 }}>
                ✓
              </div>
              <div>
                <div style={{ fontSize: 17, fontWeight: 700 }}>
                  雲端自動同步保護中 — {userDoc.settings.nickname || '存股夥伴'}
                </div>
                <div className="text-muted" style={{ fontSize: 13 }}>
                  綁定信箱：{userDoc.settings.email || '未填寫'} ‧ 狀態：{syncStatus === 'synced' ? `已同步 (${lastSyncedAt})` : syncStatus === 'syncing' ? '同步中...' : '連線就緒'}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button className="btn" onClick={() => syncWithCloud(true)}>
                🔄 立即同步最新資料
              </button>
              <button className="btn btn-primary" onClick={handleStartPair}>
                📱 產生手機 / 電腦配對條碼
              </button>
            </div>
          </div>

          {generatedPairCode && (
            <div style={{ background: 'var(--brand-soft)', border: '1px solid var(--brand)', padding: 18, borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap' }}>
              {qrDataUrl && (
                <img src={qrDataUrl} alt="Pair QR" style={{ width: 150, height: 150, borderRadius: 10, background: '#fff', padding: 6 }} />
              )}
              <div style={{ flex: 1, minWidth: 220 }}>
                <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 4 }}>
                  📸 請拿另一台手機打開相機掃描左側條碼！
                </div>
                <p className="text-muted" style={{ fontSize: 13, marginBottom: 8 }}>
                  掃描後打開網頁就會<strong>自動完成綁定並載入所有持股</strong>，完全不用打字！<br />
                  （若無法掃描，也可在另一台裝置輸入下方 6 位數配對碼，5 分鐘內有效）：
                </p>
                <div style={{ fontSize: 30, fontWeight: 800, letterSpacing: 4, color: 'var(--brand)' }}>
                  {generatedPairCode}
                </div>
              </div>
            </div>
          )}

          <div className="grid-2" style={{ gap: 14 }}>
            <div>
              <label style={{ fontSize: 13, fontWeight: 600, display: 'block', marginBottom: 4 }}>您的稱呼</label>
              <input
                className="input"
                value={regNick}
                onChange={(e) => setRegNick(e.target.value)}
              />
            </div>
            <div>
              <label style={{ fontSize: 13, fontWeight: 600, display: 'block', marginBottom: 4 }}>接收通知 Email</label>
              <input
                type="email"
                className="input"
                value={regEmail}
                onChange={(e) => setRegEmail(e.target.value)}
              />
            </div>
          </div>

          <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 14 }}>
              <input
                type="checkbox"
                checked={userDoc.settings.notifyDaily}
                onChange={(e) => updateSettings({ notifyDaily: e.target.checked })}
              />
              <span>每日盤後異常警示與除權息摘要（有事件才寄信）</span>
            </label>

            <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 14 }}>
              <input
                type="checkbox"
                checked={userDoc.settings.notifyWeekly}
                onChange={(e) => updateSettings({ notifyWeekly: e.target.checked })}
              />
              <span>每週六投資組合與股利進度週報</span>
            </label>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10, paddingTop: 8, borderTop: '1px solid var(--border-soft)' }}>
            <button className="btn btn-primary" onClick={handleSaveProfileUpdate}>
              💾 儲存資料修改
            </button>

            <button
              className="btn"
              style={{ fontSize: 12.5, color: 'var(--danger)' }}
              onClick={() => {
                if (window.confirm('確定要在這台裝置登出目前的雲端帳號嗎？（您的資料仍安全保存在雲端，隨時可重新輸入 Email 登入）')) {
                  setDeviceToken('');
                  setGeneratedPairCode(null);
                  setMsg({ type: 'ok', text: '已登出此裝置。您可以重新輸入其他 Email 帳號啟用。' });
                }
              }}
            >
              切換其他帳號 / 登出此裝置
            </button>
          </div>
        </div>
      )}

      {/* 第二排：畫面主題配色 + 傻瓜式一鍵檔案備份 */}
      <div className="grid-2">
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <h2 style={{ fontSize: 16.5, fontWeight: 700 }}>🎨 畫面深淺配色</h2>
          <p className="text-muted" style={{ fontSize: 13 }}>
            預設採用不刺眼的溫潤紙感配色，您也可以依習慣切換為夜間深色模式：
          </p>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 4 }}>
            {(['light', 'dark', 'auto'] as const).map((t) => (
              <button
                key={t}
                className={`chip ${userDoc.settings.theme === t ? 'active' : ''}`}
                style={{ padding: '8px 14px', fontSize: 13.5 }}
                onClick={() => updateSettings({ theme: t })}
              >
                {t === 'light' ? '☀️ 溫潤淺色（預設）' : t === 'dark' ? '🌙 柔和深色（護眼）' : '🖥️ 自動跟隨手機/電腦'}
              </button>
            ))}
          </div>
        </div>

        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <h2 style={{ fontSize: 16.5, fontWeight: 700 }}>📦 下載持股備份檔（選用）</h2>
          <p className="text-muted" style={{ fontSize: 13 }}>
            除了雲端自動保存外，您也可以隨時將持股清單下載成檔案保存在手機或電腦裡：
          </p>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 4 }}>
            <button
              className="btn"
              onClick={() => {
                const blob = new Blob([JSON.stringify(userDoc, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `我的存股備份-${new Date().toISOString().slice(0, 10)}.json`;
                a.click();
                setMsg({ type: 'ok', text: '📥 已下載您的持股備份檔！' });
              }}
            >
              📥 下載持股備份檔
            </button>

            <button
              className="btn"
              onClick={() => fileInputRef.current?.click()}
            >
              📤 從備份檔還原持股
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".json,application/json"
              style={{ display: 'none' }}
              onChange={handleFileRestore}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
