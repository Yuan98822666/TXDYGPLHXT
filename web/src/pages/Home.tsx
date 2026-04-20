// src/pages/Home.tsx - 首页
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getTaskStatus } from '../api'

// 任务状态接口
interface TaskStatus {
  name: string
  display_name: string
  enabled: boolean
  status: 'idle' | 'running' | 'disabled'
  last_run_time?: string
  last_run_status?: string
}

// 系统状态概览卡片
function StatusCard({ title, value, icon, color }: {
  title: string
  value: string | number
  icon: string
  color: string
}) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <span className="text-gray-500 text-sm">{title}</span>
        <span className="text-2xl">{icon}</span>
      </div>
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
    </div>
  )
}

// 快捷入口卡片
function NavCard({ to, icon, title, subtitle, color, tags }: {
  to: string
  icon: string
  title: string
  subtitle: string
  color: string
  tags: string[]
}) {
  return (
    <Link 
      to={to}
      className={`block bg-gradient-to-br ${color} rounded-xl shadow-lg p-6 text-white transition-transform hover:-translate-y-1 hover:shadow-xl`}
    >
      <div className="flex items-center gap-4 mb-4">
        <span className="text-4xl">{icon}</span>
        <div>
          <div className="text-xl font-bold">{title}</div>
          <div className="text-sm opacity-80">{subtitle}</div>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {tags.map((tag, i) => (
          <span key={i} className="bg-white/20 px-2 py-1 rounded text-xs">
            {tag}
          </span>
        ))}
      </div>
    </Link>
  )
}

// 任务状态行
function TaskStatusRow({ task }: { task: TaskStatus }) {
  const getStatusDisplay = () => {
    if (!task.enabled) return { text: '已禁用', color: 'text-red-600', dot: 'bg-red-500' }
    if (task.status === 'running') return { text: '运行中', color: 'text-green-600', dot: 'bg-green-500 animate-pulse' }
    return { text: '空闲', color: 'text-amber-600', dot: 'bg-amber-500' }
  }
  
  const status = getStatusDisplay()
  const lastRun = task.last_run_time 
    ? new Date(task.last_run_time).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : '-'
  
  return (
    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
      <div className="flex items-center gap-3">
        <span className={`w-3 h-3 rounded-full ${status.dot}`}></span>
        <div>
          <div className="font-medium">{task.display_name}</div>
          <div className="text-sm text-gray-500">上次: {lastRun}</div>
        </div>
      </div>
      <div className={`text-sm ${status.color}`}>{status.text}</div>
    </div>
  )
}

// 活动日志项
function ActivityItem({ icon, iconColor, title, time, detail }: {
  icon: string
  iconColor: string
  title: string
  time: string
  detail: string
}) {
  return (
    <div className="flex items-start gap-3 p-2 hover:bg-gray-50 rounded">
      <span className={`${iconColor} mt-1`}>{icon}</span>
      <div className="flex-1">
        <div className="text-sm">{title}</div>
        <div className="text-xs text-gray-400">{time} · {detail}</div>
      </div>
    </div>
  )
}

// 数据概览卡片
function DataCard({ value, label, color, bgColor }: {
  value: string | number
  label: string
  color: string
  bgColor: string
}) {
  return (
    <div className={`text-center p-4 ${bgColor} rounded-lg`}>
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      <div className="text-sm text-gray-500 mt-1">{label}</div>
    </div>
  )
}

// 主页面
export default function Home() {
  const [tasks, setTasks] = useState<TaskStatus[]>([])
  const [loading, setLoading] = useState(true)
  const [schedulerRunning, setSchedulerRunning] = useState(true)

  useEffect(() => {
    loadTaskStatus()
  }, [])

  async function loadTaskStatus() {
    try {
      const data = await getTaskStatus()
      if (data.status === 'success') {
        setSchedulerRunning(data.data.scheduler_running)
        setTasks(Object.values(data.data.tasks))
      }
    } catch (err) {
      console.error('加载任务状态失败:', err)
      // Mock 数据
      setTasks([
        { name: 'raw', display_name: '快照采集', enabled: true, status: 'idle', last_run_time: '2026-04-19T17:30:05' },
        { name: 'special_pool', display_name: '特殊股票池采集', enabled: true, status: 'idle', last_run_time: '2026-04-19T17:25:00' },
        { name: 'day_k', display_name: '日K采集', enabled: false, status: 'disabled', last_run_time: '2026-04-19T15:05:00' },
      ])
    } finally {
      setLoading(false)
    }
  }

  const activeTasks = tasks.filter(t => t.enabled).length
  const totalTasks = tasks.length

  return (
    <main className="max-w-7xl mx-auto px-4 py-8">
      {/* 欢迎区域 */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800">欢迎回来，大王！</h1>
        <p className="text-gray-500 mt-2">系统运行正常，数据采集服务已就绪</p>
      </div>

      {/* 系统状态概览 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatusCard
          title="调度器"
          value={schedulerRunning ? '运行中' : '已停止'}
          icon="🔄"
          color={schedulerRunning ? 'text-green-600' : 'text-red-600'}
        />
        <StatusCard
          title="活跃任务"
          value={`${activeTasks} / ${totalTasks}`}
          icon="📋"
          color="text-blue-600"
        />
        <StatusCard
          title="今日采集"
          value="1,234"
          icon="📈"
          color="text-emerald-600"
        />
        <StatusCard
          title="关注股票"
          value="156"
          icon="⭐"
          color="text-amber-600"
        />
      </div>

      {/* 快捷入口 */}
      <div className="mb-8">
        <h2 className="text-xl font-semibold text-gray-800 mb-4">🚀 快捷入口</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <NavCard
            to="/dashboard"
            icon="📊"
            title="数据看板"
            subtitle="实时数据概览"
            color="from-blue-500 to-blue-600"
            tags={['股票列表', '板块热点', '资金流向']}
          />
          <NavCard
            to="/stocks"
            icon="⭐"
            title="股票标记"
            subtitle="关注股票管理"
            color="from-amber-500 to-amber-600"
            tags={['添加关注', '批量操作', '筛选查询']}
          />
          <NavCard
            to="/analysis"
            icon="🧠"
            title="分析决策"
            subtitle="智能分析"
            color="from-purple-500 to-purple-600"
            tags={['股票评分', '异常检测', '决策建议']}
          />
        </div>
      </div>

      {/* 任务状态 + 最近活动 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* 任务状态 */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">📋 任务状态</h3>
            <Link to="/tasks" className="text-blue-500 text-sm hover:underline">管理 →</Link>
          </div>
          <div className="space-y-4">
            {loading ? (
              <div className="text-center py-4 text-gray-500">加载中...</div>
            ) : (
              tasks.map(task => <TaskStatusRow key={task.name} task={task} />)
            )}
          </div>
        </div>

        {/* 最近活动 */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">📝 最近活动</h3>
            <span className="text-gray-400 text-sm">实时更新</span>
          </div>
          <div className="space-y-3 max-h-64 overflow-y-auto">
            <ActivityItem
              icon="✓"
              iconColor="text-green-500"
              title="快照采集完成"
              time="17:30:05"
              detail="采集 156 只股票"
            />
            <ActivityItem
              icon="✓"
              iconColor="text-green-500"
              title="板块快照采集完成"
              time="17:30:03"
              detail="采集 120 个板块"
            />
            <ActivityItem
              icon="✓"
              iconColor="text-green-500"
              title="特殊股票池采集完成"
              time="17:25:00"
              detail="涨停 15 只"
            />
            <ActivityItem
              icon="ℹ"
              iconColor="text-blue-500"
              title="新增关注股"
              time="17:20:15"
              detail="002475 立讯精密"
            />
            <ActivityItem
              icon="✓"
              iconColor="text-green-500"
              title="快照采集完成"
              time="17:00:05"
              detail="采集 155 只股票"
            />
          </div>
        </div>
      </div>

      {/* 今日数据概览 */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">📈 今日数据概览</h3>
          <div className="text-sm text-gray-400">更新于 17:30:05</div>
        </div>
        
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <DataCard value="15" label="涨停" color="text-red-600" bgColor="bg-red-50" />
          <DataCard value="3" label="跌停" color="text-green-600" bgColor="bg-green-50" />
          <DataCard value="8" label="炸板" color="text-amber-600" bgColor="bg-amber-50" />
          <DataCard value="+2.3%" label="昨涨停今表现" color="text-blue-600" bgColor="bg-blue-50" />
          <DataCard value="+12.8亿" label="主力净流入" color="text-emerald-600" bgColor="bg-emerald-50" />
          <DataCard value="5" label="热点板块" color="text-purple-600" bgColor="bg-purple-50" />
        </div>
        
        {/* 热门板块 */}
        <div className="mt-6 pt-4 border-t">
          <div className="text-sm text-gray-500 mb-3">🔥 热门板块</div>
          <div className="flex flex-wrap gap-2">
            <span className="px-3 py-1 bg-red-100 text-red-700 rounded-full text-sm">白酒 +3.2%</span>
            <span className="px-3 py-1 bg-red-100 text-red-700 rounded-full text-sm">新能源车 +2.8%</span>
            <span className="px-3 py-1 bg-red-100 text-red-700 rounded-full text-sm">半导体 +2.1%</span>
            <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm">医药 -1.2%</span>
            <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm">银行 -0.8%</span>
          </div>
        </div>
      </div>
    </main>
  )
}
