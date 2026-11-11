<script setup>
import { onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useMarketStore } from '../stores/market'
import { useUserStore } from '../stores/user'
import { ICON_SEARCH } from '../utils/icons'
import ProductCard from '../components/ProductCard.vue'
import { getApiErrorMessage } from '../utils/apiError'

const router = useRouter()
const marketStore = useMarketStore()
const userStore = useUserStore()

const searchIconMarkup = `<svg viewBox="0 0 24 24" fill="none">${ICON_SEARCH}</svg>`

let searchTimer = null

// 页面打开时加载数据；如果已有搜索词，优先加载服务端搜索结果。
onMounted(async () => {
  try {
    await Promise.all([
      marketStore.searchText.trim()
        ? marketStore.searchProducts(marketStore.searchText)
        : marketStore.fetchProducts(),
      marketStore.fetchCategories(),
    ])
  } catch (error) {
    console.error('加载首页数据失败:', error)
  }

  // 登录用户加载收藏
  if (userStore.currentUser) {
    try {
      await marketStore.fetchFavorites()
    } catch (error) {
      console.error('加载收藏状态失败:', error)
    }
  }

  window.addEventListener('scroll', handleScroll)
})

// 搜索框输入后防抖：停止输入 400ms 后再请求服务端。
watch(
  () => marketStore.searchText,
  (value) => {
    clearTimeout(searchTimer)
    searchTimer = setTimeout(async () => {
      try {
        await marketStore.searchProducts(value)
      } catch (error) {
        console.error('搜索失败:', error)
      }
    }, 400)
  }
)

// 页面销毁时移除监听并清理尚未执行的搜索。
onUnmounted(() => {
  clearTimeout(searchTimer)
  window.removeEventListener('scroll', handleScroll)
})

// 监听滚动
async function handleScroll() {
  // 正在加载时不重复请求
  if (marketStore.loadingMore) {
    return
  }

  // 没有更多商品时不再请求
  if (!marketStore.hasMore) {
    return
  }

  const scrollTop = window.scrollY
  const windowHeight = window.innerHeight
  const documentHeight = document.documentElement.scrollHeight

  // 距离页面底部 300px 时加载更多
  if (scrollTop + windowHeight >= documentHeight - 300) {
    try {
      await marketStore.loadMoreProducts()
    } catch (error) {
      console.error('加载更多商品失败:', error)
    }
  }
}

// 打开商品详情
function openDetail(id) {
  router.push({
    name: 'detail',
    params: { id },
  })
}

// 收藏 / 取消收藏
async function toggleFav(id) {
  if (!userStore.currentUser) {
    router.push({
      name: 'auth',
    })
    return
  }

  try {
    await marketStore.toggleFavorite(id)
  } catch (error) {
    console.error('收藏操作失败:', error)
  }
}
</script>

<template>
  <div class="container">

    <!-- 页面标题 -->
    <div class="page-head">
      <div>
        <h1 class="page-title">二手商品</h1>

        <p class="page-sub">
          同学转手的好物，离你只有几步路
        </p>
      </div>
    </div>

    <!-- 商品分类 -->
    <div class="chip-row">

      <!-- 全部 -->
      <button
        type="button"
        class="chip"
        :class="{
          active: marketStore.activeCategory === 'all'
        }"
        @click="marketStore.activeCategory = 'all'"
      >
        全部
      </button>

      <!-- 数据库动态分类 -->
      <button
        v-for="category in marketStore.categories"
        :key="category.key"
        type="button"
        class="chip"
        :class="{
          active: marketStore.activeCategory === category.key
        }"
        @click="marketStore.activeCategory = category.key"
      >
        {{ category.name }}
      </button>

    </div>

    <!-- 商品列表 -->
    <div
      v-if="marketStore.filteredProducts.length"
      class="grid"
    >
      <ProductCard
        v-for="p in marketStore.filteredProducts"
        :key="p.id"
        :product="p"
        :is-favorite="marketStore.favorites.has(p.id)"
        @open="openDetail"
        @toggle-fav="toggleFav"
      />
    </div>

    <!-- 没有商品 -->
    <div
      v-else
      class="empty-state"
    >
      <div
        class="icon"
        v-html="searchIconMarkup"
      ></div>

      <p>
        没有找到相关闲置，换个关键词试试
      </p>
    </div>

    <!-- 加载提示 -->
    <div
      v-if="marketStore.loadingMore"
      class="loading-more"
    >
      正在加载更多商品...
    </div>

    <!-- 全部加载完成 -->
    <div
      v-if="
        !marketStore.hasMore &&
        marketStore.filteredProducts.length
      "
      class="no-more"
    >
      没有更多商品了
    </div>

  </div>
</template>
