<template>
  <div class="app">
    <header>
      <h1>🚀 Binance Monitor</h1>
      <nav>
        <button @click="view = 'dashboard'" :class="{ active: view === 'dashboard' }">Dashboard</button>
        <button @click="view = 'settings'" :class="{ active: view === 'settings' }">Settings</button>
        <button @click="view = 'history'" :class="{ active: view === 'history' }">History</button>
      </nav>
    </header>
    <main>
      <Dashboard v-if="view === 'dashboard'" :state="state" @stop="stopTrack" />
      <Settings v-if="view === 'settings'" :settings="state.settings" @update="loadState" />
      <History v-if="view === 'history'" :history="state.alert_history" />
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Dashboard from './components/Dashboard.vue'
import Settings from './components/Settings.vue'
import History from './components/History.vue'

const view = ref('dashboard')
const state = ref({ tracked_pairs: {}, settings: {}, alert_history: [] })

async function loadState() {
  const res = await fetch('/api/state')
  state.value = await res.json()
}

function stopTrack(symbol) {
  fetch(`/api/track/${symbol}/stop`, { method: 'POST' }).then(loadState)
}

onMounted(loadState)
setInterval(loadState, 30000)
</script>

<style>
body { font-family: sans-serif; margin: 0; padding: 0; background: #0f0f1a; color: #fff; }
header { background: #1a1a2e; padding: 1rem; display: flex; align-items: center; gap: 2rem; }
header h1 { margin: 0; font-size: 1.2rem; }
nav { display: flex; gap: 0.5rem; }
nav button { background: transparent; border: 1px solid #333; color: #888; padding: 0.5rem 1rem; border-radius: 4px; cursor: pointer; }
nav button.active, nav button:hover { background: #2a2a4a; color: #fff; border-color: #5a5a8a; }
main { padding: 1rem; }
</style>