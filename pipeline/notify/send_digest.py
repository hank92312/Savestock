"""Savestock v2 — Gmail SMTP 每日異常警示與除權息摘要 / 週報寄送模組。

支援兩種名單來源：
1. 若設有 `SYNC_WORKER_URL` 與 `ADMIN_SECRET`，自動向 Cloudflare Worker `/v1/admin/digest` 拉取每位使用者的最新持股與 Email。
2. 若尚未設定 Worker，預設使用 `NOTIFY_EMAIL`（預設 `hank92312@gmail.com`）針對精選 25 檔與預設持股寄送盤後摘要。
無重要事件時，每日摘要預設「安靜不打擾」（不發空信）；若加上 `--force` 則無論如何皆寄送。
"""
from __future__ import annotations

import argparse
import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import requests


def build_digest_html(
    nickname: str,
    market_date: str,
    alerts: list[dict],
    cheap_stocks: list[dict],
    upcoming_divs: list[dict],
) -> str:
    alert_rows = "".join(
        f"<tr><td style='padding:8px;border-bottom:1px solid #E5E0D6;'><b>{a['name']}</b> ({a['code']})</td>"
        f"<td style='padding:8px;border-bottom:1px solid #E5E0D6;'>{a['price']}</td>"
        f"<td style='padding:8px;border-bottom:1px solid #E5E0D6;color:#3E8E5E;'>{a['changePct']}%</td>"
        f"<td style='padding:8px;border-bottom:1px solid #E5E0D6;color:#B94A48;'>{', '.join(a['alert']['reasons'])}</td></tr>"
        for a in alerts
    ) or "<tr><td colspan='4' style='padding:10px;color:#6E6A62;'>今日持股與精選清單無異常暴跌或下跌爆量警示 🎉</td></tr>"

    cheap_rows = "".join(
        f"<tr><td style='padding:8px;border-bottom:1px solid #E5E0D6;'><b>{c['name']}</b> ({c['code']})</td>"
        f"<td style='padding:8px;border-bottom:1px solid #E5E0D6;'>{c['price']} 元</td>"
        f"<td style='padding:8px;border-bottom:1px solid #E5E0D6;color:#C8553D;font-weight:bold;'>{c['yield1y']}%</td>"
        f"<td style='padding:8px;border-bottom:1px solid #E5E0D6;color:#3F7D6E;font-weight:bold;'>{c['score']['total']} ({c['score']['grade']})</td></tr>"
        for c in cheap_stocks
    )

    ev_rows = "".join(
        f"<tr><td style='padding:8px;border-bottom:1px solid #E5E0D6;'>{e['date']}</td>"
        f"<td style='padding:8px;border-bottom:1px solid #E5E0D6;'><b>{e['name']}</b> ({e['code']})</td>"
        f"<td style='padding:8px;border-bottom:1px solid #E5E0D6;'>現金 {e['cashDiv']} 元 / 配股 {e['stockDiv']} 元</td></tr>"
        for e in upcoming_divs
    ) or "<tr><td colspan='3' style='padding:10px;color:#6E6A62;'>近期無即將除權息預告</td></tr>"

    return f"""
    <div style="background:#F7F5F0;padding:24px;font-family:-apple-system,BlinkMacSystemFont,'Microsoft JhengHei',sans-serif;color:#2B2A27;">
      <div style="max-width:640px;margin:0 auto;background:#FFFFFF;border:1px solid #E5E0D6;border-radius:14px;padding:24px;">
        <h2 style="margin:0 0 6px;color:#3F7D6E;">📈 Savestock 盤後存股防護與股利摘要</h2>
        <p style="margin:0 0 18px;color:#6E6A62;font-size:13.5px;">
          {nickname} 您好，以下為 <b>{market_date}</b> 收盤後之異常波動警示、便宜區高分存股與近期除權息提醒：
        </p>

        <h3 style="font-size:15px;margin:16px 0 8px;">🚨 今日異常跌幅 / 下跌爆量警示</h3>
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          <thead>
            <tr style="background:#EFECE5;text-align:left;">
              <th style="padding:8px;">標的</th><th style="padding:8px;">收盤</th><th style="padding:8px;">漲跌</th><th style="padding:8px;">警示原因</th>
            </tr>
          </thead>
          <tbody>{alert_rows}</tbody>
        </table>

        <h3 style="font-size:15px;margin:20px 0 8px;">🌱 位於便宜/合理偏低區之高分精選股</h3>
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          <thead>
            <tr style="background:#EFECE5;text-align:left;">
              <th style="padding:8px;">標的</th><th style="padding:8px;">現價</th><th style="padding:8px;">近1年殖利率</th><th style="padding:8px;">健康評分</th>
            </tr>
          </thead>
          <tbody>{cheap_rows}</tbody>
        </table>

        <h3 style="font-size:15px;margin:20px 0 8px;">📅 近期除權息日程提醒</h3>
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          <thead>
            <tr style="background:#EFECE5;text-align:left;">
              <th style="padding:8px;">除息日</th><th style="padding:8px;">標的</th><th style="padding:8px;">配息內容</th>
            </tr>
          </thead>
          <tbody>{ev_rows}</tbody>
        </table>

        <div style="margin-top:22px;padding-top:14px;border-top:1px solid #E5E0D6;text-align:center;">
          <a href="https://hank92312.github.io/Savestock/" style="display:inline-block;background:#3F7D6E;color:#FFFFFF;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:13.5px;">
            開啟 Savestock 網頁版查看完整分析
          </a>
        </div>
      </div>
    </div>
    """


def send_gmail(to_email: str, subject: str, html_body: str) -> bool:
    smtp_user = os.getenv("GMAIL_USER", "hank92312@gmail.com").strip()
    smtp_pass = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    if not smtp_pass:
        print(f"[NOTIFY] 未設定 GMAIL_APP_PASSWORD，略過寄信至 {to_email}（主旨：{subject}）")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Savestock 存股防護系統 <{smtp_user}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [to_email], msg.as_string())
    print(f"✅ 已成功寄出通知信至 {to_email}")
    return True


def run_notify(data_dir: Path, force: bool = False) -> None:
    scr_path = data_dir / "screener.json"
    cal_path = data_dir / "calendar.json"
    if not scr_path.exists():
        print("[NOTIFY] 找不到 screener.json，跳過通知。")
        return

    screener = json.loads(scr_path.read_text(encoding="utf-8"))
    calendar = json.loads(cal_path.read_text(encoding="utf-8")) if cal_path.exists() else {"events": []}
    market_date = screener.get("marketDate", "")
    items: dict = screener.get("items", {})
    curated_codes = set(screener.get("curatedStockCodes", [])) | set(screener.get("curatedEtfCodes", []))

    # 取得收件人清單
    recipients = [
        {
            "nickname": "Hank",
            "email": os.getenv("NOTIFY_EMAIL", "hank92312@gmail.com").strip(),
            "codes": curated_codes,
        }
    ]

    worker_url = os.getenv("SYNC_WORKER_URL", "").strip().rstrip("/")
    admin_secret = os.getenv("ADMIN_SECRET", "").strip()
    if worker_url and admin_secret:
        try:
            r = requests.get(
                f"{worker_url}/v1/admin/digest",
                headers={"Authorization": f"Bearer {admin_secret}"},
                timeout=15,
            )
            if r.ok:
                cloud_users = r.json().get("users", [])
                if cloud_users:
                    recipients = []
                    for u in cloud_users:
                        if not u.get("notify_daily"):
                            continue
                        doc = json.loads(u["doc"]) if u.get("doc") else {}
                        u_codes = {
                            k for k, v in (doc.get("holdings") or {}).items() if not v.get("deleted")
                        } | curated_codes
                        recipients.append({
                            "nickname": u.get("nickname") or "存股夥伴",
                            "email": u.get("email") or "hank92312@gmail.com",
                            "codes": u_codes,
                        })
        except Exception as e:
            print(f"[NOTIFY] 無法從 Worker 讀取名單，改用預設收件人: {e}")

    for rec in recipients:
        watch_codes = rec["codes"]
        alerts = [items[c] for c in watch_codes if c in items and items[c].get("alert", {}).get("flag")]
        cheap = sorted(
            [
                items[c]
                for c in curated_codes
                if c in items and items[c].get("priceBands", {}).get("zone") in ("cheap", "fair")
            ],
            key=lambda x: x["score"]["total"],
            reverse=True,
        )[:6]
        upcoming = [e for e in calendar.get("events", []) if e["code"] in watch_codes][:8]

        if not alerts and not upcoming and not force:
            print(f"[NOTIFY] {rec['email']} 今日無異常警示或除息事件，不打擾。")
            continue

        html = build_digest_html(rec["nickname"], market_date, alerts, cheap, upcoming)
        subject = f"📈 Savestock 盤後摘要 ({market_date}) — {len(alerts)} 檔警示 / {len(upcoming)} 檔即將除權息"
        send_gmail(rec["email"], subject, html)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="web/public/data")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    run_notify(Path(args.data), force=args.force)


if __name__ == "__main__":
    main()
