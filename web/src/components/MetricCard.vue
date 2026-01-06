<!-- src/components/MetricCard.vue -->
<template>
  <div class="metric-card">
    <div class="label">{{ label }}</div>
    <div class="value" :class="{ positive, negative }">{{ value }}</div>
  </div>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: String, required: true },
  positive: { type: Boolean, default: false },
  negative: { type: Boolean, default: false }
})
</script>

<style scoped>
.metric-card {
  padding: 16px;
  background: #f8fafc;
  border-radius: 8px;
  text-align: center;
}
.label {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 4px;
}
.value {
  font-size: 20px;
  font-weight: 600;
  color: #1e293b;
}
.positive {
  color: #10b981;
}
.negative {
  color: #ef4444;
}
</style>