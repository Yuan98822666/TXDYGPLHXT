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