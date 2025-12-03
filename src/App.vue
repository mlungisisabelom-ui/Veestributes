<script setup>
import { Analytics } from '@vercel/analytics/vue'
</script>

<template>
  <div id="app">
    <Analytics />
    <main>
      <h1>Veestributes</h1>
      <p>Music Distribution Platform - Now with Vercel Web Analytics</p>
    </main>
  </div>
</template>

<style scoped>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;
}

main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

h1 {
  font-size: 3rem;
  margin-bottom: 1rem;
}

p {
  font-size: 1.2rem;
  color: #666;
}
</style>
