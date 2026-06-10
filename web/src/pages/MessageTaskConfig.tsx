import { useState, useEffect } from 'react'
import {
  getMessageTasks,
  updateMessageTaskInterval,
  enableMessageTask,
  disableMessageTask,
  runMessageTask,
  type MessageTaskConfig,
} from '../api'

// 任务显示名称映射
const TASK_DISPLAY_NAMES: Record<string, string> = {
  cls_telegram: '📨 财联社电报',
  cls_a_share: '📈 A股消息',
  cls_company_depth: '🏢 公司深度',
  cls_headline: '🔥 头条消息',
  cls_global: '🌍 环球消息',
}

// 任务描述
const TASK_DESCRIPTIONS: Record<string, string> = {
  cls_telegram: '实时电报快讯，覆盖政策、公司、行业、市场动态',
  cls_a_share: 'A股市场深度资讯，含个股关联分析',
  cls_company_depth: '上市公司深度报道和研报',
  cls_headline: '财联社头条要闻',
  cls_global: '全球市场动态',
}

export default function MessageTaskConfig() {
  const [tasks, setTasks] = useState<MessageTaskConfig[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState<string | null>(null)
  const [running, setRunning] = useState<string | null>(null)
  const [toast, setToast] = useState({ show: false, message: '' })

  useEffect(() => {
    loadTasks()
  }, [])

  async function loadTasks() {
    try {
      setLoading(true)
      const res = await getMessageTasks()
      if (res.status === 'success') {
        setTasks(res.data)
      }
    } catch (err) {
      console.error('加载消息采集任务失败:', err)
      showToast('加载失败')
    } finally {
      setLoading(false)
    }
  }

  function showToast(message: string) {
    setToast({ show: true, message })
    setTimeout(() => setToast({ show: false, message: '' }), 3000)
  }

  async function handleIntervalChange(taskName: string, minutes: number) {
    if (minutes < 1) {
      showToast('间隔时间不能小于1分钟')
      return
    }

    try {
      setSaving(taskName)
      const res = await updateMessageTaskInterval(taskName, minutes)
      if (res.status === 'success') {
        showToast(res.message)
        // 更新本地状态
        setTasks(prev =>
          prev.map(t =>
            t.name === taskName ? { ...t, interval_minutes: minutes } : t
          )
        )
      } else {
        showToast('更新失败')
      }
    } catch (err) {
      console.error('更新间隔失败:', err)
      showToast('更新失败')
    } finally {
      setSaving(null)
    }
  }

  async function handleToggleTask(task: MessageTaskConfig) {
    try {
      if (task.enabled) {
        await disableMessageTask(task.name)
        showToast(`${task.display_name} 已禁用`)
      } else {
        await enableMessageTask(task.name)
        showToast(`${task.display_name} 已启用`)
      }
      // 刷新状态
      loadTasks()
    } catch (err) {
      console.error('切换任务状态失败:', err)
      showToast('操作失败')
    }
  }

  async function handleRunTask(task: MessageTaskConfig) {
    try {
      setRunning(task.name)
      const res = await runMessageTask(task.name)
      if (res.status === 'success') {
        showToast(`${task.display_name} 已启动，后台执行中...`)
      } else {
        showToast(`启动失败: ${res.message}`)
      }
    } catch (err) {
      console.error('执行任务失败:', err)
      showToast('执行失败')
    } finally {
      setRunning(null)
      // 3秒后刷新状态
      setTimeout(loadTasks, 3000)
    }
  }

  function formatLastRun(time?: string, status?: string) {
    if (!time) return '从未执行'
    const d = new Date(time)
    const timeStr = `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
    
    if (!status) return timeStr
    
    const isSuccess = status.includes('success') || status === 'success'
    return (
      <span className="flex items-center gap-1">
        <span className={isSuccess ? 'text-green-600' : 'text-red-600'}>
          {isSuccess ? '✓' : '✗'}
        </span>
        {timeStr}
      </span>
    )
  }

  return (
    <main className="max-w-7xl mx-auto px-4 py-6">
      {/* 页面标题 */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">📨 消息采集配置</h1>
        <p className="text-gray-500 mt-1">管理财联社消息源的采集任务和频率</p>
      </div>

      {/* 说明卡片 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
        <h3 className="font-medium text-blue-800 mb-2">💡 采集策略说明</h3>
        <ul className="text-sm text-blue-700 space-y-1">
          <li>• 首次启动：自动检测数据库最新数据，若超过24小时则采集前24小时至今的数据</li>
          <li>• 后续采集：仅采集上次采集时间之后的新增数据</li>
          <li>• 所有任务支持自动去重，不会重复插入相同数据</li>
          <li>• 修改采集间隔后自动保存到配置文件</li>
        </ul>
      </div>

      {/* 任务列表 */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold">采集任务列表</h2>
        </div>

        {loading ? (
          <div className="text-center py-12 text-gray-500">加载中...</div>
        ) : (
          <div className="divide-y divide-gray-200">
            {tasks.map(task => (
              <div key={task.name} className="px-6 py-4 hover:bg-gray-50 transition-colors">
                <div className="flex items-start justify-between">
                  {/* 任务信息 */}
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <h3 className="font-medium text-gray-900">
                        {TASK_DISPLAY_NAMES[task.name] || task.display_name}
                      </h3>
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-medium ${
                          task.enabled
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {task.enabled ? '运行中' : '已停止'}
                      </span>
                    </div>
                    <p className="text-sm text-gray-500 mt-1">
                      {TASK_DESCRIPTIONS[task.name]}
                    </p>
                    <div className="text-sm text-gray-400 mt-1">
                      上次执行: {formatLastRun(task.last_run_time, task.last_run_status)}
                    </div>
                  </div>

                  {/* 操作区 */}
                  <div className="flex items-center gap-4">
                    {/* 间隔设置 */}
                    <div className="flex items-center gap-2">
                      <label className="text-sm text-gray-600">采集间隔:</label>
                      <select
                        value={task.interval_minutes}
                        onChange={e =>
                          handleIntervalChange(task.name, parseInt(e.target.value))
                        }
                        disabled={saving === task.name}
                        className="px-2 py-1 border rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      >
                        <option value={1}>1分钟</option>
                        <option value={3}>3分钟</option>
                        <option value={5}>5分钟</option>
                        <option value={10}>10分钟</option>
                        <option value={15}>15分钟</option>
                        <option value={30}>30分钟</option>
                        <option value={60}>1小时</option>
                      </select>
                      {saving === task.name && (
                        <span className="text-xs text-gray-400">保存中...</span>
                      )}
                    </div>

                    {/* 开关 */}
                    <button
                      onClick={() => handleToggleTask(task)}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        task.enabled ? 'bg-green-500' : 'bg-gray-300'
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          task.enabled ? 'translate-x-6' : 'translate-x-1'
                        }`}
                      />
                    </button>

                    {/* 立即执行 */}
                    <button
                      onClick={() => handleRunTask(task)}
                      disabled={running === task.name}
                      className="px-3 py-1.5 bg-blue-500 text-white text-sm rounded hover:bg-blue-600 disabled:opacity-50 transition-colors"
                    >
                      {running === task.name ? '执行中...' : '立即执行'}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 刷新按钮 */}
      <div className="mt-4 flex justify-end">
        <button
          onClick={loadTasks}
          disabled={loading}
          className="px-4 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50 text-sm"
        >
          🔄 刷新状态
        </button>
      </div>

      {/* Toast */}
      {toast.show && (
        <div className="fixed bottom-4 right-4 bg-gray-800 text-white px-4 py-2 rounded shadow-lg z-50">
          {toast.message}
        </div>
      )}
    </main>
  )
}
