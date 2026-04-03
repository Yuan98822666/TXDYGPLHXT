// src/pages/Dashboard.tsx - 数据看板主页
import { useState, useEffect } from 'react'
// TODO: 等后端 API 完成后取消注释
// import { getStocks, getBlocks } from '../api'
// import type { Stock, Block } from '../api'

// 临时类型定义
interface Stock { stock_code: string; stock_name: string; stock_type: string; stock_imp: number }
interface Block { block_code: string; block_name: string; leader_stock_name?: string; money_stock_name?: string }

// 大盘资金概览卡片
function MoneyOverview() {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold mb-4">大盘资金流向</h2>
      <div className="grid grid-cols-4 gap-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-green-600">+12.8亿</div>
          <div className="text-sm text-gray-500">主力净流入</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-green-600">+5.2亿</div>
          <div className="text-sm text-gray-500">超大单净流入</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-red-500">-1.3亿</div>
          <div className="text-sm text-gray-500">大单净流入</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-gray-700">+3.1亿</div>
          <div className="text-sm text-gray-500">中小单净流入</div>
        </div>
      </div>
    </div>
  )
}

// 关注股票列表
function WatchedStocks({ stocks }: { stocks: Stock[] }) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold mb-4">关注股票 ({stocks.length}只)</h2>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b">
              <th className="text-left py-2">代码</th>
              <th className="text-left py-2">名称</th>
              <th className="text-left py-2">类型</th>
            </tr>
          </thead>
          <tbody>
            {stocks.slice(0, 10).map((stock) => (
              <tr key={stock.stock_code} className="border-b hover:bg-gray-50">
                <td className="py-2 font-mono">{stock.stock_code}</td>
                <td className="py-2">{stock.stock_name}</td>
                <td className="py-2">
                  <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">
                    {stock.stock_type}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {stocks.length > 10 && (
          <div className="text-center py-2 text-gray-500 text-sm">
            ...还有 {stocks.length - 10} 只
          </div>
        )}
      </div>
    </div>
  )
}

// 板块热点
function BlockHot({ blocks }: { blocks: Block[] }) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold mb-4">板块热点</h2>
      <div className="space-y-3">
        {blocks.slice(0, 8).map((block) => (
          <div key={block.block_code} className="flex justify-between items-center border-b pb-2">
            <div>
              <div className="font-medium">{block.block_name}</div>
              {block.leader_stock_name && (
                <div className="text-sm text-gray-500">
                  领涨: {block.leader_stock_name}
                </div>
              )}
            </div>
            {block.money_stock_name && (
              <div className="text-sm text-green-600">
                资金: {block.money_stock_name}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// 主页面
export default function Dashboard() {
  const [stocks, setStocks] = useState<Stock[]>([])
  const [blocks, setBlocks] = useState<Block[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadData() {
      try {
        // TODO: 等后端 API 完成后再连接真实数据
        // const [stockData, blockData] = await Promise.all([getStocks(), getBlocks()])
        // setStocks(stockData)
        // setBlocks(blockData)
        
        // 暂时用 mock 数据展示
        setStocks([
          { stock_code: '600519', stock_name: '贵州茅台', stock_type: '上证所主板', stock_imp: 1 },
          { stock_code: '000858', stock_name: '五粮液', stock_type: '深交所主板', stock_imp: 1 },
          { stock_code: '300750', stock_name: '宁德时代', stock_type: '创业板', stock_imp: 1 },
        ])
        setBlocks([
          { block_code: 'bk001', block_name: '白酒板块', leader_stock_name: '贵州茅台', money_stock_name: '五粮液' },
          { block_code: 'bk002', block_name: '新能源车', leader_stock_name: '比亚迪', money_stock_name: '宁德时代' },
        ])
      } catch (err) {
        setError(err instanceof Error ? err.message : '加载失败')
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-xl text-gray-600">加载中...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-xl text-red-500">错误: {error}</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* 顶部导航 */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-800">📊 股票数据看板</h1>
          <button className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
            刷新数据
          </button>
        </div>
      </header>

      {/* 主内容区 */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 左侧 - 大盘资金 + 板块热点 */}
          <div className="lg:col-span-2 space-y-6">
            <MoneyOverview />
            <BlockHot blocks={blocks} />
          </div>

          {/* 右侧 - 关注股票 */}
          <div className="lg:col-span-1">
            <WatchedStocks stocks={stocks} />
          </div>
        </div>
      </main>
    </div>
  )
}