import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

const isGitHubActions = process.env.GITHUB_ACTIONS === 'true';
const basePath = isGitHubActions ? '/Savestock/' : '/';

export default defineConfig({
  base: basePath,
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg'],
      manifest: {
        name: 'Savestock — 長線存股與 ETF 智慧追蹤系統',
        short_name: 'Savestock',
        description: '極速、零成本、跨裝置同步的台股存股健康診斷與 ETF 完整成分股追蹤平台',
        lang: 'zh-TW',
        start_url: basePath,
        scope: basePath,
        display: 'standalone',
        background_color: '#F7F5F0',
        theme_color: '#3F7D6E',
        icons: [
          { src: 'favicon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any maskable' }
        ]
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,png,ico}'],
        navigateFallback: 'index.html',
        runtimeCaching: [
          {
            urlPattern: /\/data\/meta\.json/,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'savestock-meta',
              networkTimeoutSeconds: 3
            }
          },
          {
            urlPattern: /\/data\/.*\.json/,
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'savestock-data-cache',
              expiration: { maxEntries: 300, maxAgeSeconds: 60 * 60 * 24 * 14 }
            }
          }
        ]
      }
    })
  ]
});

