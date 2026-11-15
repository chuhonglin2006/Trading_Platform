import axios from 'axios'
import { clearUserStorage } from '../utils/session.js'

const API_BASE_URL = '/api'

const request = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
})

// 这几个接口返回 401 不代表“登录过期”(比如密码错误)，不触发刷新
const NO_REFRESH = ['/auth/login', '/auth/register', '/auth/refresh', '/auth/send-code']

request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('cm_token')

    if (token) {
      config.headers = config.headers || {}
      config.headers.Authorization = `Bearer ${token}`
    }

    return config
  },
  (error) => Promise.reject(error)
)

// 多个请求同时 401 时，只发一次刷新请求，大家共用结果
let refreshing = null

function doRefresh() {
  const refreshToken = localStorage.getItem('cm_refresh')
  if (!refreshToken) {
    return Promise.reject(new Error('no refresh token'))
  }
  // 用裸 axios 发，避免再进当前拦截器造成死循环
  return axios
    .post(`${API_BASE_URL}/auth/refresh`, { refresh_token: refreshToken }, { timeout: 15000 })
    .then((res) => {
      localStorage.setItem('cm_token', res.data.access_token)
      localStorage.setItem('cm_refresh', res.data.refresh_token)
    })
}

function expireSession() {
  clearUserStorage()
  window.dispatchEvent(new CustomEvent('cm-auth-expired'))
}

request.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    const config = error?.config
    const status = error?.response?.status

    const canRefresh =
      status === 401 &&
      config &&
      !config._retry &&
      !NO_REFRESH.some((path) => config.url?.includes(path))

    if (!canRefresh) {
      // 登录/注册等接口的 401 保持原样，其余没有重试机会的 401 才算过期
      if (status === 401 && config && !NO_REFRESH.some((path) => config.url?.includes(path))) {
        expireSession()
      }
      return Promise.reject(error)
    }

    config._retry = true
    try {
      refreshing = refreshing || doRefresh().finally(() => { refreshing = null })
      await refreshing
      return request(config) // 带着新 token 重发原请求
    } catch (refreshError) {
      // 只有刷新接口明确 401(或根本没有 refresh token) 才算登录过期
      // 断网、500、超时都不踢人
      if (refreshError?.response?.status === 401 || refreshError?.message === 'no refresh token') {
        expireSession()
      }
      return Promise.reject(error)
    }
  }
)

export default request
