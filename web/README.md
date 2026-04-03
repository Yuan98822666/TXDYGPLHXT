# 东方财富股票数据看板

基于 React + Vite + Recharts + Tailwind CSS 的数据看板项目。

## 技术栈

- **React 19** + TypeScript
- **Vite 8** - 构建工具
- **Recharts** - 图表库
- **Tailwind CSS** - 样式框架

## 快速开始

```bash
# 安装依赖
npm install

# 开发模式
npm run dev

# 构建生产版本
npm run build
```

## 项目结构

```
src/
├── App.tsx           # 主应用（路由）
├── main.tsx          # 入口文件
├── index.css         # 全局样式
├── pages/            # 页面
│   ├── Dashboard.tsx # 数据看板主页
│   ├── StockDetail.tsx # 股票详情页
│   └── Analysis.tsx  # 分析决策页
├── components/       # 公共组件
│   ├── StockTable.tsx
│   └── Charts.tsx
└── api/              # API 调用
    └── index.ts
```

## 页面说明

### 1. Dashboard（数据看板）
- 大盘资金流向概览
- 板块热点排行
- 关注股票列表

### 2. StockDetail（股票详情）
- 股价 + 资金流入时序图
- 单超大/大/中/小单流入分析
- 异常行为记录

### 3. Analysis（分析决策）
- 股票评分系统
- 决策建议
- 历史评价记录

## 后端 API

后端运行在 `http://localhost:8084`，主要接口：

- `GET /api/stocks` - 股票列表
- `GET /api/stock/{code}` - 股票详情
- `GET /api/blocks` - 板块数据
- `GET /api/collector/raw/run` - 触发采集

---

开发中...