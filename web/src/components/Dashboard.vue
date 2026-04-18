<template>
  <div class="dashboard">
    <h2>Monitored Pairs ({{ Object.keys(state.tracked_pairs).length }})</h2>
    <div v-if="Object.keys(state.tracked_pairs).length === 0" class="empty">
      No pairs being tracked. Alerts will appear here when triggered.
    </div>
    <div v-else class="grid">
      <div v-for="(info, symbol) in state.tracked_pairs" :key="symbol" class="card">
        <div class="card-header">
          <strong>{{ symbol }}</strong>
          <span class="badge" :class="info.trigger_reason">
            {{ info.trigger_reason === 'volatility' ? '📊' : '💸' }}
          </span>
        </div>
        <div class="card-body">
          <div v-if="info.volatility_pct">波動: {{ info.volatility_pct }}%</div>
          <div v-if="info.funding_rate">資金費率: {{ info.funding_rate }}%</div>
          <div>觸發時間: {{ new Date(info.triggered_at).toLocaleString() }}</div>
          <div>追蹤次數: {{ info.report_count }}</div>
        </div>
        <button @click="$emit('stop', symbol)">停止追蹤</button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps(['state'])
defineEmits(['stop'])
</script>

<style scoped>
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 1rem; }
.card { background: #1a1a2e; border: 1px solid #333; border-radius: 8px; padding: 1rem; }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
.badge { font-size: 1.2rem; }
.card-body { font-size: 0.85rem; color: #aaa; margin: 0.5rem 0; }
button { background: #e74c3c; border: none; color: white; padding: 0.4rem 0.8rem; border-radius: 4px; cursor: pointer; }
.empty { color: #666; text-align: center; padding: 2rem; }
</style>