<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { ICON_HOME, ICON_USER } from '../utils/icons'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const isHomeActive = computed(() => ['home', 'detail', 'publish'].includes(route.name))
const isProfileActive = computed(() => route.name === 'profile')

function goProfile() {
  if (!userStore.currentUser) {
    router.push({ name: 'auth' })
    return
  }
  router.push({ name: 'profile' })
}
</script>

<template>
  <aside class="sidebar">
    <button
      class="side-nav-btn"
      :class="{ active: isHomeActive }"
      @click="router.push({ name: 'home' })"
      v-html="'<svg viewBox=\'0 0 24 24\' fill=\'none\'>' + ICON_HOME + '</svg><span>主页</span>'"
    ></button>
    <button
      class="side-nav-btn"
      :class="{ active: isProfileActive }"
      @click="goProfile"
      v-html="'<svg viewBox=\'0 0 24 24\' fill=\'none\'>' + ICON_USER + '</svg><span>我的</span>'"
    ></button>
  </aside>
</template>
