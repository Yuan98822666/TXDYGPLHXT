// src/App.tsx - 主应用入口（带路由）
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import StockDetail from './pages/StockDetail'

// 简单导航栏组件
function NavBar() {
  return (
    <nav className="bg-slate-800 text-white px-4 py-3">
      <div className="max-w-7xl mx-auto flex gap-6">
        <Link to="/" className="hover:text-blue-300">看板</Link>
        <Link to="/stock/600519" className="hover:text-blue-300">股票详情</Link>
        <Link to="/analysis" className="hover:text-blue-300">分析决策</Link>
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
          <Route path="/" element={<Dashboard />} />
          <Route path="/stock/:code" element={<StockDetail />} />
          <Route path="/analysis" element={<div className="p-8 text-center text-gray-500">分析决策页面开发中...</div>} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default App