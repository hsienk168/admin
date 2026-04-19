# Binance 全市場監控系統 — 設計規格書

> 狀態：已完成實作，本文為正規流程補寫之 Spec 文件

## 1. 概念與願景

一個安安靜靜、幾乎無感的全市場監控系統。坐在電腦前，完全不需要主動刷新頁面——市場出現大幅波動（5分鐘內漲跌超過設定閾值）或資金費率異常（負值過大，代表空頭刻意打壓期貨價格），系統自動第一時間通知，同時乾淨俐落地出現在瀏覽器的監控面板上。

沒有絢麗的動畫，沒有花俏的數據視覺化——只有精準、及時、安靜。

---

## 2. 設計語言

### 美學方向
**「深夜操作室」**：深色基調，資料優先，介面如專業交易終端般冷靜可靠。全系統無多餘裝飾，數據承載資訊，樣式服務功能。

### 色彩系統
| Token | Hex | 用途 |
|-------|-----|------|
| `--bg-base` | `#0a0e17` | 頁面背景 |
| `--bg-surface` | `#111827` | 卡片/面板背景 |
| `--bg-elevated` | `#1f2937` | hover / elevated 狀態 |
| `--border` | `#374151` | 邊框 |
| `--text-primary` | `#f9fafb` | 主要文字 |
| `--text-muted` | `#9ca3af` | 次要文字 |
| `--accent` | `#10b981` | 主要強調色（翠綠） |
| `--positive` | `#22c55e` | 正向數值（漲） |
| `--negative` | `#ef4444` | 負向數值（跌） |

### 字體
- UI 文字：`Geist`（Sans-serif），fallback `system-ui`
- 數字/匯率：`Geist Mono`，fallback `monospace`

### 動效哲學
- **零打擾**：無自動刷新、無全頁閃爍
- 新追蹤項目：`<TransitionGroup>` 淡入（300ms opacity）
- 按鈕回饋：`:active` 微微 scale(0.98)
- 無 `loading spinner`，用 skeleton loader 替代

---

## 3. 系統架構

```
┌──────────────────────────────────────────────────────────┐
│                     瀏覽器前端 (Vue.js)                    │
│   Dashboard  ← SSE EventSource ── 即時更新，零輪詢         │
│   Settings   ── HTTP PUT ──────────────────→ API          │
│   History                                           port 5317
└──────────────────────┬───────────────────────────────────┘
                       │ HTTP / SSE
┌──────────────────────▼───────────────────────────────────┐
│                    FastAPI (port 8765)                   │
│  GET  /api/state              全量狀態                    │
│  PUT  /api/settings/volatility 更新波動閾值               │
│  PUT  /api/settings/funding-rate 更新資金費率閾值         │
│  POST /api/track/{symbol}/stop  停止追蹤                   │
│  GET  /api/events              SSE 串流（長連線）          │
│  POST /api/events/broadcast     Monitor 觸發廣播          │
└──────┬───────────────────────────────┬───────────────────┘
       │ state.json 讀寫                │ HTTP POST (fire-and-forget)
       │                                │ 每次狀態變化後觸發
┌──────▼────────────────────────────────▼───────────────────┐
│              BinanceMarketMonitor (asyncio)               │
│                                                         │
│  polling.py：                                            │
│    每 10s → Binance 現貨 24hr ticker REST API            │
│            → 計算 5 分鐘價格變化 %                        │
│            → 超過閾值 → trigger.process_volatility()     │
│    每 10s → Binance 期貨資金費率 REST API                 │
│            → 負值超限 → trigger.process_funding_rate()  │
│                                                         │
│  trigger.py：                                            │
│    VolatilityAnalyzer — 標準差分析                        │
│    FundingRateChecker — 閾值比對                          │
│    每一個狀態變化 → state.save() → _broadcast() 觸發 SSE │
│                                                         │
│  notifier.py：                                            │
│    Telegram Bot 推送：觸發警報 + 每 N 分鐘追蹤報告        │
│                                                         │
│  state.py：                                               │
│    StateManager — state.json 的讀寫與鎖定                 │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
                    state.json（磁碟持久化）
```

### 部署拓樸
- **API**：`uvicorn api.main:app --host 0.0.0.0 --port 8765`
- **Monitor**：`python3 run_monitor.py`（獨立的 asyncio 程序）
- **Web**：`vite --host`（port 5317，開發模式熱重載）
- 三者均在同一台機器運行，通訊靠 `localhost`

---

## 4. 資料模型

### state.json

```json
{
  "monitored_at": "2026-04-19T12:00:00+00:00",
  "tracked_pairs": {
    "BTCUSDT": {
      "triggered_at": "2026-04-19T12:00:00+00:00",
      "trigger_reason": "volatility",
      "trigger_price": 67432.50,
      "volatility_pct": 5.23,
      "std_devs": 3.1,
      "funding_rate": null,
      "next_report_at": "2026-04-19T12:30:00+00:00",
      "report_count": 0
    }
  },
  "settings": {
    "volatility": {
      "enabled": true,
      "threshold_pct": 5.0,
      "std_multiplier": 3.0,
      "track_interval_minutes": 30
    },
    "funding_rate": {
      "enabled": true,
      "threshold": -1.0,
      "track_interval_minutes": 30
    }
  },
  "alert_history": []
}
```

### 資金費率 threshold 單位共識
- `state.json` 內儲存為**小數**（API 原生格式，如 `-0.0072`）
- UI 顯示時乘以 100（變成 `-0.72%`）
- API 接收 threshold 時假設為**百分比**（如 UI 送 `-1.0` 代表 `-1.0%`，內部存成 `-0.01`）
- ⚠️ `polling.py` 的 FundingRateChecker 已經過修正，不再除以 100（避免 100 倍差異）

---

## 5. API 規格

### GET /api/state
全量回傳 `state.json` 內容。

### GET /api/settings
回傳 `state.json.settings`。

### PUT /api/settings/volatility
```json
{
  "enabled": true,
  "threshold_pct": 5.0,
  "std_multiplier": 3.0,
  "track_interval_minutes": 30
}
```
所有欄位可部分更新（`Pydantic.exclude_none`）。

### PUT /api/settings/funding-rate
```json
{
  "enabled": true,
  "threshold": -1.0,
  "track_interval_minutes": 30
}
```

### POST /api/track/{symbol}/stop
停止追蹤指定交易對。成功後刪除 `state.json` 內該筆記錄。

### GET /api/events
**SSE 串流端點**。瀏覽器長連線，接收即時狀態更新。

Format:
```
event: update
data: {"tracked_pairs": {...}}

event: connected
data: {}
```

### POST /api/events/broadcast
內部端點。Monitor 在每次 `state.save()` 之後呼叫，觸發所有 SSE client 接收 `update` 事件。

---

## 6. 觸發邏輯

### 波動觸發（Volatility）
1. 每 10 秒輪詢 `GET https://api.binance.com/api/v3/ticker/24hr`
2. 對每個 USDT 交易對維護滾動 5 分鐘價格歷史（`deque`，每 10 秒新增一筆）
3. 計算：`change_pct_5m = (current_price - price_5min_ago) / price_5min_ago * 100`
4. 若 `|change_pct_5m| >= threshold_pct`（預設 5%）→ 寫入 `tracked_pairs`
5. 觸發後進入「追蹤報告」模式：每 `track_interval_minutes`（預設 30 分）Telegram 匯報一次最新價格

### 資金費率觸發（Funding Rate）
1. 每 10 秒輪詢 `GET https://fapi.binance.com/fapi/v1/premiumIndex`
2. 若 `lastFundingRate < threshold`（預設 `-1.0`，即 `-1%`）→ 寫入 `tracked_pairs`
3. 進入追蹤報告模式（同上）

### 修復記錄：資金費率 threshold 陷阱
- **Bug**：原本 UI 顯示 `-0.3%` 設定，實際只擋了 `-0.003%`（`polling.py` 內除以 100）
- **修復**：移除了除以 100 的動作，threshold 直接用 API 回傳的同一單位（小數）比較
- **後果**：UI 仍顯示百分比，但內部比對已正確

---

## 7. 前端 UI 元件

### Dashboard（監控面板）
- 三大區塊：波動觸發（card-positive / card-negative 區分漲跌）、資金費率觸發、系統狀態列
- **零輪詢**：全部靠 SSE EventSource 更新
- Skeleton loader：初始載入時顯示骨幹畫面
- Empty state：尚無追蹤時的引導提示
- 每張卡片：`@stop` 事件 → App.vue → 停止追蹤 API → SSE 推送更新

### Settings（設定頁面）
- 兩組獨立的設定卡：波動監控、資金費率監控
- Toggle 開關 + 數值輸入 + interval 下拉
- **不參與 SSE 輪詢**：設定改變只來自 user 操作，無自動刷新打擾輸入

### History（歷史記錄）
- 滾動顯示最近 100 筆 alert（觸發當下一次，報告不計入）

---

## 8. 即時更新流程（SSE）

```
Monitor 偵測到新觸發
    → state.save() 寫入 state.json
    → _broadcast() 發 POST 到 http://localhost:8765/api/events/broadcast
        → API SSEBroadcaster.broadcast("update", {tracked_pairs: ...})
            → 所有瀏覽器的 EventSource 收到 "update" 事件
                → Dashboard.vue emit('sse-update', tracked_pairs)
                    → App.vue state.value.tracked_pairs = trackedPairs
                        → Vue reactivity 自動更新 UI，無 DOM replace
```

---

## 9. 已知約束與限制

1. **WebSocket 不可用**：原本嘗試 Binance `!ticker@arr` WebSocket，環境無回應，已改用 REST polling 替代（10 秒間隔）。
2. **單機部署**：API、Monitor、Web 三者必須在同一台機器的 localhost 上。
3. **資金費率 threshold 方向**：目前只監控**負值**（空頭刻意打壓），正向資金費率（多头付空头）不在監控範圍內。
4. **Telegram token**：需要同時具備 `TELEGRAM_BOT_TOKEN` 與 `TELEGRAM_CHAT_ID`。

---

## 10. 部署與維護

### 啟動順序
1. `uvicorn api.main:app --host 0.0.0.0 --port 8765`
2. `python3 run_monitor.py`（需設定 `TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`、`STATE_FILE`）
3. `cd web && npm run dev`（port 5317）

### 重啟時的資料持久性
- `state.json` 為狀態的唯一事實來源（source of truth）
- Monitor 重啟不影響 API 和前端（API 從磁碟載入）
- 重啟完成後，Monitor 會廣播一次完整狀態，前端自動同步

### 健康檢查
```bash
curl http://localhost:8765/api/health  # → {"status":"healthy"}
```

---

## 11. 成功標準

- [x] 前端零輪詢，頁面不打斷、不閃爍
- [x] 設定頁面輸入時不被自動刷新覆蓋
- [x] 波動觸發後 10 秒內出現在 Dashboard
- [x] Telegram 通知在觸發後 10 秒內發出
- [x] 停止追蹤即時反映在 UI（不需等下次輪詢）
- [x] 狀態重啟後完整恢復
