<!-- src/views/BacktestAnalysis.vue -->
<template>
  <div class="backtest-container">
    <div class="header">
      <h2>📊 回测分析系统</h2>
      <button @click="$router.push('/')" class="btn btn-outline">
        ← 返回监控大屏
      </button>
    </div>

    <div v-if="loading" class="card">
      <div class="loading">加载中...</div>
    </div>

    <div v-else-if="error" class="card error-card">
      <p>{{ error }}</p>
      <button @click="retryLoad" class="btn btn-secondary">重试</button>
    </div>

    <div v-else-if="report" class="card report-card">
      <div class="report-header">
        <h3>{{ report.strategy }}</h3>
        <span class="status-badge">{{ report.insight_title }}</span>
      </div>

      <div class="metrics-grid">
        <MetricCard label="总收益" :value="`${report.total_return}%`" :positive="report.total_return > 0" />
        <MetricCard label="最大回撤" :value="`${report.max_drawdown}%`" negative />
        <MetricCard label="夏普比率" :value="report.sharpe_ratio.toFixed(2)" />
        <MetricCard label="交易次数" :value="report.trade_count.toString()" />
      </div>

      <div ref="chartRef" class="chart-wrapper"></div>

      <div v-if="report.insight_summary" class="insight-section">
        <h4>🧠 智能解读</h4>
        <p>{{ report.insight_summary }}</p>
      </div>

      <button @click="runBacktest" :disabled="running" class="btn btn-primary run-btn">
        {{ running ? '回测中...' : '🔄 重新运行回测' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import MetricCard from '@/components/MetricCard.vue'

// ===== API 调用（企业级封装）=====
const API_BASE = '/api/backtest'

const triggerBacktest = async () => {
  const res = await fetch(`${API_BASE}/trigger`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ trigger_type: 'manual' })
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`)
  return res.json()
}

const getLatestReport = async () => {
  const res = await fetch(`${API_BASE}/report/latest`)
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`)
  return res.json()
}

// ===== 响应式状态 =====
const loading = ref(true)
const running = ref(false)
const error = ref(null)
const report = ref(null)
const chartRef = ref(null)
let chartInstance = null

// ===== 方法 =====
const loadReport = async () => {
  try {
    error.value = null
    const data = await getLatestReport()
    report.value = data
    await nextTick()
    renderChart()
  } catch (err) {
    console.error('加载回测报告失败:', err)
    error.value = err.message || '加载报告失败，请检查网络或后端服务'
  } finally {
    loading.value = false
  }
}

const runBacktest = async () => {
  running.value = true
  error.value = null
  try {
    await triggerBacktest()
    // 等待 2 秒让后台任务启动（实际项目建议加轮询）
    await new Promise(r => setTimeout(r, 2000))
    await loadReport()
  } catch (err) {
    console.error('触发回测失败:', err)
    error.value = err.message || '回测启动失败'
  } finally {
    running.value = false
  }
}

const retryLoad = () => {
  loading.value = true
  loadReport()
}

const renderChart = () => {
  if (!report.value?.equity_curve?.length || !chartRef.value) return

  // 销毁旧实例
  if (chartInstance) {
    chartInstance.dispose()
  }

  chartInstance = echarts.init(chartRef.value)
  chartInstance.setOption({
    title: { text: '净值曲线', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis', formatter: '{b}: {c}%' },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '20%' },
    xAxis: {
      type: 'category',
      data: report.value.equity_curve.map((_, i) => `第${i + 1}天`)
    },
    yAxis: {
      type: 'value',
      name: '净值 (%)',
      axisLabel: { formatter: '{value}%' }
    },
    series: [{
      name: '策略净值',
      data: report.value.equity_curve,
      type: 'line',
      smooth: true,
      lineStyle: { width: 3, color: '#3b82f6' },
      areaStyle: { color: '#dbeafe', opacity: 0.3 }
    }]
  })
}

// ===== 生命周期 =====
onMounted(() => {
  loadReport()
})

onBeforeUnmount(() => {
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})
</script>

<style scoped>
.backtest-container {
  padding: 24px;
  height: 10 s00vh;
  background: #f9fafb;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}
.card {
  background: white;
  padding: 24px;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}
.loading {
  text-align: center;
  color: #64748b;
}
.error-card {
  border-left: 4px solid #ef4444;
}
.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}
.status-badge {
  background: #e0f2fe;
  color: #0369a1;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
}
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 16px;
  margin: 24px 0;
}
.chart-wrapper {
  height: 320px;
  margin: 24px 0;
}
.insight-section {
  background: #f0f9ff;
  padding: 16px;
  border-radius: 8px;
  margin: 24px 0;
  border-left: 3px solid #3b82f6;
}
.insight-section h4 {
  margin: 0 0 8px 0;
  color: #1e40af;
}
.btn {
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  border: none;
}
.btn-outline {
  background: transparent;
  border: 1px solid #cbd5e1;
  color: #334155;
}
.btn-outline:hover {
  background: #f1f5f9;
}
.btn-primary {
  background: #3b82f6;
  color: white;
}
.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}
.btn-secondary {
  background: #e2e8f0;
  color: #334155;
}
.btn-secondary:hover {
  background: #cbd5e1;
}
.run-btn {
  width: 100%;
  padding: 10px;
  font-weight: 500;
}
</style>