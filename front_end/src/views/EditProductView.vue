<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMarketStore } from '../stores/market'
import { productsApi } from '../api/products'
import { categoriesApi } from '../api/categories'
import { CAMPUSES } from '../constants/campus'

const route = useRoute()
const router = useRouter()
const marketStore = useMarketStore()

const loading = ref(true)
const saving = ref(false)
const error = ref('')
const categoriesLoading = ref(true)

const categories = ref([])

const campuses = CAMPUSES

const form = ref({
  name: '',
  price: '',
  original_price: '',
  description: '',
  campus: '',
  category_id: ''
})

/**
 * 加载分类
 */
async function loadCategories() {
  categoriesLoading.value = true

  try {
    const result = await categoriesApi.list()

    console.log('分类接口返回:', result)

    if (
      result?.code !== undefined &&
      result.code !== 200
    ) {
      throw new Error(
        result.message || '获取商品分类失败'
      )
    }

    // 兼容几种常见返回结构
    if (Array.isArray(result?.data)) {
      categories.value = result.data
    } else if (Array.isArray(result)) {
      categories.value = result
    } else {
      categories.value = []
    }

  } catch (e) {
    console.error('加载分类失败:', e)

    error.value =
      e?.response?.data?.detail ||
      e?.message ||
      '商品分类加载失败'

  } finally {
    categoriesLoading.value = false
  }
}

/**
 * 加载商品
 */
async function loadProduct() {
  loading.value = true
  error.value = ''

  try {
    let item = marketStore.myProducts.find(
      p => String(p.id) === String(route.params.id)
    )

    // 如果 Pinia 里面没有，就请求本人商品详情
    if (!item) {
      const result = await productsApi.myDetail(
        route.params.id
      )

      if (
        result?.code !== undefined &&
        result.code !== 200
      ) {
        throw new Error(
          result.message || '加载商品失败'
        )
      }

      const raw = result.data

      item = {
        ...raw,

        originalPrice:
          raw.original_price,

        categoryId:
          raw.category_id ??
          raw.category?.id
      }
    }

    console.log('当前商品:', item)

    form.value = {
      name: item.name || '',

      price:
        item.price ??
        '',

      original_price:
        item.originalPrice ??
        item.original_price ??
        '',

      description:
        item.description ||
        '',

      campus:
        item.campus ||
        '',

      category_id:
        item.categoryId ??
        item.category_id ??
        item.category?.id ??
        ''
    }

    console.log(
      '编辑表单:',
      form.value
    )

  } catch (e) {
    console.error(
      '加载商品失败:',
      e
    )

    error.value =
      e?.response?.data?.detail ||
      e?.message ||
      '无法加载商品，请确认本人商品详情接口已实现'

  } finally {
    loading.value = false
  }
}

/**
 * 保存商品
 */
async function save() {
  if (saving.value) return

  saving.value = true
  error.value = ''

  try {
    const data = {
      // 后端 ProductUpdate 要求 product_name
      product_name:
        form.value.name.trim(),

      price:
        Number(form.value.price),

      original_price:
        form.value.original_price === ''
          ? null
          : Number(form.value.original_price),

      description:
        form.value.description.trim(),

      campus:
        form.value.campus,

      category_id:
        Number(form.value.category_id),
    }

    console.log(
      '商品 ID:',
      route.params.id
    )

    console.log(
      '提交修改数据:',
      data
    )

    // 前端基本校验
    if (!data.product_name) {
      throw new Error(
        '请输入商品名称'
      )
    }

    if (!(data.price > 0)) {
      throw new Error(
        '请输入有效的商品价格'
      )
    }

    if (!data.category_id) {
      throw new Error(
        '请选择商品分类'
      )
    }

    if (!data.campus) {
      throw new Error(
        '请选择校区'
      )
    }

    // 提交修改
    const result =
      await productsApi.update(
        route.params.id,
        data
      )

    console.log(
      '修改商品返回:',
      result
    )

    if (
      result?.code !== undefined &&
      result.code !== 200
    ) {
      throw new Error(
        result.message ||
        '修改失败'
      )
    }

    // 修改成功后刷新我的商品
    await marketStore.fetchMyProducts(
      1,
      20
    )

    // 返回个人中心
    router.push({
      name: 'profile'
    })

  } catch (e) {
    console.error(
      '修改商品失败:',
      e
    )

    error.value =
      e?.response?.data?.detail ||
      e?.message ||
      '保存失败'

  } finally {
    saving.value = false
  }
}

/**
 * 页面加载
 *
 * 分类和商品可以同时加载
 */
onMounted(async () => {
  await Promise.all([
    loadCategories(),
    loadProduct()
  ])
})
</script>

<template>
  <main class="edit-page">

    <div class="page-header">
      <h1>修改商品</h1>

      <button
        type="button"
        class="back-button"
        @click="router.back()"
      >
        返回
      </button>
    </div>

    <!-- 页面加载 -->
    <div
      v-if="loading"
      class="loading"
    >
      正在加载商品...
    </div>

    <!-- 编辑表单 -->
    <form
      v-else-if="!error || form.name"
      class="edit-form"
      @submit.prevent="save"
    >

      <!-- 商品名称 -->
      <div class="form-item">

        <label for="product-name">
          商品名称
        </label>

        <input
          id="product-name"
          v-model="form.name"
          type="text"
          maxlength="100"
          placeholder="请输入商品名称"
          required
        />

      </div>

      <!-- 售价 -->
      <div class="form-item">

        <label for="product-price">
          售价
        </label>

        <input
          id="product-price"
          v-model.number="form.price"
          type="number"
          min="0.01"
          step="0.01"
          placeholder="请输入售价"
          required
        />

      </div>

      <!-- 原价 -->
      <div class="form-item">

        <label for="original-price">
          原价
        </label>

        <input
          id="original-price"
          v-model.number="form.original_price"
          type="number"
          min="0"
          step="0.01"
          placeholder="请输入原价"
        />

      </div>

      <!-- 商品描述 -->
      <div class="form-item">

        <label for="description">
          商品描述
        </label>

        <textarea
          id="description"
          v-model="form.description"
          rows="5"
          maxlength="1000"
          placeholder="请输入商品描述"
        ></textarea>

      </div>

      <!-- 校区 -->
      <div class="form-item">

        <label for="campus">
          校区
        </label>

        <select
          id="campus"
          v-model="form.campus"
          required
        >

          <option
            value=""
            disabled
          >
            请选择校区
          </option>

          <option
            v-for="campus in campuses"
            :key="campus"
            :value="campus"
          >
            {{ campus }}
          </option>

        </select>

      </div>

      <!-- 商品分类 -->
      <div class="form-item">

        <label for="category">
          商品分类
        </label>

        <select
          id="category"
          v-model="form.category_id"
          :disabled="categoriesLoading"
          required
        >

          <option
            value=""
            disabled
          >
            {{
              categoriesLoading
                ? '正在加载分类...'
                : '请选择商品分类'
            }}
          </option>

          <option
            v-for="category in categories"
            :key="category.id"
            :value="category.id"
          >
            {{ category.name }}
          </option>

        </select>

        <small
          v-if="!categoriesLoading && !categories.length"
          class="category-error"
        >
          暂无商品分类，请检查分类接口
        </small>

      </div>

      <!-- 错误提示 -->
      <p
        v-if="error"
        class="error"
      >
        {{ error }}
      </p>

      <!-- 操作按钮 -->
      <div class="actions">

        <button
          type="button"
          class="cancel-button"
          :disabled="saving"
          @click="router.back()"
        >
          取消
        </button>

        <button
          type="submit"
          class="save-button"
          :disabled="
            saving ||
            categoriesLoading ||
            !categories.length
          "
        >
          {{
            saving
              ? '保存中...'
              : '保存修改'
          }}
        </button>

      </div>

    </form>

    <!-- 加载失败 -->
    <div
      v-else
      class="error-page"
    >
      <p class="error">
        {{ error }}
      </p>

      <button
        type="button"
        @click="router.back()"
      >
        返回
      </button>
    </div>

  </main>
</template>

<style scoped>
.edit-page {
  max-width: 720px;
  margin: 30px auto;
  padding: 24px;
  box-sizing: border-box;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.page-header h1 {
  margin: 0;
  font-size: 28px;
}

.back-button {
  padding: 8px 14px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
}

.loading {
  padding: 40px 0;
  text-align: center;
  color: #6b7280;
}

.edit-form {
  display: grid;
  gap: 20px;
}

.form-item {
  display: grid;
  gap: 8px;
}

.form-item label {
  font-size: 15px;
  font-weight: 600;
}

input,
textarea,
select {
  width: 100%;
  box-sizing: border-box;
  padding: 11px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
  color: #111827;
  font-size: 14px;
  transition: border-color 0.2s;
}

input:focus,
textarea:focus,
select:focus {
  outline: none;
  border-color: #2563eb;
}

textarea {
  min-height: 120px;
  resize: vertical;
}

select {
  cursor: pointer;
}

select:disabled {
  cursor: not-allowed;
  background: #f3f4f6;
  color: #9ca3af;
}

.category-error {
  color: #dc2626;
  font-size: 13px;
}

.error {
  margin: 0;
  color: #dc2626;
  font-size: 14px;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 8px;
}

.actions button {
  min-width: 100px;
  padding: 10px 18px;
  border: 0;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}

.actions button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.cancel-button {
  background: #e5e7eb;
  color: #111827;
}

.save-button {
  background: #2563eb;
  color: #fff;
}

.error-page {
  text-align: center;
  padding: 40px 0;
}

.error-page button {
  margin-top: 12px;
  padding: 10px 18px;
  border: 0;
  border-radius: 8px;
  background: #2563eb;
  color: #fff;
  cursor: pointer;
}
</style>
