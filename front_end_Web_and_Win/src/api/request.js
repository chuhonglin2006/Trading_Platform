import axios from 'axios'
import { clearUserStorage } from '../utils/session.js'

const request = axios.create({
  baseURL: '/api',
  timeout: 10000,
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
