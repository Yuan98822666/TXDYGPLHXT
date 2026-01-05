<template>
  <div class="dashboard">
    <!-- 顶部状态栏 -->
    <header class="header">
      <h1>TXDYGPLHXT 股票点名监控大屏</h1>
      <div class="controls">
        <select v-model="currentSort" @change="onSortChange" class="sort-select">
          <option value="stock_zdf">📈 按涨幅排序</option>
          <option value="mention_count">📣 按点名次数排序</option>
          <option value="qiaoban_factor">💪 按撬板因子排序</option>
        </select>
        <span class="status-badge" :class="{ active: autoEnabled }">
          {{ autoEnabled ? '● 自动采集开启' : '○ 自动采集关闭' }}
        </span>
        <button @click="toggleAuto" :disabled="loading" class="btn btn-secondary">
          {{ autoEnabled ? '暂停自动' : '恢复自动' }}
        </button>
        <button @click="triggerManual" :disabled="loading" class="btn btn-primary">
          🔄 手动采集
        </button>
      </div>
    </header>

    <!-- 主体内容 -->
    <main class="main">
      <!-- 左侧控制面板 -->
      <section class="control-panel">
        <div class="panel-card">
          <h3>系统状态</h3>
          <div class="status-row">
            <span>自动采集：</span>
            <span :class="autoEnabled ? 'status-on' : 'status-off'">
              {{ autoEnabled ? '运行中' : '已暂停' }}
            </span>
          </div>
          <div class="status-row">
            <span>最近采集：</span>
            <span>{{ lastTrigger || '暂无记录' }}</span>
          </div>
          <div class="status-row">
            <span>当前排序：</span>
            <span class="sort-label">{{ sortLabels[currentSort] }}</span>
          </div>
        </div>

        <div class="panel-card">
          <h3>手动操作</h3>
          <button @click="triggerManual" :disabled="loading" class="btn btn-block">
            ⚡ 立即采集一次快照
          </button>
        </div>
      </section>

      <!-- 右侧图表区域 -->
      <section class="chart-panel">
        <div class="chart-header">
          <h3>点名股主力资金流向分析（Top 20）</h3>
          <p class="subtitle">数据来自实时快照 | {{ sortLabels[currentSort] }}</p>
        </div>
        <div ref="chartRef" class="chart-container"></div>
      </section>
    </main>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'

export default {
  name: 'App',
  setup() {
    const autoEnabled = ref(true)
    const loading = ref(false)
    const lastTrigger = ref('')
    const chartRef = ref(null)
    const currentSort = ref('stock_zdf') // 默认按涨幅排序
    let myChart = null

    const sortLabels = {
      stock_zdf: '按个股涨幅排序',
      mention_count: '按点名次数排序',
      qiaoban_factor: '按撬板因子（主力占比/市值）排序'
    }

    // 获取状态
    const fetchStatus = async () => {
      try {
        const res = await fetch('/snapshot/auto-status')
        if (res.ok) {
          const data = await res.json()
          autoEnabled.value = data.enabled
        }
      } catch (e) {
        console.error('获取状态失败', e)
      }
    }

    // 切换自动
    const toggleAuto = async () => {
      loading.value = true
      try {
        await fetch('/snapshot/auto-toggle', { method: 'POST' })
        await fetchStatus()
      } finally {
        loading.value = false
      }
    }

    // 手动采集
    const triggerManual = async () => {
      loading.value = true
      try {
        await fetch('/snapshot/blockstock', { method: 'POST' })
        lastTrigger.value = new Date().toLocaleString('zh-CN')
        await fetchHotStocks()
      } finally {
        loading.value = false
      }
    }

    // 排序切换
    const onSortChange = () => {
      fetchHotStocks()
    }

    // 构建请求参数
    const getSortQueryParam = () => {
      if (currentSort.value === 'qiaoban_factor') {
        // 后端需支持按撬板因子排序，或前端排序（此处假设后端支持）
        return 'qiaoban_factor'
      }
      return currentSort.value
    }

    // 获取热点股票并渲染图表
    const fetchHotStocks = async () => {
      try {
        const sortBy = getSortQueryParam()
        const res = await fetch(`/hot/mentioned-stocks?sort_by=${sortBy}&top_n=50`)
        const data = await res.json()
        const stocks = data.stocks || []

        // 如果后端不支持 qiaoban_factor 排序，可在此处前端排序（示例）：
        // if (currentSort.value === 'qiaoban_factor') {
        //   stocks.sort((a, b) => {
        //     const factorA = (a.stock_zl_zb || 0) / (a.market_value || 1)
        //     const factorB = (b.stock_zl_zb || 0) / (b.market_value || 1)
        //     return factorB - factorA // 降序
        //   })
        // }

        const namesWithInfo = stocks.map(s =>`${s.stock_name} (提及:${s.mention_count} 涨幅:${s.stock_zdf?.toFixed(2)/100 || 0}%)`)

        const zl = stocks.map(s => (s.stock_zl_zb || 0) / 100)
        const cd = stocks.map(s => (s.stock_cd_zb || 0) / 100)
        const dd = stocks.map(s => (s.stock_dd_zb || 0) / 100)
        const zd = stocks.map(s => (s.stock_zd_zb || 0) / 100)
        const xd = stocks.map(s => (s.stock_xd_zb || 0) / 100)

        const option = {
          tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
          legend: { bottom: 0, itemWidth: 12, itemHeight: 12 },
          grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
          xAxis: { type: 'value', name: '资金占比 (%)' },
          yAxis: {
            type: 'category',
            data: namesWithInfo,
            axisLabel: { fontSize: 12 }
          },
          series: [
            {
              name: '主力',
              type: 'bar',
              stack: 'total',
              data: zl,
              label: {
                show: true,
                position: 'inside',
                formatter: (params) => params.value.toFixed(2) + '%'
              }
            },
            {
              name: '超大单',
              type: 'bar',
              stack: 'total',
              data: cd,
              label: {
                show: true,
                position: 'inside',
                formatter: (params) => params.value.toFixed(2) + '%'
              }
            },
            {
              name: '大单',
              type: 'bar',
              stack: 'total',
              data: dd,
              label: {
                show: true,
                position: 'inside',
                formatter: (params) => params.value.toFixed(2) + '%'
              }
            },
            {
              name: '中单',
              type: 'bar',
              stack: 'total',
              data: zd,
              label: {
                show: true,
                position: 'inside',
                formatter: (params) => params.value.toFixed(2) + '%'
              }
            },
            {
              name: '小单',
              type: 'bar',
              stack: 'total',
              data: xd,
              label: {
                show: true,
                position: 'inside',
                formatter: (params) => params.value.toFixed(2) + '%'
              }
            }
          ]
        }

        if (!myChart) {
          myChart = echarts.init(chartRef.value)
        } else {
          myChart.clear()
        }
        myChart.setOption(option)
      } catch (e) {
        console.error('图表加载失败', e)
      }
    }

    // 监听窗口大小变化
    const resizeChart = () => {
      if (myChart) myChart.resize()
    }

    // 自动刷新（每60秒）
    let refreshInterval = null
    const startAutoRefresh = () => {
      refreshInterval = setInterval(fetchHotStocks, 60000)
    }

    onMounted(() => {
      fetchStatus()
      fetchHotStocks()
      window.addEventListener('resize', resizeChart)
      startAutoRefresh()
    })

    onUnmounted(() => {
      window.removeEventListener('resize', resizeChart)
      if (refreshInterval) clearInterval(refreshInterval)
      if (myChart) myChart.dispose()
    })

    return {
      autoEnabled,
      loading,
      lastTrigger,
      chartRef,
      currentSort,
      sortLabels,
      toggleAuto,
      triggerManual,
      onSortChange
    }
  }
}
</script>

<style scoped>
/* 新增样式 */
.sort-select {
  padding: 6px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: white;
  font-size: 14px;
  color: #334155;
  cursor: pointer;
}

.sort-label {
  color: #3b82f6;
  font-weight: 500;
}

/* 其他原有样式保持不变 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
  background-color: #f8fafc;
  color: #334155;
  overflow: hidden;
}

.dashboard {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 0;
  background: linear-gradient(135deg, #f0f4f8 0%, #e2e8f0 100%);
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  height: 60px;
  background: white;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
  z-index: 10;
}

.header h1 {
  font-size: 20px;
  font-weight: 600;
  color: #1e293b;
}

.controls {
  display: flex;
  gap: 16px;
  align-items: center;
}

.status-badge {
  font-size: 14px;
  font-weight: 500;
}

.status-badge.active {
  color: #10b981;
}

.status-badge:not(.active) {
  color: #ef4444;
}

.main {
  display: flex;
  flex: 1;
  padding: 24px;
  gap: 24px;
}

.control-panel {
  width: 30%;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.panel-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.panel-card h3 {
  font-size: 16px;
  margin-bottom: 16px;
  color: #334155;
  font-weight: 600;
}

.status-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 14px;
}

.status-on { color: #10b981; font-weight: 500; }
.status-off { color: #ef4444; font-weight: 500; }

.chart-panel {
  width: 70%;
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
}

.chart-header {
  margin-bottom: 16px;
}

.chart-header h3 {
  font-size: 18px;
  color: #1e293b;
  font-weight: 600;
}

.subtitle {
  font-size: 12px;
  color: #64748b;
  margin-top: 4px;
}

.chart-container {
  flex: 1;
  min-height: 0;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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

.btn-secondary:hover:not(:disabled) {
  background: #cbd5e1;
}

.btn-block {
  width: 100%;
  padding: 10px;
  font-weight: 500;
}
</style>