<template>
  <div class="dashboard">
    <!-- Section header -->
    <div class="section-header">
      <h2 class="section-title">追蹤中的交易對</h2>
      <span class="section-count">{{ pairCount }} 個</span>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="pairs-grid">
      <div v-for="i in 3" :key="i" class="pair-card skeleton-card">
        <div class="skeleton-line w-24 h-4"></div>
        <div class="skeleton-line w-32 h-7 mt-3"></div>
        <div class="skeleton-line w-48 h-3 mt-2"></div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else-if="pairCount === 0" class="empty-state">
      <div class="empty-icon">
        <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="12" r="10"/>
          <path d="M8 12h8M12 8v8"/>
        </svg>
      </div>
      <p class="empty-title">尚無追蹤中的交易對</p>
      <p class="empty-desc">當市場波動或資金費率觸發條件時，系統會自動顯示在這裡</p>
    </div>

    <!-- Volatility section -->
    <div v-if="volatilityPairs.length > 0">
      <div class="subsection-header">
        <span class="subsection-title">波動觸發</span>
        <span class="subsection-count">{{ volatilityPairs.length }} 個</span>
      </div>
      <div class="pairs-grid">
        <TransitionGroup name="list">
          <div
            v-for="entry in volatilityPairs"
            :key="entry[0]"
            class="pair-card"
            :class="parseFloat(entry[1].volatility_pct) >= 0 ? 'card-positive' : 'card-negative'"
          >
            <!-- Header row -->
            <div class="pair-header">
              <a class="pair-symbol" :href="entry[1].trigger_reason === 'funding_rate' ? 'https://www.binance.com/zh-TC/futures/' + entry[0] : 'https://www.binance.com/zh-TC/trade/' + entry[0].replace(/USDT$/, '_USDT')" target="_blank" rel="noopener">{{ entry[0] }}</a>
              <span class="pair-badge badge-volatility">波動</span>
            </div>

            <!-- Price -->
            <div class="pair-price">{{ formatPrice(entry[1].trigger_price) }}</div>

            <!-- Details -->
            <div class="pair-detail">
              <div
                v-if="entry[1].volatility_pct != null"
                class="pair-meta"
                :class="parseFloat(entry[1].volatility_pct) >= 0 ? 'positive' : 'negative'"
              >
                <span>5分鐘漲跌：</span>
                <strong>{{ parseFloat(entry[1].volatility_pct) >= 0 ? '+' : '' }}{{ entry[1].volatility_pct }}%</strong>
              </div>
              <div class="pair-meta">
                <span>觸發：</span>
                <strong>{{ formatTime(entry[1].triggered_at) }}</strong>
              </div>
              <div class="pair-meta">
                <span>追蹤次數：</span>
                <strong>{{ entry[1].report_count }}</strong>
              </div>
            </div>

            <!-- Action -->
            <div class="pair-actions">
              <button class="btn btn-danger" @click="$emit('stop', entry[0])">停止追蹤</button>
            </div>
          </div>
        </TransitionGroup>
      </div>
    </div>

    <!-- Funding rate section -->
    <div v-if="fundingPairs.length > 0">
      <div class="subsection-header">
        <span class="subsection-title">資金費率觸發</span>
        <span class="subsection-count">{{ fundingPairs.length }} 個</span>
      </div>
      <div class="pairs-grid">
        <TransitionGroup name="list">
          <div
            v-for="entry in fundingPairs"
            :key="entry[0]"
            class="pair-card"
          >
            <!-- Header row -->
            <div class="pair-header">
              <a class="pair-symbol" :href="entry[1].trigger_reason === 'funding_rate' ? 'https://www.binance.com/zh-TC/futures/' + entry[0] : 'https://www.binance.com/zh-TC/trade/' + entry[0].replace(/USDT$/, '_USDT')" target="_blank" rel="noopener">{{ entry[0] }}</a>
              <span class="pair-badge badge-funding">資金費率</span>
            </div>

            <!-- Price -->
            <div class="pair-price">{{ formatPrice(entry[1].trigger_price) }}</div>

            <!-- Details -->
            <div class="pair-detail">
              <div
                v-if="entry[1].funding_rate != null"
                class="pair-meta negative"
              >
                <span>資金費率：</span>
                <strong>{{ formatFunding(entry[1].funding_rate) }}%</strong>
              </div>
              <div class="pair-meta">
                <span>觸發：</span>
                <strong>{{ formatTime(entry[1].triggered_at) }}</strong>
              </div>
              <div class="pair-meta">
                <span>追蹤次數：</span>
                <strong>{{ entry[1].report_count }}</strong>
              </div>
            </div>

            <!-- Action -->
            <div class="pair-actions">
              <button class="btn btn-danger" @click="$emit('stop', entry[0])">停止追蹤</button>
            </div>
          </div>
        </TransitionGroup>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else-if="pairCount === 0" class="empty-state">
      <div class="empty-icon">
        <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="12" r="10"/>
          <path d="M8 12h8M12 8v8"/>
        </svg>
      </div>
      <p class="empty-title">尚無追蹤中的交易對</p>
      <p class="empty-desc">當市場波動或資金費率觸發條件時，系統會自動顯示在這裡</p>
    </div>

    <!-- System status bar -->
    <div class="status-bar">
      <div class="status-item">
        <div class="status-dot sm"></div>
        <span>系統監控中</span>
      </div>
      <div class="status-item">
        <span>波動監控：{{ state.settings?.volatility?.enabled ? '開' : '關' }}｜閾值 {{ state.settings?.volatility?.threshold_pct }}%｜{{ state.settings?.volatility?.track_interval_minutes }}分鐘</span>
      </div>
      <div class="status-item">
        <span>資金費率監控：{{ state.settings?.funding_rate?.enabled ? '開' : '關' }}｜閾值 {{ state.settings?.funding_rate?.threshold }}%｜{{ state.settings?.funding_rate?.track_interval_minutes }}分鐘</span>
      </div>
      <div class="status-item">
        <span>自動刷新：15秒</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  state: { type: Object, required: true },
  loading: { type: Boolean, default: false }
})
const emit = defineEmits(['stop', 'refresh', 'sse-update'])

let sseSource = null

onMounted(() => {
  // SSE: real-time updates without polling
  sseSource = new EventSource('/api/events')
  sseSource.addEventListener('update', (e) => {
    try {
      const data = JSON.parse(e.data)
      if (data.tracked_pairs) {
        emit('sse-update', data.tracked_pairs)
      }
    } catch (err) {
      console.error('SSE parse error:', err)
    }
  })
  sseSource.onerror = () => {
    // Silently ignore SSE errors; browser will auto-reconnect
  }
})

onUnmounted(() => {
  if (sseSource) sseSource.close()
})

const pairCount = computed(() => {
  if (!props.state?.tracked_pairs) return 0
  return Object.keys(props.state.tracked_pairs).length
})

const volatilityPairs = computed(() => {
  if (!props.state?.tracked_pairs) return []
  const entries = Object.entries(props.state.tracked_pairs).filter(
    ([, info]) => info.trigger_reason === 'volatility'
  )
  // Sort: positive values descending, negative values ascending (most negative first)
  entries.sort(([, a], [, b]) => {
    const va = parseFloat(a.volatility_pct) || 0
    const vb = parseFloat(b.volatility_pct) || 0
    if (va > 0 && vb < 0) return -1   // positives first
    if (va < 0 && vb > 0) return 1    // negatives last
    if (va > 0) return vb - va         // positives: largest first
    return va - vb                      // negatives: most negative first
  })
  return entries
})

const fundingPairs = computed(() => {
  if (!props.state?.tracked_pairs) return []
  const entries = Object.entries(props.state.tracked_pairs).filter(
    ([, info]) => info.trigger_reason === 'funding_rate'
  )
  // Sort: most negative (worst) funding rate first
  entries.sort(([, a], [, b]) => {
    const ra = parseFloat(a.funding_rate) || 0
    const rb = parseFloat(b.funding_rate) || 0
    return ra - rb
  })
  return entries
})

function formatPrice(price) {
  if (price == null) return '--'
  const p = parseFloat(price)
  if (isNaN(p)) return '--'
  if (p >= 1000) return p.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  if (p >= 1) return p.toFixed(4)
  return p.toFixed(6)
}

function formatFunding(rate) {
  if (rate == null) return '--'
  const r = parseFloat(rate)
  if (isNaN(r)) return '--'
  return (r * 100).toFixed(4)
}

function formatTime(iso) {
  if (!iso) return '--'
  const d = new Date(iso)
  const now = new Date()
  const diffMs = now - d
  if (diffMs < 60000) return '剛剛'
  if (diffMs < 3600000) return `${Math.floor(diffMs / 60000)} 分鐘前`
  if (diffMs < 86400000) return `${Math.floor(diffMs / 3600000)} 小時前`
  return d.toLocaleString('zh-TW', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.status-bar {
  margin-top: 2rem;
  padding: 0.875rem 1.25rem;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  gap: 1.5rem;
  flex-wrap: wrap;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  color: var(--text-muted);
  font-family: 'Geist Mono', monospace;
}

.status-dot.sm {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--accent);
  animation: pulse-dot 2s ease-in-out infinite;
}

/* Skeleton loader */
.skeleton-card { pointer-events: none; }

.skeleton-line {
  background: linear-gradient(90deg, var(--bg-elevated) 25%, var(--border) 50%, var(--bg-elevated) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 4px;
  margin-bottom: 0.5rem;
}

.skeleton-line.w-24 { width: 6rem; height: 1rem; }
.skeleton-line.w-32 { width: 8rem; height: 1.75rem; }
.skeleton-line.w-48 { width: 12rem; height: 0.75rem; }
.skeleton-line.h-3 { height: 0.75rem; }
.skeleton-line.h-4 { height: 1rem; }
.skeleton-line.h-7 { height: 1.75rem; }
.skeleton-line.mt-2 { margin-top: 0.5rem; }
.skeleton-line.mt-3 { margin-top: 0.75rem; }

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}

.subsection-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
  margin-top: 1.5rem;
}
.subsection-header:first-child {
  margin-top: 0;
}
.subsection-title {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}
.subsection-count {
  font-size: 0.6875rem;
  font-family: 'Geist Mono', monospace;
  color: var(--text-muted);
  background: var(--bg-elevated);
  padding: 0.125rem 0.5rem;
  border-radius: 999px;
  border: 1px solid var(--border);
}
</style>
