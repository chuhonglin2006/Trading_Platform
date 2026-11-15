<script setup>
import { ref, watch } from 'vue'
import { ICON_HEART } from '../utils/icons'
import { formatDateTime, formatPrice } from '../utils/format'
import { getImageUrl } from '../utils/image.js'
import CategoryIcon from './CategoryIcon.vue'

const props = defineProps({
  product: {
    type: Object,
    required: true,
  },

  // 是否已经收藏
  isFavorite: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['open', 'toggle-fav'])

const heartMarkup = `<svg viewBox="0 0 24 24" fill="none">${ICON_HEART}</svg>`
const imageError = ref(false)

watch(
  () => props.product.images?.[0],
  () => { imageError.value = false }
)

// 点击收藏
function onToggleFav(evt) {
  // 防止点击爱心时触发商品卡片的点击事件
  evt.stopPropagation()

  emit('toggle-fav', props.product.id)
}

// 点击商品
function onOpen() {
  emit('open', props.product.id)
}
</script>

<template>
  <div
    class="card"
    @click="onOpen"
  >
    <!-- 商品图片 -->
    <div class="card-media">
      <img
        v-if="product.images && product.images.length > 0 && !imageError"
        :src="getImageUrl(product.images[0])"
        :alt="product.name"
        class="product-image"
        loading="lazy"
        @error="imageError = true"
      />

      <!-- 没有图片或图片加载失败时显示分类图标 -->
      <CategoryIcon
        v-else
        :category="product.category"
      />

      <!-- 已售出 -->
      <span
        v-if="product.status === 'sold'"
        class="card-status"
      >
        已售出
      </span>

      <!-- 收藏按钮 -->
      <button
        class="fav-btn"
        :class="{ active: isFavorite }"
        type="button"
        :aria-pressed="isFavorite"
        :aria-label="isFavorite ? '取消收藏' : '收藏商品'"
        @click="onToggleFav"
        v-html="heartMarkup"
      ></button>
    </div>

    <!-- 商品信息 -->
    <div class="card-body">
      <p class="card-title">
        {{ product.name }}
      </p>

      <div class="card-price-row">
        <span class="card-price">
          ¥{{ formatPrice(product.price) }}
        </span>

        <span
          v-if="
            Number(product.originalPrice) >
            Number(product.price)
          "
          class="card-original"
        >
          ¥{{ formatPrice(product.originalPrice) }}
        </span>
      </div>

      <div class="card-meta">
        <span>
          {{ product.campus || '未知校区' }}
        </span>

        <span>
          {{ formatDateTime(product.createdAt) }}
        </span>
      </div>

      <p class="card-publish">
        发布于：{{ product.publishProvince || '未知' }}
      </p>
    </div>
  </div>
</template>

<style scoped>
.card {
  position: relative;
  overflow: hidden;
  cursor: pointer;
}

.card-media {
  position: relative;
  width: 100%;
  height: auto;
  aspect-ratio: 1 / 1;
  overflow: hidden;
  border-radius: 12px;
}

.product-image {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}

.product-image:not([src]) {
  display: none;
}

/* 已售出标签 */
.card-status {
  position: absolute;
  top: 10px;
  left: 10px;

  padding: 4px 8px;

  border-radius: 6px;

  background: rgba(0, 0, 0, 0.65);
  color: #fff;

  font-size: 12px;
}

/* =========================
   收藏按钮
   ========================= */

.fav-btn {
  position: absolute;
  top: 10px;
  right: 10px;

  width: 36px;
  height: 36px;

  display: flex;
  align-items: center;
  justify-content: center;

  padding: 0;

  border: none;
  border-radius: 50%;

  /*
   * 深色半透明背景
   *
   * 这样：
   * 未收藏 = 白色爱心 + 深色背景
   * 已收藏 = 红色爱心 + 深色背景
   */
  background: rgba(0, 0, 0, 0.55);

  cursor: pointer;

  /* 阴影，让按钮和商品图片分离 */
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);

  transition:
    background 0.2s ease,
    transform 0.2s ease;
}

/* 鼠标移动到收藏按钮 */
.fav-btn:hover {
  background: rgba(0, 0, 0, 0.7);

  transform: scale(1.08);
}

/* SVG 大小 */
.fav-btn :deep(svg) {
  width: 20px;
  height: 20px;

  display: block;

  transition:
    fill 0.2s ease,
    stroke 0.2s ease,
    transform 0.2s ease;
}

/* =========================
   未收藏
   ========================= */

/*
 * 未收藏：
 * 白色爱心
 */
.fav-btn:not(.active) :deep(svg *) {
  stroke: #ffffff;
}

/* =========================
   已收藏
   ========================= */

/*
 * 已收藏：
 * 红色爱心
 */
.fav-btn.active :deep(svg *) {
  stroke: #ff3b30;
  fill: #ff3b30;
}

/* 已收藏时爱心稍微放大 */
.fav-btn.active :deep(svg) {
  transform: scale(1.05);
}

/* =========================
   商品内容
   ========================= */

.card-body {
  min-width: 0;
  padding: 12px 10px 14px;
}

.card-title {
  margin: 0 0 8px;

  min-height: 2.8em;
  font-size: 15px;
  font-weight: 600;
  line-height: 1.4;

  overflow: hidden;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.card-price-row {
  display: flex;
  align-items: center;

  gap: 8px;
}

.card-price {
  font-size: 18px;
  font-weight: 700;
}

.card-original {
  font-size: 13px;
  text-decoration: line-through;
  opacity: 0.55;
}

.card-meta {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  min-width: 0;

  margin-top: 8px;

  font-size: 12px;
  opacity: 0.6;
}

.card-meta span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-publish {
  margin: 6px 0 0;
  font-size: 12px;
  opacity: 0.6;
}

@media (max-width: 520px) {
  .card-title {
    min-height: 2.8em;
    margin-bottom: 5px;
    font-size: 13px;
  }

  .card-price {
    font-size: 17px;
  }

  .card-publish {
    display: none;
  }

  .card-body {
    padding: 10px 9px 12px;
  }

  .fav-btn {
    top: 7px;
    right: 7px;
    width: 34px;
    height: 34px;
  }
}
</style>
