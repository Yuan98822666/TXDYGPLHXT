<!-- src/App.vue -->
<template>
  <div id="app">
    <nav>
      <router-link to="/snapshot">快照控制</router-link>
    </nav>
    <router-view />
  </div>
</template>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  text-align: center;
  color: #2c3e50;
  margin: 0 auto;
  max-width: 800px;
}
</style>