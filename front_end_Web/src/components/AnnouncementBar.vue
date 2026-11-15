<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  announcements: {
    type: Array,
    default: () => [],
  },
})

const expanded = ref(false)
const selected = ref(null)

const latest = computed(() => props.announcements[0] || null)

function openAnnouncement(item) {
  selected.value = item
}

function closeAnnouncement() {
  selected.value = null
}

function formatTime(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value).replace('T', ' ')
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<template>
  <div v-if="latest" class="announcement-wrap">
    <div class="announcement-bar">
      <span class="announcement-icon"></span>

      <div class="announcement-window">
        <button
          class="announcement-marquee"
          type="button"
          @click="openAnnouncement(latest)"
        >
          <span class="announcement-marquee-text">
            {{ latest.title }}：{{ latest.content }}
          </span>
        </button>
      </div>

      <button
        class="announcement-toggle"
        type="button"
        :aria-expanded="expanded"
        title="展开全部公告"
        @click="expanded = !expanded"
      >
        <span :class="{ rotated: expanded }">⌄</span>
      </button>
    </div>

    <div v-if="expanded" class="announcement-panel">
      <div class="announcement-panel-head">
        <strong>平台公告</strong>
        <button
          type="button"
          class="announcement-close-list"
          @click="expanded = false"
        >
          收起
        </button>
      </div>

      <button
        v-for="item in announcements"
        :key="item.id"
        type="button"
        class="announcement-item"
        @click="openAnnouncement(item)"
      >
        <div class="announcement-item-title">{{ item.title }}</div>
        <div class="announcement-item-content">{{ item.content }}</div>
        <div class="announcement-item-time">
          {{ formatTime(item.created_at || item.createdAt) }}
        </div>
      </button>
    </div>

    <div
      v-if="selected"
      class="announcement-modal-mask"
      @click.self="closeAnnouncement"
    >
      <div class="announcement-modal">
        <div class="announcement-modal-head">
          <h3>{{ selected.title }}</h3>
          <button
            type="button"
            class="announcement-modal-close"
            @click="closeAnnouncement"
          >
            ×
          </button>
        </div>

        <div class="announcement-modal-time">
          {{ formatTime(selected.created_at || selected.createdAt) }}
        </div>

        <div class="announcement-modal-content">
          {{ selected.content }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.announcement-wrap {
  position: relative;
  z-index: 50;
  width: 100%;
}

.announcement-bar {
  min-height: 44px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 18px;
  box-sizing: border-box;
  background: var(--card-bg, #ffffff);
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.announcement-icon {
  flex: 0 0 auto;
  font-size: 17px;
}

.announcement-window {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.announcement-marquee {
  display: block;
  width: max-content;
  min-width: 100%;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  text-align: left;
  white-space: nowrap;
  overflow: hidden;
}

.announcement-marquee-text {
  display: inline-block;
  padding-left: 100%;
  animation: announcement-scroll 16s linear infinite;
}

.announcement-marquee:hover .announcement-marquee-text {
  animation-play-state: paused;
}

@keyframes announcement-scroll {
  from { transform: translateX(0); }
  to { transform: translateX(-100%); }
}

.announcement-toggle {
  flex: 0 0 auto;
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font-size: 23px;
  line-height: 1;
}

.announcement-toggle:hover {
  background: rgba(0, 0, 0, 0.06);
}

.announcement-toggle span {
  display: inline-block;
  transition: transform 0.2s ease;
}

.announcement-toggle span.rotated {
  transform: rotate(180deg);
}

.announcement-panel {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  max-height: min(480px, 70vh);
  overflow-y: auto;
  padding: 12px;
  background: var(--card-bg, #ffffff);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-top: 0;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.12);
}

.announcement-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 6px 12px;
}

.announcement-close-list {
  border: 0;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
}

.announcement-item {
  width: 100%;
  display: block;
  padding: 13px 14px;
  margin-bottom: 8px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 10px;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.announcement-item:hover {
  background: rgba(0, 0, 0, 0.035);
}

.announcement-item-title {
  font-weight: 700;
  margin-bottom: 5px;
}

.announcement-item-content {
  color: var(--muted);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}

.announcement-item-time {
  margin-top: 7px;
  font-size: 12px;
  color: var(--muted-2);
}

.announcement-modal-mask {
  position: fixed;
  inset: 0;
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  box-sizing: border-box;
  background: rgba(0, 0, 0, 0.45);
}

.announcement-modal {
  width: min(560px, 100%);
  max-height: 80vh;
  overflow-y: auto;
  padding: 22px;
  box-sizing: border-box;
  border-radius: 16px;
  background: var(--card-bg, #ffffff);
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.2);
}

.announcement-modal-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.announcement-modal-head h3 {
  margin: 0;
  font-size: 20px;
}

.announcement-modal-close {
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  font-size: 24px;
  cursor: pointer;
}

.announcement-modal-time {
  margin-top: 7px;
  color: var(--muted-2);
  font-size: 12px;
}

.announcement-modal-content {
  margin-top: 20px;
  line-height: 1.9;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
