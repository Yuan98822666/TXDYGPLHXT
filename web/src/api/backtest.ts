// E:\Python Project\TXDYGPLHXT\frontend\src\api\backtest.ts
import axios from 'axios';

// 创建 axios 实例（后端地址）
const api = axios.create({
  baseURL: 'http://localhost:8084/api',
  timeout: 15000,
});

// 手动触发回测
export const triggerBacktest = () => {
  return api.post('/backtest/trigger', { trigger_type: 'manual' });
};

// 获取回测报告列表（支持按日期筛选）
export const getBacktestReports = (params?: { date?: string }) => {
  return api.get('/reports/backtest', { params });
};