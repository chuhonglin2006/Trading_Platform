<script setup>
import { reactive, ref, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { useMarketStore } from '../stores/market'
import { useToast } from '../composables/useToast'
import { authApi } from '../api/auth'
import ImageCaptcha from '../components/ImageCaptcha.vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const marketStore = useMarketStore()
const { show } = useToast()

const mode = ref('login')

const form = reactive({
  username: '',
  studentId: '',
  email: '',
  code: '',
  password: '',
})

const error = ref('')
const countdown = ref(0)
const submitting = ref(false)
const sendingCode = ref(false)

const captchaRef = ref(null)
const captchaId = ref('')
const captchaCode = ref('')

let countdownTimer = null


function goAfterAuth() {
  const redirect = route.query.redirect

  if (
    typeof redirect === 'string' &&
    redirect.startsWith('/') &&
    !redirect.startsWith('//')
  ) {
    return router.push(redirect)
  }

  return router.push({ name: 'home' })
}


// ==============================
// 重置表单
// ==============================

function resetForm() {
  Object.assign(form, {
    username: '',
    studentId: '',
    email: '',
    code: '',
    password: '',
  })

  error.value = ''
}


// ==============================
// 切换登录 / 注册
// ==============================

function switchMode(newMode) {
  mode.value = newMode
  resetForm()
}


// ==============================
// 发送验证码
// ==============================

async function sendCode() {
  if (sendingCode.value || countdown.value > 0) {
    return
  }

  if (!form.email || !form.email.includes('@')) {
    error.value = '请输入正确的邮箱地址'
    return
  }

  if (!captchaId.value || !captchaCode.value.trim()) {
    error.value = '请先输入图片验证码'
    return
  }

  error.value = ''
  sendingCode.value = true

  try {
    const result = await authApi.sendCode(
      form.email,
      captchaId.value,
      captchaCode.value.trim(),
    )

    console.log('验证码发送结果:', result)

    countdown.value = 60

    if (countdownTimer) {
      clearInterval(countdownTimer)
    }

    countdownTimer = setInterval(() => {
      countdown.value -= 1

      if (countdown.value <= 0) {
        countdown.value = 0
        clearInterval(countdownTimer)
        countdownTimer = null
      }
    }, 1000)

    show(result.message || '验证码发送成功')

  } catch (err) {
    console.error('发送验证码失败:', err)

    error.value =
      err.response?.data?.detail ||
      '验证码发送失败，请稍后重试'

  } finally {
    sendingCode.value = false
    captchaRef.value?.refresh()
  }
}


// ==============================
// 提交表单
// ==============================

async function submit() {
  if (submitting.value) {
    return
  }

  error.value = ''


  // ==========================
  // 注册
  // ==========================

  if (mode.value === 'register') {

    if (
      !form.username ||
      !form.studentId ||
      !form.email ||
      !form.password
    ) {
      error.value = '请完整填写注册信息（学号为必填项）'
      return
    }

    if (!form.code || form.code.length !== 6) {
      error.value = '请输入6位邮箱验证码'
      return
    }

    if (form.password.length < 6) {
      error.value = '密码至少需要6位'
      return
    }

    submitting.value = true

    try {
      const result = await authApi.register({
        username: form.username,
        student_id: form.studentId,
        email: form.email,
        password: form.password,
        code: form.code,
      })

      console.log('注册成功:', result)

      // 后端返回 access_token
      if (!result.access_token) {
        throw new Error('服务器没有返回登录 Token')
      }

      // 保存 Token
      await userStore.register(result)
      // 收藏列表加载失败不应把已经成功的注册误报为失败。
      await marketStore.fetchFavorites().catch((favoriteError) => {
        console.warn('注册成功，但收藏列表加载失败:', favoriteError)
      })

      show(result.message || '注册成功，欢迎加入')

      resetForm()

      await goAfterAuth()

    } catch (err) {
      console.error('注册失败:', err)

      error.value =
        err.response?.data?.detail ||
        err.message ||
        '注册失败，请稍后重试'

    } finally {
      submitting.value = false
    }

    return
  }


  // ==========================
  // 登录
  // ==========================

  if (!form.email || !form.email.includes('@')) {
    error.value = '请输入正确的邮箱地址'
    return
  }

  if (!form.password) {
    error.value = '请输入密码'
    return
  }

  submitting.value = true

  try {
    const result = await authApi.login({
      user_email: form.email,
      password: form.password,
    })

    console.log('登录接口返回:', result)

    // 你的后端返回的是 access_token
    if (!result.access_token) {
      throw new Error('服务器没有返回登录 Token')
    }

    // 保存 Token
    await userStore.login(result)
    // 登录本身已成功；收藏同步失败不应阻断跳转或误报登录失败。
    await marketStore.fetchFavorites().catch((favoriteError) => {
      console.warn('登录成功，但收藏列表加载失败:', favoriteError)
    })

    show(result.message || '登录成功')

    resetForm()

    await goAfterAuth()

  } catch (err) {
    console.error('登录失败:', err)

    error.value =
      err.response?.data?.detail ||
      err.message ||
      '邮箱或密码错误'

  } finally {
    submitting.value = false
  }
}


// ==============================
// 组件销毁
// ==============================

onUnmounted(() => {
  if (countdownTimer) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
})
</script>


<template>
  <div class="auth-wrap">
    <div class="auth-card">

      <h1 class="auth-title">
        {{ mode === 'login' ? '欢迎回来' : '注册账号' }}
      </h1>

      <p class="auth-sub">
        {{
          mode === 'login'
            ? '登录后继续查看'
            : '用邮箱注册，专属个人二手商品展示'
        }}
      </p>


      <!-- 错误提示 -->
      <div
        v-if="error"
        class="form-error"
      >
        {{ error }}
      </div>


      <!-- 用户名 -->
      <div
        v-if="mode === 'register'"
        class="field"
      >
        <label>用户名</label>

        <input
          v-model="form.username"
          placeholder="给自己起个名字（不可重复）"
          maxlength="50"
        />
      </div>


      <!-- 学号 -->
      <div
        v-if="mode === 'register'"
        class="field"
      >
        <label>
          学号
          <span style="color: var(--muted-2)">
            （必填）
          </span>
        </label>

        <input
          v-model="form.studentId"
          placeholder=""
          maxlength="9"
          inputmode="numeric"
        />

        <p class="field-hint">
          9 位学号
        </p>
      </div>


      <!-- 邮箱 -->
      <div class="field">
        <label>邮箱</label>

        <input
          v-model="form.email"
          type="email"
          placeholder="you@campus.edu.cn"
        />
      </div>


      <!-- 验证码 -->
      <!-- 图片验证码（发送邮箱验证码前需要先通过） -->
      <div v-if="mode === 'register'" class="field">
        <label>图片验证码</label>

        <ImageCaptcha
          ref="captchaRef"
          v-model:captchaId="captchaId"
          v-model:code="captchaCode"
        />
      </div>

      <div
        v-if="mode === 'register'"
        class="field"
      >
        <label>邮箱验证码</label>

        <div class="code-row">

          <input
            v-model="form.code"
            placeholder="6位数字"
            maxlength="6"
            inputmode="numeric"
          />

          <button
            class="code-btn"
            :disabled="
              countdown > 0 ||
              sendingCode
            "
            @click="sendCode"
          >
            {{
              countdown > 0
                ? countdown + 's后重发'
                : sendingCode
                  ? '发送中...'
                  : '发送验证码'
            }}
          </button>

        </div>
      </div>


      <!-- 密码 -->
      <div class="field">
        <label>密码</label>

        <input
          v-model="form.password"
          type="password"
          placeholder="至少6位"
          minlength="6"
        />
      </div>


      <!-- 登录 / 注册 -->
      <button
        class="btn btn-primary btn-block"
        :disabled="submitting"
        @click="submit"
      >
        {{
          submitting
            ? '处理中...'
            : mode === 'login'
              ? '登录'
              : '注册'
        }}
      </button>


      <!-- 切换 -->
      <div class="auth-switch">

        <template v-if="mode === 'login'">

          还没有账号？

          <button
            @click="switchMode('register')"
          >
            立即注册
          </button>

        </template>

        <template v-else>

          已有账号？

          <button
            @click="switchMode('login')"
          >
            直接登录
          </button>

        </template>

      </div>

    </div>
  </div>
</template>
