<script setup>
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { useMarketStore } from '../stores/market'
import { useTheme } from '../composables/useTheme'
import { ICON_SEARCH, ICON_SUN, ICON_MOON } from '../utils/icons'

const router = useRouter()
const userStore = useUserStore()
const marketStore = useMarketStore()
const { isNight, toggle } = useTheme()
const isApp = navigator.userAgent.includes('Electron')

function goPublish() {
  if (!userStore.currentUser) {
    router.push({
      name: 'auth',
      query: { redirect: '/publish' }
    })
    return
  }
  router.push({ name: 'publish' })
}

function goProfile() {
  if (!userStore.currentUser) {
    router.push({
      name: 'auth',
      query: { redirect: '/profile' }
    })
    return
  }
  router.push({ name: 'profile' })
}
</script>


<template>
  <div class="topbar">
    <div class="topbar-inner">
      <button class="logo" @click="router.push({ name: 'home' })">
        <span class="logo-mark">E</span> 个人二手商品展示平台
      </button>

      <div class="search-box">
        <span class="search-icon" v-html="'<svg viewBox=\'0 0 24 24\' fill=\'none\'>' + ICON_SEARCH + '</svg>'"></span>
        <input
          v-model="marketStore.searchText"
          placeholder="搜索教材、数码、家具…"
          @keyup.enter="router.push({ name: 'home' })"
        />
      </div>

      <div class="nav-actions">
       <button v-if="!isApp" class="btn btn-ghost" @click="router.push({ name: 'download' })">下载 App</button>
        <button class="btn btn-ghost" @click="goPublish">发布闲置</button>

        <button
          class="icon-btn"
          :title="isNight ? '退出护眼模式' : '护眼模式'"
          @click="toggle"
          v-html="'<svg viewBox=\'0 0 24 24\' fill=\'none\'>' + (isNight ? ICON_SUN : ICON_MOON) + '</svg>'"
        ></button>

        <button v-if="userStore.currentUser" class="avatar" :title="userStore.currentUser.username" @click="goProfile">
          {{ userStore.currentUser.username.slice(0, 1).toUpperCase() }}
        </button>
        <button v-else class="btn btn-primary" @click="router.push({ name: 'auth' })">登录 / 注册</button>
      </div>
    </div>
  </div>
</template>
