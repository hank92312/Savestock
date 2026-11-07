// Savestock v2 — 主應用框架、Hash 路由與側欄/底部導覽列

import React, { useEffect, useState } from 'react';
import { useAppStore } from './store';
import { DashboardPage } from './pages/DashboardPage';
import { PortfolioPage } from './pages/PortfolioPage';
import { ExplorePage } from './pages/ExplorePage';
import { EtfPage } from './pages/EtfPage';
import { SecurityDetailPage } from './pages/SecurityDetailPage';
import { SettingsPage } from './pages/SettingsPage';
import { HoldingModal } from './components/SecurityCard';
import type { SecuritySummary } from './types';

type TabKey = 'dashboard' | 'portfolio' | 'explore' | 'etf' | 'settings';

export const App: React.FC = () => {
  const initApp = useAppStore((s) => s.initApp);
  const loading = useAppStore((s) => s.loading);
  const error = useAppStore((s) => s.error);
  const meta = useAppStore((s) => s.meta);
  const syncStatus = useAppStore((s) => s.syncStatus);

  const [activeTab, setActiveTab] = useState<TabKey>('dashboard');
  const [selectedSecurity, setSelectedSecurity] = useState<string | null>(null);
  const [editingItem, setEditingItem] = useState<SecuritySummary | null>(null);

  useEffect(() => {
    initApp();
  }, [initApp]);

  // 支援 Hash 深連結（如 #/stock/2412 或 #/settings?pair=123456）
  useEffect(() => {
    const syncFromHash = () => {
      const h = window.location.hash.replace(/^#\/?/, '');
      if (h.startsWith('stock/')) {
        setSelectedSecurity(h.slice(6).toUpperCase());
      } else if (h.startsWith('settings')) {
        setSelectedSecurity(null);
        setActiveTab('settings');
      } else if (h === 'portfolio' || h === 'explore' || h === 'etf' || h === 'dashboard') {
        setSelectedSecurity(null);
        setActiveTab(h as TabKey);
      }
    };
    syncFromHash();
    window.addEventListener('hashchange', syncFromHash);
    return () => window.removeEventListener('hashchange', syncFromHash);
  }, []);

  const navigateTab = (tab: TabKey) => {
    setSelectedSecurity(null);
    setActiveTab(tab);
    window.location.hash = `#/${tab}`;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const openSecurity = (code: string) => {
    const clean = code.replace('.TW', '').replace('.TWO', '').toUpperCase();
    setSelectedSecurity(clean);
    window.location.hash = `#/stock/${clean}`;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const navItems: { id: TabKey; icon: string; label: string }[] = [
    { id: 'dashboard', icon: '🏠', label: '總覽' },
    { id: 'portfolio', icon: '💼', label: '我的持股' },
    { id: 'explore', icon: '🔍', label: '探索存股' },
    { id: 'etf', icon: '🧠', label: 'ETF 追蹤' },
    { id: 'settings', icon: '⚙️', label: '設定同步' },
  ];

  return (
    <div className="app-layout">
      {/* 桌機左側導覽欄 */}
      <aside className="sidebar">
        <div className="brand-logo" style={{ cursor: 'pointer' }} onClick={() => navigateTab('dashboard')}>
          <div className="brand-logo-icon">S</div>
          <div>
            <div style={{ fontWeight: 800, fontSize: 16.5, lineHeight: 1.2 }}>Savestock</div>
            <div className="text-muted" style={{ fontSize: 11 }}>長線存股 · ETF 追蹤</div>
          </div>
        </div>

        {navItems.map((n) => (
          <button
            key={n.id}
            className={`nav-item ${!selectedSecurity && activeTab === n.id ? 'active' : ''}`}
            onClick={() => navigateTab(n.id)}
          >
            <span style={{ fontSize: 17 }}>{n.icon}</span>
            <span>{n.label}</span>
          </button>
        ))}

        <div style={{ marginTop: 'auto', padding: '12px 10px', borderTop: '1px solid var(--border-soft)', fontSize: 12 }} className="text-muted">
          <div>收盤日：{meta?.marketDate || '更新中'}</div>
          <div>涵蓋標的：{meta?.counts.total || 0} 檔</div>
          <div style={{ marginTop: 4, cursor: 'pointer' }} onClick={() => navigateTab('settings')}>
            狀態：{syncStatus === 'synced' ? '🟢 雲端同步保護中' : '⚪ 點此開啟雲端備份'}
          </div>
        </div>
      </aside>

      {/* 主內容區 */}
      <main className="main-content">
        {loading ? (
          <div className="card" style={{ padding: 36, textAlign: 'center' }}>
            <h2 style={{ fontSize: 18, marginBottom: 6 }}>正在載入最新收盤與配息資料...</h2>
            <p className="text-muted">載入完成後即可離線秒開瀏覽</p>
          </div>
        ) : error ? (
          <div className="card" style={{ padding: 28, borderColor: 'var(--danger)' }}>
            <h3>載入錯誤：{error}</h3>
          </div>
        ) : selectedSecurity ? (
          <SecurityDetailPage
            code={selectedSecurity}
            onBack={() => window.history.back()}
            onSelectSecurity={openSecurity}
            onQuickEdit={setEditingItem}
          />
        ) : (
          <>
            {activeTab === 'dashboard' && (
              <DashboardPage
                onSelectSecurity={openSecurity}
                onQuickEdit={setEditingItem}
                onNavigateTab={(t) => navigateTab(t as TabKey)}
              />
            )}
            {activeTab === 'portfolio' && (
              <PortfolioPage
                onSelectSecurity={openSecurity}
                onQuickEdit={setEditingItem}
              />
            )}
            {activeTab === 'explore' && (
              <ExplorePage
                onSelectSecurity={openSecurity}
                onQuickEdit={setEditingItem}
              />
            )}
            {activeTab === 'etf' && (
              <EtfPage
                onSelectSecurity={openSecurity}
                onQuickEdit={setEditingItem}
              />
            )}
            {activeTab === 'settings' && <SettingsPage />}
          </>
        )}

        <footer style={{ marginTop: 40, paddingTop: 18, borderTop: '1px solid var(--border-soft)', fontSize: 12 }} className="text-muted">
          Savestock v2 — 資料取自臺灣證券交易所、證券櫃檯買賣中心、集保結算所與公開財經資訊。所有健康評分、殖利率價格帶與量化因子僅供個人投資研究參考，不構成任何買賣建議。
        </footer>
      </main>

      {/* 手機底部導覽欄 */}
      <nav className="bottom-nav">
        {navItems.map((n) => (
          <button
            key={n.id}
            className={`bottom-nav-btn ${!selectedSecurity && activeTab === n.id ? 'active' : ''}`}
            onClick={() => navigateTab(n.id)}
          >
            <span style={{ fontSize: 18 }}>{n.icon}</span>
            <span>{n.label}</span>
          </button>
        ))}
      </nav>

      {/* 快速新增/調整持股彈窗 */}
      {editingItem && (
        <HoldingModal item={editingItem} onClose={() => setEditingItem(null)} />
      )}
    </div>
  );
};

