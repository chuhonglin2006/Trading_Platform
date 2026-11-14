import axios from 'axios'
import { Capacitor } from '@capacitor/core'
import { clearUserStorage } from '../utils/session.js'

const API_BASE_URL = Capacitor.isNativePlatform()
  ? 'https://chuhlblog.top/api'
  : '/api'

const request = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
})

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

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error?.response?.status === 401) {
      clearUserStorage()
      window.dispatchEvent(new CustomEvent('cm-auth-expired'))
    }

    return Promise.reject(error)
  }
)

export default request
