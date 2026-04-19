<template>
  <div class="history">
    <div class="section-header">
      <h2 class="section-title">警報歷史</h2>
      <span class="section-count">{{ history.length }} 筆</span>
    </div>

    <!-- Empty state -->
    <div v-if="history.length === 0" class="empty-state">
      <div class="empty-icon">
        <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
          <line x1="16" y1="2" x2="16" y2="6"/>
          <line x1="8" y1="2" x2="8" y2="6"/>
          <line x1="3" y1="10" x2="21" y2="10"/>
        </svg>
      </div>
      <p class="empty-title">尚無警報記錄</p>
      <p class="empty-desc">所有觸發過的警報都會顯示在這裡</p>
    </div>

    <!-- Table -->
    <div v-else class="history-table-wrap">
      <table class="history-table">
        <thead>
          <tr>
            <th>時間</th>
            <th>交易對</th>
            <th>類型</th>
            <th>數值</th>
            <th>原因</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="alert in sortedHistory" :key="alert.id || `${alert.symbol}-${alert.triggered_at}`">
            <td class="mono">{{ formatDate(alert.triggered_at) }}</td>
            <td class="history-symbol">{{ alert.symbol }}</td>
            <td>
              <span
                class="reason-badge"
                :class="alert.trigger_reason === 'volatility' ? 'badge-volatility' : 'badge-funding'"
              >
                {{ alert.trigger_reason === 'volatility' ? '波動' : '資金費率' }}
              </span>
            </td>
            <td class="history-value mono">
              <span v-if="alert.volatility_pct != null" :class="parseFloat(alert.volatility_pct) >= 0 ? 'text-accent' : 'text-danger'">
                {{ parseFloat(alert.volatility_pct) >= 0 ? '+' : '' }}{{ alert.volatility_pct }}%
              </span>
              <span v-else-if="alert.funding_rate != null" class="text-danger">
                {{ formatFunding(alert.funding_rate) }}%
              </span>
              <span v-else>--</span>
            </td>
            <td class="text-muted">{{ alert.trigger_reason === 'volatility' ? '波動性突破閾值' : '資金費率異常' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  history: { type: Array, default: () => [] }
})

const sortedHistory = computed(() => {
  return [...props.history].sort((a, b) => {
    return new Date(b.triggered_at) - new Date(a.triggered_at)
  })
})

function formatDate(iso) {
  if (!iso) return '--'
  const d = new Date(iso)
  return d.toLocaleString('zh-TW', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  })
}

function formatFunding(rate) {
  if (rate == null) return '--'
  return (parseFloat(rate) * 100).toFixed(4)
}
</script>

<style scoped>
.mono { font-family: 'Geist Mono', monospace; }
.text-accent { color: var(--accent); }
.text-danger { color: var(--danger); }
.text-muted { color: var(--text-muted); font-size: 0.75rem; }
</style>
