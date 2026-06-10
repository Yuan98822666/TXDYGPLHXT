// src/pages/TaskManagement.tsx - 任务管理页面
import { useState, useEffect } from 'react'
import { 
  getTaskStatus, 
  enableTask, 
  disableTask, 
  enableAllTasks, 
  disableAllTasks,
  runTaskOnce,
  getTaskSchedule,
  removeTaskSchedule,
  addTaskSchedule,
  startScheduler,
  stopScheduler,
  saveConfig,
  reloadConfig,
  getRuntimeConfig,
  updateRuntimeConfig,
  resetRuntimeConfig,
  type RuntimeConfig,
} from '../api'

// 任务信息
interface TaskInfo {
  name: string
  display_name: string
  enabled: boolean
  status: 'idle' | 'running' | 'disabled'
  last_run_time?: string
  last_run_status?: string
  schedules: Schedule[]
}

// 调度配置
interface Schedule {
  name: string
  type: 'once' | 'interval'
  time?: string
  start_time?: string
  end_time?: string
  interval_seconds?: number
  action?: string
}

// 运行时配置面板组件
function RuntimeConfigPanel() {
  const [config, setConfig] = useState<RuntimeConfig | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    loadConfig()
  }, [])

  async function loadConfig() {
    try {
      setLoading(true)
      const res = await getRuntimeConfig()
      if (res.status === 'success') {
        setConfig(res.data)
      }
    } catch (err) {
      console.error('加载配置失败:', err)
      setMessage('加载配置失败')
    } finally {
      setLoading(false)
    }
  }

  async function handleSave() {
    if (!config) return
    try {
      setSaving(true)
      const res = await updateRuntimeConfig(config)
      if (res.status === 'success') {
        setMessage('配置已保存')
        setTimeout(() => setMessage(''), 2000)
      }
    } catch (err: any) {
      console.error('保存配置失败:', err)
      setMessage(err.message || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  async function handleReset() {
    if (!confirm('确定要重置为默认配置吗？')) return
    try {
      setSaving(true)
      const res = await resetRuntimeConfig()
      if (res.status === 'success') {
        setConfig(res.data)
        setMessage('已重置为默认配置')
        setTimeout(() => setMessage(''), 2000)
      }
    } catch (err) {
      console.error('重置配置失败:', err)
      setMessage('重置失败')
    } finally {
      setSaving(false)
    }
  }

  function updateField<K extends keyof RuntimeConfig>(field: K, value: RuntimeConfig[K]) {
    if (!config) return
    setConfig({ ...config, [field]: value })
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
          <span className="text-2xl">⚙️</span> 采集器配置
        </h2>
        <div className="text-center py-8 text-gray-500">加载中...</div>
      </div>
    )
  }

  if (!config) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
          <span className="text-2xl">⚙️</span> 采集器配置
        </h2>
        <div className="text-center py-8 text-gray-500">加载失败</div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <span className="text-2xl">⚙️</span> 采集器配置
        </h2>
        {message && (
          <span className={`text-sm ${message.includes('失败') ? 'text-red-500' : 'text-green-500'}`}>
            {message}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* 股票采集器配置 */}
        <div className="border rounded-lg p-4 bg-gray-50">
          <h3 className="font-medium mb-3 text-gray-700">📈 股票采集器</h3>
          <div className="space-y-3">
            <div>
              <label className="block text-sm text-gray-600 mb-1">线程数</label>
              <input
                type="number"
                min={1}
                max={20}
                value={config.stock_max_workers}
                onChange={e => updateField('stock_max_workers', parseInt(e.target.value) || 1)}
                className="w-full px-3 py-2 border rounded text-sm"
              />
              <p className="text-xs text-gray-500 mt-1">建议: 连接池大小的25%-50%</p>
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">每批数量</label>
              <input
                type="number"
                min={10}
                max={500}
                step={10}
                value={config.stock_batch_size}
                onChange={e => updateField('stock_batch_size', parseInt(e.target.value) || 100)}
                className="w-full px-3 py-2 border rounded text-sm"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">批次间隔(秒)</label>
              <input
                type="number"
                min={0.1}
                max={10}
                step={0.1}
                value={config.stock_batch_delay}
                onChange={e => updateField('stock_batch_delay', parseFloat(e.target.value) || 2)}
                className="w-full px-3 py-2 border rounded text-sm"
              />
            </div>
          </div>
        </div>

        {/* 数据库连接池配置 */}
        <div className="border rounded-lg p-4 bg-gray-50">
          <h3 className="font-medium mb-3 text-gray-700">🗄️ 数据库连接池</h3>
          <div className="space-y-3">
            <div>
              <label className="block text-sm text-gray-600 mb-1">连接池大小</label>
              <input
                type="number"
                min={5}
                max={100}
                value={config.db_pool_size}
                onChange={e => updateField('db_pool_size', parseInt(e.target.value) || 20)}
                className="w-full px-3 py-2 border rounded text-sm"
              />
              <p className="text-xs text-gray-500 mt-1">服务重启后生效</p>
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">溢出连接数</label>
              <input
                type="number"
                min={0}
                max={100}
                value={config.db_max_overflow}
                onChange={e => updateField('db_max_overflow', parseInt(e.target.value) || 40)}
                className="w-full px-3 py-2 border rounded text-sm"
              />
              <p className="text-xs text-gray-500 mt-1">服务重启后生效</p>
            </div>
          </div>
        </div>

        {/* HTTP超时配置 */}
        <div className="border rounded-lg p-4 bg-gray-50">
          <h3 className="font-medium mb-3 text-gray-700">🌐 HTTP超时</h3>
          <div className="space-y-3">
            <div>
              <label className="block text-sm text-gray-600 mb-1">默认超时(秒)</label>
              <input
                type="number"
                min={5}
                max={60}
                value={config.http_timeout_default}
                onChange={e => updateField('http_timeout_default', parseInt(e.target.value) || 15)}
                className="w-full px-3 py-2 border rounded text-sm"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">快速超时(秒)</label>
              <input
                type="number"
                min={1}
                max={30}
                value={config.http_timeout_fast}
                onChange={e => updateField('http_timeout_fast', parseInt(e.target.value) || 3)}
                className="w-full px-3 py-2 border rounded text-sm"
              />
            </div>
          </div>
        </div>
      </div>

      {/* 配置比例提示 */}
      <div className="mt-4 p-3 bg-blue-50 rounded text-sm text-blue-700">
        <strong>配置检查：</strong>
        线程数({config.stock_max_workers}) / 连接池({config.db_pool_size}) = {' '}
        <span className={config.stock_max_workers > config.db_pool_size / 2 ? 'text-red-500 font-medium' : 'text-green-600'}>
          {Math.round((config.stock_max_workers / config.db_pool_size) * 100)}%
        </span>
        {config.stock_max_workers > config.db_pool_size / 2 && (
          <span className="text-red-500"> ⚠️ 建议线程数不超过连接池的50%</span>
        )}
      </div>

      {/* 操作按钮 */}
      <div className="mt-4 flex gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 text-sm"
        >
          {saving ? '保存中...' : '💾 保存配置'}
        </button>
        <button
          onClick={handleReset}
          disabled={saving}
          className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 disabled:opacity-50 text-sm"
        >
          🔄 重置默认
        </button>
        <span className="text-xs text-gray-500 self-center">
          * 股票采集器配置下次采集时生效，数据库配置需重启服务
        </span>
      </div>
    </div>
  )
}

// Toast 提示组件
function Toast({ message, show }: { message: string; show: boolean }) {
  if (!show) return null
  return (
    <div className="fixed bottom-4 right-4 bg-gray-800 text-white px-4 py-2 rounded shadow-lg z-50">
      {message}
    </div>
  )
}

// Toggle 开关组件
function Toggle({ active, onChange }: { active: boolean; onChange: () => void }) {
  return (
    <div 
      className={`toggle ${active ? 'active' : ''}`}
      onClick={onChange}
    />
  )
}

// 状态标签
function StatusBadge({ status, enabled }: { status: string; enabled: boolean }) {
  if (!enabled) return <span className="status-badge status-disabled">已禁用</span>
  if (status === 'running') return <span className="status-badge status-running">运行中</span>
  return <span className="status-badge status-idle">空闲</span>
}

// 添加调度弹窗
function AddScheduleModal({ 
  show, 
  taskName: _taskName,
  onClose, 
  onAdd 
}: { 
  show: boolean
  taskName: string
  onClose: () => void
  onAdd: (schedule: Omit<Schedule, 'name'>, name: string) => void 
}) {
  const [name, setName] = useState('')
  const [type, setType] = useState<'once' | 'interval'>('once')
  const [time, setTime] = useState('09:30')
  const [startTime, setStartTime] = useState('09:31')
  const [endTime, setEndTime] = useState('11:30')
  const [interval, setInterval] = useState(30)

  const handleSubmit = () => {
    if (type === 'once') {
      onAdd({ type: 'once', time: time + ':00' }, name || '新调度')
    } else {
      onAdd({ 
        type: 'interval', 
        start_time: startTime + ':00', 
        end_time: endTime + ':00', 
        interval_seconds: interval 
      }, name || '新调度')
    }
    setName('')
    onClose()
  }

  if (!show) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
        <h3 className="text-lg font-semibold mb-4">添加调度配置</h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">调度名称</label>
            <input 
              type="text" 
              value={name}
              onChange={e => setName(e.target.value)}
              className="w-full px-3 py-2 border rounded"
              placeholder="如：早盘采集"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">类型</label>
            <select 
              value={type}
              onChange={e => setType(e.target.value as 'once' | 'interval')}
              className="w-full px-3 py-2 border rounded"
            >
              <option value="once">定点执行</option>
              <option value="interval">区间执行</option>
            </select>
          </div>
          
          {type === 'once' ? (
            <div>
              <label className="block text-sm font-medium mb-1">执行时间</label>
              <input 
                type="time" 
                value={time}
                onChange={e => setTime(e.target.value)}
                className="w-full px-3 py-2 border rounded"
              />
            </div>
          ) : (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium mb-1">开始时间</label>
                  <input 
                    type="time" 
                    value={startTime}
                    onChange={e => setStartTime(e.target.value)}
                    className="w-full px-3 py-2 border rounded"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">结束时间</label>
                  <input 
                    type="time" 
                    value={endTime}
                    onChange={e => setEndTime(e.target.value)}
                    className="w-full px-3 py-2 border rounded"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">执行间隔（秒）</label>
                <input 
                  type="number" 
                  value={interval}
                  onChange={e => setInterval(parseInt(e.target.value) || 30)}
                  className="w-full px-3 py-2 border rounded"
                  min="5"
                />
              </div>
            </div>
          )}
        </div>
        
        <div className="flex justify-end gap-2 mt-6">
          <button onClick={onClose} className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300">
            取消
          </button>
          <button onClick={handleSubmit} className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
            添加
          </button>
        </div>
      </div>
    </div>
  )
}

// 主页面
export default function TaskManagement() {
  const [tasks, setTasks] = useState<TaskInfo[]>([])
  const [schedulerRunning, setSchedulerRunning] = useState(true)
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState({ show: false, message: '' })
  
  // 调度配置
  const [selectedTask, setSelectedTask] = useState('raw')
  const [schedules, setSchedules] = useState<Schedule[]>([])
  const [showAddModal, setShowAddModal] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  useEffect(() => {
    if (selectedTask) {
      loadSchedules()
    }
  }, [selectedTask])

  async function loadData() {
    try {
      const data = await getTaskStatus()
      if (data.status === 'success') {
        setSchedulerRunning(data.data.scheduler_running)
        // 后端返回的是数组，直接使用
        const taskList = Array.isArray(data.data.tasks) 
          ? data.data.tasks 
          : Object.values(data.data.tasks)
        setTasks(taskList)
      }
    } catch (err) {
      console.error('加载任务状态失败:', err)
      // Mock 数据（包含所有4个任务）
      setTasks([
        { 
          name: 'raw', 
          display_name: '快照采集', 
          enabled: true, 
          status: 'idle', 
          last_run_time: '2026-04-19T17:30:05',
          last_run_status: 'success',
          schedules: []
        },
        { 
          name: 'special_pool', 
          display_name: '特殊股票池采集', 
          enabled: true, 
          status: 'idle', 
          last_run_time: '2026-04-19T17:25:00',
          last_run_status: 'success',
          schedules: []
        },
        { 
          name: 'day_k', 
          display_name: '日K采集', 
          enabled: false, 
          status: 'disabled', 
          last_run_time: '2026-04-19T15:05:00',
          last_run_status: 'success',
          schedules: []
        },
        { 
          name: 'cls_telegram', 
          display_name: '财联社电报采集', 
          enabled: true, 
          status: 'idle', 
          last_run_time: '2026-06-05T22:00:00',
          last_run_status: 'success',
          schedules: []
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  async function loadSchedules() {
    try {
      const data = await getTaskSchedule(selectedTask)
      if (data.status === 'success') {
        setSchedules(data.data.schedules || [])
      }
    } catch (err) {
      console.error('加载调度配置失败:', err)
      // Mock 数据
      if (selectedTask === 'raw') {
        setSchedules([
          { name: '开盘竞价', type: 'once', time: '09:25:00' },
          { name: '早盘连续竞价', type: 'interval', start_time: '09:31:30', end_time: '11:30:00', interval_seconds: 30 },
          { name: '午盘连续竞价', type: 'interval', start_time: '13:00:00', end_time: '14:57:00', interval_seconds: 30 },
          { name: '收盘采集', type: 'once', time: '15:00:00' },
        ])
      } else if (selectedTask === 'special_pool') {
        setSchedules([
          { name: '开盘采集', type: 'once', time: '09:30:00' },
          { name: '盘中采集', type: 'interval', start_time: '09:35:00', end_time: '14:50:00', interval_seconds: 300 },
          { name: '收盘采集', type: 'once', time: '15:05:00' },
        ])
      } else {
        setSchedules([
          { name: '早盘日K', type: 'once', time: '09:27:00', action: 'append' },
          { name: '收盘日K', type: 'once', time: '15:05:00', action: 'replace' },
        ])
      }
    }
  }

  function showToast(message: string) {
    setToast({ show: true, message })
    setTimeout(() => setToast({ show: false, message: '' }), 2000)
  }

  async function handleToggleTask(task: TaskInfo) {
    try {
      if (task.enabled) {
        await disableTask(task.name)
      } else {
        await enableTask(task.name)
      }
      await loadData()
      showToast(`${task.display_name}已${task.enabled ? '关闭' : '开启'}`)
    } catch (err) {
      console.error('切换任务状态失败:', err)
      showToast('操作失败')
    }
  }

  async function handleRunTask(task: TaskInfo) {
    try {
      const res = await runTaskOnce(task.name)
      if (res.status === 'success') {
        showToast(`${task.display_name}已启动，后台执行中...`)
        // 每3秒刷新一次状态，持续检查任务是否完成
        const checkInterval = setInterval(async () => {
          const statusRes = await getTaskStatus()
          if (statusRes.status === 'success') {
            const taskList = Array.isArray(statusRes.data.tasks) 
              ? statusRes.data.tasks 
              : Object.values(statusRes.data.tasks)
            const updatedTask = taskList.find((t: any) => t.name === task.name)
            if (updatedTask && updatedTask.status === 'idle') {
              clearInterval(checkInterval)
              showToast(`${task.display_name}执行完成: ${updatedTask.last_run_status}`)
              loadData()
            }
          }
        }, 3000)
        // 30秒后自动停止轮询
        setTimeout(() => clearInterval(checkInterval), 30000)
      } else {
        showToast(`启动失败: ${res.message}`)
      }
    } catch (err) {
      console.error('执行任务失败:', err)
      showToast('执行失败')
    }
  }

  async function handleSchedulerToggle() {
    try {
      if (schedulerRunning) {
        await stopScheduler()
      } else {
        await startScheduler()
      }
      setSchedulerRunning(!schedulerRunning)
      showToast(`调度器已${schedulerRunning ? '停止' : '启动'}`)
    } catch (err) {
      console.error('切换调度器状态失败:', err)
      showToast('操作失败')
    }
  }

  async function handleEnableAll() {
    try {
      await enableAllTasks()
      await loadData()
      showToast('所有任务已开启')
    } catch (err) {
      console.error('开启所有任务失败:', err)
      showToast('操作失败')
    }
  }

  async function handleDisableAll() {
    try {
      await disableAllTasks()
      await loadData()
      showToast('所有任务已关闭')
    } catch (err) {
      console.error('关闭所有任务失败:', err)
      showToast('操作失败')
    }
  }

  async function handleDeleteSchedule(index: number) {
    if (!confirm('确定删除此调度配置？')) return
    try {
      await removeTaskSchedule(selectedTask, index)
      await loadSchedules()
      showToast('调度配置已删除')
    } catch (err) {
      console.error('删除调度配置失败:', err)
      showToast('操作失败')
    }
  }

  async function handleAddSchedule(schedule: Omit<Schedule, 'name'>, name: string) {
    try {
      await addTaskSchedule(selectedTask, { ...schedule, name })
      await loadSchedules()
      showToast('调度配置已添加')
    } catch (err) {
      console.error('添加调度配置失败:', err)
      showToast('操作失败')
    }
  }

  async function handleSaveConfig() {
    try {
      await saveConfig()
      showToast('配置已保存')
    } catch (err) {
      console.error('保存配置失败:', err)
      showToast('保存失败')
    }
  }

  async function handleReloadConfig() {
    try {
      await reloadConfig()
      await loadData()
      showToast('配置已重新加载')
    } catch (err) {
      console.error('重载配置失败:', err)
      showToast('重载失败')
    }
  }

  function formatTime(isoTime?: string) {
    if (!isoTime) return '-'
    const d = new Date(isoTime)
    return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}:${d.getSeconds().toString().padStart(2, '0')}`
  }

  function renderScheduleDetail(s: Schedule) {
    if (s.type === 'once') {
      let detail = `定点执行：${s.time}`
      if (s.action) detail += ` (${s.action === 'append' ? '追加' : '替换'})`
      return detail
    }
    return `区间执行：${s.start_time} ~ ${s.end_time}，间隔 ${s.interval_seconds} 秒`
  }

  return (
    <main className="max-w-7xl mx-auto px-4 py-6">
      <style>{`
        .toggle {
          position: relative;
          width: 48px;
          height: 24px;
          background: #e5e7eb;
          border-radius: 12px;
          cursor: pointer;
          transition: background 0.3s;
          display: inline-block;
        }
        .toggle.active {
          background: #22c55e;
        }
        .toggle::after {
          content: '';
          position: absolute;
          top: 2px;
          left: 2px;
          width: 20px;
          height: 20px;
          background: white;
          border-radius: 50%;
          transition: transform 0.3s;
          box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        .toggle.active::after {
          transform: translateX(24px);
        }
        .status-badge {
          padding: 2px 8px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: 500;
        }
        .status-running { background: #dcfce7; color: #166534; }
        .status-idle { background: #f3f4f6; color: #6b7280; }
        .status-disabled { background: #fee2e2; color: #991b1b; }
      `}</style>

      {/* 页面标题 */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">⚙️ 任务管理</h1>
        <p className="text-gray-500 mt-1">管理采集任务和调度配置</p>
      </div>

      {/* 调度器状态 + 快捷操作 + 配置管理 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* 调度器状态 */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span className="text-2xl">🔄</span> 调度器状态
          </h2>
          <div className="flex items-center justify-between">
            <div>
              <div className={`text-xl font-bold ${schedulerRunning ? 'text-green-600' : 'text-red-600'}`}>
                {schedulerRunning ? '运行中' : '已停止'}
              </div>
              <div className="text-sm text-gray-500 mt-1">自动执行已启用的任务</div>
            </div>
            <button
              onClick={handleSchedulerToggle}
              className={`px-4 py-2 text-white rounded text-sm ${
                schedulerRunning ? 'bg-red-500 hover:bg-red-600' : 'bg-green-500 hover:bg-green-600'
              }`}
            >
              {schedulerRunning ? '停止' : '启动'}
            </button>
          </div>
        </div>

        {/* 快捷操作 */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span className="text-2xl">⚡</span> 快捷操作
          </h2>
          <div className="flex flex-col gap-2">
            <button 
              onClick={handleEnableAll}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm"
            >
              开启所有任务
            </button>
            <button 
              onClick={handleDisableAll}
              className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 text-sm"
            >
              关闭所有任务
            </button>
          </div>
        </div>

        {/* 配置管理 */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span className="text-2xl">💾</span> 配置管理
          </h2>
          <div className="flex flex-col gap-2">
            <button 
              onClick={handleSaveConfig}
              className="px-4 py-2 bg-emerald-500 text-white rounded hover:bg-emerald-600 text-sm"
            >
              保存配置到文件
            </button>
            <button 
              onClick={handleReloadConfig}
              className="px-4 py-2 bg-amber-500 text-white rounded hover:bg-amber-600 text-sm"
            >
              从文件重新加载
            </button>
          </div>
        </div>
      </div>

      {/* 任务列表 */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <span className="text-2xl">📋</span> 任务列表
        </h2>
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b-2 border-gray-200">
                <th className="text-left py-3 px-4">任务名称</th>
                <th className="text-left py-3 px-4">状态</th>
                <th className="text-center py-3 px-4">开关</th>
                <th className="text-left py-3 px-4">上次执行</th>
                <th className="text-left py-3 px-4">执行结果</th>
                <th className="text-center py-3 px-4">操作</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} className="text-center py-8 text-gray-500">加载中...</td>
                </tr>
              ) : (
                tasks.map(task => (
                  <tr key={task.name} className="border-b hover:bg-gray-50">
                    <td className="py-3 px-4">
                      <div className="font-medium">{task.display_name}</div>
                      <div className="text-sm text-gray-500">{task.name}</div>
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge status={task.status} enabled={task.enabled} />
                    </td>
                    <td className="py-3 px-4 text-center">
                      <Toggle 
                        active={task.enabled} 
                        onChange={() => handleToggleTask(task)} 
                      />
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-600">
                      {formatTime(task.last_run_time)}
                    </td>
                    <td className="py-3 px-4">
                      <span className={task.last_run_status === 'success' ? 'text-green-600' : 'text-red-600'}>
                        {task.last_run_status === 'success' ? '✓ 成功' : '✗ 失败'}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <button 
                        onClick={() => handleRunTask(task)}
                        className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
                      >
                        执行
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 调度配置 */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <span className="text-2xl">⏰</span> 调度配置
          </h2>
          <select 
            value={selectedTask}
            onChange={e => setSelectedTask(e.target.value)}
            className="px-3 py-1.5 border rounded text-sm"
          >
            {tasks.map(task => (
              <option key={task.name} value={task.name}>{task.display_name}</option>
            ))}
          </select>
        </div>
        
        <div className="space-y-4">
          {schedules.map((schedule, index) => (
            <div key={index} className="border rounded-lg p-4 bg-gray-50">
              <div className="flex items-center justify-between">
                <div className="font-medium">{schedule.name}</div>
                <div className="flex gap-2">
                  <button 
                    onClick={() => handleDeleteSchedule(index)}
                    className="text-red-500 hover:text-red-700 text-sm"
                  >
                    删除
                  </button>
                </div>
              </div>
              <div className="text-sm text-gray-600 mt-1">
                {renderScheduleDetail(schedule)}
              </div>
            </div>
          ))}
        </div>
        
        {/* 添加新调度 */}
        <div className="mt-4 pt-4 border-t">
          <button 
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm"
          >
            + 添加调度配置
          </button>
        </div>
      </div>

      {/* 添加调度弹窗 */}
      <AddScheduleModal
        show={showAddModal}
        taskName={selectedTask}
        onClose={() => setShowAddModal(false)}
        onAdd={handleAddSchedule}
      />

      {/* 运行时配置面板 */}
      <RuntimeConfigPanel />

      {/* Toast */}
      <Toast message={toast.message} show={toast.show} />
    </main>
  )
}
