import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { productsApi } from '../api/products.js'
import { favoritesApi } from '../api/favorites.js'
import { ordersApi } from '../api/orders.js'
import { salesApi } from '../api/sales.js'
import { reportsApi } from '../api/reports.js'
import { usersApi } from '../api/users.js'
import { categoriesApi } from '../api/categories.js'
import { announcementsApi } from '../api/announcements.js'
import { useUserStore } from './user.js'
import { clearUserData } from '../utils/session.js'

function readArray(key) {
  try {
    const value = localStorage.getItem(key)
    const parsed = value ? JSON.parse(value) : []
    return Array.isArray(parsed) ? parsed : []
  } catch {
    localStorage.removeItem(key)
    return []
  }
}

function normalizeList(result) {
  // 兼容 FastAPI 直接返回数组、常见分页结构和 { data: [...] } 包装。
  if (Array.isArray(result)) return result

  const candidates = [
    result?.data,
    result?.items,
    result?.results,
    result?.products,
    result?.list,
    result?.categories,
    result?.orders,
    result?.favorites,
    result?.announcements,
  ]

  for (const candidate of candidates) {
    if (Array.isArray(candidate)) return candidate
  }

  // 有些接口会再包一层 data，例如 { data: { items: [...] } }。
  if (result?.data && typeof result.data === 'object') {
    return normalizeList(result.data)
  }

  return []
}

function unwrapData(result) {
  let value = result
  // 兼容 { code, data: ... } 以及少数多层包装的接口返回。
  for (let depth = 0; depth < 3; depth += 1) {
    if (
      value &&
      typeof value === 'object' &&
      !Array.isArray(value) &&
      value.id == null &&
      value.data != null
    ) {
      value = value.data
    } else {
      break
    }
  }
  return value
}

function assertSuccess(result, fallbackMessage) {
  if (result?.code !== undefined && result.code !== 200) {
    throw new Error(result.message || fallbackMessage)
  }

  return result
}

export const useMarketStore = defineStore('market', () => {
  const userStore = useUserStore()

  // =========================
  // 商品
  // =========================

  const products = ref([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const loadingMore = ref(false)

  // =========================
  // 我的商品
  // =========================

  const myProducts = ref([])
  const myProductsTotal = ref(0)
  const myProductsPage = ref(1)
  const myProductsPageSize = ref(20)
  const myProductsLoadingMore = ref(false)

  // =========================
  // 本地数据
  // =========================

  const favorites = ref(
    new Set(
      readArray('cm_favs')
        .map((id) => Number(id))
        .filter(Number.isFinite)
    )
  )

  const orders = ref(readArray('cm_orders'))
  const mySales = ref(readArray('cm_mysales'))
  const reports = ref(readArray('cm_reports'))

  // =========================
  // 搜索 / 分类
  // =========================

  const searchText = ref('')
  const activeCategory = ref('all')

  // =========================
  // 卖家缓存
  // =========================

  const sellerCache = ref(new Map())
  const sellerProductsCache = ref(new Map())

  // =========================
  // 分类 / 公告
  // =========================

  const categories = ref([])
  const announcements = ref([])

  // =========================
  // 分页
  // =========================

  const hasMore = computed(() => {
    return products.value.length < total.value
  })

  const myProductsHasMore = computed(() => {
    return myProducts.value.length < myProductsTotal.value
  })

  // =========================
  // 本地持久化
  // =========================

  function saveLocal(key, value) {
    if (!userStore.currentUser) return
    localStorage.setItem(key, JSON.stringify(value))
  }


  function persistLocal() {
    localStorage.setItem(
      'cm_favs',
      JSON.stringify([...favorites.value])
    )

    saveLocal('cm_orders', orders.value)

    localStorage.setItem(
      'cm_mysales',
      JSON.stringify(mySales.value)
    )

    localStorage.setItem(
      'cm_reports',
      JSON.stringify(reports.value)
    )
  }

    function resetUserData() {
    favorites.value = new Set()
    orders.value = []
    mySales.value = []
    reports.value = []
    myProducts.value = []
    myProductsTotal.value = 0
    myProductsPage.value = 1
    myProductsLoadingMore.value = false
    // 只清业务数据缓存，不动令牌（换账号时新账号的令牌刚写入）
    clearUserData()
  }
  // 用 watch 统一处理：退出登录、登录过期、被踢下线、换账号，
  // 不管走哪条路径，只要当前用户变了就清空
  watch(
    () => userStore.currentUser?.id ?? null,
    (newId, oldId) => {
      if (oldId !== null && newId !== oldId) {
        resetUserData()
      }
    }
  )

  // =========================
  // 商品数据转换
  // =========================

  function convertProduct(product = {}) {
    const category = product.category || {}
    const seller = product.seller || {}

    /*
     * 公共商品只从商品本身的 seller_id / seller.id 获取卖家。
     * 不根据当前登录用户推断卖家身份，否则缺失 seller_id 的其他用户商品
     * 可能被错误识别为自己的商品。仅 fetchMyProducts 会对本人商品兜底。
     */

    let sellerId =
      product.seller_id ??
      product.seller?.id ??
      seller.id ??
      null

    // 公共商品数据缺少 seller_id 时不能擅自认定为当前用户的商品。
    // 仅 fetchMyProducts 会在“我的商品”接口中安全地补充当前用户 ID。

    return {
      id: product.id,

      name: product.name || '',

      price: Number(product.price || 0),

      originalPrice: Number(product.original_price || 0),

      description: product.description || '',

      status: product.status || 'on_sale',

      reviewStatus: product.review_status || '',

      activeOrderStatus:
        product.active_order_status ??
        product.activeOrderStatus ??
        null,

      viewCount: Number(product.view_count || 0),

      campus: product.campus || '',

      publishProvince:
        product.publish_province ||
        product.publishProvince ||
        '未知',

      createdAt: product.created_at || null,

      images: Array.isArray(product.images)
        ? product.images
        : [],

      category:
        category.key ||
        product.category_key ||
        'all',

      categoryId:
        category.id ??
        product.category_id ??
        null,

      categoryName:
        category.name ||
        '未分类',

      sellerId: sellerId,

      sellerName:
        seller.username ||
        seller.name ||
        product.seller_name ||
        '用户',
    }
  }

  // =========================
  // 订单转换
  // =========================

  function convertOrder(order = {}) {
    return {
      ...order,

      id: order.id,

      productId:
        order.product_id ??
        order.productId,

      buyerId:
        order.buyer_id ??
        order.buyerId ??
        null,

      sellerId:
        order.seller_id ??
        order.sellerId ??
        null,

      name:
        order.product?.name ||
        order.product_name ||
        order.name ||
        '',

      price: Number(
        order.price ??
        order.product?.price ??
        0
      ),

      status:
        order.status ||
        'pending',

      createdAt:
        order.created_at ||
        order.createdAt ||
        '',

      sellerName:
        order.seller?.username ||
        order.seller_name ||
        order.sellerName ||
        '用户',

      product: order.product
        ? convertProduct(order.product)
        : undefined,
    }
  }

  // =========================
  // 销售转换
  // =========================

  function convertSale(sale = {}) {
    return {
      ...sale,

      id: sale.id,

      buyerName:
        sale.buyer_name ||
        sale.buyerName ||
        '用户',

      day:
        sale.day ||
        sale.created_at ||
        '',

      amount: Number(
        sale.amount ||
        sale.price ||
        0
      ),

      createdAt:
        sale.created_at ||
        sale.createdAt ||
        null,
    }
  }

  // =========================
  // 获取商品列表
  // =========================

  async function fetchProducts(
    currentPage = 1,
    currentPageSize = 20,
    append = false
  ) {
    const result = await productsApi.list({
      page: currentPage,
      page_size: currentPageSize,
    })

    assertSuccess(result, '获取商品失败')

    const converted =
      normalizeList(result).map(convertProduct)

    products.value = append
      ? [...products.value, ...converted]
      : converted

    total.value = Number(
      result?.total ??
      result?.data?.total ??
      products.value.length
    )

    page.value = Number(
      result?.page ??
      result?.data?.page ??
      currentPage
    )

    pageSize.value = Number(
      result?.page_size ??
      result?.data?.page_size ??
      currentPageSize
    )

    return result
  }

  // =========================
  // 搜索商品
  // =========================

  // 搜索请求序号：防止较早发出的慢请求覆盖较新的搜索结果。
  let searchSeq = 0

  async function searchProducts(productName) {
    const keyword = String(productName || '').trim()
    const seq = ++searchSeq

    if (!keyword) {
      return fetchProducts(1, pageSize.value, false)
    }

    const result = await productsApi.search(keyword)

    // 已经有更新的搜索发出时，忽略这个过期请求的结果。
    if (seq !== searchSeq) return result

    assertSuccess(result, '搜索商品失败')

    products.value = normalizeList(result).map(convertProduct)

    total.value = Number(
      result?.total ??
      result?.data?.total ??
      products.value.length
    )

    page.value = Number(result?.page ?? result?.data?.page ?? 1)

    return result
  }

  // =========================
  // 获取我的商品
  // =========================

  async function fetchMyProducts(
    currentPage = 1,
    currentPageSize = 20,
    append = false
  ) {
    const result = await productsApi.my({
      page: currentPage,
      page_size: currentPageSize,
    })

    assertSuccess(
      result,
      '获取我的商品失败'
    )

    const list =
      normalizeList(result)

    /*
     * 这里专门处理“我的商品”。
     *
     * 因为 /api/my 是当前用户自己的商品，
     * 所以即使后端暂时没有返回 seller_id，
     * 也可以安全使用当前登录用户 ID。
     */

    const converted = list.map((item) => {
      const convertedProduct =
        convertProduct(item)

      if (
        (convertedProduct.sellerId === null ||
          convertedProduct.sellerId === undefined) &&
        userStore.currentUser?.id !== undefined
      ) {
        convertedProduct.sellerId =
          userStore.currentUser.id
      }

      return convertedProduct
    })

    myProducts.value = append
      ? [...myProducts.value, ...converted]
      : converted

    myProductsTotal.value = Number(
      result?.total ??
      result?.data?.total ??
      myProducts.value.length
    )

    myProductsPage.value = Number(
      result?.page ??
      result?.data?.page ??
      currentPage
    )

    myProductsPageSize.value = Number(
      result?.page_size ??
      result?.data?.page_size ??
      currentPageSize
    )

    return result
  }

  // =========================
  // 加载更多商品
  // =========================

  async function loadMoreProducts() {
    if (
      loadingMore.value ||
      !hasMore.value
    ) {
      return
    }

    loadingMore.value = true

    try {
      await fetchProducts(
        page.value + 1,
        pageSize.value,
        true
      )
    } finally {
      loadingMore.value = false
    }
  }

  // =========================
  // 加载更多我的商品
  // =========================

  async function loadMoreMyProducts() {
    if (
      myProductsLoadingMore.value ||
      !myProductsHasMore.value
    ) {
      return
    }

    myProductsLoadingMore.value = true

    try {
      await fetchMyProducts(
        myProductsPage.value + 1,
        myProductsPageSize.value,
        true
      )
    } finally {
      myProductsLoadingMore.value = false
    }
  }

  // =========================
  // 商品详情
  // =========================

  async function fetchProductDetail(productId) {
    if (
      productId === undefined ||
      productId === null ||
      productId === ''
    ) {
      throw new Error('商品 ID 无效')
    }

    const result =
      await productsApi.detail(productId)

    assertSuccess(
      result,
      '获取商品详情失败'
    )

    const detail = unwrapData(result)

    if (!detail || typeof detail !== 'object' || detail.id == null) {
      throw new Error('商品详情接口未返回有效商品数据')
    }

    const converted = convertProduct(detail)

    const index =
      products.value.findIndex(
        (item) =>
          String(item.id) ===
          String(productId)
      )

    if (index >= 0) {
      products.value[index] =
        converted
    }

    const myIndex =
      myProducts.value.findIndex(
        (item) =>
          String(item.id) ===
          String(productId)
      )

    if (myIndex >= 0) {
      myProducts.value[myIndex] =
        converted
    }

    return converted
  }

  // =========================
  // 上一页 / 下一页
  // =========================

  async function nextPage() {
    const maxPage =
      Math.ceil(
        total.value /
        pageSize.value
      )

    if (page.value < maxPage) {
      await fetchProducts(
        page.value + 1,
        pageSize.value,
        false
      )
    }
  }

  async function previousPage() {
    if (page.value > 1) {
      await fetchProducts(
        page.value - 1,
        pageSize.value,
        false
      )
    }
  }

  // =========================
  // 商品筛选
  // =========================

  const filteredProducts = computed(() => {
    return products.value.filter((product) => {
      if (
        activeCategory.value !== 'all' &&
        product.category !== activeCategory.value
      ) {
        return false
      }
      return true
    })
  })

  // =========================
  // 根据商品 ID 获取商品
  // =========================

  function productById(id) {
    return (
      products.value.find(
        (product) =>
          String(product.id) ===
          String(id)
      ) ||
      myProducts.value.find(
        (product) =>
          String(product.id) ===
          String(id)
      )
    )
  }

  // =========================
  // 获取卖家信息
  // =========================

  async function fetchSellerInfo(sellerId) {
    /*
     * 严格禁止把商品 ID 当卖家 ID。
     */

    if (
      sellerId === undefined ||
      sellerId === null ||
      sellerId === ''
    ) {
      throw new Error('卖家 ID 无效')
    }

    const numericSellerId =
      Number(sellerId)

    if (
      !Number.isFinite(numericSellerId) ||
      numericSellerId <= 0
    ) {
      throw new Error('卖家 ID 无效')
    }

    const key =
      String(numericSellerId)

    if (
      sellerCache.value.has(key)
    ) {
      return sellerCache.value.get(key)
    }

    const result =
      await usersApi.detail(
        numericSellerId
      )

    assertSuccess(
      result,
      '获取卖家信息失败'
    )

    const data =
      result?.data ||
      result?.user ||
      result

    const seller = {
      id:
        data?.id ??
        numericSellerId,

      name:
        data?.username ||
        data?.name ||
        '用户',

      campus:
        data?.campus ||
        '—',

      score: Number(
        data?.score ??
        data?.credit_score ??
        100
      ),

      ipProvince:
        data?.ip_province ||
        data?.ipProvince ||
        '未知',
    }

    sellerCache.value.set(
      key,
      seller
    )

    return seller
  }

  // =========================
  // 获取卖家商品
  // =========================

  async function fetchSellerProducts(
    sellerId,
    currentPage = 1,
    currentPageSize = 20
  ) {
    if (
      sellerId === undefined ||
      sellerId === null ||
      sellerId === ''
    ) {
      throw new Error('卖家 ID 无效')
    }

    const numericSellerId =
      Number(sellerId)

    if (
      !Number.isFinite(numericSellerId) ||
      numericSellerId <= 0
    ) {
      throw new Error('卖家 ID 无效')
    }

    const result =
      await productsApi.bySeller(
        numericSellerId,
        {
          page: currentPage,
          page_size: currentPageSize,
        }
      )

    assertSuccess(
      result,
      '获取卖家商品失败'
    )

    const list =
      normalizeList(result)
        .map(convertProduct)

    sellerProductsCache.value.set(
      String(numericSellerId),
      list
    )

    return list
  }

  // =========================
  // 获取商品对应卖家
  // =========================

  function sellerOf(product) {
    if (!product) {
      return {
        id: null,
        name: '用户',
        campus: '—',
        score: 100,
        ipProvince: '未知',
      }
    }

    return {
      id:
        product.sellerId ??
        null,

      name:
        product.sellerName ||
        '用户',

      campus:
        product.campus ||
        '—',

      score: 100,
      ipProvince: '未知',
    }
  }

  // =========================
  // 根据卖家 ID 获取商品
  // =========================

  function productsBySeller(sellerId) {
    return (
      sellerProductsCache.value.get(
        String(sellerId)
      ) ||
      products.value.filter(
        (product) =>
          String(product.sellerId) ===
          String(sellerId)
      )
    )
  }

  // =========================
  // 根据 ID 获取缓存卖家
  // =========================

  function sellerInfoById(sellerId) {
    return (
      sellerCache.value.get(
        String(sellerId)
      ) || null
    )
  }

  // =========================
  // 销售统计
  // =========================

  const completedSales = computed(() => {
    return mySales.value.filter(
      sale => sale.status === 'completed'
    )
  })

  const soldCount = computed(() => {
    return myProducts.value.filter(
      product => product.status === 'sold'
    ).length
  })

  const totalRevenue = computed(() => {
    return completedSales.value.reduce(
      (sum, sale) =>
        sum +
        Number(sale.amount || 0),
      0
    )
  })

  // =========================
  // 收藏
  // =========================

  async function fetchFavorites() {
    const result =
      await favoritesApi.list()

    assertSuccess(
      result,
      '获取收藏失败'
    )

    const ids = normalizeList(result)
      .map((item) => {
        if (item && typeof item === 'object') {
          return item.product_id ?? item.productId ?? item.id
        }
        return item
      })

    favorites.value = new Set(
      ids
        .map(Number)
        .filter((id) => Number.isFinite(id) && id > 0)
    )

    localStorage.setItem(
      'cm_favs',
      JSON.stringify([
        ...favorites.value,
      ])
    )

    return result
  }

  function clearFavorites() {
    favorites.value = new Set()
    localStorage.removeItem(
      'cm_favs'
    )
  }

  async function toggleFavorite(id) {
    const productId = Number(id)

    if (
      !Number.isFinite(productId)
    ) {
      throw new Error(
        '商品 ID 无效'
      )
    }

    const isFavorite =
      favorites.value.has(productId)

    const result = isFavorite
      ? await favoritesApi.remove(
          productId
        )
      : await favoritesApi.add(
          productId
        )

    assertSuccess(
      result,
      isFavorite
        ? '取消收藏失败'
        : '收藏失败'
    )

    const next =
      new Set(favorites.value)

    if (isFavorite) {
      next.delete(productId)
    } else {
      next.add(productId)
    }

    favorites.value = next

    localStorage.setItem(
      'cm_favs',
      JSON.stringify([...next])
    )

    return result
  }

  // =========================
  // 订单
  // =========================

  async function fetchOrders() {
    const result =
      await ordersApi.listMine()

    assertSuccess(
      result,
      '获取订单失败'
    )

    orders.value =
      normalizeList(result)
        .map(convertOrder)

    localStorage.setItem(
      'cm_orders',
      JSON.stringify(
        orders.value
      )
    )

    return result
  }

  async function createOrder(
    product,
    currentUser
  ) {
    if (!product?.id) {
      throw new Error(
        '商品信息无效'
      )
    }

    const result =
      await ordersApi.create({
        product_id: Number(
          product.id
        ),
      })

    assertSuccess(
      result,
      '创建订单失败'
    )

    const orderData = unwrapData(result)
    const order =
      orderData && typeof orderData === 'object' && orderData.id != null
        ? convertOrder(orderData)
        : null

    if (order) {
      orders.value.unshift(order)
    } else {
      await fetchOrders()
    }

    localStorage.setItem(
      'cm_orders',
      JSON.stringify(
        orders.value
      )
    )

    return result
  }

  async function cancelOrder(orderId) {
    const result =
      await ordersApi.cancel(orderId)

    assertSuccess(
      result,
      '取消订单失败'
    )

    await fetchOrders()

    return result
  }

  async function completeOrder(orderId) {
    const result =
      await ordersApi.complete(orderId)

    assertSuccess(
      result,
      '完成订单失败'
    )

    await fetchOrders()

    return result
  }

  // =========================
  // 销售记录
  // =========================

  async function fetchMySales() {
    const result =
      await salesApi.listMine()

    assertSuccess(
      result,
      '获取销售记录失败'
    )

    mySales.value =
      normalizeList(result)
        .map(convertSale)

    localStorage.setItem(
      'cm_mysales',
      JSON.stringify(
        mySales.value
      )
    )

    return result
  }

  async function markAsSold(product) {
    if (!product?.id) {
      throw new Error(
        '商品信息无效'
      )
    }

    const result =
      await productsApi.markSold(
        product.id
      )

    assertSuccess(
      result,
      '标记商品已售失败'
    )

    const target =
      productById(product.id)

    if (target) {
      target.status = 'sold'
    }

    await Promise.allSettled([
      fetchMyProducts(
        myProductsPage.value || 1,
        myProductsPageSize.value || 20,
        false
      ),

      fetchMySales(),
    ])

    return result
  }

  async function seedMySalesIfNeeded() {
    if (
      localStorage.getItem(
        'cm_mysales'
      )
    ) {
      localStorage.removeItem(
        'cm_mysales'
      )
    }

    try {
      await fetchMySales()
    } catch (error) {
      console.error(
        '获取销售记录失败：',
        error
      )

      mySales.value = []
    }
  }

  // =========================
  // 举报
  // =========================

  async function submitReport({
    targetType,
    targetId,
    reason,
  }) {
    const result =
      await reportsApi.create({
        target_type: targetType,
        target_id: Number(targetId),
        reason,
      })

    assertSuccess(
      result,
      '提交举报失败'
    )

    return result
  }

  // =========================
  // 分类
  // =========================

  async function fetchCategories() {
    const result =
      await categoriesApi.list()

    assertSuccess(
      result,
      '获取商品分类失败'
    )

    categories.value =
      normalizeList(result)

    return result
  }

  // =========================
  // 公告
  // =========================

  async function fetchAnnouncements() {
    const result =
      await announcementsApi.list()

    assertSuccess(
      result,
      '获取公告失败'
    )

    announcements.value =
      normalizeList(result).sort(
        (a, b) => {
          const aTime =
            new Date(
              a?.created_at ||
              a?.createdAt ||
              0
            ).getTime()

          const bTime =
            new Date(
              b?.created_at ||
              b?.createdAt ||
              0
            ).getTime()

          return bTime - aTime
        }
      )

    return result
  }

  // =========================
  // 发布商品
  // =========================

  function publish(newProduct) {
    if (newProduct) {
      products.value.unshift(
        convertProduct(newProduct)
      )
    }
  }

  // =========================
  // 购买
  // =========================

  async function buy(
    product,
    currentUser
  ) {
    return createOrder(
      product,
      currentUser
    )
  }

  // =========================
  // 对外暴露
  // =========================

  return {
    products,
    total,
    page,
    pageSize,
    loadingMore,
    hasMore,
    filteredProducts,

    myProducts,
    myProductsTotal,
    myProductsPage,
    myProductsPageSize,
    myProductsLoadingMore,
    myProductsHasMore,

    fetchProducts,
    searchProducts,
    fetchMyProducts,
    fetchProductDetail,

    loadMoreProducts,
    loadMoreMyProducts,

    nextPage,
    previousPage,

    productById,
    productsBySeller,

    fetchSellerProducts,
    sellerOf,
    sellerInfoById,
    fetchSellerInfo,

    searchText,
    activeCategory,

    categories,
    fetchCategories,

    announcements,
    fetchAnnouncements,

    favorites,
    fetchFavorites,
    toggleFavorite,
    clearFavorites,

    orders,
    fetchOrders,
    createOrder,
    cancelOrder,
    completeOrder,
    buy,

    mySales,
    completedSales,
    soldCount,
    totalRevenue,
    fetchMySales,
    markAsSold,
    seedMySalesIfNeeded,

    publish,

    reports,
    submitReport,
  }
})
