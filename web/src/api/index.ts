// src/api/index.ts - API 统一入口
const API_BASE = 'http://localhost:8084'

// 通用请求方法
async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })
  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`)
  }
  return response.json()
}

// ============ 数据接口 ============

// 股票列表
export async function getStocks() {
  return fetchAPI<any[]>('/api/stocks')
}

// 股票详情
export async function getStockDetail(code: string) {
  return fetchAPI<any>(`/api/stock/${code}`)
}

// 板块数据
export async function getBlocks() {
  return fetchAPI<any[]>('/api/blocks')
}

// 触发采集
export async function triggerCollector() {
  return fetchAPI<any>('/api/collector/raw/run', { method: 'POST' })
}

// 采集状态
export async function getCollectorStatus() {
  return fetchAPI<any>('/api/collector/status')
}

// ============ 任务管理接口 ============

// 获取所有任务状态
export async function getTaskStatus() {
  return fetchAPI<any>('/api/task/status')
}

// 开启所有任务
export async function enableAllTasks() {
  return fetchAPI<any>('/api/task/start-all', { method: 'POST' })
}

// 关闭所有任务
export async function disableAllTasks() {
  return fetchAPI<any>('/api/task/stop-all', { method: 'POST' })
}

// 开启单个任务
export async function enableTask(taskName: string) {
  return fetchAPI<any>(`/api/task/${taskName}/enable`, { method: 'POST' })
}

// 关闭单个任务
export async function disableTask(taskName: string) {
  return fetchAPI<any>(`/api/task/${taskName}/disable`, { method: 'POST' })
}

// 手动执行单个任务
export async function runTaskOnce(taskName: string) {
  return fetchAPI<any>(`/api/task/${taskName}/run`, { method: 'POST' })
}

// 获取任务调度配置
export async function getTaskSchedule(taskName: string) {
  return fetchAPI<any>(`/api/task/${taskName}/schedule`)
}

// 更新调度配置
export async function updateTaskSchedule(taskName: string, index: number, updates: Record<string, any>) {
  return fetchAPI<any>(`/api/task/${taskName}/schedule`, {
    method: 'PUT',
    body: JSON.stringify({ index, updates })
  })
}

// 添加调度配置
export async function addTaskSchedule(taskName: string, schedule: Record<string, any>) {
  return fetchAPI<any>(`/api/task/${taskName}/schedule`, {
    method: 'POST',
    body: JSON.stringify(schedule)
  })
}

// 删除调度配置
export async function removeTaskSchedule(taskName: string, scheduleIndex: number) {
  return fetchAPI<any>(`/api/task/${taskName}/schedule/${scheduleIndex}`, { 
    method: 'DELETE' 
  })
}

// 启动调度器
export async function startScheduler() {
  return fetchAPI<any>('/api/task/scheduler/start', { method: 'POST' })
}

// 停止调度器
export async function stopScheduler() {
  return fetchAPI<any>('/api/task/scheduler/stop', { method: 'POST' })
}

// 保存配置
export async function saveConfig() {
  return fetchAPI<any>('/api/task/config/save', { method: 'POST' })
}

// 重载配置
export async function reloadConfig() {
  return fetchAPI<any>('/api/task/config/reload', { method: 'POST' })
}

// ============ 股票标记管理接口 ============

// 获取股票列表（分页、筛选）
export async function getStockMarkList(params: {
  page?: number
  page_size?: number
  keyword?: string
  stock_type?: string
  stock_risk?: number
  stock_imp?: number
  exchange?: string
}) {
  const query = new URLSearchParams()
  if (params.page) query.set('page', String(params.page))
  if (params.page_size) query.set('page_size', String(params.page_size))
  if (params.keyword) query.set('keyword', params.keyword)
  if (params.stock_type) query.set('stock_type', params.stock_type)
  if (params.stock_risk !== undefined) query.set('stock_risk', String(params.stock_risk))
  if (params.stock_imp !== undefined) query.set('stock_imp', String(params.stock_imp))
  if (params.exchange) query.set('exchange', params.exchange)
  return fetchAPI<any>(`/stock/mark/list?${query}`)
}

// 获取已关注股票列表
export async function getMarkedStocks(page = 1, pageSize = 100) {
  return fetchAPI<any>(`/stock/mark/marked?page=${page}&page_size=${pageSize}`)
}

// 获取标记统计
export async function getMarkStats() {
  return fetchAPI<any>('/stock/mark/stats')
}

// 搜索股票（自动补全）
export async function searchStocks(keyword: string, limit = 20) {
  return fetchAPI<any>(`/stock/mark/search?q=${encodeURIComponent(keyword)}&limit=${limit}`)
}

// 添加关注（单个）
export async function addStockMark(code: string) {
  return fetchAPI<any>('/stock/mark/add', {
    method: 'POST',
    body: JSON.stringify({ code })
  })
}

// 移除关注（单个）
export async function removeStockMark(code: string, skipDays = 0) {
  return fetchAPI<any>('/stock/mark/remove', {
    method: 'POST',
    body: JSON.stringify({ code, skip_days: skipDays })
  })
}

// 切换关注状态
export async function toggleStockMark(code: string) {
  return fetchAPI<any>('/stock/mark/toggle', {
    method: 'POST',
    body: JSON.stringify({ code })
  })
}

// 批量添加关注
export async function batchAddStockMark(codes: string[]) {
  return fetchAPI<any>('/stock/mark/batch/add', {
    method: 'POST',
    body: JSON.stringify({ codes, imp: 1 })
  })
}

// 批量移除关注
export async function batchRemoveStockMark(codes: string[], skipDays: number = 0) {
  return fetchAPI<any>('/stock/mark/batch/remove', {
    method: 'POST',
    body: JSON.stringify({ codes, imp: 0, skip_days: skipDays })
  })
}

// 清空所有关注
export async function clearAllMarks() {
  return fetchAPI<any>('/stock/mark/batch/clear', { method: 'POST' })
}

// 按条件批量标记
export async function batchMarkByCondition(params: {
  stock_type?: string
  stock_risk?: number
  exchange?: string
  imp: number
}) {
  return fetchAPI<any>('/stock/mark/batch/by-condition', {
    method: 'POST',
    body: JSON.stringify(params)
  })
}

// ============ 类型定义 ============

export interface Stock {
  stock_code: string
  stock_name: string
  stock_type: string
  stock_imp: number
}

export interface Block {
  block_code: string
  block_name: string
  leader_stock_code?: string
  leader_stock_name?: string
  money_stock_code?: string
  money_stock_name?: string
}

export interface StockSnapshot {
  stock_code: string
  trade_time: string
  price: number
  volume: number
  amount: number
  inflow_large: number   // 大单流入
  inflow_medium: number  // 中单流入
  inflow_small: number    // 小单流入
}
