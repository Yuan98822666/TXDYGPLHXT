// src/router/index.ts
import { createRouter, createWebHashHistory } from 'vue-router'
import Home from '@/views/Home.vue'
import BacktestAnalysis from '@/views/BacktestAnalysis.vue'

const routes = [
  { path: '/', component: Home },
  { path: '/backtest', component: BacktestAnalysis }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router