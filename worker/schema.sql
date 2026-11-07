-- Savestock v2 — Cloudflare D1 Database Schema (SQLite)

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nickname TEXT NOT NULL,
  email TEXT NOT NULL,
  notify_daily INTEGER NOT NULL DEFAULT 1,
  notify_weekly INTEGER NOT NULL DEFAULT 1,
  is_admin INTEGER NOT NULL DEFAULT 0,
  recovery_hash TEXT NOT NULL,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS devices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  token_hash TEXT UNIQUE NOT NULL,
  label TEXT NOT NULL DEFAULT 'browser',
  created_at INTEGER NOT NULL,
  last_seen_at INTEGER NOT NULL,
  revoked INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS invites (
  code TEXT PRIMARY KEY,
  created_by INTEGER,
  used_by INTEGER,
  expires_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS pair_codes (
  code TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL,
  expires_at INTEGER NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS user_docs (
  user_id INTEGER PRIMARY KEY,
  doc TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  updated_at INTEGER NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 預設建立管理員邀請碼 HANK-ADMIN（供你與少數朋友首次啟用）
INSERT OR IGNORE INTO invites (code, created_by, used_by, expires_at)
VALUES ('HANK-ADMIN', 0, NULL, 4102444800000);
