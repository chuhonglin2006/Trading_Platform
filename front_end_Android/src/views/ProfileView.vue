<template>
  <div class="my-products-page">

    <!-- ==================== 顶部用户信息 ==================== -->
    <section class="user-header">

      <div class="user-info">

        <div class="avatar">
          {{ userName.charAt(0).toUpperCase() }}
        </div>

        <div class="user-text">
          <h1>{{ userName }}</h1>

          <p>
            {{ currentUser?.email || '欢迎回来' }}
            ·
            信用分
            {{
              currentUser?.score ??
              currentUser?.credit_score ??
              '—'
            }}
            ·
            IP：{{ currentUser?.ipProvince || '未知' }}
          </p>
        </div>

      </div>

      <div class="user-stats">

        <div class="stat-item">
          <div class="stat-value">
            {{ myProducts.length }}
          </div>

          <div class="stat-label">
            已加载商品
          </div>
        </div>

        <div class="stat-item">
          <div class="stat-value">
            {{ marketStore.myProductsTotal }}
          </div>

          <div class="stat-label">
            商品总数
          </div>
        </div>

        <div class="stat-item">
          <div class="stat-value">
            {{ marketStore.soldCount }}
          </div>

          <div class="stat-label">
            已售商品
          </div>
        </div>

        <div class="stat-item">
          <div class="stat-value">
            ¥{{ Number(marketStore.totalRevenue || 0).toFixed(2) }}
          </div>

          <div class="stat-label">
            销售额
          </div>
        </div>

      </div>

      <!-- ==================== 退出登录 ==================== -->
      <button
        class="logout-btn"
        type="button"
        @click="handleLogout"
      >
        退出登录
      </button>

    </section>


    <!-- ==================== 销售统计 ==================== -->
    <section class="sales-card">

      <div class="section-title">

        <h2>
          销售统计
        </h2>

        <span>
          共 {{ marketStore.completedSales.length }} 笔已完成销售
        </span>

      </div>

      <!-- ==================== 收益折线图 ==================== -->
      <div
        v-if="marketStore.completedSales.length"
        class="sales-line-chart"
      >

        <svg
          class="line-chart-svg"
          viewBox="0 0 800 280"
          preserveAspectRatio="none"
        >

          <line
            v-for="line in 5"
            :key="line"
            x1="50"
            :y1="getGridY(line)"
            x2="780"
            :y2="getGridY(line)"
            class="chart-grid-line"
          />

          <polyline
            :points="getChartPoints()"
            fill="none"
            class="chart-line"
          />

          <circle
            v-for="(sale, index) in marketStore.completedSales"
            :key="`point-${index}`"
            :cx="getChartX(index)"
            :cy="getChartY(sale.amount)"
            r="5"
            class="chart-point"
          />

          <text
            v-for="(sale, index) in marketStore.completedSales"
            :key="`amount-${index}`"
            :x="getChartX(index)"
            :y="getChartY(sale.amount) - 12"
            text-anchor="middle"
            class="chart-amount"
          >
            ¥{{ Number(sale.amount || 0).toFixed(2) }}
          </text>

          <text
            v-for="(sale, index) in marketStore.completedSales"
            :key="`date-${index}`"
            :x="getChartX(index)"
            y="265"
            text-anchor="middle"
            class="chart-date-text"
          >
            {{ formatDate(sale.day) }}
          </text>

        </svg>

      </div>

      <!-- 没有销售 -->
      <div
        v-else
        class="empty-sales"
      >
        暂无销售记录
      </div>

    </section>


    <!-- ==================== 标签页 ==================== -->
    <div class="tabs">

      <!-- 我的商品 -->
      <button
        class="tab"
        :class="{ active: activeTab === 'products' }"
        type="button"
        @click="activeTab = 'products'"
      >
        我的商品

        <span class="tab-count">
          {{ marketStore.myProductsTotal }}
        </span>
      </button>


      <!-- 我的收藏 -->
      <button
        class="tab"
        :class="{ active: activeTab === 'favorites' }"
        type="button"
        @click="activeTab = 'favorites'"
      >
        我的收藏

        <span class="tab-count">
          {{ favoriteProducts.length }}
        </span>
      </button>


      <!-- 我的订单 -->
      <button
        class="tab"
        :class="{ active: activeTab === 'orders' }"
        type="button"
        @click="activeTab = 'orders'"
      >
        我的订单

        <span class="tab-count">
          {{ marketStore.orders.length }}
        </span>
      </button>


      <!-- 我的销售 -->
      <button
        class="tab"
        :class="{ active: activeTab === 'sales' }"
        type="button"
        @click="activeTab = 'sales'"
      >
        我的销售

        <span class="tab-count">
          {{ marketStore.mySales.length }}
        </span>
      </button>

    </div>


    <!-- ===================================================== -->
    <!-- 我的商品 -->
    <!-- ===================================================== -->

    <section
      v-if="activeTab === 'products'"
      class="products-section"
    >

      <div class="section-header">

        <div>

          <h2>
            我发布的商品
          </h2>

          <p>
            已加载
            {{ myProducts.length }}
            /
            {{ marketStore.myProductsTotal }}
            件
          </p>

        </div>

      </div>


      <!-- 加载中 -->
      <div
        v-if="initialLoading"
        class="loading"
      >
        正在加载我的商品...
      </div>


      <!-- 没有商品 -->
      <div
        v-else-if="myProducts.length === 0"
        class="empty"
      >

        <div class="empty-icon">
          📦
        </div>

        <h3>
          暂无商品
        </h3>

        <p>
          你还没有发布任何商品
        </p>

      </div>


      <!-- 商品列表 -->
      <div
        v-else
        class="product-grid"
      >

        <div
          v-for="product in myProducts"
          :key="product.id"
          class="product-card"
        >

          <!-- 商品图片 -->
          <div
            class="product-image-wrapper clickable-product"
            role="link"
            tabindex="0"
            @click="openMyProduct(product)"
            @keydown.enter="openMyProduct(product)"
          >

            <img
              v-if="product.images?.length"
              :src="getImageUrl(product.images[0])"
              :alt="product.name"
              class="product-image"
            />

            <div
              v-else
              class="no-image"
            >
              暂无图片
            </div>

            <!-- 商品状态 -->
            <div
              class="status-badge"
              :class="getStatusClass(product)"
            >
              {{ getStatusText(product) }}
            </div>

          </div>


          <!-- 商品内容 -->
          <div class="product-content">

            <h3
              class="product-name clickable-product"
              role="link"
              tabindex="0"
              :title="product.name"
              @click="openMyProduct(product)"
              @keydown.enter="openMyProduct(product)"
            >
              {{ product.name }}
            </h3>


            <div class="product-category">
              {{ product.categoryName }}
            </div>


            <div class="product-price-row">

              <div class="product-price">
                ¥{{ Number(product.price || 0).toFixed(2) }}
              </div>

              <div
                v-if="product.originalPrice"
                class="original-price"
              >
                ¥{{ Number(product.originalPrice).toFixed(2) }}
              </div>

            </div>


            <div class="product-meta">

              <span>
                {{ product.campus || '未知校区' }}
              </span>

              <span>
                👁 {{ product.viewCount || 0 }}
              </span>

            </div>

            <div class="product-publish">
              发布于：{{ product.publishProvince || '未知' }}
            </div>


            <div class="product-description">
              {{ product.description || '暂无商品描述' }}
            </div>


            <!-- ==================== 操作按钮 ==================== -->
            <div class="product-actions">

              <!-- 标记已售 -->
              <button
                v-if="product.status === 'on_sale'"
                class="btn btn-sold"
                type="button"
                @click.stop="handleMarkAsSold(product)"
              >
                标记已售
              </button>


              <!-- 删除商品 -->
              <button
                class="btn btn-delete"
                type="button"
                :disabled="deleteLoadingId === product.id"
                @click.stop="handleDeleteProduct(product)"
              >
                {{
                  deleteLoadingId === product.id
                    ? '删除中...'
                    : '删除'
                }}
              </button>


              <!-- 修改 -->
              <button
                v-if="product.status !== 'sold'"
                class="btn btn-edit"
                type="button"
                @click.stop="openEditProduct(product)"
              >
                修改
              </button>


              <!-- 已售 -->
              <span
                v-if="product.status === 'sold'"
                class="sold-text"
              >
                已售出
              </span>


              <!-- 其他状态 -->
              <span
                v-if="
                  product.status !== 'sold' &&
                  product.status !== 'on_sale'
                "
                class="status-text"
              >
                {{ getStatusText(product) }}
              </span>

            </div>

          </div>

        </div>

      </div>


      <!-- 自动加载中 -->
      <div
        v-if="
          myProducts.length > 0 &&
          marketStore.myProductsLoadingMore
        "
        class="loading"
      >
        正在加载更多商品...
      </div>


      <!-- 全部加载完成 -->
      <div
        v-else-if="
          myProducts.length > 0 &&
          !marketStore.myProductsHasMore
        "
        class="no-more"
      >
        已经到底了，共
        {{ marketStore.myProductsTotal }}
        件商品
      </div>

    </section>


    <!-- ===================================================== -->
    <!-- 我的收藏 -->
    <!-- ===================================================== -->

    <section
      v-if="activeTab === 'favorites'"
      class="products-section"
    >

      <div class="section-header">

        <div>

          <h2>
            我的收藏
          </h2>

          <p>
            共 {{ favoriteProducts.length }} 件
          </p>

        </div>

      </div>


      <!-- 收藏加载中 -->
      <div
        v-if="favoriteLoading"
        class="loading"
      >
        正在加载收藏...
      </div>


      <!-- 没有收藏 -->
      <div
        v-else-if="favoriteProducts.length === 0"
        class="empty"
      >

        <div class="empty-icon">
          ❤️
        </div>

        <h3>
          暂无收藏
        </h3>

        <p>
          你收藏的商品会显示在这里
        </p>

      </div>


      <!-- 收藏商品 -->
      <div
        v-else
        class="product-grid"
      >

        <div
          v-for="product in favoriteProducts"
          :key="product.id"
          class="product-card favorite-product-card"
          @click="openFavoriteProduct(product)"
        >

          <div class="product-image-wrapper">

            <img
              v-if="product.images?.length"
              :src="getImageUrl(product.images[0])"
              :alt="product.name"
              class="product-image"
            />

            <div
              v-else
              class="no-image"
            >
              暂无图片
            </div>

          </div>


          <div class="product-content">

            <h3
              class="product-name"
              :title="product.name"
            >
              {{ product.name }}
            </h3>


            <div class="product-category">
              {{ product.categoryName }}
            </div>


            <div class="product-price-row">

              <div class="product-price">
                ¥{{ Number(product.price || 0).toFixed(2) }}
              </div>

              <div
                v-if="product.originalPrice"
                class="original-price"
              >
                ¥{{ Number(product.originalPrice).toFixed(2) }}
              </div>

            </div>


            <div class="product-meta">

              <span>
                {{ product.campus || '未知校区' }}
              </span>

              <span>
                👁 {{ product.viewCount || 0 }}
              </span>

            </div>

            <div class="product-publish">
              发布于：{{ product.publishProvince || '未知' }}
            </div>


            <div class="product-description">
              {{ product.description || '暂无商品描述' }}
            </div>


            <!-- ==================== 收藏商品操作 ==================== -->
            <div class="favorite-actions">

              <!-- 取消收藏 -->
              <button
                class="btn btn-cancel-favorite"
                type="button"
                @click.stop="removeFavorite(product.id)"
              >
                取消收藏
              </button>


              <!-- 举报商品 -->
              <button
                class="btn btn-report"
                type="button"
                @click.stop="openReportProduct(product)"
              >
                举报商品
              </button>

            </div>

          </div>

        </div>

      </div>

    </section>


    <!-- ===================================================== -->
    <!-- 我的订单 -->
    <!-- ===================================================== -->

    <section
      v-if="activeTab === 'orders'"
      class="orders-section"
    >

      <div class="section-header">

        <div>

          <h2>
            我的订单
          </h2>

          <p>
            共 {{ marketStore.orders.length }} 笔订单
          </p>

        </div>

      </div>


      <!-- 没有订单 -->
      <div
        v-if="marketStore.orders.length === 0"
        class="empty"
      >

        <div class="empty-icon">
          🛒
        </div>

        <h3>
          暂无订单
        </h3>

        <p>
          购买商品后的订单会显示在这里
        </p>

      </div>


      <!-- 订单列表 -->
      <div
        v-else
        class="orders-list"
      >

        <div
          v-for="order in marketStore.orders"
          :key="order.id"
          class="order-card"
          role="button"
          tabindex="0"
          @click="openOrder(order.id)"
          @keydown.enter="openOrder(order.id)"
        >

          <div class="order-main">

            <div class="order-name">
              {{ order.name || `订单 ${order.order_no || order.id}` }}
            </div>


            <div class="order-info">

              <span>
                卖家：
                {{ order.sellerName || '用户' }}
              </span>

              <span>
                订单编号：
                {{ order.order_no || '暂无' }}
              </span>

              <span>
                {{ formatDate(order.createdAt || order.created_at) }}
              </span>

            </div>

          </div>


          <div class="order-right">

            <div class="order-price">
              ¥{{ Number(order.price || 0).toFixed(2) }}
            </div>


            <div
              class="order-status"
              :class="{
                pending: order.status === 'pending',
                received: order.status === 'received',
                completed: order.status === 'completed',
                cancelled: order.status === 'cancelled'
              }"
            >
              {{ getOrderStatus(order.status) }}
            </div>

          </div>

        </div>

      </div>

    </section>


    <!-- ===================================================== -->
    <!-- 我的销售 -->
    <!-- ===================================================== -->

    <section
      v-if="activeTab === 'sales'"
      class="orders-section"
    >

      <div class="section-header">

        <div>

          <h2>
            我的销售
          </h2>

          <p>
            别人购买我的商品产生的订单
          </p>

        </div>

      </div>


      <!-- 没有销售订单 -->
      <div
        v-if="marketStore.mySales.length === 0"
        class="empty"
      >

        <div class="empty-icon">
          💰
        </div>

        <h3>
          暂无销售订单
        </h3>

        <p>
          有人购买你的商品后，销售订单会显示在这里
        </p>

      </div>


      <!-- 销售订单 -->
      <div
        v-else
        class="orders-list"
      >

        <div
          v-for="order in marketStore.mySales"
          :key="order.id"
          class="order-card"
          role="button"
          tabindex="0"
          @click="openOrder(order.id)"
          @keydown.enter="openOrder(order.id)"
        >

          <div class="order-main">

            <div class="order-name">
              {{ order.name || `订单 ${order.order_no || order.id}` }}
            </div>


            <div class="order-info">

              <span>
                买家：
                {{ order.buyerName || '用户' }}
              </span>

              <span>
                订单编号：
                {{ order.order_no || '暂无' }}
              </span>

              <span>
                {{ formatDate(order.createdAt || order.created_at) }}
              </span>

            </div>

          </div>


          <div class="order-right">

            <div class="order-price">
              ¥{{ Number(order.price || order.amount || 0).toFixed(2) }}
            </div>


            <div
              class="order-status"
              :class="{
                pending: order.status === 'pending',
                received: order.status === 'received',
                completed: order.status === 'completed',
                cancelled: order.status === 'cancelled'
              }"
            >
              {{ getOrderStatus(order.status) }}
            </div>

          </div>

        </div>

      </div>

    </section>

  </div>


  <!-- ===================================================== -->
  <!-- 商品举报弹窗 -->
  <!-- ===================================================== -->

  <div
    v-if="reportVisible"
    class="report-overlay"
    @click.self="closeReportProduct"
  >

    <div class="report-dialog">

      <div class="report-header">

        <h3>
          举报商品
        </h3>

        <button
          class="report-close"
          type="button"
          :disabled="reportLoading"
          @click="closeReportProduct"
        >
          ×
        </button>

      </div>


      <!-- 被举报商品 -->
      <div class="report-product">

        <div class="report-product-name">
          {{ reportProduct?.name || '商品' }}
        </div>

        <div class="report-product-price">
          ¥{{ Number(reportProduct?.price || 0).toFixed(2) }}
        </div>

      </div>


      <!-- 举报原因 -->
      <div class="report-form">

        <label>
          举报原因
        </label>

        <textarea
          v-model="reportReason"
          maxlength="500"
          rows="5"
          placeholder="请输入举报原因，例如：商品信息虚假、违规商品、图片与实物不符等"
          :disabled="reportLoading"
        ></textarea>

        <div class="report-counter">
          {{ reportReason.length }}/500
        </div>

      </div>


      <!-- 操作按钮 -->
      <div class="report-actions">

        <button
          class="report-cancel-btn"
          type="button"
          :disabled="reportLoading"
          @click="closeReportProduct"
        >
          取消
        </button>


        <button
          class="report-submit-btn"
          type="button"
          :disabled="reportLoading"
          @click="submitProductReport"
        >
          {{
            reportLoading
              ? '提交中...'
              : '提交举报'
          }}
        </button>

      </div>

    </div>

  </div>


  <TradeSafetyDialog ref="safetyDialog" />

</template>


<script setup>
import { getImageUrl } from '../utils/image.js'

import {
  ref,
  computed,
  onMounted,
  onUnmounted
} from 'vue'

import {
  useRouter
} from 'vue-router'

import {
  productsApi
} from '../api/products'

import {
  reportsApi
} from '../api/reports'

import {
  chatApi
} from '../api/chat'

import {
  useMarketStore
} from '../stores/market'

import {
  useUserStore
} from '../stores/user'

import {
  orderStatusText
} from '../constants/status'


// =========================================================
// Router / Store
// =========================================================

const router = useRouter()

const marketStore = useMarketStore()

const userStore = useUserStore()

const safetyDialog = ref(null)


// =========================================================
// 当前用户
// =========================================================

const currentUser = computed(() => {
  return userStore.currentUser
})


const userName = computed(() => {
  return (
    currentUser.value?.username ||
    currentUser.value?.name ||
    '用户'
  )
})


// =========================================================
// 当前标签
// =========================================================

const activeTab = ref('products')


// =========================================================
// 我的商品
// =========================================================

const myProducts = computed(() => {
  return marketStore.myProducts || []
})


// =========================================================
// 收藏商品
// =========================================================

const favoriteProducts = ref([])

const favoriteLoading = ref(false)


// =========================================================
// 初始加载
// =========================================================

const initialLoading = ref(false)


// =========================================================
// 删除商品状态
// =========================================================

const deleteLoadingId = ref(null)


// =========================================================
// 举报商品
// =========================================================

const reportVisible = ref(false)

const reportProduct = ref(null)

const reportReason = ref('')

const reportLoading = ref(false)


// =========================================================
// 加载我的商品
// =========================================================

async function loadMyProducts() {

  initialLoading.value = true

  try {

    await marketStore.fetchMyProducts(
      1,
      20,
      false
    )

  } catch (error) {

    console.error(
      '加载我的商品失败：',
      error
    )

  } finally {

    initialLoading.value = false

  }

}


// =========================================================
// 加载收藏
// =========================================================

async function loadFavoriteProducts() {

  favoriteLoading.value = true

  try {

    await marketStore.fetchFavorites()

    const favoriteIds = [
      ...marketStore.favorites
    ]


    if (favoriteIds.length === 0) {

      favoriteProducts.value = []

      return
    }


    const products = await Promise.all(

      favoriteIds.map(
        async (id) => {

          try {

            return await marketStore.fetchProductDetail(
              id
            )

          } catch (error) {

            console.error(
              `加载收藏商品 ${id} 失败：`,
              error
            )

            return null
          }

        }
      )

    )


    favoriteProducts.value =
      products.filter(Boolean)

  } catch (error) {

    console.error(
      '加载收藏失败：',
      error
    )

    favoriteProducts.value = []

  } finally {

    favoriteLoading.value = false

  }

}


// =========================================================
// 打开收藏商品
// =========================================================

function openFavoriteProduct(product) {

  if (
    !product ||
    product.id === undefined ||
    product.id === null
  ) {
    return
  }


  router.push({
    name: 'detail',
    params: {
      id: product.id
    }
  })

}


// =========================================================
// 打开自己的商品
// =========================================================

function openMyProduct(product) {

  if (
    !product ||
    product.id === undefined ||
    product.id === null
  ) {
    return
  }


  router.push({
    name: 'detail',
    params: {
      id: product.id
    },
    query: {
      mine: '1'
    }
  })

}


// =========================================================
// 打开订单
// =========================================================

function openOrder(orderId) {

  if (
    orderId === undefined ||
    orderId === null
  ) {
    return
  }


  router.push({
    name: 'order-detail',
    params: {
      id: orderId
    }
  })

}


// =========================================================
// 修改商品
// =========================================================

function openEditProduct(product) {

  if (
    !product ||
    product.id === undefined ||
    product.id === null
  ) {
    return
  }


  router.push({
    name: 'edit-product',
    params: {
      id: product.id
    }
  })

}


// =========================================================
// 打开商品举报窗口
// =========================================================

function openReportProduct(product) {

  if (
    !product ||
    product.id === undefined ||
    product.id === null
  ) {
    return
  }

  reportProduct.value = product
  reportReason.value = ''
  reportVisible.value = true
}


// =========================================================
// 关闭商品举报窗口
// =========================================================

function closeReportProduct() {

  if (reportLoading.value) {
    return
  }

  reportVisible.value = false
  reportProduct.value = null
  reportReason.value = ''
}


// =========================================================
// 提交商品举报
// =========================================================

async function submitProductReport() {

  if (reportLoading.value) {
    return
  }

  if (!reportProduct.value) {
    return
  }

  const reason =
    reportReason.value.trim()

  if (!reason) {

    window.alert(
      '请输入举报原因'
    )

    return
  }

  if (reason.length > 500) {

    window.alert(
      '举报原因不能超过500个字符'
    )

    return
  }

  reportLoading.value = true

  try {

    const result =
      await reportsApi.create({

        target_type: 'product',

        target_id:
          reportProduct.value.id,

        reason

      })


    if (
      result?.code !== undefined &&
      result.code !== 200
    ) {

      throw new Error(
        result.message ||
        '举报提交失败'
      )

    }


    window.alert(
      '举报提交成功，我们会尽快处理'
    )


    closeReportProduct()

  } catch (error) {

    console.error(
      '举报商品失败：',
      error
    )


    const message = getApiErrorMessage(error, '举报提交失败，请稍后重试')


    window.alert(message)

  } finally {

    reportLoading.value = false

  }

}


// =========================================================
// 自动加载更多商品
// =========================================================

async function loadMoreMyProducts() {

  if (
    activeTab.value !== 'products'
  ) {
    return
  }


  if (
    marketStore.myProductsLoadingMore
  ) {
    return
  }


  if (
    !marketStore.myProductsHasMore
  ) {
    return
  }


  try {

    await marketStore.loadMoreMyProducts()

  } catch (error) {

    console.error(
      '加载更多我的商品失败：',
      error
    )

  }

}


// =========================================================
// 页面滚动
// =========================================================

function handleScroll() {

  if (
    activeTab.value !== 'products'
  ) {
    return
  }


  const scrollTop =
    window.scrollY ||
    document.documentElement.scrollTop


  const windowHeight =
    window.innerHeight


  const documentHeight =
    document.documentElement.scrollHeight


  const distanceToBottom =
    documentHeight -
    (
      scrollTop +
      windowHeight
    )


  if (
    distanceToBottom <= 500
  ) {

    loadMoreMyProducts()

  }

}


// =========================================================
// 删除商品
// =========================================================

async function handleDeleteProduct(product) {

  if (!product) {
    return
  }


  if (deleteLoadingId.value !== null) {
    return
  }


  const productName =
    product.name || '这个商品'


  const confirmed =
    window.confirm(
      `确定要删除「${productName}」吗？\n\n` +
      `删除后商品将从平台移除。\n` +
      `相关未完成订单会一并处理。\n` +
      `已经完成且未满 6 个月的订单记录将保留。`
    )


  if (!confirmed) {
    return
  }


  deleteLoadingId.value = product.id


  try {

    const result =
      await productsApi.delete(
        product.id
      )


    if (
      result?.code !== undefined &&
      result.code !== 200
    ) {

      throw new Error(
        result.message ||
        '删除商品失败'
      )

    }


    window.alert(
      '商品删除成功'
    )


    await marketStore.fetchMyProducts(
      1,
      20,
      false
    )


    try {

      await marketStore.fetchMySales()

    } catch (error) {

      console.warn(
        '刷新销售数据失败：',
        error
      )

    }

  } catch (error) {

    console.error(
      '删除商品失败：',
      error
    )


    const message = getApiErrorMessage(error, '删除商品失败，请稍后重试')


    window.alert(message)

  } finally {

    deleteLoadingId.value = null

  }

}


// =========================================================
// 标记已售
// =========================================================

async function handleMarkAsSold(product) {

  if (!product) {
    return
  }


  const confirmed =
    window.confirm(
      `确定要将「${product.name}」标记为已售吗？`
    )


  if (!confirmed) {
    return
  }


  try {

    await marketStore.markAsSold(
      product
    )


    await marketStore.fetchMyProducts(
      1,
      20,
      false
    )

  } catch (error) {

    console.error(
      '标记已售失败：',
      error
    )


    window.alert(
      error?.message ||
      '标记已售失败'
    )

  }

}


// =========================================================
// 删除收藏
// =========================================================

async function removeFavorite(productId) {

  if (
    !marketStore.favorites ||
    !marketStore.favorites.has(productId)
  ) {
    return
  }


  try {

    const result =
      await marketStore.toggleFavorite(
        productId
      )


    if (!result) {
      return
    }


    favoriteProducts.value =
      favoriteProducts.value.filter(
        product =>
          String(product.id) !==
          String(productId)
      )

  } catch (error) {

    console.error(
      '取消收藏失败：',
      error
    )

  }

}


// =========================================================
// 退出登录
// =========================================================

function handleLogout() {

  const confirmed =
    window.confirm(
      '确定要退出登录吗？'
    )


  if (!confirmed) {
    return
  }


  userStore.logout()

  marketStore.clearFavorites()

  router.push({
    name: 'auth'
  })

}


// =========================================================
// 商品状态
// =========================================================

function isProductTrading(product) {

  return (
    marketStore.mySales || []
  ).some(
    sale =>
      String(
        sale.product_id ??
        sale.productId
      ) === String(product.id) &&
      ['pending', 'received'].includes(
        sale.status
      )
  )

}


function getStatusText(product) {

  if (
    product.status === 'sold'
  ) {

    return '已售出'

  }


  if (
    product.status === 'off_sale'
  ) {

    return isProductTrading(product)
      ? '交易中'
      : '已下架'

  }


  if (
    product.reviewStatus === 'pending'
  ) {

    return '审核中'

  }


  if (
    product.reviewStatus === 'rejected'
  ) {

    return '审核未通过'

  }


  if (
    product.status === 'on_sale'
  ) {

    return '出售中'

  }


  return '未知状态'

}


// =========================================================
// 商品状态 CSS
// =========================================================

function getStatusClass(product) {

  if (
    product.status === 'sold'
  ) {

    return 'status-sold'

  }


  if (
    product.reviewStatus === 'pending'
  ) {

    return 'status-pending'

  }


  if (
    product.reviewStatus === 'rejected'
  ) {

    return 'status-rejected'

  }

  if (
    product.status === 'off_sale'
  ) {

    return isProductTrading(product)
      ? 'status-trading'
      : 'status-other'

  }


  if (
    product.status === 'on_sale'
  ) {

    return 'status-on-sale'

  }


  return 'status-other'

}


// =========================================================
// 订单角色
// =========================================================

function isBuyer(order) {

  return String(
    order.buyerId ??
    order.buyer_id ??
    ''
  ) === String(
    currentUser.value?.id ?? ''
  )

}


function isSeller(order) {

  return String(
    order.sellerId ??
    order.seller_id ??
    ''
  ) === String(
    currentUser.value?.id ?? ''
  )

}


// =========================================================
// 联系买家
// =========================================================
// 注意：
// 现在“我的销售”列表已经不再显示聊天按钮。
// 这个函数暂时保留，后面的 OrderDetailView.vue 会使用同样的逻辑。
// =========================================================

async function handleContactBuyer(order) {

  if (!order) {
    return
  }


  if (!isSeller(order)) {

    window.alert(
      '你不是该订单的卖家'
    )

    return
  }


  try {

    const response =
      await chatApi.getOrCreate(
        order.id
      )


    if (
      response?.code !== undefined &&
      response.code !== 200
    ) {

      throw new Error(
        response.message ||
        '获取聊天会话失败'
      )

    }


    const conversation =
      response?.data


    if (
      !conversation?.conversation_id
    ) {

      throw new Error(
        '获取聊天会话失败'
      )

    }


    router.push({
      name: 'chat',
      params: {
        conversationId:
          conversation.conversation_id
      }
    })

  } catch (error) {

    console.error(
      '进入买家聊天失败：',
      error
    )


   const message = getApiErrorMessage(error, '进入聊天失败，请稍后重试')


    window.alert(message)

  }

}


// =========================================================
// 买家确认收货
// =========================================================
// 现在个人中心列表页已经删除这个按钮。
// 订单详情页继续使用对应逻辑。
// =========================================================

async function handleReceive(order) {

  if (!order) {
    return
  }


  const confirmed =
    await safetyDialog.value.show({

      title: '收货安全提醒',

      message:
        '请在确认收货前仔细检查商品，确认商品与描述相符、数量完整、商品没有明显问题。确认无误后再完成收货。',

      confirmText: '确认收货'

    })


  if (!confirmed) {
    return
  }


  try {

    await marketStore.completeOrder(
      order.id
    )


    await marketStore.fetchOrders()

    await marketStore.fetchMySales()

  } catch (error) {

    console.error(
      '确认收货失败：',
      error
    )


    window.alert(
      error?.message ||
      '确认收货失败'
    )

  }

}


// =========================================================
// 卖家完成交易
// =========================================================
// 现在个人中心列表页已经删除这个按钮。
// 订单详情页继续使用对应逻辑。
// =========================================================

async function handleSellerComplete(order) {

  if (!order) {
    return
  }


  const confirmed =
    await safetyDialog.value.show({

      title: '交易安全提醒',

      message:
        '请确认商品已经完整交付，并核实买家和交易信息无误。交易过程中请提高警惕，谨防诈骗。',

      confirmText: '确认完成交易'

    })


  if (!confirmed) {
    return
  }


  try {

    await marketStore.completeOrder(
      order.id
    )


    await marketStore.fetchOrders()

    await marketStore.fetchMySales()

  } catch (error) {

    console.error(
      '完成交易失败：',
      error
    )


    window.alert(
      error?.message ||
      '完成交易失败'
    )

  }

}


// =========================================================
// 订单状态
// =========================================================

function getOrderStatus(status) {

  return orderStatusText(status)

}


// =========================================================
// 日期格式化
// =========================================================

function formatDate(value) {

  if (!value) {
    return '暂无'
  }


  try {

    const date =
      new Date(value)


    if (
      Number.isNaN(
        date.getTime()
      )
    ) {

      return value

    }


    return date.toLocaleString(
      'zh-CN',
      {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      }
    )

  } catch {

    return value

  }

}


// =========================================================
// 折线图：最大金额
// =========================================================

function getMaxSaleAmount() {

  const sales =
    marketStore.completedSales || []


  if (
    sales.length === 0
  ) {

    return 1

  }


  return Math.max(

    ...sales.map(
      sale =>
        Number(
          sale.amount || 0
        )
    ),

    1

  )

}


// =========================================================
// 折线图：X
// =========================================================

function getChartX(index) {

  const sales =
    marketStore.completedSales || []


  const count =
    sales.length


  if (
    count <= 1
  ) {

    return 400

  }


  const left =
    50

  const right =
    780


  return (
    left +
    index *
    (
      (right - left) /
      (count - 1)
    )
  )

}


// =========================================================
// 折线图：Y
// =========================================================

function getChartY(amount) {

  const max =
    getMaxSaleAmount()


  const value =
    Number(amount || 0)


  const top =
    30

  const bottom =
    220


  const height =
    bottom - top


  return (
    bottom -
    (
      value / max
    ) *
    height
  )

}


// =========================================================
// 折线图：点
// =========================================================

function getChartPoints() {

  const sales =
    marketStore.completedSales || []


  return sales
    .map(
      (sale, index) => {

        return (
          `${getChartX(index)},${getChartY(sale.amount)}`
        )

      }
    )
    .join(' ')

}


// =========================================================
// 折线图：辅助线
// =========================================================

function getGridY(index) {

  const top =
    30

  const bottom =
    220

  const count =
    4


  return (
    top +
    (
      index - 1
    ) *
    (
      (bottom - top) /
      count
    )
  )

}


// =========================================================
// 页面加载
// =========================================================

onMounted(async () => {

  if (
    !userStore.currentUser
  ) {

    router.push({
      name: 'auth'
    })

    return

  }


  await Promise.allSettled([

    marketStore.fetchMySales(),

    marketStore.fetchOrders(),

    loadMyProducts(),

    loadFavoriteProducts()

  ])


  window.addEventListener(
    'scroll',
    handleScroll,
    {
      passive: true
    }
  )

})


// =========================================================
// 页面销毁
// =========================================================

onUnmounted(() => {

  window.removeEventListener(
    'scroll',
    handleScroll
  )

})

</script>


<style scoped>

/* =========================================================
   页面
   ========================================================= */

.my-products-page {
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
  padding: 30px 24px 60px;
  box-sizing: border-box;
  color: var(--ink);
}


/* =========================================================
   用户头部
   ========================================================= */

.user-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 30px;
  padding: 30px;
  margin-bottom: 24px;
  border-radius: 18px;
  background: var(--card-bg, #ffffff);
  border: 1px solid var(--border);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
}


.user-info {
  display: flex;
  align-items: center;
  gap: 18px;
}


.avatar {
  width: 70px;
  height: 70px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--ink);
  color: var(--bg);
  font-size: 28px;
  font-weight: 700;
}


.user-text h1 {
  margin: 0 0 6px;
  font-size: 25px;
}


.user-text p {
  margin: 0;
  color: var(--muted);
}


.user-stats {
  display: flex;
  gap: 35px;
}


.stat-item {
  text-align: center;
}


.stat-value {
  font-size: 22px;
  font-weight: 700;
}


.stat-label {
  margin-top: 5px;
  color: var(--muted);
  font-size: 13px;
}


/* =========================================================
   退出登录
   ========================================================= */

.logout-btn {
  flex-shrink: 0;
  padding: 10px 18px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  color: var(--muted);
  cursor: pointer;
  font-size: 14px;
  white-space: nowrap;
  transition: 0.2s;
}


.logout-btn:hover {
  background: var(--panel);
  color: var(--ink);
}


/* =========================================================
   销售统计
   ========================================================= */

.sales-card {
  padding: 26px;
  margin-bottom: 24px;
  border-radius: 18px;
  background: var(--card-bg, #ffffff);
  border: 1px solid var(--border);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
}


.section-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
}


.section-title h2 {
  margin: 0;
  font-size: 20px;
}


.section-title span {
  color: var(--muted);
  font-size: 14px;
}


/* =========================================================
   折线图
   ========================================================= */

.sales-line-chart {
  width: 100%;
  height: 280px;
  margin-top: 20px;
  overflow-x: auto;
}


.line-chart-svg {
  width: 100%;
  min-width: 600px;
  height: 280px;
  display: block;
}


.chart-grid-line {
  stroke: var(--border);
  stroke-width: 1;
}


.chart-line {
  stroke: var(--ink);
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
}


.chart-point {
  fill: var(--surface);
  stroke: var(--ink);
  stroke-width: 3;
}


.chart-amount {
  fill: var(--ink);
  font-size: 12px;
  font-weight: 600;
}


.chart-date-text {
  fill: var(--muted);
  font-size: 11px;
}


.empty-sales {
  padding: 50px 0;
  text-align: center;
  color: var(--muted-2);
}


/* =========================================================
   Tabs
   ========================================================= */

.tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 24px;
  padding: 6px;
  border-radius: 12px;
  background: var(--panel);
}


.tab {
  flex: 1;
  padding: 12px 20px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
  font-size: 15px;
  transition: 0.2s;
}


.tab:hover {
  color: var(--ink);
}


.tab.active {
  background: var(--surface);
  color: var(--ink);
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}


.tab-count {
  margin-left: 5px;
  color: var(--muted-2);
}


/* =========================================================
   区域
   ========================================================= */

.products-section,
.orders-section {
  min-height: 300px;
}


.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}


.section-header h2 {
  margin: 0 0 5px;
  font-size: 21px;
}


.section-header p {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
}


/* =========================================================
   商品网格
   ========================================================= */

.product-grid {
  display: grid;
  grid-template-columns: repeat(
    auto-fill,
    minmax(250px, 1fr)
  );
  gap: 20px;
}


.product-card {
  overflow: hidden;
  border-radius: 15px;
  border: 1px solid var(--border);
  background: var(--surface);
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.06);
  transition:
    transform 0.2s,
    box-shadow 0.2s;
}


.product-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}


.favorite-product-card {
  cursor: pointer;
}


.favorite-product-card:hover {
  transform: translateY(-4px);
}


/* =========================================================
   商品图片
   ========================================================= */

.product-image-wrapper {
  position: relative;
  width: 100%;
  height: 210px;
  overflow: hidden;
  background: var(--panel);
}


.product-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}


.no-image {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--muted-2);
}


/* =========================================================
   商品状态
   ========================================================= */

.status-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 5px 9px;
  border-radius: 7px;
  font-size: 12px;
  font-weight: 600;
  background: var(--surface);
}


.status-on-sale {
  color: #166534;
}


.status-sold {
  color: #6b7280;
}


.status-pending {
  color: #92400e;
}

.status-trading {
  color: #1d4ed8;
}


.status-rejected {
  color: #991b1b;
}


.status-other {
  color: #374151;
}


/* =========================================================
   商品内容
   ========================================================= */

.product-content {
  padding: 16px;
}


.product-name {
  margin: 0 0 8px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  font-size: 17px;
}


.product-category {
  margin-bottom: 10px;
  color: var(--muted);
  font-size: 13px;
}


.product-price-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 10px;
}


.product-price {
  color: var(--ink);
  font-size: 21px;
  font-weight: 700;
}


.original-price {
  color: var(--muted-2);
  font-size: 13px;
  text-decoration: line-through;
}


.product-meta {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
  color: var(--muted);
  font-size: 12px;
}


.product-publish {
  margin: -2px 0 10px;
  color: var(--muted);
  font-size: 12px;
}


.product-description {
  height: 40px;
  margin-bottom: 15px;
  overflow: hidden;
  color: var(--muted);
  font-size: 13px;
  line-height: 20px;
}


.product-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 8px;
}


.clickable-product {
  cursor: pointer;
}


.product-name.clickable-product:hover {
  color: #2563eb;
}


/* =========================================================
   通用按钮
   ========================================================= */

.btn {
  border: 0;
  border-radius: 8px;
  padding: 9px 15px;
  cursor: pointer;
  transition: 0.2s;
}


.btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}


/* =========================================================
   标记已售
   ========================================================= */

.btn-sold {
  background: #111827;
  color: #ffffff;
}


.btn-sold:hover {
  opacity: 0.85;
}


/* =========================================================
   删除按钮
   ========================================================= */

.btn-delete {
  background: #fee2e2;
  color: #b91c1c;
}


.btn-delete:hover {
  background: #fecaca;
}


.btn-delete:disabled {
  background: #f3f4f6;
  color: #9ca3af;
}


/* =========================================================
   修改
   ========================================================= */

.btn-edit {
  background: #dbeafe;
  color: #1d4ed8;
}


.btn-edit:hover {
  background: #bfdbfe;
}


.sold-text {
  color: var(--muted);
  font-size: 13px;
}


.status-text {
  color: var(--muted);
  font-size: 13px;
}


/* =========================================================
   加载更多
   ========================================================= */

.no-more {
  padding: 28px 0;
  text-align: center;
  color: var(--muted-2);
  font-size: 13px;
}


/* =========================================================
   空状态
   ========================================================= */

.empty {
  padding: 80px 20px;
  text-align: center;
}


.empty-icon {
  margin-bottom: 15px;
  font-size: 45px;
}


.empty h3 {
  margin: 0 0 8px;
}


.empty p {
  margin: 0;
  color: var(--muted-2);
}


/* =========================================================
   收藏商品操作
   ========================================================= */

.favorite-actions {
  display: flex;
  gap: 8px;
}


.favorite-actions .btn {
  flex: 1;
}


.btn-cancel-favorite {
  background: #f3f4f6;
  color: #374151;
}


.btn-cancel-favorite:hover {
  background: #e5e7eb;
}


/* =========================================================
   举报商品按钮
   ========================================================= */

.btn-report {
  background: #fee2e2;
  color: #b91c1c;
}


.btn-report:hover {
  background: #fecaca;
}


/* =========================================================
   举报弹窗
   ========================================================= */

.report-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(0, 0, 0, 0.45);
}


.report-dialog {
  width: 100%;
  max-width: 500px;
  overflow: hidden;
  border-radius: 16px;
  border: 1px solid var(--border);
  background: var(--surface);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}


.report-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 22px;
  border-bottom: 1px solid var(--border);
}


.report-header h3 {
  margin: 0;
  font-size: 19px;
}


.report-close {
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--muted);
  font-size: 25px;
  line-height: 1;
  cursor: pointer;
}


.report-close:hover {
  background: var(--panel);
}


.report-close:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}


/* =========================================================
   举报商品信息
   ========================================================= */

.report-product {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 15px;
  margin: 20px 22px;
  padding: 14px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--panel);
}


.report-product-name {
  overflow: hidden;
  color: var(--ink);
  font-size: 15px;
  font-weight: 600;
  white-space: nowrap;
  text-overflow: ellipsis;
}


.report-product-price {
  flex-shrink: 0;
  color: var(--ink);
  font-size: 16px;
  font-weight: 700;
}


/* =========================================================
   举报表单
   ========================================================= */

.report-form {
  position: relative;
  padding: 0 22px;
}


.report-form label {
  display: block;
  margin-bottom: 8px;
  color: var(--ink);
  font-size: 14px;
  font-weight: 600;
}


.report-form textarea {
  width: 100%;
  box-sizing: border-box;
  resize: vertical;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: 10px;
  outline: none;
  background: var(--bg);
  color: var(--ink);
  font-family: inherit;
  font-size: 14px;
  line-height: 21px;
  transition: border-color 0.2s;
}


.report-form textarea:focus {
  border-color: var(--ink);
}


.report-form textarea:disabled {
  background: var(--panel);
  cursor: not-allowed;
}


.report-counter {
  margin-top: 5px;
  text-align: right;
  color: var(--muted-2);
  font-size: 12px;
}


/* =========================================================
   举报操作
   ========================================================= */

.report-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 20px 22px 22px;
}


.report-cancel-btn,
.report-submit-btn {
  padding: 9px 18px;
  border: 0;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: 0.2s;
}


.report-cancel-btn {
  background: var(--panel);
  color: var(--ink);
}


.report-cancel-btn:hover {
  opacity: .8;
}


.report-submit-btn {
  background: var(--btn-bg);
  color: var(--btn-text);
}


.report-submit-btn:hover {
  opacity: 0.88;
}


.report-cancel-btn:disabled,
.report-submit-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}


/* =========================================================
   订单
   ========================================================= */

.orders-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}


.order-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 20px;
  border-radius: 14px;
  border: 1px solid var(--border);
  background: var(--surface);
  box-shadow: 0 3px 15px rgba(0, 0, 0, 0.05);
  cursor: pointer;
  transition:
    transform 0.2s,
    box-shadow 0.2s;
}


.order-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
}


.order-card:focus-visible {
  outline: 2px solid #2563eb;
  outline-offset: 2px;
}


.order-main {
  min-width: 0;
  flex: 1;
}


.order-name {
  margin-bottom: 8px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  font-size: 16px;
  font-weight: 600;
}


.order-info {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 20px;
  color: var(--muted-2);
  font-size: 12px;
}


.order-right {
  min-width: 140px;
  text-align: right;
}


.order-price {
  margin-bottom: 5px;
  font-size: 17px;
  font-weight: 700;
}


.order-status {
  font-size: 12px;
}


.order-status.pending {
  color: #92400e;
}


.order-status.received {
  color: #1d4ed8;
}


.order-status.completed {
  color: #166534;
}


.order-status.cancelled {
  color: #991b1b;
}


/* =========================================================
   订单操作
   ========================================================= */

.order-action-btn {
  margin-top: 8px;
  padding: 7px 12px;
  border: 0;
  border-radius: 7px;
  background: var(--btn-bg);
  color: var(--btn-text);
  cursor: pointer;
  font-size: 12px;
  transition: 0.2s;
}


.order-action-btn:hover {
  opacity: 0.88;
}


/* =========================================================
   联系买家按钮
   ========================================================= */

.chat-order-btn {
  background: var(--panel);
  color: var(--ink);
  border: 1px solid var(--border);
}


.chat-order-btn:hover {
  opacity: .8;
}


/* =========================================================
   Loading
   ========================================================= */

.loading {
  padding: 80px 20px;
  text-align: center;
  color: var(--muted);
}


/* =========================================================
   响应式
   ========================================================= */

@media (max-width: 1100px) {

  .user-header {
    flex-wrap: wrap;
  }


  .user-stats {
    flex: 1;
  }


  .logout-btn {
    margin-left: auto;
  }

}


@media (max-width: 900px) {

  .user-header {
    flex-direction: column;
    align-items: flex-start;
  }


  .user-stats {
    width: 100%;
    justify-content: space-between;
    gap: 10px;
  }


  .logout-btn {
    margin-left: 0;
  }

}


@media (max-width: 600px) {

  .my-products-page {
    padding:
      18px
      max(12px, env(safe-area-inset-right))
      40px
      max(12px, env(safe-area-inset-left));
  }


  .user-header {
    gap: 18px;
    padding: 18px;
    border-radius: 15px;
  }


  .user-info {
    width: 100%;
    gap: 14px;
  }


  .avatar {
    width: 56px;
    height: 56px;
    font-size: 22px;
  }


  .user-text {
    min-width: 0;
    flex: 1;
  }


  .user-text h1 {
    overflow: hidden;
    font-size: 21px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }


  .user-text p {
    font-size: 12px;
    line-height: 1.6;
    overflow-wrap: anywhere;
  }


  .user-stats {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 14px;
    width: 100%;
    padding-top: 4px;
  }


  .stat-item {
    padding: 12px 10px;
    border-radius: 10px;
    background: var(--panel);
  }


  .stat-value {
    overflow: hidden;
    font-size: 19px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }


  .stat-label {
    margin-top: 3px;
    font-size: 11px;
  }


  .logout-btn {
    width: 100%;
    min-height: 42px;
  }


  .product-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }


  .tabs {
    gap: 4px;
    margin-left: -12px;
    margin-right: -12px;
    padding: 6px 12px;
    border-radius: 0;
    overflow-x: auto;
    scrollbar-width: none;
  }


  .tabs::-webkit-scrollbar {
    display: none;
  }


  .tab {
    flex: 0 0 auto;
    min-width: 110px;
    padding: 10px 14px;
    font-size: 13px;
  }


  .product-card {
    display: grid;
    grid-template-columns: 112px minmax(0, 1fr);
    border-radius: 14px;
  }


  .product-card:hover {
    transform: none;
  }


  .product-image-wrapper {
    height: 100%;
    min-height: 164px;
  }


  .product-content {
    min-width: 0;
    padding: 13px 14px;
  }


  .product-name {
    margin-bottom: 6px;
    font-size: 15px;
  }


  .product-category,
  .product-publish,
  .product-description {
    display: none;
  }


  .product-price-row {
    margin: 7px 0;
  }


  .product-price {
    font-size: 19px;
  }


  .product-meta {
    margin-bottom: 12px;
    font-size: 11px;
  }


  .product-actions {
    justify-content: flex-start;
    gap: 6px;
  }


  .product-actions .btn {
    min-height: 34px;
    padding: 7px 10px;
    font-size: 12px;
  }


  .status-badge {
    top: 8px;
    right: 8px;
    padding: 4px 7px;
    font-size: 11px;
  }


  .order-card {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
    padding: 17px 15px;
  }


  .order-main {
    width: 100%;
  }


  .order-info {
    flex-direction: column;
    gap: 5px;
  }


  .order-right {
    min-width: 0;
    padding-top: 10px;
    border-top: 1px solid var(--border);
    text-align: left;
  }


  .favorite-actions {
    flex-direction: column;
  }


  .report-overlay {
    padding: 12px;
  }


  .report-dialog {
    max-width: none;
  }


  .sales-card {
    padding: 18px;
    border-radius: 15px;
  }


  .section-title {
    align-items: flex-start;
    flex-direction: column;
    gap: 5px;
  }


  .sales-line-chart {
    margin-right: -18px;
  }


  .line-chart-svg {
    min-width: 540px;
  }


  .report-overlay {
    padding:
      calc(12px + env(safe-area-inset-top))
      max(12px, env(safe-area-inset-right))
      calc(12px + env(safe-area-inset-bottom))
      max(12px, env(safe-area-inset-left));
  }


  .report-dialog {
    max-height: calc(100dvh - env(safe-area-inset-top) - env(safe-area-inset-bottom) - 24px);
    overflow-y: auto;
  }

}

</style>
