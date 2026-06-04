// src/pages/BlockFlow.tsx - 板块资金走向页面
import { useState, useEffect, useMemo, useCallback } from 'react'
import ReactECharts from 'echarts-for-react'

// API 基础配置
const API_BASE = 'http://localhost:8084/api/block-flow'

// 数据接口
interface BlockTop5Item {
  code: string
  name: string
  inflow: number
  speed: number
}

interface BlockTypeStats {
  total: number
  active: number
  top5: BlockTop5Item[]
}

interface BlockStatsResponse {
  date: string
  concept: BlockTypeStats
  industry: BlockTypeStats
}

interface BlockSeriesItem {
  code: string
  name: string
  type: 'GN' | 'HY'
  current_flow: number
  series: number[]
  speed: number
}

interface BlockTimeSeriesResponse {
  date: string
  time_labels: string[]
  blocks: BlockSeriesItem[]
}

interface StockData {
  stock_code: string
  stock_name: string
  price: number
  change_percent: number
  zl_inflow: number
  blocks: string[]
}

// 图表数据集接口
interface ChartDataset {
  name: string
  data: number[]
  color: string
  lineStyle: {
    width: number
    type: 'solid' | 'dashed'
  }
}

// 顶部统计卡片
function StatCard({ title, value, subtext, color }: {
  title: string
  value: string
  subtext: string
  color: string
}) {
  return (
    <div className="bg-slate-800/50 backdrop-blur rounded-xl p-4 border border-slate-700">
      <div className="text-sm text-slate-400 mb-1">{title}</div>
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      <div className="text-xs text-slate-500 mt-1">{subtext}</div>
    </div>
  )
}

// 板块标签
function BlockTag({ name, onClick, isActive, color }: {
  name: string
  onClick: () => void
  isActive: boolean
  color: string
}) {
  const colorMap: Record<string, string> = {
    blue: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    purple: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    pink: 'bg-pink-500/20 text-pink-400 border-pink-500/30',
    green: 'bg-green-500/20 text-green-400 border-green-500/30',
    orange: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  }

  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center px-2 py-1 rounded text-xs border transition-all ${
        isActive ? 'ring-2 ring-offset-1 ring-offset-slate-900 ring-blue-500 ' + colorMap[color] : colorMap[color]
      }`}
    >
      {name}
    </button>
  )
}

export default function BlockFlow() {
  const [loading, setLoading] = useState(true)
  const [selectedDate, setSelectedDate] = useState<string>(() => {
    const today = new Date()
    return today.toISOString().split('T')[0]
  })
  const [selectedBlock, setSelectedBlock] = useState<string | null>(null)
  const [searchKeyword, setSearchKeyword] = useState('')
  const [sortBy, setSortBy] = useState<'flow' | 'change' | 'marketCap'>('flow')
  const [currentPage, setCurrentPage] = useState(1)
  const pageSize = 20

  // API 数据
  const [blockStats, setBlockStats] = useState<BlockStatsResponse | null>(null)
  const [gnTimeSeries, setGnTimeSeries] = useState<BlockTimeSeriesResponse | null>(null)
  const [hyTimeSeries, setHyTimeSeries] = useState<BlockTimeSeriesResponse | null>(null)
  const [stocks, setStocks] = useState<StockData[]>([])

  // 颜色配置
  const colors = ['#3b82f6', '#8b5cf6', '#d946ef', '#ec4899', '#f43f5e', '#ef4444', '#f97316', '#f59e0b', '#eab308', '#84cc16', '#22c55e', '#10b981', '#14b8a6', '#06b6d4', '#0ea5e9']

  // 获取统计数据
  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/stats?query_date=${selectedDate}`)
      if (res.ok) {
        const data = await res.json()
        setBlockStats(data)
      }
    } catch (e) {
      console.error('获取统计数据失败:', e)
    }
  }, [selectedDate])

  // 获取时间序列数据
  const fetchTimeSeries = useCallback(async () => {
    try {
      const [gnRes, hyRes] = await Promise.all([
        fetch(`${API_BASE}/timeseries?block_type=GN&query_date=${selectedDate}`),
        fetch(`${API_BASE}/timeseries?block_type=HY&query_date=${selectedDate}`)
      ])
      
      if (gnRes.ok) {
        const gnData = await gnRes.json()
        setGnTimeSeries(gnData)
      }
      if (hyRes.ok) {
        const hyData = await hyRes.json()
        setHyTimeSeries(hyData)
      }
    } catch (e) {
      console.error('获取时间序列数据失败:', e)
    }
  }, [selectedDate])

  // 获取股票列表
  const fetchStocks = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/stocks?query_date=${selectedDate}`)
      if (res.ok) {
        const data = await res.json()
        setStocks(data.stocks || [])
      } else {
        setStocks([])
      }
    } catch (e) {
      console.error('获取股票列表失败:', e)
      setStocks([])
    }
  }, [selectedDate])

  // 初始加载和定时刷新
  useEffect(() => {
    const loadData = async () => {
      setLoading(true)
      await Promise.all([fetchStats(), fetchTimeSeries(), fetchStocks()])
      setLoading(false)
    }
    
    loadData()
    
    // 每20秒刷新
    const interval = setInterval(() => {
      fetchStats()
      fetchTimeSeries()
    }, 20000)
    
    return () => clearInterval(interval)
  }, [fetchStats, fetchTimeSeries, fetchStocks])

  // 金额转换：元 -> 万元，四舍五入
  const toWan = (value: number): number => {
    return Math.round(value / 10000)
  }

  // 处理图表数据
  const processChartData = (timeSeries: BlockTimeSeriesResponse | null): { labels: string[], datasets: ChartDataset[] } => {
    if (!timeSeries || !timeSeries.blocks.length) {
      return { labels: [], datasets: [] }
    }

    // 按资金流入和增速排序取Top10
    const byFlow = [...timeSeries.blocks].sort((a, b) => b.current_flow - a.current_flow).slice(0, 10)
    const bySpeed = [...timeSeries.blocks].sort((a, b) => b.speed - a.speed).slice(0, 10)
    
    // 合并并去重
    const merged = new Map<string, BlockSeriesItem & { _flowTop?: boolean; _speedTop?: boolean }>()
    byFlow.forEach(b => merged.set(b.code, { ...b, _flowTop: true }))
    bySpeed.forEach(b => {
      if (merged.has(b.code)) {
        merged.set(b.code, { ...merged.get(b.code)!, _speedTop: true })
      } else {
        merged.set(b.code, { ...b, _speedTop: true })
      }
    })

    const datasets: ChartDataset[] = Array.from(merged.values()).map((block, i) => {
      const isFlowTop = block._flowTop
      const isSpeedTop = block._speedTop
      const isBoth = isFlowTop && isSpeedTop
      
      return {
        name: block.name,
        data: block.series.map(v => toWan(v)),
        color: colors[i % colors.length],
        lineStyle: {
          width: isBoth ? 4 : 2,
          type: isSpeedTop && !isFlowTop ? 'dashed' : 'solid',
        },
      }
    })

    return {
      labels: timeSeries.time_labels,
      datasets
    }
  }

  const gnChartData = useMemo(() => processChartData(gnTimeSeries), [gnTimeSeries])
  const hyChartData = useMemo(() => processChartData(hyTimeSeries), [hyTimeSeries])

  // ECharts 配置
  const getChartOption = (data: { labels: string[], datasets: ChartDataset[] }, title: string) => {
    return {
      backgroundColor: 'transparent',
      title: {
        text: title,
        left: 'center',
        textStyle: { color: '#94a3b8', fontSize: 14 }
      },
      grid: { left: 60, right: 120, top: 40, bottom: 30 },
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(15, 23, 42, 0.9)',
        borderColor: 'rgba(255,255,255,0.1)',
        textStyle: { color: '#e2e8f0' },
        formatter: (params: any[]) => {
          let html = `<div style="font-weight:bold;margin-bottom:5px">${params[0].axisValue}</div>`
          params.forEach(p => {
            html += `<div style="display:flex;align-items:center;gap:5px">
              <span style="display:inline-block;width:10px;height:10px;background:${p.color};border-radius:50%"></span>
              <span>${p.seriesName}: ${p.value?.toLocaleString()}万</span>
            </div>`
          })
          return html
        },
      },
      legend: {
        type: 'scroll',
        top: 30,
        textStyle: { color: '#94a3b8', fontSize: 11 },
        pageIconColor: '#64748b',
        pageTextStyle: { color: '#64748b' },
      },
      xAxis: {
        type: 'category',
        data: data.labels,
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
        axisLabel: { color: '#64748b', fontSize: 10 },
        splitLine: { show: false },
      },
      yAxis: {
        type: 'value',
        name: '净流入(万)',
        nameTextStyle: { color: '#64748b', fontSize: 10 },
        axisLine: { show: false },
        axisLabel: { color: '#64748b', fontSize: 10, formatter: '{value}万' },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
      },
      series: data.datasets.map((ds) => ({
        name: ds.name,
        type: 'line',
        data: ds.data,
        smooth: true,
        symbol: 'none',
        lineStyle: ds.lineStyle,
        itemStyle: { color: ds.color },
        emphasis: { focus: 'series' },
        endLabel: {
          show: true,
          formatter: '{a}: {c}万',
          color: ds.color,
          fontSize: 11,
          distance: 8,
        },
        labelLayout: {
          hideOverlap: true,
          moveOverlap: 'shiftY',
        },
      })),
    }
  }

  // 筛选和排序股票
  const filteredStocks = useMemo(() => {
    let result = stocks

    // 搜索筛选
    if (searchKeyword) {
      const kw = searchKeyword.toLowerCase()
      result = result.filter(s =>
        s.stock_code.toLowerCase().includes(kw) ||
        s.stock_name.toLowerCase().includes(kw)
      )
    }

    // 板块筛选
    if (selectedBlock) {
      result = result.filter(s => s.blocks.includes(selectedBlock))
    }

    // 排序
    result = [...result].sort((a, b) => {
      if (sortBy === 'flow') return b.zl_inflow - a.zl_inflow
      if (sortBy === 'change') return b.change_percent - a.change_percent
      return b.price - a.price
    })

    return result
  }, [stocks, searchKeyword, selectedBlock, sortBy])

  // 分页
  const totalPages = Math.ceil(filteredStocks.length / pageSize)
  const pageStocks = filteredStocks.slice((currentPage - 1) * pageSize, currentPage * pageSize)

  const tagColors = ['blue', 'purple', 'pink', 'green', 'orange']

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-slate-400">加载中...</div>
      </div>
    )
  }

  const stats = blockStats || {
    date: selectedDate,
    concept: { total: 0, active: 0, top5: [] },
    industry: { total: 0, active: 0, top5: [] }
  }

  // 合并 Top5 用于显示
  const allTop5 = [
    ...stats.concept.top5.map(b => ({ ...b, type: 'GN' as const })),
    ...stats.industry.top5.map(b => ({ ...b, type: 'HY' as const }))
  ].sort((a, b) => b.inflow - a.inflow).slice(0, 5)

  return (
    <div className="min-h-screen bg-slate-900 p-6">
      {/* 日期选择器 */}
      <div className="mb-6 flex items-center gap-4">
        <h1 className="text-2xl font-bold text-white">板块资金走向</h1>
        <div className="flex items-center gap-2">
          <label className="text-slate-400 text-sm">选择日期:</label>
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
          />
        </div>
        <div className="text-xs text-slate-500">
          每20秒自动刷新
        </div>
      </div>

      {/* 顶部统计栏 */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4 mb-6">
        <StatCard
          title="概念活跃"
          value={`${stats.concept.active}/${stats.concept.total}`}
          subtext="净流入>0的板块"
          color="text-blue-400"
        />
        <StatCard
          title="行业活跃"
          value={`${stats.industry.active}/${stats.industry.total}`}
          subtext="净流入>0的板块"
          color="text-purple-400"
        />
        {allTop5.map((block, i) => (
          <StatCard
            key={block.code}
            title={`Top${i + 1} ${block.type === 'GN' ? '概念' : '行业'}`}
            value={block.name}
            subtext={`${block.inflow > 0 ? '+' : ''}${block.inflow.toFixed(0)}万`}
            color={block.inflow > 0 ? 'text-green-400' : 'text-red-400'}
          />
        ))}
      </div>

      {/* 双折线图 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div className="bg-slate-800/50 backdrop-blur rounded-xl p-4 border border-slate-700">
          <ReactECharts
            option={getChartOption(gnChartData, '概念板块资金流向')}
            style={{ height: '650px' }}
            theme="dark"
          />
        </div>
        <div className="bg-slate-800/50 backdrop-blur rounded-xl p-4 border border-slate-700">
          <ReactECharts
            option={getChartOption(hyChartData, '行业板块资金流向')}
            style={{ height: '650px' }}
            theme="dark"
          />
        </div>
      </div>

      {/* 股票列表 */}
      <div className="bg-slate-800/50 backdrop-blur rounded-xl border border-slate-700 overflow-hidden">
        {/* 筛选栏 */}
        <div className="p-4 border-b border-slate-700 flex flex-wrap gap-4 items-center">
          <input
            type="text"
            placeholder="搜索股票代码/名称"
            value={searchKeyword}
            onChange={(e) => { setSearchKeyword(e.target.value); setCurrentPage(1) }}
            className="bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white text-sm w-64 focus:outline-none focus:border-blue-500"
          />
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
            className="bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
          >
            <option value="flow">按主力净流入排序</option>
            <option value="change">按涨跌幅排序</option>
            <option value="marketCap">按市值排序</option>
          </select>
          {selectedBlock && (
            <button
              onClick={() => setSelectedBlock(null)}
              className="text-sm text-blue-400 hover:text-blue-300"
            >
              清除筛选
            </button>
          )}
        </div>

        {/* 表格 */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-900/50">
              <tr>
                <th className="px-2 py-3 text-left text-xs font-medium text-slate-400 w-[80px]">代码</th>
                <th className="px-2 py-3 text-left text-xs font-medium text-slate-400 w-[100px]">名称</th>
                <th className="px-2 py-3 text-right text-xs font-medium text-slate-400 w-[60px]">最新价</th>
                <th className="px-2 py-3 text-right text-xs font-medium text-slate-400 w-[60px]">涨跌幅</th>
                <th className="px-2 py-3 text-right text-xs font-medium text-slate-400 w-[120px]">主力净流入</th>
                <th className="px-2 py-3 text-left text-xs font-medium text-slate-400">所属板块</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {pageStocks.map((stock) => (
                <tr key={stock.stock_code} className="hover:bg-slate-800/30">
                  <td className="px-2 py-3 text-sm text-slate-300">{stock.stock_code}</td>
                  <td className="px-2 py-3 text-sm text-white font-medium">{stock.stock_name}</td>
                  <td className="px-2 py-3 text-sm text-slate-300 text-right">{stock.price.toFixed(2)}</td>
                  <td className={`px-2 py-3 text-sm text-right ${stock.change_percent > 0 ? 'text-red-400' : stock.change_percent < 0 ? 'text-green-400' : 'text-slate-300'}`}>
                    {stock.change_percent > 0 ? '+' : ''}{stock.change_percent.toFixed(2)}%
                  </td>
                  <td className={`px-2 py-3 text-sm text-right ${stock.zl_inflow > 0 ? 'text-red-400' : stock.zl_inflow < 0 ? 'text-green-400' : 'text-slate-300'}`}>
                    {stock.zl_inflow > 0 ? '+' : ''}{(stock.zl_inflow / 100000000).toFixed(2)}亿
                  </td>
                  <td className="px-2 py-3">
                    <div className="flex flex-wrap gap-1">
                      {stock.blocks.map((block, i) => (
                        <BlockTag
                          key={block}
                          name={block}
                          color={tagColors[i % tagColors.length]}
                          isActive={selectedBlock === block}
                          onClick={() => setSelectedBlock(selectedBlock === block ? null : block)}
                        />
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* 分页 */}
        <div className="p-4 border-t border-slate-700 flex items-center justify-between">
          <div className="text-sm text-slate-400">
            共 {filteredStocks.length} 条，第 {currentPage}/{totalPages} 页
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1 bg-slate-700 text-white text-sm rounded disabled:opacity-50 hover:bg-slate-600"
            >
              上一页
            </button>
            <button
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="px-3 py-1 bg-slate-700 text-white text-sm rounded disabled:opacity-50 hover:bg-slate-600"
            >
              下一页
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
