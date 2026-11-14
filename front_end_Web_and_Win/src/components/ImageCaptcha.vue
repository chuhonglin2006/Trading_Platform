<!--
  放置位置：front_end/src/components/ImageCaptcha.vue

  用法：
    <ImageCaptcha
      ref="captchaRef"
      v-model:captchaId="captchaId"
      v-model:code="captchaCode"
    />

  - 点击图片可以换一张
  - 每张图片只能校验一次（对错都作废）：提交后不管成功还是失败，
    都要调用 captchaRef.value.refresh() 换新图
-->
<script setup>
import { onMounted, ref } from 'vue'
import request from '../api/request.js'

const captchaId = defineModel('captchaId', { type: String, default: '' })
const code = defineModel('code', { type: String, default: '' })

const image = ref('')
const loading = ref(false)
const failed = ref(false)

async function refresh() {
  if (loading.value) return

  loading.value = true
  failed.value = false
  code.value = ''

  try {
    // request 的响应拦截器已经返回了 response.data
    const data = await request.get('/captcha')
    captchaId.value = data.captcha_id
    image.value = data.image
  } catch {
    captchaId.value = ''
    image.value = ''
    failed.value = true
  } finally {
    loading.value = false
  }
}

onMounted(refresh)

defineExpose({ refresh })
</script>

<template>
  <div class="image-captcha">
    <input
      v-model.trim="code"
      class="captcha-input"
      type="text"
      maxlength="4"
      autocomplete="off"
      autocapitalize="characters"
      placeholder="图片验证码"
    />

    <button
      type="button"
      class="captcha-image"
      :disabled="loading"
      title="看不清？点击换一张"
      @click="refresh"
    >
      <img
        v-if="image"
        :src="image"
        alt="图片验证码，点击换一张"
        width="132"
        height="44"
      />
      <span v-else class="captcha-placeholder">
        {{ failed ? '加载失败，点击重试' : '加载中…' }}
      </span>
    </button>
  </div>
</template>

<style scoped>
.image-captcha {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 4px 0 12px;
}

.captcha-input {
  flex: 1;
  min-width: 0;
  text-transform: uppercase;
}

.captcha-image {
  flex: none;
  width: 132px;
  height: 44px;
  padding: 0;
  border: 1px solid #e1e7f1;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  overflow: hidden;
}

.captcha-image img {
  display: block;
}

.captcha-placeholder {
  font-size: 12px;
  color: #8a94a6;
}
</style>