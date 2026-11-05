<script setup>
import { ref } from 'vue'

const visible = ref(false)
const title = ref('交易安全提醒')
const message = ref('')
const confirmText = ref('确认')
const resolveDialog = ref(null)

function show(options = {}) {
  title.value = options.title || '交易安全提醒'
  message.value = options.message || ''
  confirmText.value = options.confirmText || '确认'
  visible.value = true

  return new Promise((resolve) => {
    resolveDialog.value = resolve
  })
}

function confirm() {
  visible.value = false
  if (resolveDialog.value) {
    resolveDialog.value(true)
    resolveDialog.value = null
  }
}

function cancel() {
  visible.value = false
  if (resolveDialog.value) {
    resolveDialog.value(false)
    resolveDialog.value = null
  }
}

defineExpose({ show })
</script>

<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="trade-dialog-mask"
      @click.self="cancel"
    >
      <div class="trade-dialog">
        <div class="trade-dialog-icon">⚠️</div>

        <h3>{{ title }}</h3>

        <div class="trade-dialog-content">
          <p>{{ message }}</p>
          <p class="trade-dialog-warning">
            请提高警惕，谨防诈骗，不要向他人泄露密码、验证码等重要信息。
          </p>
        </div>

        <div class="trade-dialog-actions">
          <button
            type="button"
            class="trade-dialog-cancel"
            @click="cancel"
          >
            取消
          </button>

          <button
            type="button"
            class="trade-dialog-confirm"
            @click="confirm"
          >
            {{ confirmText }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.trade-dialog-mask {
  position: fixed;
  inset: 0;
  z-index: 11000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  box-sizing: border-box;
  background: rgba(0, 0, 0, 0.45);
}

.trade-dialog {
  width: min(430px, 100%);
  padding: 28px;
  box-sizing: border-box;
  border-radius: 16px;
  background: var(--card-bg, #ffffff);
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.2);
}

.trade-dialog-icon {
  margin-bottom: 10px;
  text-align: center;
  font-size: 36px;
}

.trade-dialog h3 {
  margin: 0 0 18px;
  text-align: center;
  font-size: 20px;
}

.trade-dialog-content {
  color: #555;
  font-size: 14px;
  line-height: 1.8;
}

.trade-dialog-content p {
  margin: 0 0 12px;
}

.trade-dialog-warning {
  color: #d97706;
}

.trade-dialog-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}

.trade-dialog-actions button {
  flex: 1;
  height: 42px;
  border: 0;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}

.trade-dialog-cancel {
  background: #f3f4f6;
  color: #555;
}

.trade-dialog-confirm {
  background: #2563eb;
  color: #fff;
}

.trade-dialog-cancel:hover {
  background: #e5e7eb;
}

.trade-dialog-confirm:hover {
  background: #1d4ed8;
}
</style>
