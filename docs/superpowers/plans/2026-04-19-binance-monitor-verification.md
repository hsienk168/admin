# Binance 全市場監控系統 — 實作驗收計畫

> **Agent 要求**：使用 `superpowers:subagent-driven-development`（推薦）或 `superpowers:executing-plans` 執行。
>
> **Goal**：以 Spec 為基準，逐一核對實作細節，確認系統完全合規並可直接交付老闆使用。

---

## 架構摘要

- **前端**：Vue.js + Vite（port 5317），SSE EventSource 即時更新，零輪詢
- **API**：FastAPI（port 8765），SSEBroadcaster 管理長連線，REST endpoint 處理設定
- **Monitor**：asyncio polling 程序，每 10s 輪詢 Binance REST，觸發後更新 state.json 並廣播
- **持久化**：state.json 為唯一事實來源，StateManager 統一讀寫

---

## Task 1：API SSE 廣播機制驗收

**目的**：確認 API 的 SSE 實作完全符合 Spec 第 5 節定義的介面與行為。

- [ ] **Step 1：確認 SSEBroadcaster 存在於 `api/main.py`**
  檢查：`SSEBroadcaster` class 有 `_clients: set[asyncio.Queue]`、`connect()`、`disconnect()`、`broadcast()` 三個方法。

- [ ] **Step 2：確認 `GET /api/events` 端點**
  路由：`@app.get("/api/events")`，回傳 `StreamingResponse`，media_type 為 `text/event-stream`。
  Header 包含 `Cache-Control: no-cache`、`Connection: keep-alive`、`X-Accel-Buffering: no`。

- [ ] **Step 3：確認心跳（keepalive）機制**
  `asyncio.wait_for(queue.get(), timeout=30)`，逾時後 yield `": keepalive\n\n"`。

- [ ] **Step 4：確認 `POST /api/events/broadcast` 端點**
  路由：`@app.post("/api/events/broadcast")`，呼叫 `await _broadcaster.broadcast(event, payload)`。

- [ ] **Step 5：確認連線時發送 `connected` 事件**
  第一個 yield：`f"event: connected\ndata: {{}}\n\n"`

---

## Task 2：Monitor 廣播觸發點驗收

**目的**：確認 `trigger.py` 和 `polling.py` 在每一次 `state.save()` 後都觸發 SSE 廣播，且廣播內容正確。

- [ ] **Step 1：確認 `trigger.py` 有 `_API_BASE` 與 `_broadcast()` 方法**
  `_API_BASE = "http://localhost:8765"`，`_broadcast()` 使用 `threading.Thread` 做 fire-and-forget POST。

- [ ] **Step 2：確認觸發後廣播（`process_volatility`）**
  `trigger.py:121`：在 `state.save()` 後呼叫 `self._broadcast()`。

- [ ] **Step 3：確認觸發後廣播（`process_volatility_24h`）**
  `trigger.py:162`：在 `state.save()` 後呼叫 `self._broadcast()`。

- [ ] **Step 4：確認觸發後廣播（`process_funding_rate`）**
  `trigger.py:192`：在 `state.save()` 後呼叫 `self._broadcast()`。

- [ ] **Step 5：確認追蹤報告廣播（`check_tracking`）**
  `trigger.py:214`：在 `state.save()` 後呼叫 `self._broadcast()`。

- [ ] **Step 6：確認停止追蹤廣播（`stop_tracking`）**
  `trigger.py:226`：在 `state.save()` 後呼叫 `self._broadcast()`。

- [ ] **Step 7：確認 reload 廣播**
  `trigger.py:87`：在 `state.save()` 後呼叫 `self._broadcast()`。

- [ ] **Step 8：確認 `polling.py` 有 `_API_BASE` 與 `_broadcast_state()` 方法**

- [ ] **Step 9：確認 Monitor 啟動時廣播一次**
  `polling.py:76`：`self._broadcast_state()` 在 `state.save()` 後立即呼叫。

- [ ] **Step 10：確認廣播 payload 格式正確**
  `json={"tracked_pairs": self.state.data.get("tracked_pairs", {})}`

---

## Task 3：前端 SSE 整合驗收

**目的**：確認 Vue 前端完全移除 polling，完全依靠 SSE 更新，且 Settings 頁面不受打擾。

- [ ] **Step 1：確認 `App.vue` 無 polling**
  搜尋 `setInterval`、`setTimeout`、`refreshTimer`，應該為空（無）。
  `onMounted` 只呼叫 `loadState()` 一次。

- [ ] **Step 2：確認 `App.vue` 有 `onSseUpdate()` handler**
  `function onSseUpdate(trackedPairs) { state.value.tracked_pairs = trackedPairs }`

- [ ] **Step 3：確認 `App.vue` 對 Dashboard 綁定 `@sse-update`**
  `<Dashboard ... @sse-update="onSseUpdate" />`

- [ ] **Step 4：確認 `Dashboard.vue` EventSource 初始化**
  `onMounted` 內：`sseSource = new EventSource('/api/events')`

- [ ] **Step 5：確認 `Dashboard.vue` 監聽 `update` 事件**
  `sseSource.addEventListener('update', (e) => { emit('sse-update', data.tracked_pairs) })`

- [ ] **Step 6：確認 `Dashboard.vue` 忽略 SSE 錯誤**
  `sseSource.onerror = () => {}`（啞巴處理，瀏覽器自動重連）

- [ ] **Step 7：確認 `Dashboard.vue` onUnmounted 關閉連線**
  `onUnmounted(() => { if (sseSource) sseSource.close() })`

- [ ] **Step 8：確認 `Dashboard.vue` 無任何 polling timer**
  移除 `setInterval`、`setTimeout`。

---

## Task 4：資金費率 threshold 正確性驗收

**目的**：確認 funding rate threshold 比較邏輯已修復，不再有 100 倍差異。

- [ ] **Step 1：確認 `FundingRateChecker.check()` 的比較方向**
  API 回傳值為小數（如 `-0.0072`），threshold 為 `-0.01`（代表 -1%），直接比對：`funding_rate < threshold`。

- [ ] **Step 2：確認 `polling.py` 中**未**做 `funding_rate / 100` 的動作**
  搜尋 `/ 100` 在 `funding_rate` 相關行，正確做法是不做任何除法，直接用 API 回傳值。

- [ ] **Step 3：確認 UI 顯示時乘以 100**
  `Dashboard.vue` 的 `formatFunding(rate)` 為 `(r * 100).toFixed(4)`。

---

## Task 5：Settings 頁面隔離驗收

**目的**：確認 Settings 頁面完全不參與 SSE 自動更新，user 輸入時不會被覆蓋。

- [ ] **Step 1：確認 `App.vue` 中 Settings 的 `defineProps`**
  `<Settings :settings="state.settings" @update="loadState" />`
  `settings` 是從 `state.settings` 來的被動值，無自動刷新。

- [ ] **Step 2：確認 Settings 無 EventSource**
  `Settings.vue` 內無 `EventSource`、`setInterval`、`SSE`。

- [ ] **Step 3：確認 Settings 改動後手動 reload**
  Settings 的 `@update="loadState"` 事件，App.vue 收到後手動呼叫一次 API。

---

## Task 6：部署與端到端驗收

**目的**：系統啟動、正常運行、資料持久化整組確認。

- [ ] **Step 1：確認 process 都在運行**
  ```bash
  ps aux | grep -E "(uvicorn|run_monitor|node)" | grep -v grep
  ```
  預期：三行（uvicorn、python3 run_monitor.py、node vite）

- [ ] **Step 2：API 健康檢查**
  ```bash
  curl -s http://localhost:8765/api/health
  ```
  預期：`{"status":"healthy"}`

- [ ] **Step 3：SSE 廣播測試**
  ```bash
  curl -s -X POST http://localhost:8765/api/events/broadcast \
    -H "Content-Type: application/json" \
    -d '{"tracked_pairs":{}}'
  ```
  預期：`{"status":"ok","clients":0}`（無 client 連線時 clients=0 為正常）

- [ ] **Step 4：state.json 存在且格式正確**
  ```bash
  cat /home/hsien/admin/上傳/state.json | python3 -m json.tool > /dev/null && echo "valid json"
  ```
  預期：`valid json`

- [ ] **Step 5：Settings 更新後 state.json 同步**
  ```bash
  curl -s -X PUT http://localhost:8765/api/settings/volatility \
    -H "Content-Type: application/json" \
    -d '{"threshold_pct":6.0}' && \
  grep threshold_pct /home/hsien/admin/上傳/state.json
  ```
  預期：`"threshold_pct": 6.0`

- [ ] **Step 6：停止追蹤狀態正確**
  確認 `state.json.tracked_pairs` 內Symbol 刪除後，API `/api/state` 回傳已更新。

---

## Task 7：緊急還原機制（預防性）

**目的**：確認 state.json 損壞或 Monitor 崩潰時的恢復流程。

- [ ] **Step 1：確認 StateManager 有 `_default_state()` fallback**
  當 `state.json` 不存在或損壞時，回傳預設值而非 crash。

- [ ] **Step 2：確認 StateManager 使用檔案鎖（threading.Lock）**
  防止並發寫入衝突（API 和 Monitor 可能同時寫）。

---

## 自審查清單（Brainstorming → Spec → Plan）

- [x] **Spec 覆蓋所有核心需求**（SSE、即時更新、雙觸發條件、Telegram、state 持久化）
- [x] **Plan 每個 Task 有明確的 Step，可直接交給工程師執行**
- [x] **Plan 的每個 Step 都有驗收命令或判斷標準**
- [x] **無任何 TBD、TODO、placeholder**
- [x] **資金費率 threshold 陷阱已記錄（Spec Section 6、Plan Task 4）**
- [x] **Settings 頁面隔離已確認（Plan Task 5）**

---

## 交付給老闆的 End-to-End 摘要

| 層 | 元件 | 技術 | 狀態 |
|----|------|------|------|
| 前端 | Dashboard | Vue.js + SSE | 已實作 |
| 前端 | Settings | Vue.js + HTTP PUT | 已實作 |
| 前端 | History | Vue.js | 已實作 |
| API | SSE 廣播 | FastAPI + StreamingResponse | 已實作 |
| API | 狀態讀寫 | FastAPI + state.json | 已實作 |
| API | 設定更新 | PUT /api/settings/* | 已實作 |
| Monitor | 現貨波動 | asyncio + REST 10s polling | 已實作 |
| Monitor | 期貨資金費率 | asyncio + REST 10s polling | 已實作 |
| Monitor | 廣播觸發 | threading POST (fire-and-forget) | 已實作 |
| 通知 | Telegram | requests POST | 已實作 |
| 持久化 | state.json | StateManager + threading.Lock | 已實作 |
