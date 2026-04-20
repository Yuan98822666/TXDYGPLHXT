// src/pages/StockMarkManagement.tsx - 股票标记管理页面
import { useState, useEffect, useCallback } from 'react'
import {
  getStockMarkList,
  getMarkStats,
  searchStocks,
  addStockMark,
  toggleStockMark,
  batchAddStockMark,
  batchRemoveStockMark,
  clearAllMarks,
  batchMarkByCondition
} from '../api'

// 类型定义
interface Stock {
  code: string
  name: string
  secid: string
  exchange: string
  stock_type: string
  stock_risk: number
  stock_imp: number
  pdate_time: string
}

interface Stats {
  total_stocks: number
  marked_count: number
  unmarked_count: number
  risk_count: number
  by_type: Record<string, { total: number; marked: number }>
}

// 板块类型映射
const STOCK_TYPE_MAP: Record<string, string> = {
  'SH_ZB': '沪主板',
  'SZ_ZB': '深主板',
  'KCB': '科创板',
  'CYB': '创业板',
  'BJS': '北交所'
}

// 交易所映射
const EXCHANGE_MAP: Record<string, string> = {
  '1': '沪市',
  '0': '深京'
}

// 主页面
export default function StockMarkManagement() {
  // 状态
  const [stocks, setStocks] = useState<Stock[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)
  const [searchKeyword, setSearchKeyword] = useState('')
  const [searchResults, setSearchResults] = useState<Stock[]>([])
  const [showSearchDropdown, setShowSearchDropdown] = useState(false)
  
  // 筛选条件
  const [filters, setFilters] = useState({
    stock_type: '',
    stock_risk: -1, // -1 表示全部
    stock_imp: -1,  // -1 表示全部
    exchange: ''
  })
  
  // 分页
  const [page, setPage] = useState(1)
  const [pageSize] = useState(50)
  const [total, setTotal] = useState(0)
  const totalPages = Math.ceil(total / pageSize)
  
  // 批量操作
  const [selectedCodes, setSelectedCodes] = useState<Set<string>>(new Set())
  const [showBatchPanel, setShowBatchPanel] = useState(false)
  
  // 加载数据
  const loadStocks = useCallback(async () => {
    setLoading(true)
    try {
      const params: any = { page, page_size: pageSize }
      if (filters.stock_type) params.stock_type = filters.stock_type
      if (filters.stock_risk >= 0) params.stock_risk = filters.stock_risk
      if (filters.stock_imp >= 0) params.stock_imp = filters.stock_imp
      if (filters.exchange) params.exchange = filters.exchange
      
      const data = await getStockMarkList(params)
      setStocks(data.data)
      setTotal(data.total)
    } catch (err) {
      console.error('加载股票列表失败:', err)
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, filters])
  
  const loadStats = async () => {
    try {
      const data = await getMarkStats()
      setStats(data)
    } catch (err) {
      console.error('加载统计失败:', err)
    }
  }
  
  useEffect(() => {
    loadStocks()
    loadStats()
  }, [loadStocks])
  
  // 搜索股票
  const handleSearch = async (keyword: string) => {
    setSearchKeyword(keyword)
    if (keyword.length < 1) {
      setSearchResults([])
      setShowSearchDropdown(false)
      return
    }
    try {
      const data = await searchStocks(keyword, 10)
      setSearchResults(data.data)
      setShowSearchDropdown(true)
    } catch (err) {
      console.error('搜索失败:', err)
    }
  }
  
  // 快速添加关注
  const handleQuickAdd = async (code: string) => {
    try {
      await addStockMark(code)
      loadStocks()
      loadStats()
      setSearchKeyword('')
      setSearchResults([])
      setShowSearchDropdown(false)
    } catch (err) {
      console.error('添加失败:', err)
    }
  }
  
  // 切换关注状态
  const handleToggle = async (code: string) => {
    try {
      await toggleStockMark(code)
      loadStocks()
      loadStats()
    } catch (err) {
      console.error('切换失败:', err)
    }
  }
  
  // 批量操作
  const handleSelectAll = () => {
    if (selectedCodes.size === stocks.length) {
      setSelectedCodes(new Set())
    } else {
      setSelectedCodes(new Set(stocks.map(s => s.code)))
    }
  }
  
  const handleSelect = (code: string) => {
    const newSet = new Set(selectedCodes)
    if (newSet.has(code)) {
      newSet.delete(code)
    } else {
      newSet.add(code)
    }
    setSelectedCodes(newSet)
  }
  
  const handleBatchAdd = async () => {
    if (selectedCodes.size === 0) return
    try {
      await batchAddStockMark(Array.from(selectedCodes))
      setSelectedCodes(new Set())
      loadStocks()
      loadStats()
    } catch (err) {
      console.error('批量添加失败:', err)
    }
  }
  
  const handleBatchRemove = async () => {
    if (selectedCodes.size === 0) return
    try {
      await batchRemoveStockMark(Array.from(selectedCodes))
      setSelectedCodes(new Set())
      loadStocks()
      loadStats()
    } catch (err) {
      console.error('批量移除失败:', err)
    }
  }
  
  const handleClearAll = async () => {
    if (!confirm('确定要清空所有关注吗？此操作不可撤销！')) return
    try {
      await clearAllMarks()
      loadStocks()
      loadStats()
    } catch (err) {
      console.error('清空失败:', err)
    }
  }
  
  // 按条件批量标记
  const handleMarkByType = async (stockType: string, imp: number) => {
    try {
      await batchMarkByCondition({ stock_type: stockType, imp })
      loadStocks()
      loadStats()
    } catch (err) {
      console.error('批量标记失败:', err)
    }
  }

  return (
    <main className="max-w-7xl mx-auto px-4 py-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">⭐ 股票标记管理</h1>
          <p className="text-gray-500 text-sm mt-1">管理关注股票，采集时仅采集标记为关注的股票</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowBatchPanel(!showBatchPanel)}
            className="px-4 py-2 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 flex items-center gap-2"
          >
            <span>📦</span>
            <span>批量操作</span>
          </button>
          <button
            onClick={handleClearAll}
            className="px-4 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 flex items-center gap-2"
          >
            <span>🗑️</span>
            <span>清空全部</span>
          </button>
        </div>
      </div>
      
      {/* 统计卡片 */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-gray-500 text-sm">股票总数</div>
            <div className="text-2xl font-bold text-gray-800 mt-1">{stats.total_stocks.toLocaleString()}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-gray-500 text-sm">已关注</div>
            <div className="text-2xl font-bold text-amber-600 mt-1">{stats.marked_count.toLocaleString()}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-gray-500 text-sm">未关注</div>
            <div className="text-2xl font-bold text-gray-400 mt-1">{stats.unmarked_count.toLocaleString()}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-gray-500 text-sm">风险股</div>
            <div className="text-2xl font-bold text-red-500 mt-1">{stats.risk_count.toLocaleString()}</div>
          </div>
        </div>
      )}
      
      {/* 批量操作面板 */}
      {showBatchPanel && (
        <div className="bg-slate-50 rounded-lg p-4 mb-6 border border-slate-200">
          <div className="flex items-center justify-between mb-3">
            <span className="font-medium text-slate-700">📦 快速批量标记</span>
            <button onClick={() => setShowBatchPanel(false)} className="text-slate-400 hover:text-slate-600">✕</button>
          </div>
          <div className="flex flex-wrap gap-3">
            <span className="text-sm text-slate-500 self-center">按板块类型：</span>
            {Object.entries(STOCK_TYPE_MAP).map(([type, name]) => (
              <button
                key={type}
                onClick={() => handleMarkByType(type, 1)}
                className="px-3 py-1.5 bg-amber-100 text-amber-700 rounded hover:bg-amber-200 text-sm"
              >
                关注全部{name}
              </button>
            ))}
            <span className="text-slate-300 self-center">|</span>
            <button
              onClick={() => batchMarkByCondition({ stock_risk: 0, imp: 0 })}
              className="px-3 py-1.5 bg-red-100 text-red-700 rounded hover:bg-red-200 text-sm"
            >
              取消全部风险股关注
            </button>
          </div>
        </div>
      )}
      
      {/* 工具栏 */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex flex-wrap gap-4 items-center">
          {/* 搜索框 */}
          <div className="relative flex-1 min-w-[200px] max-w-[400px]">
            <input
              type="text"
              value={searchKeyword}
              onChange={(e) => handleSearch(e.target.value)}
              placeholder="搜索股票代码或名称..."
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            {showSearchDropdown && searchResults.length > 0 && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-10 max-h-64 overflow-y-auto">
                {searchResults.map((stock) => (
                  <div
                    key={stock.code}
                    className="flex items-center justify-between px-4 py-2 hover:bg-gray-50 cursor-pointer"
                    onClick={() => handleQuickAdd(stock.code)}
                  >
                    <div>
                      <span className="font-mono text-sm">{stock.code}</span>
                      <span className="ml-2 text-gray-600">{stock.name}</span>
                    </div>
                    <span className={`text-xs px-2 py-0.5 rounded ${stock.stock_imp === 1 ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-500'}`}>
                      {stock.stock_imp === 1 ? '已关注' : '未关注'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
          
          {/* 筛选器 */}
          <select
            value={filters.stock_imp}
            onChange={(e) => setFilters({ ...filters, stock_imp: Number(e.target.value) })}
            className="px-3 py-2 border border-gray-300 rounded-lg"
          >
            <option value={-1}>全部状态</option>
            <option value={1}>已关注</option>
            <option value={0}>未关注</option>
          </select>
          
          <select
            value={filters.stock_type}
            onChange={(e) => setFilters({ ...filters, stock_type: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg"
          >
            <option value="">全部板块</option>
            {Object.entries(STOCK_TYPE_MAP).map(([type, name]) => (
              <option key={type} value={type}>{name}</option>
            ))}
          </select>
          
          <select
            value={filters.stock_risk}
            onChange={(e) => setFilters({ ...filters, stock_risk: Number(e.target.value) })}
            className="px-3 py-2 border border-gray-300 rounded-lg"
          >
            <option value={-1}>全部风险</option>
            <option value={1}>正常</option>
            <option value={0}>有风险</option>
          </select>
          
          <select
            value={filters.exchange}
            onChange={(e) => setFilters({ ...filters, exchange: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg"
          >
            <option value="">全部交易所</option>
            <option value="1">沪市</option>
            <option value="0">深京</option>
          </select>
          
          <button
            onClick={() => setFilters({ stock_type: '', stock_risk: -1, stock_imp: -1, exchange: '' })}
            className="px-3 py-2 text-gray-500 hover:text-gray-700"
          >
            重置
          </button>
        </div>
      </div>
      
      {/* 批量操作栏 */}
      {selectedCodes.size > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4 flex items-center justify-between">
          <span className="text-amber-700">
            已选择 <strong>{selectedCodes.size}</strong> 只股票
          </span>
          <div className="flex gap-2">
            <button
              onClick={handleBatchAdd}
              className="px-3 py-1.5 bg-amber-500 text-white rounded hover:bg-amber-600 text-sm"
            >
              批量关注
            </button>
            <button
              onClick={handleBatchRemove}
              className="px-3 py-1.5 bg-gray-500 text-white rounded hover:bg-gray-600 text-sm"
            >
              批量取消
            </button>
            <button
              onClick={() => setSelectedCodes(new Set())}
              className="px-3 py-1.5 text-gray-500 hover:text-gray-700 text-sm"
            >
              取消选择
            </button>
          </div>
        </div>
      )}
      
      {/* 股票列表 */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {loading ? (
          <div className="text-center py-12 text-gray-500">加载中...</div>
        ) : (
          <>
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-4 py-3 text-left">
                    <input
                      type="checkbox"
                      checked={selectedCodes.size === stocks.length && stocks.length > 0}
                      onChange={handleSelectAll}
                      className="rounded"
                    />
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">代码</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">名称</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">板块</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">交易所</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">风险</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-gray-500">关注</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-gray-500">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {stocks.map((stock) => (
                  <tr key={stock.code} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selectedCodes.has(stock.code)}
                        onChange={() => handleSelect(stock.code)}
                        className="rounded"
                      />
                    </td>
                    <td className="px-4 py-3 font-mono text-sm">{stock.code}</td>
                    <td className="px-4 py-3 text-sm font-medium">{stock.name}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs">
                        {STOCK_TYPE_MAP[stock.stock_type] || stock.stock_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {EXCHANGE_MAP[stock.exchange] || stock.exchange}
                    </td>
                    <td className="px-4 py-3">
                      {stock.stock_risk === 0 ? (
                        <span className="px-2 py-1 bg-red-50 text-red-600 rounded text-xs">风险</span>
                      ) : (
                        <span className="px-2 py-1 bg-green-50 text-green-600 rounded text-xs">正常</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => handleToggle(stock.code)}
                        className={`w-8 h-8 rounded-full flex items-center justify-center transition-colors ${
                          stock.stock_imp === 1
                            ? 'bg-amber-100 text-amber-600 hover:bg-amber-200'
                            : 'bg-gray-100 text-gray-400 hover:bg-gray-200'
                        }`}
                      >
                        {stock.stock_imp === 1 ? '⭐' : '☆'}
                      </button>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => handleToggle(stock.code)}
                        className={`px-3 py-1 rounded text-sm ${
                          stock.stock_imp === 1
                            ? 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                            : 'bg-amber-500 text-white hover:bg-amber-600'
                        }`}
                      >
                        {stock.stock_imp === 1 ? '取消关注' : '添加关注'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            
            {/* 分页 */}
            <div className="px-4 py-3 bg-gray-50 border-t flex items-center justify-between">
              <div className="text-sm text-gray-500">
                共 {total.toLocaleString()} 只股票，当前显示第 {(page - 1) * pageSize + 1}-{Math.min(page * pageSize, total)} 只
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-1 border rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  上一页
                </button>
                <span className="px-3 py-1 text-gray-500">
                  {page} / {totalPages || 1}
                </span>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="px-3 py-1 border rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  下一页
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </main>
  )
}
