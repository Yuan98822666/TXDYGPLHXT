// src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'
import SnapshotControl from '../views/SnapshotControl.vue'

const routes = [
  {
    path: '/',
    redirect: '/snapshot'
  },
  {
    path: '/snapshot',
    name: 'SnapshotControl',
    component: SnapshotControl
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router