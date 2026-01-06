<template>
  <div class="snapshot-control">
    <h1>快照采集控制台</h1>

    <div class="status">
      <p>自动快照状态: {{ autoStatus ? '🟢 开启' : '🔴 关闭' }}</p>
      <button @click="toggleAuto">切换自动快照</button>
    </div>

    <div class="manual">
      <button @click="triggerManual">▶️ 手动触发一次快照</button>
      <p v-if="lastTrigger">上次触发: {{ lastTrigger }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getAutoStatus, toggleAutoSnapshot, triggerSnapshot } from '@/api/snapshot'

const autoStatus = ref(false)
const lastTrigger = ref(null)

const loadStatus = async () => {
  const res = await getAutoStatus()
  autoStatus.value = res.enabled
}

const toggleAuto = async () => {
  await toggleAutoSnapshot()
  await loadStatus()
}

const triggerManual = async () => {
  await triggerSnapshot()
  lastTrigger.value = new Date().toLocaleString()
  alert('快照任务已启动')
}

onMounted(() => {
  loadStatus()
})
</script>

<style scoped>
.snapshot-control {
  padding: 20px;
  font-family: sans-serif;
}
button {
  margin: 10px;
  padding: 8px 16px;
  background: #007bff;
  color: white;
  border: none;
  cursor: pointer;
}
button:hover {
  background: #0056b3;
}
</style>