import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '../api/auth.js'
import { clearUserStorage } from '../utils/session.js'

function readUser() {
  try {
    const value = localStorage.getItem('cm_user')
    return value ? JSON.parse(value) : null
  } catch {
    localStorage.removeItem('cm_user')
    return null
  }
}

export const useUserStore = defineStore('user', () => {
  const currentUser = ref(readUser())
  const restoring = ref(false)

  function persist() {
    if (currentUser.value) {
      localStorage.setItem('cm_user', JSON.stringify(currentUser.value))
    } else {
      localStorage.removeItem('cm_user')
    }
  }

  function setSession(token, user = null) {
    if (token) {
      localStorage.setItem('cm_token', token)
    }

    if (user) {
      currentUser.value = user
      persist()
    }
  }

  async function login(result) {
    setSession(result?.access_token, result?.user)
    return currentUser.value
  }

  async function register(result) {
    setSession(result?.access_token, result?.user)
    return currentUser.value
  }

  async function restoreSession() {
    if (restoring.value) {
      return currentUser.value
    }

    const token = localStorage.getItem('cm_token')
    if (!token) {
      currentUser.value = null
      return null
    }

    restoring.value = true

    try {
      const result = await authApi.me()

      if (result && typeof result === 'object') {
        currentUser.value = result.user || result.data || result
        persist()
      }

      return currentUser.value
    } catch (error) {
      // 只有令牌确实失效（401）才清除登录状态；网络错误、500、502 不代表令牌失效。
      // 401 时 request.js 的拦截器已经清过缓存并通知 App，这里不用重复处理
      if (error?.response?.status === 401) {
        currentUser.value = null
      }
      return currentUser.value
    } finally {
      restoring.value = false
    }
  }

  function logout() {
    currentUser.value = null
    // 令牌、用户信息，以及订单 / 销售记录 / 举报 / 收藏等缓存一起清掉
    clearUserStorage()
  }

  return {
    currentUser,
    restoring,
    login,
    register,
    restoreSession,
    setSession,
    logout,
  }
})
