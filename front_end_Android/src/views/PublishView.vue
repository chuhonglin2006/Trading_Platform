<template>
  <div class="publish-page">

    <div class="publish-container">

      <!-- =========================
           页面标题
      ========================== -->
      <div class="page-header">
        <h1>发布商品</h1>
        <p>填写商品信息，上传商品图片，发布你的闲置商品</p>
      </div>


      <!-- =========================
           发布卡片
      ========================== -->
      <div class="publish-card">

        <!-- =========================
             商品图片
        ========================== -->
        <section class="form-section">

          <div class="section-title">
            <span>商品图片</span>

            <span class="required">*</span>

            <span class="image-count">
              {{ images.length }}/9
            </span>
          </div>


          <div class="image-tip">
            第一张图片为商品主图，支持 JPG、PNG、WEBP，单张最大 10MB
          </div>


          <div class="image-list">

            <!-- 已选择的图片 -->
            <div
              v-for="(image, index) in images"
              :key="image.id"
              class="image-item"
              :class="{ main: index === 0 }"
            >

              <img
                :src="image.preview"
                alt="商品图片"
              />


              <!-- 主图 -->
              <div
                v-if="index === 0"
                class="main-label"
              >
                主图
              </div>


              <!-- 删除 -->
              <button
                type="button"
                class="delete-image"
                @click="removeImage(index)"
              >
                ×
              </button>


              <!-- 设置主图 -->
              <button
                v-if="index !== 0"
                type="button"
                class="set-main"
                @click="setMainImage(index)"
              >
                设为主图
              </button>

            </div>


            <!-- 添加图片 -->
            <label
              v-if="images.length < 9"
              class="upload-box"
            >

              <input
                ref="fileInput"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                multiple
                hidden
                @change="handleImageChange"
              />

              <div class="upload-icon">
                +
              </div>

              <div class="upload-text">
                添加图片
              </div>

              <div class="upload-subtext">
                最多9张
              </div>

            </label>

          </div>


          <!-- 图片错误 -->
          <div
            v-if="imageError"
            class="error-message"
          >
            {{ imageError }}
          </div>

        </section>


        <!-- =========================
             商品基本信息
        ========================== -->
        <section class="form-section">

          <div class="section-title">
            商品信息
          </div>


          <!-- 商品名称 -->
          <div class="form-item">

            <label>
              商品名称
              <span class="required">*</span>
            </label>

            <input
              v-model.trim="form.product_name"
              type="text"
              maxlength="100"
              placeholder="请输入商品名称"
            />

            <div class="input-count">
              {{ form.product_name.length }}/100
            </div>

          </div>


          <!-- 商品分类 -->
          <div class="form-item">

            <label>
              商品分类
              <span class="required">*</span>
            </label>

            <select
              v-model="form.category_id"
              :disabled="categoriesLoading"
            >

              <option
                value=""
                disabled
              >
                {{
                  categoriesLoading
                    ? '正在加载商品分类...'
                    : '请选择商品分类'
                }}
              </option>

              <option
                v-for="category in marketStore.categories"
                :key="category.id"
                :value="category.id"
              >
                {{ category.name }}
              </option>

            </select>

            <div
              v-if="categoriesError"
              class="error-message"
            >
              {{ categoriesError }}
            </div>

          </div>


          <!-- =========================
               价格
          ========================== -->
          <div class="price-row">

            <!-- 售价 -->
            <div class="form-item">

              <label>
                售价
                <span class="required">*</span>
              </label>

              <div class="price-input">

                <span>¥</span>

                <input
                  v-model="form.price"
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="请输入售价"
                />

              </div>

            </div>


            <!-- 原价 -->
            <div class="form-item">

              <label>
                原价
              </label>

              <div class="price-input">

                <span>¥</span>

                <input
                  v-model="form.original_price"
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="可选"
                />

              </div>

            </div>

          </div>


          <!-- =========================
               校区
          ========================== -->
          <div class="form-item">

            <label>
              校区
              <span class="required">*</span>
            </label>

            <select v-model="form.campus">

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


          <!-- =========================
               商品描述
          ========================== -->
          <div class="form-item">

            <label>
              商品描述
              <span class="required">*</span>
            </label>

            <textarea
              v-model.trim="form.description"
              maxlength="1000"
              rows="7"
              placeholder="请输入商品详细描述，例如：

商品成色
购买时间
使用情况
是否有损坏
交易方式
其他需要说明的信息"
            />

            <div class="textarea-count">
              {{ form.description.length }}/1000
            </div>

          </div>

        </section>


        <!-- =========================
             审核提示
        ========================== -->
        <div class="review-notice">

          <div class="notice-icon">
            !
          </div>

          <div>

            <div class="notice-title">
              商品发布后需要经过审核
            </div>

            <div class="notice-text">
              请确保商品信息真实有效，不得发布违法、违规、虚假或不符合平台规定的商品。
            </div>

          </div>

        </div>


        <!-- =========================
             错误信息
        ========================== -->
        <div
          v-if="submitError"
          class="submit-error"
        >
          {{ submitError }}
        </div>


        <!-- =========================
             提交按钮
        ========================== -->
        <button
          type="button"
          class="submit-button"
          :disabled="submitting"
          @click="submit"
        >

          <span v-if="submitting">
            正在发布...
          </span>

          <span v-else>
            发布商品
          </span>

        </button>

      </div>

    </div>

  </div>
</template>


<script setup>

import {
  reactive,
  ref,
  onMounted,
  onBeforeUnmount
} from 'vue'

import { useRouter } from 'vue-router'
import { productsApi } from '../api/products'
import { useMarketStore } from '../stores/market'
import { CAMPUSES } from '../constants/campus'


const router = useRouter()

const marketStore = useMarketStore()


/*
|--------------------------------------------------------------------------
| 页面加载
|--------------------------------------------------------------------------
|
| 从后端数据库获取商品分类。
|
| 分类数据来源：
|
| categories 数据库表
|       ↓
| /api/products/categories
|       ↓
| categoriesApi
|       ↓
| marketStore.categories
|
|--------------------------------------------------------------------------
*/
const categoriesLoading = ref(false)

const categoriesError = ref('')


onMounted(async () => {

  categoriesLoading.value = true

  categoriesError.value = ''

  try {

    await marketStore.fetchCategories()

  } catch (error) {

    console.error(
      '获取商品分类失败:',
      error
    )

    categoriesError.value =
      error?.message ||
      '获取商品分类失败，请刷新页面重试'

  } finally {

    categoriesLoading.value = false

  }

})


/*
|--------------------------------------------------------------------------
| 校区
|--------------------------------------------------------------------------
*/
const campuses = CAMPUSES


/*
|--------------------------------------------------------------------------
| 表单
|--------------------------------------------------------------------------
*/
const form = reactive({

  product_name: '',

  price: '',

  original_price: '',

  description: '',

  category_id: '',

  campus: ''

})


/*
|--------------------------------------------------------------------------
| 图片
|--------------------------------------------------------------------------
|
| 每张图片：
|
| {
|     id,
|     file,
|     preview
| }
|
*/
const images = ref([])


/*
|--------------------------------------------------------------------------
| 状态
|--------------------------------------------------------------------------
*/
const submitting = ref(false)

const imageError = ref('')

const submitError = ref('')

const fileInput = ref(null)


/*
|--------------------------------------------------------------------------
| 图片选择
|--------------------------------------------------------------------------
*/
function handleImageChange(event) {

  imageError.value = ''

  const files = Array.from(
    event.target.files || []
  )


  if (files.length === 0) {
    return
  }


  /*
   * 最多9张
   */
  const remaining =
    9 - images.value.length


  if (remaining <= 0) {

    imageError.value =
      '最多只能上传9张图片'

    return
  }


  /*
   * 如果一次选择太多
   */
  const selectedFiles =
    files.slice(0, remaining)


  if (files.length > remaining) {

    imageError.value =
      `最多上传9张图片，本次只添加 ${remaining} 张`
  }


  /*
   * 遍历图片
   */
  for (const file of selectedFiles) {

    /*
     * 文件类型
     */
    const allowedTypes = [
      'image/jpeg',
      'image/png',
      'image/webp'
    ]


    if (!allowedTypes.includes(file.type)) {

      imageError.value =
        `${file.name} 不是支持的图片格式`

      continue
    }


    /*
     * 文件大小
     *
     * 10 MB
     */
    const maxSize =
      10 * 1024 * 1024


    if (file.size > maxSize) {

      imageError.value =
        `${file.name} 超过10MB`

      continue
    }


    /*
     * 生成本地预览
     */
    const preview =
      URL.createObjectURL(file)


    images.value.push({

      id:
        Date.now() +
        Math.random(),

      file,

      preview

    })
  }


  /*
   * 清空 input
   *
   * 允许再次选择相同文件。
   */
  if (fileInput.value) {

    fileInput.value.value = ''
  }

}


/*
|--------------------------------------------------------------------------
| 删除图片
|--------------------------------------------------------------------------
*/
function removeImage(index) {

  const image =
    images.value[index]


  if (image?.preview) {

    URL.revokeObjectURL(
      image.preview
    )
  }


  images.value.splice(
    index,
    1
  )

}


/*
|--------------------------------------------------------------------------
| 设置主图
|--------------------------------------------------------------------------
|
| 第一张图片永远是主图。
|
*/
function setMainImage(index) {

  if (
    index <= 0 ||
    index >= images.value.length
  ) {
    return
  }


  const image =
    images.value.splice(
      index,
      1
    )[0]


  images.value.unshift(image)

}


/*
|--------------------------------------------------------------------------
| 格式化 FastAPI 错误
|--------------------------------------------------------------------------
|
| 防止出现：
|
| [object Object]
|
*/
function formatError(error) {

  /*
   * Error 对象
   */
  if (error instanceof Error) {

    return error.message
  }


  /*
   * 字符串
   */
  if (typeof error === 'string') {

    return error
  }


  /*
   * FastAPI detail 数组
   */
  if (
    error &&
    Array.isArray(error.detail)
  ) {

    return error.detail
      .map(item => {

        const field =
          Array.isArray(item.loc)
            ? item.loc.join('.')
            : ''

        const message =
          item.msg || '参数错误'

        return field
          ? `${field}: ${message}`
          : message

      })
      .join('；')
  }


  /*
   * detail 字符串
   */
  if (
    error &&
    typeof error.detail === 'string'
  ) {

    return error.detail
  }


  /*
   * message 字符串
   */
  if (
    error &&
    typeof error.message === 'string'
  ) {

    return error.message
  }


  /*
   * 最后尝试 JSON
   */
  try {

    return JSON.stringify(
      error
    )

  } catch {

    return '发生未知错误'
  }

}


/*
|--------------------------------------------------------------------------
| 表单验证
|--------------------------------------------------------------------------
*/
function validateForm() {

  submitError.value = ''

  imageError.value = ''


  /*
   * 商品名称
   */
  if (!form.product_name) {

    submitError.value =
      '请输入商品名称'

    return false
  }


  /*
   * 名称长度
   */
  if (
    form.product_name.length > 100
  ) {

    submitError.value =
      '商品名称不能超过100个字符'

    return false
  }


  /*
   * 售价
   */
  if (
    form.price === '' ||
    form.price === null ||
    form.price === undefined
  ) {

    submitError.value =
      '请输入商品售价'

    return false
  }


  const price =
    Number(form.price)


  if (
    !Number.isFinite(price) ||
    price <= 0
  ) {

    submitError.value =
      '商品售价必须大于 0'

    return false
  }


  /*
   * 原价
   */
  if (
    form.original_price !== '' &&
    form.original_price !== null &&
    form.original_price !== undefined
  ) {

    const originalPrice =
      Number(form.original_price)


    if (
      !Number.isFinite(originalPrice) ||
      originalPrice <= 0
    ) {

      submitError.value =
        '商品原价必须大于 0'

      return false
    }
  }


  /*
   * 分类
   */
  if (
    form.category_id === '' ||
    form.category_id === null ||
    form.category_id === undefined
  ) {

    submitError.value =
      '请选择商品分类'

    return false
  }


  /*
   * 校区
   */
  if (!form.campus) {

    submitError.value =
      '请选择校区'

    return false
  }


  /*
   * 描述
   */
  if (!form.description) {

    submitError.value =
      '请输入商品描述'

    return false
  }


  /*
   * 图片
   */
  if (images.value.length === 0) {

    imageError.value =
      '请至少上传一张商品图片'

    return false
  }


  return true

}


/*
|--------------------------------------------------------------------------
| 发布商品
|--------------------------------------------------------------------------
*/
async function submit() {

  if (submitting.value) return


  if (!validateForm()) return


  submitting.value = true

  submitError.value = ''


  try {

    const formData =
      new FormData()


    formData.append(
      'product_name',
      form.product_name
    )


    formData.append(
      'price',
      String(form.price)
    )


    if (
      form.original_price !== '' &&
      form.original_price !== null &&
      form.original_price !== undefined
    ) {

      formData.append(
        'original_price',
        String(form.original_price)
      )

    }


    formData.append(
      'description',
      form.description
    )


    formData.append(
      'category_id',
      String(form.category_id)
    )


    formData.append(
      'campus',
      form.campus
    )


    for (
      const image
      of images.value
    ) {

      formData.append(
        'images',
        image.file,
        image.file.name
      )

    }


    const result =
      await productsApi.create(
        formData
      )


    if (
      result?.code !== undefined &&
      result.code !== 200
    ) {

      throw new Error(
        result.message ||
        '商品发布失败'
      )

    }


    const successMessage =
      result?.message ||
      '商品发布成功，等待后台审核'


    alert(successMessage)


    /*
     * 释放图片预览
     */
    for (
      const image
      of images.value
    ) {

      if (image.preview) {

        URL.revokeObjectURL(
          image.preview
        )

      }

    }


    images.value = []


    resetForm()


    await router.push({
      name: 'home'
    })


  } catch (error) {

    console.error(
      '发布商品失败:',
      error
    )


    submitError.value =
      formatError(
        error?.response?.data ||
        error
      )


  } finally {

    submitting.value = false

  }

}


/*
|--------------------------------------------------------------------------
| 重置表单
|--------------------------------------------------------------------------
*/
function resetForm() {

  form.product_name = ''

  form.price = ''

  form.original_price = ''

  form.description = ''

  form.category_id = ''

  form.campus = ''

}


/*
|--------------------------------------------------------------------------
| 页面销毁
|--------------------------------------------------------------------------
|
| 释放 blob URL，防止内存泄漏。
|--------------------------------------------------------------------------
*/
onBeforeUnmount(() => {

  for (
    const image
    of images.value
  ) {

    if (image.preview) {

      URL.revokeObjectURL(
        image.preview
      )

    }

  }

})

</script>


<style scoped>

/* =========================================================
   页面
========================================================= */

.publish-page {
  min-height: 100vh;
  min-height: 100dvh;

  padding: 40px 20px 80px;

  background: var(--panel);
  color: var(--ink);
}


.publish-container {
  width: 100%;
  max-width: 900px;

  margin: 0 auto;
}


/* =========================================================
   标题
========================================================= */

.page-header {
  margin-bottom: 24px;
}


.page-header h1 {
  margin: 0 0 8px;

  font-size: 30px;
  font-weight: 700;

  color: var(--ink);
}


.page-header p {
  margin: 0;

  font-size: 14px;

  color: var(--muted);
}


/* =========================================================
   卡片
========================================================= */

.publish-card {
  padding: 32px;

  border: 1px solid var(--border);
  border-radius: 16px;

  background: var(--surface);

  box-shadow:
    0 2px 12px
    rgba(0, 0, 0, 0.05);
}


/* =========================================================
   Section
========================================================= */

.form-section {
  margin-bottom: 32px;
}


.section-title {
  display: flex;
  align-items: center;

  margin-bottom: 14px;

  font-size: 18px;
  font-weight: 600;

  color: var(--ink);
}


.required {
  margin-left: 4px;

  color: #f04444;
}


.image-count {
  margin-left: auto;

  font-size: 13px;
  font-weight: normal;

  color: var(--muted-2);
}


.image-tip {
  margin-bottom: 16px;

  font-size: 13px;

  color: var(--muted);
}


/* =========================================================
   图片区域
========================================================= */

.image-list {
  display: flex;
  flex-wrap: wrap;

  gap: 14px;
}


.image-item,
.upload-box {
  position: relative;

  width: 150px;
  height: 150px;

  overflow: hidden;

  border-radius: 8px;
}


.image-item {
  border: 1px solid var(--border);

  background: var(--panel);
}


.image-item.main {
  border: 2px solid var(--ink);
}


.image-item img {
  width: 100%;
  height: 100%;

  display: block;

  object-fit: cover;
}


/* =========================================================
   主图标签
========================================================= */

.main-label {
  position: absolute;

  left: 0;
  top: 0;

  padding: 5px 10px;

  border-bottom-right-radius: 8px;

  color: var(--btn-text);

  background: var(--btn-bg);

  font-size: 12px;
}


/* =========================================================
   删除按钮
========================================================= */

.delete-image {
  position: absolute;

  right: 6px;
  top: 6px;

  width: 26px;
  height: 26px;

  padding: 0;

  border: none;
  border-radius: 50%;

  color: white;

  background: rgba(0, 0, 0, 0.55);

  font-size: 20px;
  line-height: 26px;

  cursor: pointer;
}


.delete-image:hover {
  background: rgba(0, 0, 0, 0.8);
}


/* =========================================================
   设置主图
========================================================= */

.set-main {
  position: absolute;

  left: 50%;
  bottom: 8px;

  transform: translateX(-50%);

  width: calc(100% - 16px);
  height: 30px;

  border: none;
  border-radius: 5px;

  color: white;

  background: rgba(0, 0, 0, 0.6);

  font-size: 12px;

  cursor: pointer;
}


.set-main:hover {
  background: rgba(0, 0, 0, 0.8);
}


/* =========================================================
   上传图片
========================================================= */

.upload-box {
  display: flex;

  flex-direction: column;

  align-items: center;

  justify-content: center;

  border: 2px dashed var(--border);

  background: var(--bg);

  cursor: pointer;

  transition: all 0.2s;
}


.upload-box:hover {
  border-color: var(--ink);

  background: var(--panel);
}


.upload-icon {
  font-size: 42px;
  font-weight: 200;

  color: var(--muted-2);

  line-height: 1;
}


.upload-text {
  margin-top: 12px;

  font-size: 14px;

  color: var(--muted);
}


.upload-subtext {
  margin-top: 4px;

  font-size: 12px;

  color: var(--muted-2);
}


/* =========================================================
   表单
========================================================= */

.form-item {
  position: relative;

  margin-bottom: 22px;
}


.form-item > label {
  display: block;

  margin-bottom: 8px;

  font-size: 14px;
  font-weight: 500;

  color: var(--ink);
}


.form-item input,
.form-item select,
.form-item textarea {
  box-sizing: border-box;

  width: 100%;

  padding: 12px 14px;

  border: 1px solid var(--border);
  border-radius: 7px;

  outline: none;

  background: var(--bg);

  color: var(--ink);

  font-size: 14px;

  transition:
    border-color 0.2s;
}


.form-item input:focus,
.form-item select:focus,
.form-item textarea:focus {
  border-color: var(--ink);
}


.form-item textarea {
  min-height: 150px;

  resize: vertical;

  line-height: 1.6;
}


/* =========================================================
   字数
========================================================= */

.input-count {
  position: absolute;

  right: 12px;
  bottom: 12px;

  font-size: 12px;

  color: var(--muted-2);
}


.textarea-count {
  position: absolute;

  right: 12px;
  bottom: 10px;

  font-size: 12px;

  color: var(--muted-2);
}


/* =========================================================
   价格
========================================================= */

.price-row {
  display: grid;

  grid-template-columns:
    1fr 1fr;

  gap: 20px;
}


.price-input {
  display: flex;

  align-items: center;

  overflow: hidden;

  border: 1px solid var(--border);
  border-radius: 7px;
}


.price-input:focus-within {
  border-color: var(--ink);
}


.price-input span {
  padding-left: 14px;

  color: var(--muted-2);
}


.price-input input {
  border: none !important;

  border-radius: 0 !important;
}


.price-input input:focus {
  border: none !important;
}


/* =========================================================
   审核提示
========================================================= */

.review-notice {
  display: flex;

  gap: 12px;

  padding: 15px;

  margin-bottom: 20px;

  border: 1px solid var(--border);
  border-radius: 10px;

  background: var(--panel);
}


.notice-icon {
  flex-shrink: 0;

  width: 22px;
  height: 22px;

  display: flex;

  align-items: center;
  justify-content: center;

  border-radius: 50%;

  background: var(--ink);

  color: var(--bg);
  font-size: 13px;
}


.notice-title {
  margin-bottom: 5px;

  font-size: 14px;
  font-weight: 500;

  color: var(--ink);
}


.notice-text {
  font-size: 13px;

  line-height: 1.6;

  color: var(--muted);
}


/* =========================================================
   错误
========================================================= */

.error-message {
  margin-top: 10px;

  color: #f04444;

  font-size: 13px;
}


.submit-error {
  padding: 12px;

  margin-bottom: 15px;

  border-radius: 6px;

  background: #fff2f2;

  color: #f04444;

  font-size: 13px;

  line-height: 1.6;

  white-space: pre-wrap;
}


/* =========================================================
   提交按钮
========================================================= */

.submit-button {
  width: 100%;
  height: 48px;

  border: none;
  border-radius: 7px;

  background: var(--btn-bg);
  color: var(--btn-text);

  font-size: 16px;
  font-weight: 500;

  cursor: pointer;

  transition:
    background 0.2s;
}


.submit-button:hover:not(:disabled) {
  opacity: .86;
}


.submit-button:disabled {
  opacity: 0.6;

  cursor: not-allowed;
}


/* =========================================================
   手机端
========================================================= */

@media (max-width: 700px) {

  .publish-page {
    padding:
      18px
      max(12px, env(safe-area-inset-right))
      40px
      max(12px, env(safe-area-inset-left));
  }


  .publish-card {
    padding: 18px 14px;
    border-radius: 14px;
  }


  .page-header h1 {
    font-size: 24px;
  }


  .image-item,
  .upload-box {
    width: 100%;
    height: auto;
    aspect-ratio: 1 / 1;
  }


  .image-list {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
  }


  .price-row {
    grid-template-columns: 1fr;

    gap: 0;
  }


  .form-item input,
  .form-item select,
  .form-item textarea {
    min-height: 46px;
    font-size: 16px;
  }


  .form-item textarea {
    min-height: 180px;
  }


  .submit-button {
    height: 50px;
    font-size: 15px;
  }

}

</style>
