<!-- src/App.vue -->
<template>
  <router-view />
</template>

<script setup>
// 仅作为路由出口，不包含业务逻辑
</script>

<style>
/* 全局样式（从原 App.vue 移过来） */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
  background-color: #f8fafc;
  color: #334155;
  overflow: hidden;
}
</style>