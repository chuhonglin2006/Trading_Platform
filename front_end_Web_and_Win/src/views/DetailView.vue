<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useMarketStore } from '../stores/market'
import { useUserStore } from '../stores/user'
import { useToast } from '../composables/useToast'
import { catInfo } from '../utils/icons'
import CategoryIcon from '../components/CategoryIcon.vue'
import TradeSafetyDialog from '../components/TradeSafetyDialog.vue'
import { productsApi } from '../api/products'
import { reportsApi } from '../api/reports'
import { formatDateTime } from '../utils/format'
import { getApiErrorMessage } from '../utils/apiError'

const props = defineProps({
  id: {
    type: [String, Number],
    required: true,
  },
})

const router = useRouter()
const route = useRoute()
const marketStore = useMarketStore()
const userStore = useUserStore()
const { show } = useToast()

const safetyDialog = ref(null)

// =========================================================
// 页面状态
// =========================================================

const loading = ref(true)
const loadError = ref('')
const product = ref(null)
const imageError = ref(false)
const buying = ref(false)
const sellerProfile = ref(null)

// =========================================================
// 商品图片状态
// =========================================================

const currentImageIndex = ref(0)

// =========================================================
// 举报状态
// =========================================================

const reportDialogVisible = ref(false)
const reportSubmitting = ref(false)
const reportReason = ref('')
const reportDescription = ref('')
const reportError = ref('')

const reportReasons = [
  '虚假商品信息',
  '商品与描述严重不符',
  '疑似诈骗',
  '禁止发布的商品',
  '价格信息虚假',
  '其他',
]

// =========================================================
// 我的商品数据转换
// =========================================================

function convertMineProduct(item = {}) {
  return {
    id: item.id,

    name: item.name || '',

    price: Number(item.price || 0),

    originalPrice: Number(
      item.original_price ??
      item.originalPrice ??
      0
    ),

    description: item.description || '',

    status: item.status || 'on_sale',

    activeOrderStatus:
      item.active_order_status ??
      item.activeOrderStatus ??
      null,

    reviewStatus:
      item.review_status ??
      item.reviewStatus ??
      '',

    images: Array.isArray(item.images)
      ? item.images
      : [],

    campus: item.campus || '',

    publishProvince:
      item.publish_province ||
      item.publishProvince ||
      '未知',

    viewCount: Number(
      item.view_count ??
      item.viewCount ??
      0
    ),

    createdAt:
      item.created_at ??
      item.createdAt ??
      null,

    sellerId:
      item.seller_id ??
      item.sellerId ??
      item.seller?.id ??
      (route.query.mine === '1'
        ? userStore.currentUser?.id
        : null),

    sellerName:
      item.seller?.username ??
      item.sellerName ??
      userStore.currentUser?.username ??
      '用户',

    categoryName:
      item.category?.name ??
      item.categoryName ??
      '未分类',

    category:
      item.category?.key ??
      item.category_key ??
      (typeof item.category === 'string'
        ? item.category
        : 'all'),
  }
}

// =========================================================
// 是否是自己的商品
// =========================================================

const isOwnProduct = computed(() => {
  if (!product.value) {
    return false
  }

  const currentUserId =
    userStore.currentUser?.id

  if (
    currentUserId === undefined ||
    currentUserId === null ||
    currentUserId === ''
  ) {
    return false
  }

  const sellerId =
    product.value.sellerId

  if (
    sellerId !== undefined &&
    sellerId !== null &&
    sellerId !== ''
  ) {
    return (
      String(sellerId) ===
      String(currentUserId)
    )
  }

  return route.query.mine === '1'
})

// =========================================================
// 商品状态
// =========================================================

const productStatusText = computed(() => {
  switch (product.value?.status) {
    case 'on_sale':
      return '在售中'

    case 'off_sale':
      return product.value?.activeOrderStatus
        ? '交易中'
        : '已下架'

    case 'sold':
      return '已售出'

    default:
      return '暂不可购买'
  }
})

const buyButtonText = computed(() => {
  if (buying.value) {
    return '正在创建订单...'
  }

  switch (product.value?.status) {
    case 'on_sale':
      return '拍下，联系卖家'

    case 'off_sale':
      return product.value?.activeOrderStatus
        ? '已被拍下'
        : '已下架'

    case 'sold':
      return '已售出'

    default:
      return '暂不可购买'
  }
})

const canBuy = computed(() => {
  return (
    !!product.value &&
    !isOwnProduct.value &&
    product.value.status === 'on_sale' &&
    !buying.value
  )
})

// =========================================================
// 加载商品详情
// =========================================================

async function loadProductDetail(productId) {
  loading.value = true
  loadError.value = ''
  imageError.value = false
  currentImageIndex.value = 0
  product.value = null

  try {
    if (route.query.mine === '1') {
      // 我的商品：每次进入详情页都请求后端
      const result = await productsApi.myDetail(productId)

      if (
        result?.code !== undefined &&
        result.code !== 200
      ) {
        throw new Error(
          result.message || '获取商品失败'
        )
      }

      const data = result?.data ?? result

      if (!data || !data.id) {
        throw new Error('商品不存在或暂时无法加载')
      }

      product.value = convertMineProduct(data)
    } else {
      // 普通商品详情：保留原有逻辑
      const result = await marketStore.fetchProductDetail(productId)

      if (!result) {
        throw new Error('商品不存在或暂时无法加载')
      }

      product.value = result
    }

    if (!product.value) {
      throw new Error(
        '商品不存在或暂时无法加载'
      )
    }

    sellerProfile.value = null

    if (product.value.sellerId) {
      try {
        sellerProfile.value =
          await marketStore.fetchSellerInfo(
            product.value.sellerId
          )
      } catch (error) {
        console.warn(
          '卖家地区信息加载失败:',
          error
        )
      }
    }

    // 防止当前索引超过图片数量
    if (
      currentImageIndex.value >=
      productImages.value.length
    ) {
      currentImageIndex.value = 0
    }

    // 调试信息
    console.log(
      '商品详情:',
      product.value
    )

    console.log(
      '商品图片:',
      product.value.images
    )

    console.log(
      '当前用户:',
      userStore.currentUser
    )

    console.log(
      '商品卖家ID:',
      product.value.sellerId
    )

    console.log(
      '是否自己的商品:',
      isOwnProduct.value
    )
  } catch (error) {
    console.error(
      '商品详情加载失败:',
      error
    )

    loadError.value = getApiErrorMessage(error, '商品不存在或暂时无法加载')
  } finally {
    loading.value = false
  }
}

// =========================================================
// 首次加载及路由变化
// =========================================================

onMounted(() => {
  loadProductDetail(props.id)
})

watch(
  [
    () => props.id,
    () => route.query.mine,
  ],
  ([newId, newMine], [oldId, oldMine]) => {
    if (
      newId !== oldId ||
      newMine !== oldMine
    ) {
      loadProductDetail(newId)
    }
  }
)

// =========================================================
// 商品图片
// =========================================================

/**
 * 统一处理图片数据
 *
 * 后端目前返回：
 *
 * [
 *   "/images/18/xxx.png",
 *   "/images/18/xxx.jpg"
 * ]
 *
 * 同时兼容：
 *
 * {
 *   image_url: "/images/xxx.jpg"
 * }
 *
 * 或：
 *
 * {
 *   url: "/images/xxx.jpg"
 * }
 */
const productImages = computed(() => {
  if (
    !product.value ||
    !Array.isArray(product.value.images)
  ) {
    return []
  }

  return product.value.images
    .map((image) => {
      if (typeof image === 'string') {
        return image
      }

      return (
        image?.image_url ||
        image?.url ||
        ''
      )
    })
    .filter(Boolean)
})

/**
 * 当前正在显示的图片
 */
const currentProductImage = computed(() => {
  return (
    productImages.value[
      currentImageIndex.value
    ] || ''
  )
})

/**
 * 选择指定图片
 */
function selectImage(index) {
  if (
    index < 0 ||
    index >= productImages.value.length
  ) {
    return
  }

  currentImageIndex.value = index
  imageError.value = false
}

/**
 * 上一张
 */
function previousImage() {
  const length =
    productImages.value.length

  if (length <= 1) {
    return
  }

  currentImageIndex.value =
    (
      currentImageIndex.value -
      1 +
      length
    ) % length

  imageError.value = false
}

/**
 * 下一张
 */
function nextImage() {
  const length =
    productImages.value.length

  if (length <= 1) {
    return
  }

  currentImageIndex.value =
    (
      currentImageIndex.value +
      1
    ) % length

  imageError.value = false
}

/**
 * 图片加载失败
 */
function onImageError() {
  imageError.value = true
}

// =========================================================
// 键盘切换图片
// =========================================================

function handleKeydown(event) {
  if (
    !productImages.value.length
  ) {
    return
  }

  if (event.key === 'ArrowLeft') {
    previousImage()
  }

  if (event.key === 'ArrowRight') {
    nextImage()
  }
}

// =========================================================
// 卖家信息
// =========================================================

const seller = computed(() => {
  if (!product.value) {
    return null
  }

  return {
    id: product.value.sellerId,

    name:
      sellerProfile.value?.name ||
      product.value.sellerName ||
      '用户',

    score:
      sellerProfile.value?.score ??
      '—',

    campus:
      sellerProfile.value?.campus ||
      product.value.campus ||
      '—',

    ipProvince:
      sellerProfile.value?.ipProvince ||
      '未知',
  }
})

// =========================================================
// 收藏状态
// =========================================================

const isFavorite = computed(() => {
  if (!product.value) {
    return false
  }

  return marketStore.favorites.has(
    product.value.id
  )
})

// =========================================================
// 登录检查
// =========================================================

function requireLogin() {
  if (!userStore.currentUser) {
    router.push({
      name: 'auth',
      query: {
        redirect: route.fullPath
      }
    })

    return false
  }

  return true
}

// =========================================================
// 收藏
// =========================================================

async function toggleFav() {
  if (!requireLogin()) {
    return
  }

  if (!product.value) {
    return
  }

  try {
    const wasFavorite =
      isFavorite.value

    await marketStore.toggleFavorite(
      product.value.id
    )

    show(
      wasFavorite
        ? '已取消收藏'
        : '已收藏'
    )
  } catch (error) {
    console.error(
      '收藏操作失败:',
      error
    )

    show(getApiErrorMessage(error, '收藏操作失败'))
  }
}

// =========================================================
// 举报商品
// =========================================================

function openReportDialog() {
  if (!requireLogin()) {
    return
  }

  if (!product.value) {
    show('商品信息不存在')
    return
  }

  if (isOwnProduct.value) {
    show('不能举报自己的商品')
    return
  }

  reportReason.value = ''
  reportDescription.value = ''
  reportError.value = ''

  reportDialogVisible.value = true
}

function closeReportDialog() {
  if (reportSubmitting.value) {
    return
  }

  reportDialogVisible.value = false
  reportReason.value = ''
  reportDescription.value = ''
  reportError.value = ''
}

async function submitReport() {
  if (reportSubmitting.value) {
    return
  }

  if (!requireLogin()) {
    return
  }

  if (!product.value) {
    reportError.value =
      '商品信息不存在'
    return
  }

  if (isOwnProduct.value) {
    reportError.value =
      '不能举报自己的商品'
    return
  }

  if (!reportReason.value) {
    reportError.value =
      '请选择举报原因'
    return
  }

  const description =
    reportDescription.value.trim()

  if (description.length > 500) {
    reportError.value =
      '补充说明不能超过500个字符'
    return
  }

  reportSubmitting.value = true
  reportError.value = ''

  try {
    const reason =
      description
        ? `${reportReason.value}：${description}`
        : reportReason.value

    const result =
      await reportsApi.create({
        target_type: 'product',
        target_id: product.value.id,
        reason,
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

    show(
      result?.message ||
      '举报提交成功，我们会尽快审核'
    )

    reportDialogVisible.value = false
    reportReason.value = ''
    reportDescription.value = ''
    reportError.value = ''
  } catch (error) {
    console.error(
      '举报商品失败:',
      error
    )

    reportError.value = getApiErrorMessage(error, '举报提交失败，请稍后重试')

  } finally {
    reportSubmitting.value = false
  }
}

// =========================================================
// 购买
// =========================================================

async function buyNow() {
  if (buying.value) {
    return
  }

  if (!requireLogin()) {
    return
  }

  if (!product.value) {
    show('商品信息不存在')
    return
  }

  if (isOwnProduct.value) {
    show('不能购买自己发布的商品')
    return
  }

  const currentUserId =
    userStore.currentUser?.id

  const sellerId =
    product.value.sellerId

  if (
    currentUserId != null &&
    sellerId != null &&
    String(currentUserId) ===
      String(sellerId)
  ) {
    show('不能购买自己发布的商品')
    return
  }

  if (product.value.status === 'sold') {
    show('商品已经售出')
    return
  }

  if (
    product.value.status ===
    'off_sale'
  ) {
    show('该商品已经被拍下')
    return
  }

  if (
    product.value.status !==
    'on_sale'
  ) {
    show('该商品当前无法购买')
    return
  }

  if (!safetyDialog.value) {
    show(
      '交易安全提醒暂时无法打开，请稍后重试'
    )
    return
  }

  const confirmed =
    await safetyDialog.value.show({
      title: '购买安全提醒',

      message:
        '请在下单前仔细确认商品名称、商品成色、价格、卖家信息等内容，确认商品信息无误后再继续下单。',

      confirmText:
        '我已确认，继续下单',
    })

  if (!confirmed) {
    return
  }

  if (
    buying.value ||
    isOwnProduct.value
  ) {
    if (isOwnProduct.value) {
      show(
        '不能购买自己发布的商品'
      )
    }

    return
  }

  buying.value = true

  try {
    await marketStore.buy(
      product.value,
      userStore.currentUser
    )

    show(
      '已生成订单，请与卖家约定交易时间地点'
    )

    await router.push({
      name: 'profile',
    })
  } catch (error) {
    console.error(
      '创建订单失败:',
      error
    )

    const responseData =
      error?.response?.data

    const detail =
      responseData?.detail ||
      responseData?.message

    if (
      typeof detail === 'string' &&
      detail.trim()
    ) {
      show(detail)
      return
    }

    if (
      error?.response?.status === 400
    ) {
      show(
        '下单失败，请确认商品是否仍可购买'
      )

      return
    }

    show(
      error?.message ||
      '创建订单失败，请稍后重试'
    )
  } finally {
    buying.value = false
  }
}

// =========================================================
// 查看卖家
// =========================================================

function openSeller() {
  if (!product.value) {
    show('商品信息不存在')
    return
  }

  let sellerId =
    product.value.sellerId

  if (
    route.query.mine === '1' &&
    (
      sellerId === undefined ||
      sellerId === null ||
      sellerId === ''
    )
  ) {
    sellerId =
      userStore.currentUser?.id
  }

  if (
    sellerId === undefined ||
    sellerId === null ||
    sellerId === ''
  ) {
    console.error(
      '无法获取卖家 ID:',
      {
        product: product.value,
        productId:
          product.value.id,
        currentUserId:
          userStore.currentUser?.id,
      }
    )

    show('无法获取卖家信息')
    return
  }

  const numericSellerId =
    Number(sellerId)

  if (
    !Number.isSafeInteger(
      numericSellerId
    ) ||
    numericSellerId <= 0
  ) {
    show('卖家 ID 无效')
    return
  }

  router.push({
    name: 'seller',
    params: {
      id: numericSellerId,
    },
  })
}
</script>

<template>
  <!-- =====================================================
       加载中
  ====================================================== -->
  <div
    v-if="loading"
    class="container"
  >
    <div class="empty-state">
      <p>正在加载商品详情...</p>
    </div>
  </div>

  <!-- =====================================================
       加载失败
  ====================================================== -->
  <div
    v-else-if="loadError || !product"
    class="container"
  >
    <div class="empty-state">
      <p>
        {{
          loadError ||
          '商品不存在或暂未加载'
        }}
      </p>

      <div class="empty-actions">
        <button
          class="btn btn-ghost"
          type="button"
          @click="
            loadProductDetail(props.id)
          "
        >
          重新加载
        </button>

        <button
          class="btn btn-primary"
          type="button"
          @click="
            router.push({
              name: 'home'
            })
          "
        >
          返回商品列表
        </button>
      </div>
    </div>
  </div>

  <!-- =====================================================
       商品详情
  ====================================================== -->
  <div
    v-else
    class="container"
  >
    <!-- 返回 -->
    <div class="breadcrumb">
      <button
        type="button"
        @click="
          router.push({
            name: 'home'
          })
        "
      >
        ← 返回列表
      </button>
    </div>

    <div class="detail-grid">
      <!-- =================================================
           商品图片
      ================================================== -->
      <div class="detail-media-wrapper">
        <!-- 主图片 -->
        <div
          class="detail-media"
          tabindex="0"
          @keydown="handleKeydown"
        >
          <!-- 正常图片 -->
          <img
            v-if="
              currentProductImage &&
              !imageError
            "
            :src="currentProductImage"
            :alt="product.name"
            class="detail-image"
            @error="onImageError"
          />

          <!-- 图片加载失败 -->
          <CategoryIcon
            v-else
            :category="product.category"
          />

          <!-- 左箭头 -->
          <button
            v-if="
              productImages.length > 1
            "
            type="button"
            class="image-nav image-nav-prev"
            aria-label="上一张"
            @click="previousImage"
          >
            ‹
          </button>

          <!-- 右箭头 -->
          <button
            v-if="
              productImages.length > 1
            "
            type="button"
            class="image-nav image-nav-next"
            aria-label="下一张"
            @click="nextImage"
          >
            ›
          </button>

          <!-- 图片数量 -->
          <div
            v-if="
              productImages.length > 1
            "
            class="image-counter"
          >
            {{
              currentImageIndex + 1
            }}
            /
            {{
              productImages.length
            }}
          </div>
        </div>

        <!-- =================================================
             缩略图
        ================================================== -->
        <div
          v-if="
            productImages.length > 1
          "
          class="image-thumbnails"
        >
          <button
            v-for="(
              image, index
            ) in productImages"
            :key="`${image}-${index}`"
            type="button"
            class="image-thumbnail"
            :class="{
              active:
                currentImageIndex ===
                index
            }"
            @click="
              selectImage(index)
            "
          >
            <img
              :src="image"
              :alt="
                `${product.name} 图片 ${
                  index + 1
                }`
              "
            />
          </button>
        </div>
      </div>

      <!-- =================================================
           商品信息
      ================================================== -->
      <div class="detail-info">
        <!-- 状态 -->
        <span
          class="detail-status"
          :class="
            'status-' +
            product.status
          "
        >
          {{ productStatusText }}
        </span>

        <!-- 商品名称 -->
        <h1 class="detail-title">
          {{ product.name }}
        </h1>

        <!-- 价格 -->
        <div class="detail-price-row">
          <span class="detail-price">
            ¥{{
              Number(
                product.price || 0
              ).toFixed(2)
            }}
          </span>

          <span
            v-if="
              Number(product.originalPrice) >
              Number(product.price)
            "
            class="detail-original"
          >
            ¥{{
              Number(
                product.originalPrice
              ).toFixed(2)
            }}
          </span>
        </div>

        <!-- 商品基本信息 -->
        <div class="detail-meta-list">
          <div
            class="detail-meta-item"
          >
            校区&nbsp;
            <b>
              {{
                product.campus ||
                '—'
              }}
            </b>
          </div>

          <div
            class="detail-meta-item"
          >
            分类&nbsp;
            <b>
              {{
                product.categoryName ||
                catInfo(
                  product.category
                ).label
              }}
            </b>
          </div>

          <div
            class="detail-meta-item"
          >
            发布于&nbsp;
            <b>
              {{
                product.publishProvince ||
                '未知'
              }}
            </b>
          </div>

          <div
            class="detail-meta-item"
          >
            发布时间&nbsp;
            <b>
              {{
                formatDateTime(product.createdAt) ||
                '—'
              }}
            </b>

            · 浏览

            <b>
              {{
                product.viewCount || 0
              }}
            </b>

            次
          </div>
        </div>

        <!-- 描述 -->
        <p class="detail-desc">
          {{
            product.description ||
            '暂无更多描述。'
          }}
        </p>

        <!-- =================================================
             卖家
        ================================================== -->
        <div
          v-if="seller"
          class="seller-card seller-card-link"
          role="button"
          tabindex="0"
          @click="openSeller"
          @keydown.enter="
            openSeller
          "
        >
          <div class="avatar">
            {{
              seller.name
                ? seller.name.slice(0, 1)
                : '用'
            }}
          </div>

          <div>
            <div class="seller-name">
              {{ seller.name }}
            </div>

            <div class="seller-score">
              信用分
              {{
                seller.score ?? '—'
              }}

              ·

              {{
                seller.campus || '—'
              }}

              ·

              IP：{{
                seller.ipProvince || '未知'
              }}
            </div>
          </div>

          <span
            class="seller-card-arrow"
          >
            ›
          </span>
        </div>

        <!-- =================================================
             操作按钮
        ================================================== -->
        <div class="detail-actions">

          <!-- 自己的商品 -->
          <template
            v-if="isOwnProduct"
          >
            <button
              class="btn btn-ghost"
              type="button"
              @click="
                router.push({
                  name: 'profile'
                })
              "
            >
              返回我的商品
            </button>

            <button
              v-if="
                product.status !==
                'sold'
              "
              class="btn btn-primary"
              type="button"
              @click="
                router.push({
                  name: 'edit-product',
                  params: {
                    id: product.id
                  }
                })
              "
            >
              修改商品
            </button>

            <span
              v-if="
                product.status ===
                'sold'
              "
              class="own-product-notice"
            >
              该商品已售出
            </span>

            <span
              v-else-if="
                product.status ===
                'off_sale' &&
                product.activeOrderStatus
              "
              class="own-product-notice"
            >
              该商品正在交易中
            </span>

            <span
              v-else-if="
                product.status ===
                'off_sale'
              "
              class="own-product-notice"
            >
              该商品已下架
            </span>
          </template>

          <!-- 别人的商品 -->
          <template v-else>
            <button
              class="btn btn-ghost"
              type="button"
              @click="toggleFav"
            >
              {{
                isFavorite
                  ? '已收藏'
                  : '收藏'
              }}
            </button>

            <button
              class="btn btn-primary"
              type="button"
              :disabled="!canBuy"
              @click="buyNow"
            >
              {{ buyButtonText }}
            </button>
          </template>

          <!-- 举报按钮 -->
          <button
            v-if="!isOwnProduct"
            class="btn btn-report"
            type="button"
            @click="openReportDialog"
          >
            举报商品
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- =====================================================
       举报商品弹窗
  ====================================================== -->
  <div
    v-if="reportDialogVisible"
    class="report-overlay"
    @click.self="closeReportDialog"
  >
    <div class="report-dialog">
      <!-- 标题 -->
      <div class="report-header">
        <h2>举报商品</h2>

        <button
          type="button"
          class="report-close"
          :disabled="reportSubmitting"
          @click="closeReportDialog"
        >
          ×
        </button>
      </div>

      <!-- 商品信息 -->
      <div
        v-if="product"
        class="report-product"
      >
        <div class="report-product-name">
          {{ product.name }}
        </div>

        <div class="report-product-price">
          ¥{{
            Number(
              product.price || 0
            ).toFixed(2)
          }}
        </div>
      </div>

      <!-- 举报原因 -->
      <div class="report-form-item">
        <label>
          举报原因
          <span class="report-required">
            *
          </span>
        </label>

        <div class="report-reasons">
          <label
            v-for="reason in reportReasons"
            :key="reason"
            class="report-reason"
            :class="{
              active:
                reportReason === reason
            }"
          >
            <input
              v-model="reportReason"
              type="radio"
              name="report-reason"
              :value="reason"
            />

            <span>
              {{ reason }}
            </span>
          </label>
        </div>
      </div>

      <!-- 补充说明 -->
      <div class="report-form-item">
        <label>
          补充说明
          <span class="report-optional">
            （可选）
          </span>
        </label>

        <textarea
          v-model="reportDescription"
          maxlength="500"
          rows="5"
          placeholder="请详细说明举报原因，方便平台审核..."
        ></textarea>

        <div class="report-count">
          {{
            reportDescription.length
          }}/500
        </div>
      </div>

      <!-- 错误 -->
      <div
        v-if="reportError"
        class="report-error"
      >
        {{ reportError }}
      </div>

      <!-- 按钮 -->
      <div class="report-actions">
        <button
          type="button"
          class="report-cancel"
          :disabled="reportSubmitting"
          @click="closeReportDialog"
        >
          取消
        </button>

        <button
          type="button"
          class="report-submit"
          :disabled="reportSubmitting"
          @click="submitReport"
        >
          {{
            reportSubmitting
              ? '正在提交...'
              : '提交举报'
          }}
        </button>
      </div>
    </div>
  </div>

  <!-- =====================================================
       交易安全提醒
  ====================================================== -->
  <TradeSafetyDialog
    ref="safetyDialog"
  />
</template>

<style scoped>
/* =========================================================
   整体布局
========================================================= */

.detail-grid {
  display: grid;
  grid-template-columns:
    minmax(0, 1.1fr)
    minmax(0, 1fr);
  gap: 40px;
  align-items: start;
}

/* =========================================================
   返回按钮
========================================================= */

.breadcrumb {
  margin-bottom: 22px;
}

.breadcrumb button {
  padding: 0;
  border: none;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font-size: 14px;
  opacity: 0.75;
}

.breadcrumb button:hover {
  opacity: 1;
}

/* =========================================================
   商品图片区域
========================================================= */

.detail-media-wrapper {
  width: 100%;
  min-width: 0;
}

.detail-media {
  position: relative;

  width: 100%;
  min-height: 420px;

  display: flex;
  align-items: center;
  justify-content: center;

  overflow: hidden;

  border-radius: 16px;

  background: #f5f5f5;

  outline: none;
}

.detail-media:focus-visible {
  outline: 2px solid #2563eb;
  outline-offset: 3px;
}

.detail-image {
  width: 100%;
  height: 420px;

  display: block;

  object-fit: contain;

  background: #f5f5f5;
}

/* =========================================================
   图片左右按钮
========================================================= */

.image-nav {
  position: absolute;

  top: 50%;
  transform: translateY(-50%);

  z-index: 3;

  width: 42px;
  height: 42px;

  display: flex;
  align-items: center;
  justify-content: center;

  padding: 0;

  border: none;
  border-radius: 50%;

  background: rgba(0, 0, 0, 0.45);

  color: #fff;

  font-size: 34px;
  line-height: 1;

  cursor: pointer;

  transition:
    background 0.2s,
    transform 0.2s;
}

.image-nav:hover {
  background: rgba(0, 0, 0, 0.65);
}

.image-nav:active {
  transform: translateY(-50%) scale(0.95);
}

.image-nav-prev {
  left: 14px;
}

.image-nav-next {
  right: 14px;
}

/* =========================================================
   图片计数
========================================================= */

.image-counter {
  position: absolute;

  right: 14px;
  bottom: 14px;

  z-index: 3;

  padding: 5px 10px;

  border-radius: 20px;

  background: rgba(0, 0, 0, 0.55);

  color: #fff;

  font-size: 12px;

  line-height: 1;
}

/* =========================================================
   图片缩略图
========================================================= */

.image-thumbnails {
  display: flex;

  gap: 10px;

  margin-top: 12px;

  padding-bottom: 4px;

  overflow-x: auto;
}

.image-thumbnail {
  position: relative;

  flex: 0 0 76px;

  width: 76px;
  height: 76px;

  padding: 0;

  border: 2px solid transparent;
  border-radius: 9px;

  overflow: hidden;

  background: #f5f5f5;

  cursor: pointer;

  transition:
    border-color 0.2s,
    opacity 0.2s;
}

.image-thumbnail:hover {
  opacity: 0.8;
}

.image-thumbnail.active {
  border-color: #2563eb;
}

.image-thumbnail img {
  width: 100%;
  height: 100%;

  display: block;

  object-fit: cover;
}

/* =========================================================
   商品信息
========================================================= */

.detail-info {
  min-width: 0;
}

.detail-title {
  margin: 14px 0 18px;

  font-size: 30px;
  line-height: 1.35;
  font-weight: 700;

  overflow-wrap: anywhere;
}

/* =========================================================
   价格
========================================================= */

.detail-price-row {
  display: flex;
  align-items: center;

  flex-wrap: wrap;

  gap: 12px;

  margin-bottom: 24px;
}

.detail-price {
  font-size: 30px;
  font-weight: 700;
}

.detail-original {
  font-size: 16px;

  text-decoration: line-through;

  opacity: 0.5;
}

/* =========================================================
   商品状态
========================================================= */

.detail-status {
  display: inline-flex;
  align-items: center;

  padding: 5px 10px;

  border-radius: 6px;

  font-size: 13px;
  font-weight: 500;
}

.status-on_sale {
  background: rgba(34, 197, 94, 0.12);
  color: #16a34a;
}

.status-off_sale {
  background: rgba(245, 158, 11, 0.12);
  color: #d97706;
}

.status-sold {
  background: rgba(107, 114, 128, 0.12);
  color: #6b7280;
}

/* =========================================================
   商品基本信息
========================================================= */

.detail-meta-list {
  display: flex;
  flex-direction: column;

  gap: 12px;

  margin-bottom: 24px;
}

.detail-meta-item {
  font-size: 14px;
  line-height: 1.6;

  opacity: 0.75;
}

.detail-meta-item b {
  opacity: 1;
}

/* =========================================================
   描述
========================================================= */

.detail-desc {
  margin: 0 0 28px;

  font-size: 15px;
  line-height: 1.8;

  white-space: pre-wrap;
  word-break: break-word;
}

/* =========================================================
   卖家
========================================================= */

.seller-card {
  display: flex;
  align-items: center;

  gap: 12px;

  padding: 14px;

  margin-bottom: 28px;

  border-radius: 12px;

  background: #f7f7f7;
}

.seller-card-link {
  cursor: pointer;

  transition: background 0.2s;
}

.seller-card-link:hover {
  background: #eeeeee;
}

.seller-card-link:focus-visible {
  outline: 2px solid #2563eb;
  outline-offset: 3px;
}

.avatar {
  width: 44px;
  height: 44px;

  flex-shrink: 0;

  display: flex;
  align-items: center;
  justify-content: center;

  border-radius: 50%;

  background: #e5e7eb;

  font-size: 18px;
  font-weight: 600;
}

.seller-name {
  font-size: 15px;
  font-weight: 600;

  margin-bottom: 4px;
}

.seller-score {
  font-size: 12px;

  opacity: 0.6;
}

.seller-card-arrow {
  margin-left: auto;

  font-size: 28px;
  line-height: 1;

  opacity: 0.5;
}

/* =========================================================
   操作按钮
========================================================= */

.detail-actions {
  display: flex;
  align-items: center;

  flex-wrap: wrap;

  gap: 12px;
}

.detail-actions .btn {
  min-height: 44px;

  padding: 0 22px;
}

.detail-actions .btn:disabled {
  opacity: 0.55;

  cursor: not-allowed;
}

.own-product-notice {
  font-size: 14px;

  color: #6b7280;
}

/* =========================================================
   举报按钮
========================================================= */

.btn-report {
  min-height: 44px;

  padding: 0 22px;

  border: 1px solid #e5e7eb;

  border-radius: 8px;

  background: #fff;

  color: #666;

  cursor: pointer;

  transition:
    border-color 0.2s,
    color 0.2s,
    background 0.2s;
}

.btn-report:hover {
  border-color: #f04444;

  color: #f04444;

  background: #fff7f7;
}

.btn-report:active {
  transform: translateY(1px);
}

/* =========================================================
   举报弹窗遮罩
========================================================= */

.report-overlay {
  position: fixed;

  inset: 0;

  z-index: 9999;

  display: flex;

  align-items: center;
  justify-content: center;

  padding: 20px;

  background: rgba(0, 0, 0, 0.48);
}

/* =========================================================
   举报弹窗
========================================================= */

.report-dialog {
  position: relative;

  width: 100%;
  max-width: 520px;

  max-height: calc(100vh - 40px);

  overflow-y: auto;

  padding: 24px;

  border-radius: 14px;

  background: #fff;

  box-shadow:
    0 20px 60px
    rgba(0, 0, 0, 0.2);
}

/* =========================================================
   举报标题
========================================================= */

.report-header {
  display: flex;

  align-items: center;

  justify-content: space-between;

  margin-bottom: 20px;
}

.report-header h2 {
  margin: 0;

  font-size: 20px;

  font-weight: 600;

  color: #222;
}

.report-close {
  width: 32px;
  height: 32px;

  padding: 0;

  border: none;

  border-radius: 50%;

  background: #f5f5f5;

  color: #666;

  font-size: 22px;

  line-height: 32px;

  cursor: pointer;
}

.report-close:hover {
  background: #eee;
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

  gap: 16px;

  padding: 12px 14px;

  margin-bottom: 22px;

  border-radius: 8px;

  background: #f7f7f7;
}

.report-product-name {
  min-width: 0;

  overflow: hidden;

  text-overflow: ellipsis;

  white-space: nowrap;

  font-size: 14px;

  color: #333;
}

.report-product-price {
  flex-shrink: 0;

  font-size: 15px;

  font-weight: 600;

  color: #f04444;
}

/* =========================================================
   举报表单
========================================================= */

.report-form-item {
  position: relative;

  margin-bottom: 20px;
}

.report-form-item > label {
  display: block;

  margin-bottom: 10px;

  font-size: 14px;

  font-weight: 500;

  color: #333;
}

.report-required {
  margin-left: 3px;

  color: #f04444;
}

.report-optional {
  font-size: 12px;

  font-weight: normal;

  color: #999;
}

/* =========================================================
   举报原因
========================================================= */

.report-reasons {
  display: grid;

  grid-template-columns: 1fr 1fr;

  gap: 10px;
}

.report-reason {
  display: flex;

  align-items: center;

  gap: 8px;

  padding: 11px 12px;

  border: 1px solid #e5e5e5;

  border-radius: 7px;

  background: #fff;

  color: #555;

  font-size: 13px;

  cursor: pointer;

  transition:
    border-color 0.2s,
    background 0.2s;
}

.report-reason:hover {
  border-color: #bbb;
}

.report-reason.active {
  border-color: #409eff;

  background: #f0f7ff;

  color: #2563eb;
}

.report-reason input {
  margin: 0;

  accent-color: #409eff;
}

/* =========================================================
   举报说明
========================================================= */

.report-form-item textarea {
  box-sizing: border-box;

  width: 100%;

  min-height: 110px;

  padding: 11px 12px;

  border: 1px solid #ddd;

  border-radius: 7px;

  outline: none;

  resize: vertical;

  font-family: inherit;

  font-size: 13px;

  line-height: 1.6;

  color: #333;

  transition: border-color 0.2s;
}

.report-form-item textarea:focus {
  border-color: #409eff;
}

.report-count {
  position: absolute;

  right: 10px;
  bottom: 9px;

  font-size: 12px;

  color: #aaa;
}

/* =========================================================
   举报错误
========================================================= */

.report-error {
  padding: 10px 12px;

  margin-bottom: 16px;

  border-radius: 6px;

  background: #fff2f2;

  color: #f04444;

  font-size: 13px;

  line-height: 1.5;
}

/* =========================================================
   举报操作
========================================================= */

.report-actions {
  display: flex;

  justify-content: flex-end;

  gap: 10px;

  padding-top: 4px;
}

.report-cancel,
.report-submit {
  min-width: 90px;

  height: 40px;

  padding: 0 18px;

  border-radius: 7px;

  font-size: 14px;

  cursor: pointer;
}

.report-cancel {
  border: 1px solid #ddd;

  background: #fff;

  color: #555;
}

.report-cancel:hover:not(:disabled) {
  background: #f5f5f5;
}

.report-submit {
  border: none;

  background: #409eff;

  color: #fff;
}

.report-submit:hover:not(:disabled) {
  background: #337ecc;
}

.report-cancel:disabled,
.report-submit:disabled {
  opacity: 0.6;

  cursor: not-allowed;
}

/* =========================================================
   加载失败
========================================================= */

.empty-actions {
  display: flex;

  justify-content: center;

  gap: 10px;

  margin-top: 16px;
}

/* =========================================================
   移动端
========================================================= */

@media (max-width: 768px) {
  .detail-grid {
    grid-template-columns: 1fr;

    gap: 24px;
  }

  .detail-media {
    min-height: 300px;
  }

  .detail-image {
    height: 300px;
  }

  .image-nav {
    width: 38px;
    height: 38px;

    font-size: 30px;
  }

  .image-nav-prev {
    left: 10px;
  }

  .image-nav-next {
    right: 10px;
  }

  .image-thumbnail {
    flex-basis: 64px;

    width: 64px;
    height: 64px;
  }

  .detail-title {
    font-size: 24px;
  }

  .detail-price {
    font-size: 26px;
  }

  .detail-actions {
    flex-direction: column;

    align-items: stretch;
  }

  .detail-actions .btn,
  .btn-report {
    width: 100%;
  }

  .empty-actions {
    flex-wrap: wrap;
  }

  .report-reasons {
    grid-template-columns: 1fr;
  }

  .report-dialog {
    padding: 20px;

    max-height: calc(100vh - 24px);
  }

  .report-overlay {
    padding: 12px;
  }

  .report-actions {
    flex-direction: column-reverse;
  }

  .report-cancel,
  .report-submit {
    width: 100%;
  }
}
</style>
