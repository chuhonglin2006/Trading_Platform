<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TopBar from './components/TopBar.vue'
import SidebarNav from './components/SidebarNav.vue'
import ToastHost from './components/ToastHost.vue'
import AnnouncementBar from './components/AnnouncementBar.vue'
import SiteFooter from './components/SiteFooter.vue'
import { useMarketStore } from './stores/market'
import { useUserStore } from './stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const marketStore = useMarketStore()

function handleAuthExpired() {
  userStore.logout()
  if (route.name !== 'auth') {
    router.push({ name: 'auth' })
  }
}

onMounted(async () => {
  window.addEventListener('cm-auth-expired', handleAuthExpired)

  try {
    await marketStore.fetchAnnouncements()
  } catch (error) {
    console.error('加载公告失败:', error)
  }
})

onUnmounted(() => {
  window.removeEventListener('cm-auth-expired', handleAuthExpired)
})
</script>

<template>
  <template v-if="route.meta.hideChrome">
    <router-view />
  </template>

  <template v-else>
    <TopBar />
    <AnnouncementBar :announcements="marketStore.announcements" />
    <div class="body-shell">
      <SidebarNav />
      <main>
        <router-view />
      </main>
    </div>
    <SiteFooter />
  </template>

  <ToastHost />
</template>
