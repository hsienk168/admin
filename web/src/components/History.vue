<template>
  <div class="history">
    <h2>Alert History</h2>
    <div v-if="history.length === 0" class="empty">No alerts yet.</div>
    <table v-else>
      <thead><tr><th>Time</th><th>Symbol</th><th>Reason</th><th>Value</th></tr></thead>
      <tbody>
        <tr v-for="alert in history" :key="alert.id">
          <td>{{ new Date(alert.triggered_at).toLocaleString() }}</td>
          <td>{{ alert.symbol }}</td>
          <td>{{ alert.trigger_reason }}</td>
          <td>{{ alert.volatility_pct || alert.funding_rate }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
defineProps(['history'])
</script>

<style scoped>
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 0.5rem; border-bottom: 1px solid #333; }
.empty { color: #666; }
</style>