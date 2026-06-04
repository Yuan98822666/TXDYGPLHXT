// src/pages/ZTPotential.tsx - 涨停潜力分析页面
import { useState, useEffect, useCallback } from 'react'

const API_BASE = 'http://localhost:8084/api/analysis/zt-potential'

// 数据接口
interface ZTPotentialItem {
  stock_code: string
  stock_name: string
  zt_potential_factor: number
  attention_factor: number
  stock_zl_inflow: number
  stock_ltsz: number
  is_leader: boolean
  is_money_leader: boolean
  is_resonance: boolean
  block_count: number
  stock_spj: number
  stock_zdf: number
}

interface ResonanceDetail {
  block_code: string
  block_name: string
  block_type: string
  is_leader: boolean
  is_money_leader: boolean
  is_resonance: boolean
  zt_potential_factor: number
  attention_factor: number
  block_importance_factor: number
}

interface StockStrengthItem {
  stock_code: string
  stock_name: string
  strength_factor: number
  leader_count: number
  money_leader_count: number
  total_blocks: number
}

interface StatsData {
  trade_date: string
  total_analyzed: number
  resonance_stock_count: number
  leader_stock_count: number
  factor_distribution: { range: string; count: number }[]
}

// 统计卡片
function StatCard({ title, value, subtext, color }: {
  title: string
  value: string | number
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

// 标签组件
function Tag({ text, color }: { text: string; color: string }) {
  const colorClasses: Record<string, string> = {
    red: 'bg-red-500/20 text-red-400 border-red-500/30',
    orange: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    green: 'bg-green-500/20 text-green-400 border-green-500/30',
    blue: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  }
  return (
    <span className={`px-2 py-0.5 rounded text-xs border ${colorClasses[color] || colorClasses.blue}`}>
      {text}
    </span>
  )
}

export default function ZTPotential() {
  const [selectedDate, setSelectedDate] = useState<string>(new Date().toISOString().split('T')[0])
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState<StatsData | null>(null)
  const [rankingData, setRankingData] = useState<ZTPotentialItem[]>([])
  const [strengthData, setStrengthData] = useState<StockStrengthItem[]>([])
  const [onlyResonance, setOnlyResonance] = useState(false)
  const [onlyLeader, setOnlyLeader] = useState(false)
  const [minFactor, setMinFactor] = useState<string>('')
  const [selectedStock, setSelectedStock] = useState<ZTPotentialItem | null>(null)
  const [resonanceDetails, setResonanceDetails] = useState<ResonanceDetail[]>([])
  const [showModal, setShowModal] = useState(false)

  // 格式化金额
  const formatMoney = (value: number) => {
    if (value >= 100000000) {
      return `${(value / 100000000).toFixed(2)}亿`
    } else if (value >= 10000) {
      return `${(value / 10000).toFixed(0)}万`
    }
    return value.toString()
  }

  // 格式化百分比
  const formatPercent = (value: number) => {
    return `${(value * 100).toFixed(3)}%`
  }

  // 加载统计数据
  const loadStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/stats?query_date=${selectedDate}`)
      const data = await res.json()
      setStats(data)
    } catch (error) {
      console.error('加载统计失败:', error)
    }
  }, [selectedDate])

  // 加载排名数据
  const loadRanking = useCallback(async () => {
    setLoading(true)
    try {
      let url = `${API_BASE}/ranking?query_date=${selectedDate}&page_size=50`
      if (onlyResonance) url += '&only_resonance=true'
      if (onlyLeader) url += '&only_leader=true'
      if (minFactor) url += `&min_factor=${minFactor}`
      
      const res = await fetch(url)
      const data = await res.json()
      setRankingData(data.data || [])
    } catch (error) {
      console.error('加载排名失败:', error)
    } finally {
      setLoading(false)
    }
  }, [selectedDate, onlyResonance, onlyLeader, minFactor])

  // 获取个股共振详情
  const loadResonanceDetail = async (stockCode: string) => {
    try {
      const res = await fetch(`${API_BASE}/stock/${stockCode}/resonance?query_date=${selectedDate}`)
      const data = await res.json()
      setResonanceDetails(data.resonance_details || [])
    } catch (error) {
      console.error('加载共振详情失败:', error)
      setResonanceDetails([])
    }
  }

  // 处理股票点击
  const handleStockClick = (item: ZTPotentialItem) => {
    setSelectedStock(item)
    loadResonanceDetail(item.stock_code)
    setShowModal(true)
  }

  // 加载强度排名
  const loadStrength = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/strength-ranking?query_date=${selectedDate}&page_size=20`)
      const data = await res.json()
      setStrengthData(data.data || [])
    } catch (error) {
      console.error('加载强度排名失败:', error)
    }
  }, [selectedDate])

  // 初始加载
  useEffect(() => {
    loadStats()
    loadRanking()
    loadStrength()
  }, [loadStats, loadRanking, loadStrength])

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <h1 className="text-2xl font-bold mb-6">涨停潜力分析</h1>
      
      {/* 顶部统计栏 */}
      {stats && (
        <div className="grid grid-cols-6 gap-4 mb-6">
          <StatCard 
            title="分析股票数" 
            value={stats.total_analyzed} 
            subtext="今日分析" 
            color="text-white"
          />
          <StatCard 
            title="共振股票" 
            value={stats.resonance_stock_count}
            subtext="与板块同向流入" 
            color="text-green-400"
          />
          <StatCard 
            title="领涨股" 
            value={stats.leader_stock_count} 
            subtext="板块涨幅第一" 
            color="text-red-400"
          />
          <StatCard 
            title="高潜力分布" 
            value={stats.factor_distribution?.find((d: {range: string, count: number}) => d.range.includes('极高'))?.count || 0} 
            subtext="极高潜力(80-100)" 
            color="text-blue-400"
          />
          <StatCard 
            title="数据日期" 
            value={stats.trade_date} 
            subtext="分析日期" 
            color="text-slate-300"
          />
        </div>
      )}

      {/* 筛选栏 */}
      <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700 mb-6">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-slate-400">日期:</span>
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="bg-slate-700 border border-slate-600 rounded px-3 py-1 text-white"
            />
          </div>
          
          <div className="flex items-center gap-2">
            <span className="text-slate-400">最小潜力因子:</span>
            <input
              type="number"
              value={minFactor}
              onChange={(e) => setMinFactor(e.target.value)}
              placeholder="如: 0.001"
              step="0.0001"
              className="bg-slate-700 border border-slate-600 rounded px-3 py-1 text-white w-32"
            />
          </div>
          
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={onlyResonance}
              onChange={(e) => setOnlyResonance(e.target.checked)}
              className="w-4 h-4"
            />
            <span className="text-slate-300">仅共振</span>
          </label>
          
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={onlyLeader}
              onChange={(e) => setOnlyLeader(e.target.checked)}
              className="w-4 h-4"
            />
            <span className="text-slate-300">仅领涨/资金龙头</span>
          </label>
          
          <button
            onClick={loadRanking}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-1 rounded transition-colors"
          >
            刷新
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* 涨停潜力排名 */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700 overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-700 bg-slate-800/80">
            <h2 className="text-lg font-semibold">涨停潜力排名</h2>
          </div>
          <div className="overflow-x-auto">
            {loading ? (
              <div className="p-8 text-center text-slate-400">加载中...</div>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-slate-800/80 text-slate-400">
                  <tr>
                    <th className="px-3 py-2 text-left">排名</th>
                    <th className="px-3 py-2 text-left">代码</th>
                    <th className="px-3 py-2 text-left">名称</th>
                    <th className="px-3 py-2 text-right">最新价</th>
                    <th className="px-3 py-2 text-right">涨跌幅</th>
                    <th className="px-3 py-2 text-right">潜力因子</th>
                    <th className="px-3 py-2 text-right">主力净流入</th>
                    <th className="px-3 py-2 text-center">标记</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700">
                  {rankingData.map((item, index) => (
                    <tr 
                      key={item.stock_code} 
                      className="hover:bg-slate-700/50 cursor-pointer"
                      onClick={() => handleStockClick(item)}
                    >
                      <td className="px-3 py-2 text-slate-400">{index + 1}</td>
                      <td className="px-3 py-2 font-mono">{item.stock_code}</td>
                      <td className="px-3 py-2">{item.stock_name}</td>
                      <td className="px-3 py-2 text-right">{item.stock_spj?.toFixed(2) || '-'}</td>
                      <td className="px-3 py-2 text-right">
                        <span className={item.stock_zdf > 0 ? 'text-red-400' : item.stock_zdf < 0 ? 'text-green-400' : 'text-slate-400'}>
                          {item.stock_zdf > 0 ? '+' : ''}{item.stock_zdf?.toFixed(2) || '-'}%
                        </span>
                      </td>
                      <td className="px-3 py-2 text-right">
                        <span className={`
                          font-bold
                          ${item.zt_potential_factor > 0.001 ? 'text-red-400' : 
                            item.zt_potential_factor > 0.0005 ? 'text-orange-400' : 'text-green-400'}
                        `}>
                          {formatPercent(item.zt_potential_factor)}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-right">
                        <span className={item.stock_zl_inflow > 0 ? 'text-red-400' : 'text-green-400'}>
                          {item.stock_zl_inflow > 0 ? '+' : ''}{formatMoney(item.stock_zl_inflow)}
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex gap-1 justify-center">
                          {item.is_leader && <Tag text="领涨" color="red" />}
                          {item.is_money_leader && <Tag text="资金龙头" color="orange" />}
                          {item.is_resonance && <Tag text="共振" color="green" />}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* 个股强度排名 */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700 overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-700 bg-slate-800/80">
            <h2 className="text-lg font-semibold">个股强度排名</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-800/80 text-slate-400">
                <tr>
                  <th className="px-3 py-2 text-left">排名</th>
                  <th className="px-3 py-2 text-left">代码</th>
                  <th className="px-3 py-2 text-left">名称</th>
                  <th className="px-3 py-2 text-right">强度因子</th>
                  <th className="px-3 py-2 text-right">领涨次数</th>
                  <th className="px-3 py-2 text-right">资金龙头次数</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700">
                {strengthData.map((item, index) => (
                  <tr key={item.stock_code} className="hover:bg-slate-700/50">
                    <td className="px-3 py-2 text-slate-400">{index + 1}</td>
                    <td className="px-3 py-2 font-mono">{item.stock_code}</td>
                    <td className="px-3 py-2">{item.stock_name}</td>
                    <td className="px-3 py-2 text-right">
                      <span className="text-blue-400 font-bold">{item.strength_factor}</span>
                    </td>
                    <td className="px-3 py-2 text-right">{item.leader_count}</td>
                    <td className="px-3 py-2 text-right">{item.money_leader_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* 股票详情弹窗 */}
      {showModal && selectedStock && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowModal(false)}>
          <div className="bg-slate-800 rounded-xl border border-slate-700 w-full max-w-4xl max-h-[80vh] overflow-auto m-4" onClick={e => e.stopPropagation()}>
            <div className="px-6 py-4 border-b border-slate-700 flex justify-between items-center">
              <div>
                <h3 className="text-xl font-bold">{selectedStock.stock_name} ({selectedStock.stock_code})</h3>
                <div className="text-sm text-slate-400 mt-1">
                  最新价: <span className="text-white">{selectedStock.stock_spj?.toFixed(2) || '-'}</span> |
                  涨跌幅: <span className={selectedStock.stock_zdf > 0 ? 'text-red-400' : 'text-green-400'}>
                    {selectedStock.stock_zdf > 0 ? '+' : ''}{selectedStock.stock_zdf?.toFixed(2) || '-'}%
                  </span> |
                  涉及板块: {selectedStock.block_count}个
                </div>
              </div>
              <button 
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-white text-2xl"
              >
                ×
              </button>
            </div>
            <div className="p-6">
              {resonanceDetails.length === 0 ? (
                <div className="text-center text-slate-400 py-8">暂无板块共振数据</div>
              ) : (
                <table className="w-full text-sm">
                  <thead className="bg-slate-700/50 text-slate-300">
                    <tr>
                      <th className="px-4 py-2 text-left">板块名称</th>
                      <th className="px-4 py-2 text-center">类型</th>
                      <th className="px-4 py-2 text-center">领涨</th>
                      <th className="px-4 py-2 text-center">资金龙头</th>
                      <th className="px-4 py-2 text-center">共振</th>
                      <th className="px-4 py-2 text-right">潜力因子</th>
                      <th className="px-4 py-2 text-right">板块重视度</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-700">
                    {resonanceDetails.map((detail, index) => (
                      <tr key={index} className="hover:bg-slate-700/30">
                        <td className="px-4 py-3">
                          <div className="font-medium">{detail.block_name}</div>
                          <div className="text-xs text-slate-500">{detail.block_code}</div>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className={`px-2 py-0.5 rounded text-xs ${
                            detail.block_type === 'GN' ? 'bg-purple-500/20 text-purple-400' : 'bg-blue-500/20 text-blue-400'
                          }`}>
                            {detail.block_type === 'GN' ? '概念' : '行业'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          {detail.is_leader ? (
                            <span className="text-red-400 font-bold">是</span>
                          ) : (
                            <span className="text-slate-600">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-center">
                          {detail.is_money_leader ? (
                            <span className="text-orange-400 font-bold">是</span>
                          ) : (
                            <span className="text-slate-600">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-center">
                          {detail.is_resonance ? (
                            <span className="text-green-400 font-bold">是</span>
                          ) : (
                            <span className="text-slate-600">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <span className={detail.zt_potential_factor > 0.001 ? 'text-red-400' : 'text-slate-400'}>
                            {(detail.zt_potential_factor * 100).toFixed(3)}%
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          {(detail.block_importance_factor * 100).toFixed(3)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
