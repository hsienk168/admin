<template>
  <div class="settings">
    <div class="section-header">
      <h2 class="section-title">監控設定</h2>
    </div>

    <!-- Volatility Trigger Settings -->
    <div class="card settings-card">
      <div class="card-header">
        <div class="card-title-row">
          <span class="badge badge-volatility">波動</span>
          <h3 class="card-subtitle">波動觸發設定</h3>
        </div>
        <label class="toggle">
          <input type="checkbox" v-model="local.volatility.enabled" />
          <span class="toggle-slider"></span>
        </label>
      </div>

      <form class="settings-form" @submit.prevent="saveVolatility">
        <!-- Threshold -->
        <div class="form-group">
          <label class="form-label" for="vol-threshold">波動閾值</label>
          <input
            id="vol-threshold"
            v-model.number="local.volatility.threshold_pct"
            class="form-input"
            type="number"
            step="0.1"
            min="0.1"
            :disabled="!local.volatility.enabled"
          />
          <span class="form-hint">5分鐘漲跌百分比超過此值時觸發追蹤，單位：%</span>
        </div>

        <!-- Std multiplier -->
        <div class="form-group">
          <label class="form-label" for="vol-std">統計倍數</label>
          <input
            id="vol-std"
            v-model.number="local.volatility.std_multiplier"
            class="form-input"
            type="number"
            step="0.1"
            min="0.1"
            :disabled="!local.volatility.enabled"
          />
          <span class="form-hint">相對於過去24小時標準差的倍數</span>
        </div>

        <!-- Track interval -->
        <div class="form-group">
          <label class="form-label" for="vol-interval">追蹤間隔</label>
          <input
            id="vol-interval"
            v-model.number="local.volatility.track_interval_minutes"
            class="form-input"
            type="number"
            step="1"
            min="1"
            max="1440"
            :disabled="!local.volatility.enabled"
          />
          <span class="form-hint">觸發後每多久回報一次，單位：分鐘</span>
        </div>

        <!-- Save button -->
        <div class="form-actions">
          <button type="submit" class="btn btn-primary" :disabled="savingVol">
            <span v-if="savingVol">儲存中...</span>
            <span v-else-if="savedVol">已儲存</span>
            <span v-else>儲存波動設定</span>
          </button>
        </div>
      </form>
    </div>

    <!-- Funding Rate Trigger Settings -->
    <div class="card settings-card">
      <div class="card-header">
        <div class="card-title-row">
          <span class="badge badge-funding">資金費率</span>
          <h3 class="card-subtitle">資金費率觸發設定</h3>
        </div>
        <label class="toggle">
          <input type="checkbox" v-model="local.funding_rate.enabled" />
          <span class="toggle-slider"></span>
        </label>
      </div>

      <!-- Countdown timer -->
      <div v-if="countdownFund > 0" class="countdown-bar">
        <div class="countdown-info">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 16 14"/>
          </svg>
          <span>設定將在 <strong>{{ countdownFund }}</strong> 秒後生效</span>
        </div>
        <div class="countdown-track">
          <div class="countdown-fill" :style="{ width: (countdownFund / 60 * 100) + '%' }"></div>
        </div>
      </div>

      <form class="settings-form" @submit.prevent="saveFundingRate">
        <!-- Funding rate threshold -->
        <div class="form-group">
          <label class="form-label" for="fund-threshold">資金費率閾值</label>
          <input
            id="fund-threshold"
            v-model.number="local.funding_rate.threshold"
            class="form-input"
            type="number"
            step="0.001"
            min="-1"
            max="0"
            :disabled="!local.funding_rate.enabled"
          />
          <span class="form-hint">資金費率低於此值時觸發，填入數值（-1 代表 -1%）</span>
        </div>

        <!-- Track interval -->
        <div class="form-group">
          <label class="form-label" for="fund-interval">追蹤間隔</label>
          <input
            id="fund-interval"
            v-model.number="local.funding_rate.track_interval_minutes"
            class="form-input"
            type="number"
            step="1"
            min="1"
            max="1440"
            :disabled="!local.funding_rate.enabled"
          />
          <span class="form-hint">觸發後每多久回報一次，單位：分鐘</span>
        </div>

        <!-- Save button -->
        <div class="form-actions">
          <button type="submit" class="btn btn-primary" :disabled="savingFund">
            <span v-if="savingFund">儲存中...</span>
            <span v-else-if="savedFund">已儲存</span>
            <span v-else>儲存資金費率設定</span>
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps(['settings'])
const emit = defineEmits(['update'])

const local = ref({
  volatility: { enabled: true, threshold_pct: 5, std_multiplier: 2, track_interval_minutes: 30 },
  funding_rate: { enabled: true, threshold: -1.0, track_interval_minutes: 30 }
})

// Volatility save state
const savingVol = ref(false)
const savedVol = ref(false)

// Funding rate save state
const savingFund = ref(false)
const savedFund = ref(false)
const countdownFund = ref(0)
let countdownFundTimer = null

function startCountdownFund() {
  if (countdownFundTimer) clearInterval(countdownFundTimer)
  countdownFund.value = 60
  countdownFundTimer = setInterval(() => {
    countdownFund.value--
    if (countdownFund.value <= 0) {
      clearInterval(countdownFundTimer)
      countdownFundTimer = null
    }
  }, 1000)
}

watch(() => props.settings, v => {
  if (v) {
    local.value = {
      volatility: { ...v.volatility },
      funding_rate: { ...v.funding_rate }
    }
  }
}, { deep: true, immediate: true })

async function saveVolatility() {
  savingVol.value = true
  savedVol.value = false
  try {
    await fetch('/api/settings/volatility', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(local.value.volatility)
    })
    savedVol.value = true
    emit('update')
    setTimeout(() => { savedVol.value = false }, 2000)
  } catch (e) {
    console.error('Save volatility failed:', e)
  } finally {
    savingVol.value = false
  }
}

async function saveFundingRate() {
  savingFund.value = true
  savedFund.value = false
  try {
    await fetch('/api/settings/funding-rate', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(local.value.funding_rate)
    })
    savedFund.value = true
    startCountdownFund()
    emit('update')
    setTimeout(() => { savedFund.value = false }, 2000)
  } catch (e) {
    console.error('Save funding rate failed:', e)
  } finally {
    savingFund.value = false
  }
}
</script>

<style scoped>
.settings {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.settings-card {
  max-width: 520px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.25rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border);
}

.card-title-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.card-subtitle {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.badge {
  font-size: 0.6875rem;
  font-weight: 700;
  padding: 0.2rem 0.5rem;
  border-radius: 999px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.badge-volatility {
  background: rgba(251, 146, 60, 0.15);
  color: #fb923c;
}

.badge-funding {
  background: rgba(96, 165, 250, 0.15);
  color: #60a5fa;
}

/* Toggle switch */
.toggle {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
  cursor: pointer;
}

.toggle input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  inset: 0;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 999px;
  transition: all 0.2s ease;
}

.toggle-slider::before {
  content: '';
  position: absolute;
  height: 18px;
  width: 18px;
  left: 2px;
  bottom: 2px;
  background: var(--text-muted);
  border-radius: 50%;
  transition: all 0.2s ease;
}

.toggle input:checked + .toggle-slider {
  background: var(--accent);
  border-color: var(--accent);
}

.toggle input:checked + .toggle-slider::before {
  transform: translateX(20px);
  background: white;
}

.toggle input:disabled + .toggle-slider {
  opacity: 0.4;
  cursor: not-allowed;
}

.form-actions {
  margin-top: 0.5rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
}

/* Countdown timer */
.countdown-bar {
  margin-bottom: 1rem;
  padding: 0.6rem 0.8rem;
  background: rgba(96, 165, 250, 0.08);
  border: 1px solid rgba(96, 165, 250, 0.2);
  border-radius: 8px;
}

.countdown-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
  color: #60a5fa;
  margin-bottom: 0.4rem;
}

.countdown-info svg {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.countdown-info strong {
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.countdown-track {
  height: 3px;
  background: rgba(96, 165, 250, 0.15);
  border-radius: 999px;
  overflow: hidden;
}

.countdown-fill {
  height: 100%;
  background: linear-gradient(90deg, #60a5fa, #93c5fd);
  border-radius: 999px;
  transition: width 1s linear;
}
</style>
