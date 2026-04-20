// src/App.tsx - 主应用入口（带路由）
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import StockDetail from './pages/StockDetail'
import Home from './pages/Home'
import TaskManagement from './pages/TaskManagement'
import StockMarkManagement from './pages/StockMarkManagement'

// 简单导航栏组件
function NavBar() {
  const location = useLocation()
  
  const navItems = [
    { path: '/', label: '🏠 首页', exact: true },
    { path: '/dashboard', label: '📊 数据看板', exact: false },
    { path: '/stocks', label: '⭐ 股票标记', exact: true },
    { path: '/tasks', label: '⚙️ 任务管理', exact: true },
    { path: '/analysis', label: '🧠 分析决策', exact: true },
  ]
  
  return (
    <nav className="bg-slate-800 text-white px-4 py-3 shadow-lg">
      <div className="max-w-7xl mx-auto flex justify-between items-center">
        <div className="flex items-center gap-3">
          <span className="text-2xl">📊</span>
          <span className="text-xl font-bold">天下第一股票量化系统</span>
          <span className="text-sm text-slate-400 ml-2">v0.3.0</span>
        </div>
        <div className="flex gap-6">
          {navItems.map((item) => {
            const isActive = item.exact 
              ? location.pathname === item.path
              : location.pathname.startsWith(item.path)
            return (
              <Link 
                key={item.path}
                to={item.path} 
                className={`hover:text-blue-300 ${isActive ? 'text-blue-300 font-medium' : ''}`}
              >
                {item.label}
              </Link>
            )
          })}
        </div>
      </div>
    </nav>
  )
}

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-100">
        <NavBar />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/stock/:code" element={<StockDetail />} />
          <Route path="/stocks" element={<StockMarkManagement />} />
          <Route path="/tasks" element={<TaskManagement />} />
          <Route path="/analysis" element={<div className="p-8 text-center text-gray-500">分析决策页面开发中...</div>} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default App
