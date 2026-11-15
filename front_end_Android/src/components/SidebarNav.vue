<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { ICON_HOME, ICON_PLUS, ICON_USER } from '../utils/icons'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const isHomeActive = computed(() => ['home', 'detail', 'seller'].includes(route.name))
const isPublishActive = computed(() => route.name === 'publish')
const isProfileActive = computed(() => ['profile', 'edit-product', 'order-detail', 'chat'].includes(route.name))

function goPublish() {
  if (!userStore.currentUser) {
    router.push({
      name: 'auth',
      query: { redirect: '/publish' },
    })
    return
  }
  router.push({ name: 'publish' })
}

function goProfile() {
  if (!userStore.currentUser) {
    router.push({ name: 'auth' })
    return
  }
  router.push({ name: 'profile' })
}
</script>

<template>
  <nav class="sidebar" aria-label="主要导航">
    <button
      class="side-nav-btn"
      :class="{ active: isHomeActive }"
      type="button"
      aria-label="主页"
      @click="router.push({ name: 'home' })"
    >
      <span
        class="side-nav-icon"
        v-html="'<svg viewBox=\'0 0 24 24\' fill=\'none\'>' + ICON_HOME + '</svg>'"
      ></span>
      <span>主页</span>
    </button>

    <button
      class="side-nav-btn side-nav-publish"
      :class="{ active: isPublishActive }"
      type="button"
      aria-label="发布闲置"
      @click="goPublish"
    >
      <span
        class="side-nav-icon side-nav-publish-icon"
        v-html="'<svg viewBox=\'0 0 24 24\' fill=\'none\'>' + ICON_PLUS + '</svg>'"
      ></span>
      <span>发布</span>
    </button>

    <button
      class="side-nav-btn"
      :class="{ active: isProfileActive }"
      type="button"
      aria-label="我的"
      @click="goProfile"
    >
      <span
        class="side-nav-icon"
        v-html="'<svg viewBox=\'0 0 24 24\' fill=\'none\'>' + ICON_USER + '</svg>'"
      ></span>
      <span>我的</span>
    </button>
  </nav>
</template>
