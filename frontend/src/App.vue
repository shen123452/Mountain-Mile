<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <div class="shell">
    <header class="topbar"><RouterLink class="brand" to="/">山程 <span>Mountain Mile</span></RouterLink><nav><RouterLink to="/world">群岛</RouterLink><RouterLink to="/agent">向导</RouterLink><RouterLink to="/login">登录</RouterLink></nav></header>
    <main><RouterView /></main>
  </div>
</template>
