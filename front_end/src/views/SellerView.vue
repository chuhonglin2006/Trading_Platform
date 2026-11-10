<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { useMarketStore } from '../stores/market'
import { useToast } from '../composables/useToast'
import { ICON_FLAG, ICON_BOX } from '../utils/icons'
import ProductCard from '../components/ProductCard.vue'

const props = defineProps({
  id: {
    type: [String, Number],
    required: true,
  },
})

const router = useRouter()
const userStore = useUserStore()
const marketStore = useMarketStore()
const { show } = useToast()

const flagMarkup = `<svg viewBox="0 0 24 24" fill="none">${ICON_FLAG}</svg>`
const boxMarkup = `<svg viewBox="0 0 24 24" fill="none">${ICON_BOX}</svg>`

const loading = ref(true)
const loadError = ref('')

const seller = ref({
  id: null,
  name: '用户',
  campus: '—',
  score: 100,
  ipProvince: '未知',
})

const sellerProducts = ref([])

// =========================
// 当前查看的是否是自己
// =========================

const isSelf = computed(() => {
  if (!userStore.currentUser) {
    return false
  }

  if (
    props.id === undefined ||
    props.id === null ||
    props.id === ''
  ) {
    return false
  }

  return (
    String(userStore.currentUser.id) ===
    String(props.id)
  )
})

// =========================
// 校验卖家 ID
// =========================

function getSellerId() {
  if (
    props.id === undefined ||
    props.id === null ||
    props.id === ''
  ) {
    throw new Error('卖家 ID 无效')
  }

  const sellerId = Number(props.id)

  if (
    !Number.isFinite(sellerId) ||
    sellerId <= 0
  ) {
    throw new Error('卖家 ID 无效')
  }

  return sellerId
}

// =========================
// 加载卖家
// =========================

async function loadSeller() {
  loading.value = true
  loadError.value = ''

  sellerProducts.value = []

  try {
    const sellerId = getSellerId()

    console.log(
      '========== 加载卖家 =========='
    )

    console.log(
      '卖家 ID:',
      sellerId
    )

    console.log(
      '当前用户 ID:',
      userStore.currentUser?.id
    )

    console.log(
      '是否自己:',
      isSelf.value
    )

    console.log(
      '=============================='
    )

    // =========================
    // 自己
    // =========================

    if (isSelf.value) {
      seller.value = {
        id: userStore.currentUser.id,

        name:
          userStore.currentUser.username ||
          userStore.currentUser.name ||
          '用户',

        campus:
          userStore.currentUser.campus ||
          '—',

        score: Number(
          userStore.currentUser.score ??
          userStore.currentUser.credit_score ??
          100
        ),

        ipProvince:
          userStore.currentUser.ipProvince ||
          userStore.currentUser.ip_province ||
          '未知',
      }
    }

    // =========================
    // 其他用户
    // =========================

    else {
      seller.value =
        await marketStore.fetchSellerInfo(
          sellerId
        )
    }

    // =========================
    // 获取该卖家的商品
    // =========================

    sellerProducts.value =
      await marketStore.fetchSellerProducts(
        sellerId
      )

  } catch (error) {
    console.error(
      '加载卖家页面失败:',
      error
    )

    loadError.value =
      error?.response?.data?.detail ||
      error?.message ||
      '卖家信息加载失败'

    sellerProducts.value = []

  } finally {
    loading.value = false
  }
}

// =========================
// 打开商品详情
// =========================

function openDetail(pid) {
  if (
    pid === undefined ||
    pid === null ||
    pid === ''
  ) {
    return
  }

  router.push({
    name: 'detail',
    params: {
      id: pid,
    },
  })
}

// =========================
// 收藏
// =========================

async function toggleFav(pid) {
  if (!userStore.currentUser) {
    router.push({
      name: 'auth',
    })

    return
  }

  try {
    await marketStore.toggleFavorite(pid)

  } catch (error) {
    show(
      error?.message ||
      '收藏操作失败'
    )
  }
}

// =========================
// 举报
// =========================

const showReportForm = ref(false)
const reportReason = ref('')
const reportError = ref('')
const reporting = ref(false)

function openReport() {
  if (!userStore.currentUser) {
    router.push({
      name: 'auth',
    })

    return
  }

  showReportForm.value = true
  reportError.value = ''
  reportReason.value = ''
}

async function submitReport() {
  if (
    !reportReason.value.trim()
  ) {
    reportError.value =
      '请填写举报原因'

    return
  }

  if (reporting.value) {
    return
  }

  reporting.value = true

  try {
    const sellerId =
      getSellerId()

    await marketStore.submitReport({
      targetType: 'user',
      targetId: sellerId,
      reason:
        reportReason.value.trim(),
    })

    showReportForm.value = false
    reportReason.value = ''
    reportError.value = ''

    show(
      '举报已提交，我们会尽快核实处理'
    )

  } catch (error) {
    reportError.value =
      error?.response?.data?.detail ||
      error?.message ||
      '举报提交失败'

  } finally {
    reporting.value = false
  }
}

// =========================
// 生命周期
// =========================

onMounted(loadSeller)

watch(
  () => props.id,
  () => {
    loadSeller()
  }
)
</script>

<template>
  <div class="container">

    <!-- 返回 -->
    <div class="breadcrumb">
      <button @click="router.back()">
        ← 返回
      </button>
    </div>

    <!-- 卖家信息 -->
    <div class="seller-profile-head">

      <div class="profile-avatar">
        {{
          seller.name
            ? seller.name.slice(0, 1)
            : '用'
        }}
      </div>

      <div class="seller-profile-info">

        <p class="profile-name">
          {{ seller.name }}
        </p>

        <p class="profile-sub">
          {{ seller.campus }}
          ·
          信用分 {{ seller.score }}
          ·
          IP：{{ seller.ipProvince || '未知' }}
        </p>

      </div>

      <!-- 自己不显示举报 -->
      <button
        v-if="!isSelf"
        class="btn btn-ghost report-btn"
        @click="openReport"
        v-html="
          flagMarkup +
          '<span>举报</span>'
        "
      ></button>

    </div>

    <!-- 举报表单 -->
    <div
      v-if="showReportForm"
      class="form-card report-panel"
    >

      <p class="sales-title">
        举报该用户
      </p>

      <div
        v-if="reportError"
        class="form-error"
      >
        {{ reportError }}
      </div>

      <div class="field">

        <label>
          举报原因
        </label>

        <textarea
          v-model="reportReason"
          rows="3"
          placeholder="请描述具体问题，例如商品与描述严重不符、涉嫌诈骗等"
        ></textarea>

      </div>

      <div
        style="
          display: flex;
          gap: 10px;
        "
      >

        <button
          class="btn btn-ghost"
          style="flex: 1"
          @click="
            showReportForm = false
          "
        >
          取消
        </button>

        <button
          class="btn btn-primary"
          style="flex: 1"
          :disabled="reporting"
          @click="submitReport"
        >
          {{
            reporting
              ? '提交中...'
              : '提交举报'
          }}
        </button>

      </div>

    </div>

    <!-- 商品标题 -->
    <p
      class="page-sub"
      style="margin: 28px 0 16px"
    >
      TA 发布的商品
      （{{ sellerProducts.length }}）
    </p>

    <!-- 加载 -->
    <div
      v-if="loading"
      class="loading"
    >
      正在加载卖家信息...
    </div>

    <!-- 错误 -->
    <div
      v-else-if="loadError"
      class="empty-state"
    >
      <p>
        {{ loadError }}
      </p>
    </div>

    <!-- 商品 -->
    <div
      v-else-if="
        sellerProducts.length
      "
      class="grid"
    >

      <ProductCard
        v-for="p in sellerProducts"
        :key="p.id"
        :product="p"
        :is-favorite="
          marketStore.favorites.has(p.id)
        "
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
        v-html="boxMarkup"
      ></div>

      <p>
        这位同学还没有发布过闲置
      </p>

    </div>

  </div>
</template>
