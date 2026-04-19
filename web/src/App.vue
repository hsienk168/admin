<template>
  <div class="app">
    <!-- Header -->
    <header class="header">
      <div class="header-inner">
        <div class="logo">
          <div class="logo-icon">
            <!-- Chart icon -->
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
            </svg>
          </div>
          <span>Binance 市場監控</span>
          <div class="status-dot"></div>
        </div>
        <nav class="nav">
          <button
            class="nav-btn"
            :class="{ active: view === 'dashboard' }"
            @click="view = 'dashboard'"
          >
            監控面板
          </button>
          <button
            class="nav-btn"
            :class="{ active: view === 'settings' }"
            @click="view = 'settings'"
          >
            設定
          </button>
          <button
            class="nav-btn"
            :class="{ active: view === 'history' }"
            @click="view = 'history'"
          >
            歷史記錄
          </button>
        </nav>
      </div>
    </header>

    <!-- Main -->
    <main class="main">
      <Transition name="fade" mode="out-in">
        <Dashboard
          v-if="view === 'dashboard'"
          :state="state"
          :loading="loading"
          @stop="stopTrack"
          @refresh="loadState"
          @sse-update="onSseUpdate"
        />
        <Settings
          v-else-if="view === 'settings'"
          :settings="state.settings"
          @update="loadState"
        />
        <History
          v-else-if="view === 'history'"
          :history="state.alert_history"
        />
      </Transition>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Dashboard from './components/Dashboard.vue'
import Settings from './components/Settings.vue'
import History from './components/History.vue'

const view = ref('dashboard')
const loading = ref(false)
const state = ref({
  tracked_pairs: {},
  settings: {},
  alert_history: []
})

async function loadState() {
  loading.value = true
  try {
    const res = await fetch('/api/state')
    state.value = await res.json()
  } catch (e) {
    console.error('Failed to load state:', e)
  } finally {
    loading.value = false
  }
}

function stopTrack(symbol) {
  fetch(`/api/track/${symbol}/stop`, { method: 'POST' })
    .then(() => loadState())
}

function onSseUpdate(trackedPairs) {
  state.value.tracked_pairs = trackedPairs
}

onMounted(loadState)
</script>
