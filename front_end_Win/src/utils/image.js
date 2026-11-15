/**
 * 将后端返回的商品图片路径转换为可访问地址。
 * Windows Tauri 使用公网 API 域名；未配置绝对 API 地址时保留同源相对路径。
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

const IMAGE_BASE_URL = /^https?:\/\//i.test(API_BASE_URL)
  ? API_BASE_URL.replace(/\/api\/?$/, '').replace(/\/$/, '')
  : ''

export function getImageUrl(url) {
  if (!url || typeof url !== 'string') return ''

  // 完整 URL、Blob 预览及 Data URL 不做处理
  if (/^(https?:|blob:|data:)/i.test(url)) return url

  const path = url.replace(/^\/+/, '')
  return IMAGE_BASE_URL ? `${IMAGE_BASE_URL}/${path}` : `/${path}`
}
