<!-- E:\Python Project\TXDYGPLHXT\frontend\src\components\BacktestReportCard.vue -->
<template>
  <el-card class="report-card" :class="{ failed: report.status === 'failed' }">
    <div class="header">
      <span class="tag" :class="report.trigger_type">{{ report.trigger_type === 'auto' ? '自动' : '手动' }}</span>
      <span class="date">{{ formatDate(report.report_date) }}</span>
      <el-tag v-if="report.status === 'running'" type="info">分析中...</el-tag>
      <el-tag v-else-if="report.status === 'failed'" type="danger">失败</el-tag>
      <el-tag v-else type="success">完成</el-tag>
    </div>

    <h3 class="title">{{ report.insight_title }}</h3>
    <p class="summary">{{ report.insight_summary }}</p>

    <el-collapse v-if="report.raw_data && Object.keys(report.raw_data).length > 0">
      <el-collapse-item title="📊 查看原始回测数据">
        <pre class="raw-data">{{ JSON.stringify(report.raw_data, null, 2) }}</pre>
      </el-collapse-item>
    </el-collapse>
  </el-card>
</template>

<script setup lang="ts">
import { defineProps } from 'vue';

interface Report {
  id: number;
  report_date: string; // ISO date string
  trigger_type: 'manual' | 'auto';
  status: 'running' | 'success' | 'failed';
  insight_title: string;
  insight_summary: string;
  raw_data: Record<string, any>;
}

const props = defineProps<{ report: Report }>();

const formatDate = (dateStr: string) => {
  const d = new Date(dateStr);
  return d.toLocaleDateString('zh-CN');
};
</script>

<style scoped>
.report-card {
  margin-bottom: 20px;
  transition: box-shadow 0.3s;
}
.report-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
.report-card.failed {
  border-left: 4px solid #f56c6c;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-size: 14px;
}
.tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: bold;
}
.manual {
  background-color: #e6a23c;
  color: white;
}
.auto {
  background-color: #409eff;
  color: white;
}
.date {
  color: #909399;
}
.title {
  margin: 8px 0;
  font-size: 18px;
  color: #303133;
}
.summary {
  color: #606266;
  line-height: 1.6;
}
.raw-data {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  max-height: 300px;
  overflow: auto;
}
</style>