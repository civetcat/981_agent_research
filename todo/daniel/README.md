# Stock Simulator

台股 + 美股的股票模擬、回測、選股與 AI 分析平台。預設是**單機版**，資料留在本機；目前已開始加入 `APP_MODE=single|multi` 的多人線上版基礎。

## 目前狀態

- **單機版**：可用，預設模式。使用 `scripts/start.ps1` 一鍵啟動前後端。
- **多人線上版**：規劃 / 基礎建置中。目標是部署到自家 Ubuntu always-on 主機，使用 Tailscale Funnel 對外，朋友家人可 OAuth 登入並自帶 Grok API key。

## 功能總覽

| 功能 | 路徑 | 說明 |
| --- | --- | --- |
| 首頁 | `/` | 所有主要功能入口卡片 |
| 個股分析 | `/stock/:symbol` | K 線、技術指標、基本面、推薦評分儀表板、建議買進區、目標價、停損價、資金流向、月營收 / 配息、AI 問答 |
| 條件選股 | `/screener` | 基本面 + 技術面條件組合，欄位有 hover 名詞解釋 |
| 策略回測 | `/backtest` | 單檔 / 多檔回測，內建策略、參數設定、權益曲線、交易紀錄 |
| 策略推薦 | `/recommend` | 5 / 10 / 15 / 20 / 30 日當前進場訊號，依歷史回測期望值排序 |
| 策略目錄 | `/strategies` | 策略 metadata、適用場景、優缺點、預測計算機 |
| ETF 排行 | `/etfs` | 台美主流 ETF：AUM、費用率、殖利率、多期報酬、台股法人流向；整列可點到分析頁 |
| AI 選股 | `/ai-picks` | Grok-4 reasoning + Web Search，依題材與 Top N 產生熱門題材與候選股（24h 快取） |
| AI 推薦 ETF | `/ai-etfs` | Grok-4 reasoning 推薦值得關注的 ETF 主題與代表 ETF（24h 快取） |
| 模擬投資組合 | `/portfolio` | 總資金、入金 / 出金、持倉、交易紀錄、績效 |

## 推薦評分與建議買進區

個股頁的「推薦評分」是純規則式，沒有使用 AI。分數來源包含：

- 策略期望值
- 短中期動能
- 籌碼面 / Insider 動向
- MFI 資金流量
- 量能異常

建議買進區可以在儀表板切換 4 種進場策略：

| 策略 | 說明 |
| --- | --- |
| 保守 | 等較深回檔，約 `收盤價 - 1.0 ATR ~ 收盤價 - 0.2 ATR` |
| 平衡 | 預設模式，約 `收盤價 - 0.5 ATR ~ 收盤價 + 0.3 ATR` |
| 積極 | 允許小幅追價，約 `收盤價 ~ 收盤價 + 0.8 ATR` |
| 均線回測 | 取最接近現價的 SMA20 / SMA60 附近作為進場區 |

目標價與停損價來自 5 / 10 / 15 / 20 / 30 日策略預測的歷史回測統計中位數。

## AI 與 Token 行為

- AI 選股與 AI 推薦 ETF 會使用 Grok-4 reasoning + Web Search。
- 相同參數在 24 小時內會走後端檔案快取，不會重複消耗 token。
- 前端同一個 session 內也有記憶體快取，切 tab 回來不會重新送 request。
- 個股 AI 問答每次送出問題都會消耗 token，第一次送出前會提示確認。
- 現階段單機版可使用 `backend/.env` 的 `GROK_API_KEY`；多人線上版規劃為使用者自行在設定頁提供 API key。

## 技術棧

- **後端**：Python 3.13 + FastAPI + SQLAlchemy + SQLite + pandas / numpy + yfinance + FinMind v4 (`httpx`) + `ta` + OpenAI SDK（呼叫 xAI Grok）
- **前端**：React + TypeScript + Vite + Tailwind + lightweight-charts + Recharts
- **儲存**：
  - `backend/stocksim.db`：投資組合、推薦快照、股票清單、單機 user 基礎資料
  - `backend/data_cache/`：OHLCV Parquet、FinMind JSON、AI Picks / AI ETF Picks JSON 快取

## 目錄結構

```text
backend/
  app/
    auth/           APP_MODE / current user 基礎（single mode 會固定 user_id=1）
    routers/        FastAPI 端點（stocks / backtest / recommend / etfs / verdict / ai_picks / ai_etf_picks ...）
    services/       業務邏輯（recommend / prediction / verdict / etf / ai_picks / portfolio / llm）
    data/           資料源（fetcher / fund_flow / finmind / listings / etf_list）
    backtest/       策略 + 自訂 vectorized runner
    strategies/     策略 catalog metadata
    analytics/      技術指標
    models/         ORM + Pydantic schema
  requirements.txt
  .env.example
frontend/
  src/
    pages/          每個 route 對應一頁
    components/     KLineChart / VerdictGauge / StockChatBox / FundFlowSection / CapitalBadge / BackButton / InfoTip
    api/client.ts   所有 API 型別 + axios client
scripts/
  start.ps1         一鍵啟動前後端（PowerShell，已具備 reuse/restart 檢查）
  start.cmd         一鍵啟動前後端（CMD 包裝）
  stop.ps1          一鍵停止
```

## 環境變數（`backend/.env`）

```env
# 執行模式：single = 本機單人版（預設）；multi = 線上多人版（OAuth 後續啟用）
APP_MODE=single

# DB URL：留空時使用 backend/stocksim.db；Ubuntu 線上版可設 sqlite:////var/lib/stocksim/stocksim.db
DATABASE_URL=

# Cookie/session 簽章 secret（multi 模式會使用；single 可保留預設）
SESSION_SECRET=dev-secret-change-me

# CORS 白名單，逗號分隔
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# FinMind token（可選）
FINMIND_TOKEN=

# Grok（xAI）
GROK_API_KEY=
GROK_MODEL=grok-4

PORT=8000
DATA_CACHE_DIR=data_cache
CACHE_TTL_HOURS=12
```

## 一鍵啟動（推薦）

第一次先依下方「初次安裝」裝好依賴，之後就可以：

**PowerShell**：
```powershell
.\scripts\start.ps1
```

**CMD / 雙擊**：
```cmd
scripts\start.cmd
```

`start.ps1` 會先檢查 8000 / 5173：

- 服務正常：reuse 既有視窗，不重複開
- port 有 listener 但 healthcheck 失敗：kill stale process 後重開
- port 沒人 listen：開新 PowerShell 視窗

啟動後：

- 後端：`http://127.0.0.1:8000`（API 文件 `/docs`）
- 前端：`http://localhost:5173`

停止：
```powershell
.\scripts\stop.ps1
```

## 初次安裝

### 後端

```powershell
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

> 建議 Python 3.13。Python 3.14 目前可能遇到 numpy / pandas wheel 相容性問題。

### 前端

```powershell
cd frontend
npm install
```

之後用 `scripts/start.ps1` 一次拉起兩端。

## Ubuntu 線上多人版規劃

目標部署方式：

- 一台長時間開著的 Ubuntu 主機
- `APP_MODE=multi`
- SQLite WAL mode，資料庫放 `/var/lib/stocksim/stocksim.db`
- systemd 開機自動啟動 backend
- Tailscale Funnel 對外提供 HTTPS 網址
- 使用者用 Google/GitHub OAuth 登入
- 使用者自行在設定頁提供 Grok API key，server 不保存 key

這部分目前是規劃與基礎建置中，單機版仍是穩定主流程。

## 快取清理

- 個股 OHLCV：`backend/data_cache/ohlcv/`
- AI 選股：`backend/data_cache/ai_picks/`（24h TTL）
- AI 推薦 ETF：`backend/data_cache/ai_etf_picks/`（24h TTL）
- FinMind：`backend/data_cache/finmind/`
- 想完整重置本機資料：刪 `backend/stocksim.db` + `backend/data_cache/`，重啟後會重建

## 驗證指令

Backend import：
```powershell
cd backend
.\.venv\Scripts\python.exe -c "from app.main import app; print('ok', app.title)"
```

Frontend type check：
```powershell
cd frontend
npx tsc --noEmit
```

API smoke test：
```powershell
curl.exe -s http://127.0.0.1:8000/api/health
curl.exe -s http://127.0.0.1:8000/api/portfolio/summary
curl.exe -s http://127.0.0.1:8000/api/recommend/horizons
```

## 注意事項

- **不要把專案放在 OneDrive 同步資料夾下**（venv / node_modules / SQLite 都會跟同步打架）。建議放 `C:\dev\stock-simulator`。
- 首次抓盤後資料量可能到數百 MB，主要在 `data_cache/`。
- 全市場掃描（`/recommend`）會在背景跑數十秒到數分鐘，建議先用 Top 500。
- AI 功能請留意 token 成本；按「重新分析」才會強制重打 Grok。
- 多人線上版尚未完成 OAuth 與 BYO key 全流程，目前 `APP_MODE=multi` 只先建立後端基礎。
