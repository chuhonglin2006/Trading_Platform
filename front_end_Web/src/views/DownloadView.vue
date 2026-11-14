<script setup>
import { ref, computed, onMounted } from 'vue'

const data = ref(null)
const error = ref(false)

const ua = navigator.userAgent
const current = /Android/i.test(ua) ? 'android'
  : /iPhone|iPad/i.test(ua) ? 'ios'
  : /Windows/i.test(ua) ? 'windows'
  : /Mac/i.test(ua) ? 'mac' : ''

const items = computed(() => {
  const list = data.value?.items || []
  // 当前系统排在最前面
  return [...list].sort((a, b) => (b.platform === current) - (a.platform === current))
})

onMounted(async () => {
  try {
    const res = await fetch('/downloads/releases.json', { cache: 'no-store' })
    if (!res.ok) throw new Error()
    data.value = await res.json()
  } catch {
    error.value = true
  }
})
</script>

<template>
  <div class="download-page">
    <h1>下载 App</h1>
    <p v-if="data" class="meta">最新版本 {{ data.version }} · 更新于 {{ data.updated }}</p>
    <p v-if="error" class="meta">暂时无法获取下载信息，请稍后再试</p>

    <div class="cards">
      <div v-for="it in items" :key="it.platform" class="card">
        <h3>
          {{ it.name }}
          <span v-if="it.platform === current" class="tag">适合你的设备</span>
        </h3>
        <p>{{ it.note }}</p>
        <a class="btn" :href="`/downloads/${it.file}`" download>下载</a>
      </div>

      <div v-if="current === 'ios'" class="card">
        <h3>iOS</h3>
        <p>暂未提供安装包。用 Safari 打开本站，点“分享”→“添加到主屏幕”即可。</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.download-page { max-width: 800px; margin: 0 auto; padding: 24px 16px; }
.meta { color: #8a94a6; font-size: 14px; }
.cards { display: grid; gap: 16px; margin-top: 20px; }
.card { border: 1px solid #e3e6ec; border-radius: 12px; padding: 16px 20px; }
.card h3 { margin: 0 0 8px; }
.tag { margin-left: 8px; padding: 2px 8px; font-size: 12px; border-radius: 10px; background: #e8f0fe; color: #1a5fd0; }
.btn { display: inline-block; margin-top: 8px; padding: 8px 20px; border-radius: 8px; background: #1a5fd0; color: #fff; text-decoration: none; }
</style>