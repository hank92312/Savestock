// Savestock v2 — Cloudflare Worker (D1 跨裝置同步 API + QR 裝置配對 + GitHub Actions 定時觸發器)

export interface Env {
  DB: any;
  ALLOWED_ORIGIN: string;
  GITHUB_REPO: string;
  GITHUB_WORKFLOW: string;
  GITHUB_PAT?: string;
  ADMIN_SECRET?: string;
}

async function sha256Hex(input: string): Promise<string> {
  const buf = new TextEncoder().encode(input);
  const digest = await crypto.subtle.digest('SHA-256', buf);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

function randomToken(bytes = 24): string {
  const arr = new Uint8Array(bytes);
  crypto.getRandomValues(arr);
  return Array.from(arr)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

function randomSixDigits(): string {
  const arr = new Uint32Array(1);
  crypto.getRandomValues(arr);
  return String(100000 + (arr[0] % 900000));
}

function corsHeaders(origin: string | null) {
  return {
    'Access-Control-Allow-Origin': origin || '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  };
}

function jsonResponse(data: unknown, status = 200, origin: string | null = '*') {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      ...corsHeaders(origin),
    },
  });
}

async function authenticate(req: Request, env: Env): Promise<{ userId: number; deviceId: number } | null> {
  const auth = req.headers.get('Authorization') || '';
  if (!auth.startsWith('Bearer ')) return null;
  const rawToken = auth.slice(7).trim();
  if (!rawToken) return null;
  const tokenHash = await sha256Hex(rawToken);
  const row = await env.DB.prepare(
    'SELECT id, user_id FROM devices WHERE token_hash = ? AND revoked = 0',
  )
    .bind(tokenHash)
    .first();
  if (!row) return null;
  await env.DB.prepare('UPDATE devices SET last_seen_at = ? WHERE id = ?')
    .bind(Date.now(), row.id)
    .run();
  return { userId: Number(row.user_id), deviceId: Number(row.id) };
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const origin = req.headers.get('Origin');
    if (req.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders(origin) });
    }

    const url = new URL(req.url);
    const path = url.pathname;

    // 1. POST /v1/register — 使用邀請碼啟用雲端同步（若同 Email 已存在則直接新增裝置並回傳雲端文件）
    if (req.method === 'POST' && path === '/v1/register') {
      const body: any = await req.json();
      const inviteCode = String(body.inviteCode || 'HANK-ADMIN').trim();
      const email = String(body.email || '').trim().toLowerCase();
      const nickname = String(body.nickname || '存股夥伴').trim();
      const doc = body.doc || {};

      if (!email) {
        return jsonResponse({ error: '請填寫接收通知的 Email' }, 400, origin);
      }

      const inv = await env.DB.prepare(
        'SELECT code, expires_at FROM invites WHERE code = ?',
      )
        .bind(inviteCode)
        .first();
      if (!inv || Number(inv.expires_at) < Date.now()) {
        return jsonResponse({ error: '邀請碼無效或已過期（預設邀請碼為 HANK-ADMIN）' }, 403, origin);
      }

      const existingUser = await env.DB.prepare('SELECT id FROM users WHERE email = ?')
        .bind(email)
        .first();

      let userId: number;
      let recoveryCode = '';
      if (existingUser) {
        userId = Number(existingUser.id);
        // 若已有帳號，更新暱稱
        if (nickname) {
          await env.DB.prepare('UPDATE users SET nickname = ? WHERE id = ?')
            .bind(nickname, userId)
            .run();
        }
      } else {
        recoveryCode = randomToken(8).toUpperCase();
        const recHash = await sha256Hex(recoveryCode);
        const ins = await env.DB.prepare(
          'INSERT INTO users (nickname, email, notify_daily, notify_weekly, is_admin, recovery_hash, created_at) VALUES (?, ?, 1, 1, 1, ?, ?)',
        )
          .bind(nickname, email, recHash, Date.now())
          .run();
        userId = Number(ins.meta.last_row_id);
        await env.DB.prepare(
          'INSERT OR REPLACE INTO user_docs (user_id, doc, version, updated_at) VALUES (?, ?, 1, ?)',
        )
          .bind(userId, JSON.stringify(doc), Date.now())
          .run();
      }

      const rawToken = randomToken(24);
      const tokenHash = await sha256Hex(rawToken);
      await env.DB.prepare(
        'INSERT INTO devices (user_id, token_hash, label, created_at, last_seen_at, revoked) VALUES (?, ?, ?, ?, ?, 0)',
      )
        .bind(userId, tokenHash, 'primary', Date.now(), Date.now())
        .run();

      return jsonResponse({ token: rawToken, recoveryCode, userId }, 200, origin);
    }

    // 2. POST /v1/pair/start — 已登入 PC 產生 6 位數手機配對碼（5分鐘有效）
    if (req.method === 'POST' && path === '/v1/pair/start') {
      const auth = await authenticate(req, env);
      if (!auth) return jsonResponse({ error: '未授權' }, 401, origin);

      const code = randomSixDigits();
      const expiresAt = Date.now() + 5 * 60 * 1000;
      await env.DB.prepare(
        'INSERT OR REPLACE INTO pair_codes (code, user_id, expires_at, attempts) VALUES (?, ?, ?, 0)',
      )
        .bind(code, auth.userId, expiresAt)
        .run();

      return jsonResponse({ code, expiresAt }, 200, origin);
    }

    // 3. POST /v1/pair/claim — 手機掃描 QR Code 或輸入 6 位數配對碼換取獨立 Token
    if (req.method === 'POST' && path === '/v1/pair/claim') {
      const body: any = await req.json();
      const code = String(body.code || '').trim();
      const label = String(body.label || 'mobile').slice(0, 64);

      const row = await env.DB.prepare(
        'SELECT code, user_id, expires_at, attempts FROM pair_codes WHERE code = ?',
      )
        .bind(code)
        .first();

      if (!row || Number(row.expires_at) < Date.now() || Number(row.attempts) >= 5) {
        return jsonResponse({ error: '配對碼無效或已過期' }, 400, origin);
      }

      await env.DB.prepare('DELETE FROM pair_codes WHERE code = ?').bind(code).run();

      const rawToken = randomToken(24);
      const tokenHash = await sha256Hex(rawToken);
      await env.DB.prepare(
        'INSERT INTO devices (user_id, token_hash, label, created_at, last_seen_at, revoked) VALUES (?, ?, ?, ?, ?, 0)',
      )
        .bind(row.user_id, tokenHash, label, Date.now(), Date.now())
        .run();

      return jsonResponse({ token: rawToken, userId: row.user_id }, 200, origin);
    }

    // 4. GET / PUT /v1/doc — 取得或更新同步持股文件
    if (path === '/v1/doc') {
      const auth = await authenticate(req, env);
      if (!auth) return jsonResponse({ error: '未授權' }, 401, origin);

      if (req.method === 'GET') {
        const row = await env.DB.prepare('SELECT doc, version, updated_at FROM user_docs WHERE user_id = ?')
          .bind(auth.userId)
          .first();
        if (!row) return jsonResponse({ doc: null, version: 0 }, 200, origin);
        return jsonResponse(
          { doc: JSON.parse(String(row.doc)), version: Number(row.version), updatedAt: Number(row.updated_at) },
          200,
          origin,
        );
      }

      if (req.method === 'PUT') {
        const body: any = await req.json();
        const incomingDoc = body.doc;
        if (!incomingDoc) return jsonResponse({ error: '缺少 doc' }, 400, origin);

        const nextVer = Number(incomingDoc.version || 1);
        await env.DB.prepare(
          'INSERT OR REPLACE INTO user_docs (user_id, doc, version, updated_at) VALUES (?, ?, ?, ?)',
        )
          .bind(auth.userId, JSON.stringify(incomingDoc), nextVer, Date.now())
          .run();

        // 同步更新使用者的 Email 與通知開關
        if (incomingDoc.settings) {
          const userEmail = (incomingDoc.settings.email || '').trim().toLowerCase();
          const userNick = (incomingDoc.settings.nickname || '').trim() || '存股夥伴';
          if (userEmail) {
            await env.DB.prepare(
              'UPDATE users SET nickname = ?, email = ?, notify_daily = ?, notify_weekly = ? WHERE id = ?',
            )
              .bind(
                userNick,
                userEmail,
                incomingDoc.settings.notifyDaily ? 1 : 0,
                incomingDoc.settings.notifyWeekly ? 1 : 0,
                auth.userId,
              )
              .run();
          }
        }

        return jsonResponse({ ok: true, version: nextVer }, 200, origin);
      }
    }

    // 5. GET /v1/admin/digest — 供 GitHub Actions Email 通知讀取所有啟用通知的使用者與持股
    if (req.method === 'GET' && path === '/v1/admin/digest') {
      const secret = req.headers.get('Authorization')?.replace('Bearer ', '').trim();
      const expected = env.ADMIN_SECRET || 'savestock-admin-2026-secret';
      if (!secret || secret !== expected) {
        return jsonResponse({ error: 'Forbidden' }, 403, origin);
      }
      try {
        await env.DB.prepare('ALTER TABLE users ADD COLUMN last_notified_date TEXT').run();
      } catch {
        // 欄位已存在
      }
      const rows = await env.DB.prepare(
        'SELECT u.id, u.nickname, u.email, u.notify_daily, u.notify_weekly, u.last_notified_date, d.doc FROM users u LEFT JOIN user_docs d ON u.id = d.user_id',
      ).all();
      return jsonResponse({ users: rows.results || [] }, 200, origin);
    }

    // 6. POST /v1/admin/digest-ack — 記錄使用者今日已寄過通知，確保 1 天最多只寄 1 次
    if (req.method === 'POST' && path === '/v1/admin/digest-ack') {
      const secret = req.headers.get('Authorization')?.replace('Bearer ', '').trim();
      const expected = env.ADMIN_SECRET || 'savestock-admin-2026-secret';
      if (!secret || secret !== expected) {
        return jsonResponse({ error: 'Forbidden' }, 403, origin);
      }
      const body: any = await req.json();
      const email = String(body.email || '').trim().toLowerCase();
      const dateStr = String(body.date || '').trim();
      if (email && dateStr) {
        try {
          await env.DB.prepare('ALTER TABLE users ADD COLUMN last_notified_date TEXT').run();
        } catch {
          // 欄位已存在
        }
        await env.DB.prepare('UPDATE users SET last_notified_date = ? WHERE email = ?')
          .bind(dateStr, email)
          .run();
      }
      return jsonResponse({ ok: true }, 200, origin);
    }

    return jsonResponse({ service: 'savestock-sync-worker', status: 'ok' }, 200, origin);
  },

  // Cron Trigger：準時觸發 GitHub Actions 每日盤後資料建置與部署
  async scheduled(_event: any, env: Env, _ctx: any) {
    if (!env.GITHUB_PAT) return;
    const url = `https://api.github.com/repos/${env.GITHUB_REPO}/actions/workflows/${env.GITHUB_WORKFLOW}/dispatches`;
    await fetch(url, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${env.GITHUB_PAT}`,
        Accept: 'application/vnd.github+json',
        'User-Agent': 'savestock-cloudflare-cron',
      },
      body: JSON.stringify({ ref: 'main' }),
    });
  },
};

