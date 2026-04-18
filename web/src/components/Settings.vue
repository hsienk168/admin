<template>
  <div class="settings">
    <h2>Settings</h2>
    <div class="form">
      <label>波動閾值 (%) <input v-model.number="local.volatility_threshold_pct" type="number" step="0.1" /></label>
      <label>標準差倍數 <input v-model.number="local.volatility_std_multiplier" type="number" step="0.1" /></label>
      <label>資金費率閾值 <input v-model.number="local.funding_rate_threshold" type="number" step="0.001" /></label>
      <label>追蹤間隔 (分鐘) <input v-model.number="local.track_interval_minutes" type="number" /></label>
      <button @click="save">儲存</button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
const props = defineProps(['settings'])
const emit = defineEmits(['update'])
const local = ref({ ...props.settings })
watch(() => props.settings, v => { local.value = { ...v } })
async function save() {
  await fetch('/api/settings', { method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(local.value) })
  emit('update')
}
</script>

<style scoped>
.form { display: flex; flex-direction: column; gap: 0.75rem; max-width: 400px; }
label { display: flex; flex-direction: column; font-size: 0.85rem; color: #aaa; }
input { background: #1a1a2e; border: 1px solid #333; color: #fff; padding: 0.5rem; border-radius: 4px; margin-top: 0.25rem; }
button { background: #27ae60; border: none; color: white; padding: 0.6rem 1.2rem; border-radius: 4px; cursor: pointer; align-self: flex-start; }
</style>