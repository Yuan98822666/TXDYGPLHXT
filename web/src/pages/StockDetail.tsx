// src/pages/StockDetail.tsx - 股票详情页（带图表）
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Legend } from 'recharts'

// 模拟数据 - 股价与资金流入时序图
const priceAndFlowData = [
  { time: '09:30', price: 100.5, inflow: 1200 },
  { time: '09:45', price: 101.2, inflow: 2500 },
  { time: '10:00', price: 102.0, inflow: 3800 },
  { time: '10:15', price: 101.8, inflow: 1500 },
  { time: '10:30', price: 102.5, inflow: 4200 },
  { time: '10:45', price: 103.1, inflow: 5600 },
  { time: '11:00', price: 103.5, inflow: 3200 },
  { time: '11:30', price: 104.0, inflow: 4800 },
  { time: '13:00', price: 104.2, inflow: 2100 },
  { time: '13:30', price: 104.8, inflow: 3900 },
  { time: '14:00', price: 105.2, inflow: 5200 },
  { time: '14:30', price: 105.0, inflow: 2800 },
  { time: '15:00', price: 105.5, inflow: 4100 },
]

// 模拟数据 - 单超大/大/中/小单流入
const orderSizeData = [
  { name: '09:30', 超大单: 800, 大单: 400, 中单: 200, 小单: -200 },
  { name: '09:45', 超大单: 1500, 大单: 800, 中单: 300, 小单: -100 },
  { name: '10:00', 超大单: 2200, 大单: 1200, 中单: 500, 小单: -100 },
  { name: '10:30', 超大单: 2800, 大单: 1000, 中单: 600, 小单: -200 },
  { name: '11:00', 超大单: 1800, 大单: 900, 中单: 400, 小单: 100 },
  { name: '11:30', 超大单: 2500, 大单: 1500, 中单: 700, 小单: 100 },
  { name: '13:00', 超大单: 1200, 大单: 600, 中单: 300, 小单: 0 },
  { name: '13:30', 超大单: 2100, 大单: 1200, 中单: 500, 小单: 100 },
  { name: '14:00', 超大单: 3000, 大单: 1500, 中单: 600, 小单: 100 },
  { name: '14:30', 超大单: 1600, 大单: 800, 中单: 300, 小单: 100 },
  { name: '15:00', 超大单: 2400, 大单: 1200, 中单: 400, 小单: 100 },
]

// 异常行为记录
function AnomalyRecord({ records }: { records: string[] }) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">⚠️ 异常行为记录</h3>
      {records.length === 0 ? (
        <div className="text-gray-500">暂无异常记录</div>
      ) : (
        <ul className="space-y-2">
          {records.map((record, i) => (
            <li key={i} className="text-red-600 text-sm">• {record}</li>
          ))}
        </ul>
      )}
    </div>
  )
}

// 股票评价
function StockRating({ rating }: { rating: { score: number; label: string; reason: string } }) {
  const scoreColor = rating.score >= 80 ? 'text-green-600' : rating.score >= 60 ? 'text-yellow-600' : 'text-red-600'
  
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">📈 股票评价</h3>
      <div className="flex items-center gap-4 mb-4">
        <div className={`text-4xl font-bold ${scoreColor}`}>{rating.score}</div>
        <div className="text-xl font-medium">{rating.label}</div>
      </div>
      <div className="text-gray-600 text-sm">{rating.reason}</div>
    </div>
  )
}

// 决策建议
function Decision({ decision }: { decision: string }) {
  const getBgColor = () => {
    if (decision.includes('买入') || decision.includes('增持')) return 'bg-green-50 border-green-500'
    if (decision.includes('卖出') || decision.includes('减持')) return 'bg-red-50 border-red-500'
    return 'bg-gray-50 border-gray-500'
  }
  
  return (
    <div className={`rounded-lg border p-6 ${getBgColor()}`}>
      <h3 className="text-lg font-semibold mb-2">💡 决策建议</h3>
      <div className="text-xl font-bold">{decision}</div>
    </div>
  )
}

// 股价+资金流入 时序图
function PriceFlowChart() {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">📊 股价与资金流入走势</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={priceAndFlowData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="time" />
          <YAxis yAxisId="left" />
          <YAxis yAxisId="right" orientation="right" />
          <Tooltip />
          <Legend />
          <Line yAxisId="left" type="monotone" dataKey="price" stroke="#2563eb" name="股价(元)" strokeWidth={2} />
          <Line yAxisId="right" type="monotone" dataKey="inflow" stroke="#16a34a" name="资金流入(万)" strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

// 单超大/大/中/小单流入柱状图
function OrderSizeChart() {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">📊 超大/大/中/小单流入分布</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={orderSizeData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey="超大单" stackId="a" fill="#7c3aed" />
          <Bar dataKey="大单" stackId="a" fill="#2563eb" />
          <Bar dataKey="中单" stackId="a" fill="#f59e0b" />
          <Bar dataKey="小单" stackId="a" fill="#6b7280" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

// 主页面
export default function StockDetail() {
  // 模拟数据
  const anomalies = ['2026-04-03 10:30 大单砸盘后迅速拉回', '2026-04-02 14:00 资金大幅流出']
  const rating = { score: 82, label: '推荐买入', reason: '资金持续净流入，股价走势稳健，基本面良好' }
  const decision = '建议买入：短期有资金推动，可适度参与'

  return (
    <div className="min-h-screen bg-gray-100">
      {/* 顶部导航 */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <a href="/" className="text-blue-500 hover:underline">← 返回</a>
            <h1 className="text-2xl font-bold text-gray-800">600519 贵州茅台</h1>
            <span className="text-green-600 text-xl">¥105.50 +2.35%</span>
          </div>
          <div className="text-gray-500">上证所主板</div>
        </div>
      </header>

      {/* 主内容区 */}
      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* 评价与决策 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <StockRating rating={rating} />
          <Decision decision={decision} />
          <AnomalyRecord records={anomalies} />
        </div>

        {/* 图表 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <PriceFlowChart />
          <OrderSizeChart />
        </div>
      </main>
    </div>
  )
}