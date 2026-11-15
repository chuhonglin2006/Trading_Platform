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
  <header class="topbar">
    <div class="topbar-inner">
      <button
        class="logo"
        type="button"
        aria-label="返回首页"
        @click="router.push({ name: 'home' })"
      >
        <span class="logo-mark">E</span>
        <span class="logo-copy">
          <span class="logo-title">个人二手商品展示平台</span>
          <span class="logo-mobile-title">校园二手</span>
        </span>
      </button>

      <div class="search-box">
        <span class="search-icon" v-html="'<svg viewBox=\'0 0 24 24\' fill=\'none\'>' + ICON_SEARCH + '</svg>'"></span>
        <input
          v-model="marketStore.searchText"
          type="search"
          enterkeyhint="search"
          aria-label="搜索商品"
          placeholder="搜索教材、数码、家具…"
          @keyup.enter="router.push({ name: 'home' })"
        />
      </div>

      <div class="nav-actions">
        <button class="btn btn-ghost nav-publish" type="button" @click="goPublish">发布闲置</button>

        <button
          class="icon-btn"
          type="button"
          :title="isNight ? '退出护眼模式' : '护眼模式'"
          :aria-label="isNight ? '退出护眼模式' : '护眼模式'"
          @click="toggle"
          v-html="'<svg viewBox=\'0 0 24 24\' fill=\'none\'>' + (isNight ? ICON_SUN : ICON_MOON) + '</svg>'"
        ></button>

        <button
          v-if="userStore.currentUser"
          class="avatar"
          type="button"
          :title="userStore.currentUser.username"
          :aria-label="`打开${userStore.currentUser.username}的个人中心`"
          @click="goProfile"
        >
          {{ userStore.currentUser.username.slice(0, 1).toUpperCase() }}
        </button>
        <button
          v-else
          class="btn btn-primary btn-login"
          type="button"
          @click="router.push({ name: 'auth' })"
        >
          登录 / 注册
        </button>
      </div>
    </div>
  </header>
</template>
