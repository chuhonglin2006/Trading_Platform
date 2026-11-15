<script setup>
import { reactive, ref, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { useMarketStore } from '../stores/market'
import { useToast } from '../composables/useToast'
import { authApi } from '../api/auth'
import ImageCaptcha from '../components/ImageCaptcha.vue'
import { getApiErrorMessage } from '../utils/apiError'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const marketStore = useMarketStore()
const { show } = useToast()

const mode = ref('login') // login | register | forgot

const MODE_TEXT = {
  login: { title: '欢迎回来', sub: '登录后继续查看', submit: '登录' },
  register: {
    title: '注册账号',
    sub: '用邮箱注册，专属个人二手商品展示',
    submit: '注册',
  },
  forgot: {
    title: '找回密码',
    sub: '输入注册邮箱，验证后即可设置新密码',
    submit: '重置密码',
  },
}

const form = reactive({
  username: '',
  studentId: '',
  email: '',
  code: '',
  password: '',
  confirmPassword: '',
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
    confirmPassword: '',
  })

  error.value = ''
}


// ==============================
// 切换 登录 / 注册 / 忘记密码
// ==============================

function switchMode(newMode) {
  mode.value = newMode
  resetForm()

  // 各模式的验证码互相独立：清掉倒计时，并换一张新的图片验证码
  if (countdownTimer) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
  countdown.value = 0
  captchaRef.value?.refresh()
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
    const sendApi =
      mode.value === 'forgot' ? authApi.forgotSendCode : authApi.sendCode

    const result = await sendApi(
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
    error.value = getApiErrorMessage(err, '验证码发送失败，请稍后重试')

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
      error.value = getApiErrorMessage(err, '注册失败，请稍后重试')

    } finally {
      submitting.value = false
    }

    return
  }


  // ==========================
  // 忘记密码（验证码通过后重置）
  // ==========================

  if (mode.value === 'forgot') {
    if (!form.email || !form.email.includes('@')) {
      error.value = '请输入正确的邮箱地址'
      return
    }

    if (!/^\d{6}$/.test(form.code.trim())) {
      error.value = '请输入6位邮箱验证码'
      return
    }

    if (form.password.length < 6) {
      error.value = '新密码至少需要6位'
      return
    }

    // 后端限制 64 位，且 bcrypt 只取前 72 字节（中文每字 3 字节）
    if (
      form.password.length > 64 ||
      new TextEncoder().encode(form.password).length > 72
    ) {
      error.value = '新密码过长，请缩短后重试'
      return
    }

    if (form.password !== form.confirmPassword) {
      error.value = '两次输入的密码不一致'
      return
    }

    submitting.value = true

    try {
      const email = form.email

      const result = await authApi.resetPassword({
        email,
        code: form.code.trim(),
        new_password: form.password,
      })

      show(result.message || '密码重置成功，请使用新密码登录')

      // 回到登录页，保留邮箱方便直接登录
      switchMode('login')
      form.email = email

    } catch (err) {
      error.value = getApiErrorMessage(err, '重置失败，请稍后重试')

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
    error.value = getApiErrorMessage(err, '邮箱或密码错误')

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
      <div class="auth-brand" aria-label="校园二手">
        <span class="auth-brand-mark">E</span>
        <span>校园二手</span>
      </div>

      <h1 class="auth-title">
        {{ MODE_TEXT[mode].title }}
      </h1>

      <p class="auth-sub">
        {{ MODE_TEXT[mode].sub }}
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
      <div v-if="mode !== 'login'" class="field">
        <label>图片验证码</label>

        <ImageCaptcha
          ref="captchaRef"
          v-model:captchaId="captchaId"
          v-model:code="captchaCode"
        />
      </div>

      <div
        v-if="mode !== 'login'"
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
        <label>{{ mode === 'forgot' ? '新密码' : '密码' }}</label>

        <input
          v-model="form.password"
          type="password"
          :placeholder="mode === 'forgot' ? '设置新密码，至少6位' : '至少6位'"
          :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
          minlength="6"
          maxlength="64"
        />
      </div>


      <!-- 确认新密码（仅忘记密码） -->
      <div
        v-if="mode === 'forgot'"
        class="field"
      >
        <label>确认新密码</label>

        <input
          v-model="form.confirmPassword"
          type="password"
          placeholder="再输入一次新密码"
          autocomplete="new-password"
          minlength="6"
          maxlength="64"
        />
      </div>


      <!-- 忘记密码入口（仅登录） -->
      <div
        v-if="mode === 'login'"
        class="auth-forgot"
      >
        <button
          type="button"
          @click="switchMode('forgot')"
        >
          忘记密码？
        </button>
      </div>


      <!-- 登录 / 注册 -->
      <button
        class="btn btn-primary btn-block"
        :disabled="submitting"
        @click="submit"
      >
        {{ submitting ? '处理中...' : MODE_TEXT[mode].submit }}
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

        <template v-else-if="mode === 'register'">

          已有账号？

          <button
            @click="switchMode('login')"
          >
            直接登录
          </button>

        </template>

        <template v-else>

          想起密码了？

          <button
            @click="switchMode('login')"
          >
            返回登录
          </button>

        </template>

      </div>

    </div>
  </div>
</template>
