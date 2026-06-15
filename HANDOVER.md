# Savestock 交接報告（2026-06-15 第二次更新）

> 單一架構入口仍是 [APP.md](APP.md)；本檔聚焦「本次 session 做了什麼、現況、待驗證、如何接手」。
> 待辦與部署指令見 [TODONEXT.md](TODONEXT.md)。

---

## 1. 本次 session 摘要（2026-06-15 下午段）

### A. Bug 修正：「產生可分享網頁報表」無反應
* **根因**：`url_launcher_web 2.4.1` 已從 `dart:html` 遷移至 `package:web`，`LaunchMode.externalApplication` 在 Flutter Web 下靜默失敗（無新分頁、無 SnackBar）。
* **修法**：改用 `package:web` 直接呼叫 `web.window.open(url, '_blank')`，繞過 url_launcher 中間層，瀏覽器才能正確開新分頁或顯示封鎖提示圖示。

### B. 新功能：多元分享（Phase 4）
試算結果的「產生可分享網頁報表」按鈕改為「分享」，點開底部 Sheet，5 個選項：

| 選項 | 實作 |
|---|---|
| 複製連結 | `Clipboard.setData` 將報表 URL 塞剪貼簿 |
| 開啟報表 | `web.window.open(reportUrl, '_blank')` |
| LINE | `web.window.open(LINE share URL)` |
| Facebook | `web.window.open(FB sharer URL)` |
| 下載試算圖片 | `RepaintBoundary.toImage` → PNG → Blob anchor click |

**試算圖片**：`_ShareCard` widget（白底 375px）以 `Positioned(left: -2000)` 渲染於 off-screen Stack 中（確保有 render object 可截圖）。內容含：Savestock 標題 + 年份、總額漸層卡、各持股明細（名稱/代號/股數/股利/已公告或估算標籤）、網站 footer。

### C. 本地開發 CORS
`backend/main.py` 加 `allow_origin_regex=r"http://localhost(:\d+)?"`，`flutter run -d chrome` 不再被 CORS 封鎖，不須部署即可本地驗收。

---

## 2. 生產環境現況

| 資源 | 服務/網址 | 狀態 |
|---|---|---|
| 前端 | https://savestock.netlify.app | ✅ 含分享功能（**尚未部署本次改動**，僅本地驗收） |
| 後端 API | `savestock-api`（Cloud Run，min=1）<br>https://savestock-api-62102931839.asia-east1.run.app | ✅ revision 00023（含 CORS localhost regex） |
| 報表服務 | `savestock-report`（Cloud Run，min=0）<br>https://savestock-report-62102931839.asia-east1.run.app | ✅ revision 00004 |
| 資料庫 | Neon PostgreSQL（免費） | ✅ |
| ETL 排程 | Cloud Scheduler `savestock-etl-daily`（週一至五 15:00） | ✅ |

> **前端尚未部署到 Netlify**：本次改動已在本地（`flutter run -d chrome`）驗收分享 Sheet + 下載圖片正常。下一 session 驗收完畢後再部署，節省 Netlify credits（每次 production deploy 耗 15 credits）。

---

## 3. ⏳ 待下一 session 驗證與部署

### 驗收清單（本地 `flutter run -d chrome`）
1. 計算後按「分享」→ 底部 Sheet 出現 5 個選項（複製連結、開啟報表、LINE、Facebook、下載試算圖片）。
2. 「開啟報表」→ 新分頁直接開啟 Django 報表（不再顯示 SnackBar 錯誤）。
3. 「複製連結」→ 剪貼簿有 `https://savestock-report-.../report?d=...` 格式網址。
4. 「LINE」→ 開啟 LINE 分享對話框（新分頁）。
5. 「Facebook」→ 開啟 FB sharer 新分頁。
6. 「下載試算圖片」→ 瀏覽器下載 `savestock_股利試算.png`，內含持股明細。

### 驗收完成後部署前端
```powershell
cd C:\Savestock\frontend
flutter build web --release
cd C:\Savestock\frontend\build\web
netlify deploy --prod --dir=. --site=ebec3bc6-8ea5-4131-98b0-e08c54aaaac8
```

---

## 4. 已知限制 / 待辦

* **上櫃（.TWO）年配股**：證交所 `t187ap45_L` 只含上市，上櫃無已公告資料、走估算。
* **IG 分享**：IG 無 web share URL，下載圖片後手動上傳是唯一方式（已於 Share Sheet subtitle 提示）。
* **台積電 2330 Dividend_1Y 偏高問題**：約 26.5 vs 實際配息 ~18–20，疑似 ETL 重複計入，屬既有資料問題，與本功能無關。
* 通知系統接線（`User_Preferences` 已備欄位）。

---

## 5. 本次 session 修改的檔案

| 檔案 | 變更 |
|---|---|
| `frontend/lib/screens/dividend_calc_screen.dart` | Bug 修正 + 分享 Sheet + `_ShareCard` / `_ShareHoldingRow` + Stack off-screen RepaintBoundary |
| `frontend/pubspec.yaml` | 加 `web: ^1.1.0`（direct dep） |
| `backend/main.py` | CORS 加 `allow_origin_regex` 允許 localhost |

---

## 6. 部署指令速查

```powershell
# 前端 → Netlify（驗收完再執行）
cd C:\Savestock\frontend; flutter build web --release
cd C:\Savestock\frontend\build\web
netlify deploy --prod --dir=. --site=ebec3bc6-8ea5-4131-98b0-e08c54aaaac8

# 後端 FastAPI → Cloud Run
gcloud builds submit "C:\Savestock\backend" --tag=asia-east1-docker.pkg.dev/savestock-app/savestock-repo/savestock-api:latest --project=savestock-app
gcloud run deploy savestock-api --image=asia-east1-docker.pkg.dev/savestock-app/savestock-repo/savestock-api:latest --region=asia-east1 --project=savestock-app

# Django 報表 → Cloud Run
gcloud builds submit --config cloudbuild.yaml --project=savestock-app .
gcloud run deploy savestock-report --image=asia-east1-docker.pkg.dev/savestock-app/savestock-repo/savestock-report:latest --region=asia-east1 --project=savestock-app

# 本機開發
cd C:\Savestock\frontend; flutter run -d chrome   # CORS 已允許 localhost
cd C:\Savestock; .venv\Scripts\python.exe -m pytest backend\tests\ -q   # 7 tests
```
