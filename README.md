# Binance 全市場監控系統

即時監控 Binance 現貨市場所有交易對，偵測高波動事件與負資金費率，透過 Telegram 發送即時通知，並支援 30 分鐘追蹤回報。

---

## 功能特色

- **全市場掃描**：支援 Binance 現貨市場所有交易對（300+）
- **雙重偵測**：波動率異常偵測 + 負資金費率偵測
- **即時通知**：Telegram Bot 即時推送 alert
- **30 分鐘追蹤**：被標記的交易對每 30 分鐘自動回報最新狀態
- **狀態持久化**：所有資料寫入 `state.json`，支援程式重啟後恢復
- **線上儀表板**：Vue 3 前端即時顯示監控狀態
- **設定調整**：可透過 UI 或 API 即時調整監控參數

---

## 架構

```
┌─────────────────────────────────────────────┐
│            Binance WebSocket                │
│   wss://stream.binance.com:9443/ws/!ticker  │
└──────────────────┬──────────────────────────┘
                   │ 1sec tickers
                   ▼
┌─────────────────────────────────────────────┐
│           Python Monitor Agent              │
│  ┌─────────┐  ┌──────────┐  ┌───────────┐  │
│  │Analyzer │→│ Trigger   │→│ Notifier   │  │
│  │(Vol+FR) │  │ Engine    │  │(Telegram) │  │
│  └─────────┘  └──────────┘  └───────────┘  │
│       ↑                                    │
│  ┌─────────┐                               │
│  │ State   │← state.json (共享)            │
│  │ Manager │                               │
│  └─────────┘                               │
└──────────────────┬──────────────────────────┘
                   │ REST API (FastAPI)
                   ▼
┌─────────────────────────────────────────────┐
│           Vue 3 Frontend (port 5173)         │
│      Dashboard / Settings / History         │
└─────────────────────────────────────────────┘
```

**三元件共享 `state.json`**：Monitor Agent 寫入，FastAPI 讀取，Vue 前端透過 API 展示。

---

## 安裝步驟

### 前置需求

- Python 3.10+
- Node.js 18+ (for frontend)
- Telegram Bot Token (透過 [@BotFather](https://t.me/BotFather) 取得)
- Telegram Chat ID (透過 [@userinfobot](https://t.me/userinfobot) 取得)

### 1. 複製專案

```bash
cd ~/.config/superpowers/worktrees/binance-monitor/binance-monitor
```

### 2. 安裝 Python 依賴

```bash
python3 -m pip install --break-system-packages -r requirements.txt
```

### 3. 設定 config.json

```bash
# 建立設定檔
cp state.json config.json  # 第一次需手動建立 config.json
```

编辑 `config.json`：

```json
{
  "telegram_bot_token": "YOUR_BOT_TOKEN",
  "telegram_chat_id": "YOUR_CHAT_ID",
  "volatility_threshold_pct": 3.0,
  "volatility_std_multiplier": 2,
  "funding_rate_threshold": -0.01,
  "track_interval_minutes": 30
}
```

### 4. 安裝前端依賴

```bash
cd web
npm install
cd ..
```

---

## 使用方式

### 啟動 Monitor Agent

```bash
python3 run_monitor.py
```

### 啟動 FastAPI Server

```bash
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 啟動 Vue 前端

```bash
cd web
npm run dev
# 開啟 http://localhost:5173
```

---

## API 文件

| Method | Endpoint | 說明 |
|--------|----------|------|
| GET | `/api/state` | 取得目前監控狀態 |
| GET | `/api/settings` | 取得監控設定 |
| PUT | `/api/settings` | 更新監控設定 |
| POST | `/api/track/{symbol}/stop` | 停止追蹤特定交易對 |
| GET | `/api/health` | 健康檢查 |

### 設定參數說明

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `volatility_threshold_pct` | 3.0 | 波動率警報閾值（%） |
| `volatility_std_multiplier` | 2 | 標準差倍數（相對歷史波動） |
| `funding_rate_threshold` | -0.01 | 資金費率警報閾值（-1%） |
| `track_interval_minutes` | 30 | 追蹤回報間隔（分鐘） |

---

## 開發指南

### 執行測試

```bash
python3 -m pytest -v
```

### 模組結構

```
monitor/
├── state.py       # 執行緒安全的 JSON 狀態讀寫
├── analyzer.py    # VolatilityAnalyzer + FundingRateChecker
├── trigger.py     # TriggerEngine 狀態機
├── notifier.py    # TelegramNotifier
└── websocket.py   # BinanceMonitor WebSocket 消費者
```

### 通知觸發條件

- **波動率觸發**： `(price_change_pct >= volatility_threshold_pct) AND (price_change_pct >= std_multiplier * historical_std)`
- **資金費率觸發**：`funding_rate <= funding_rate_threshold`（即 <= -1%）
- 兩種條件任一滿足即開始 30 分鐘追蹤週期

---

## TODO

- [ ] 支援 Binance 期貨市場
- [ ] 網頁視覺化（已實作 Vue 前端，待強化）
- [ ] 對接交易策略
- [ ] 歷史資料匯出（CSV/JSON）
- [ ] 多交易所支援
- [ ] Alert 濃縮（同一交易對短時間內不重複通知）
- [ ] 效能優化（全市場 300+ 交易對報價吞吐）

---

## License

MIT
