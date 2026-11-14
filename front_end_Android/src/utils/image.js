const IMAGE_BASE_URL = 'https://chuhlblog.top'

export function getImageUrl(url) {
  if (!url) return ''

  const value = String(url).trim()
  if (!value) return ''

  // data: 和 blob: 用于验证码、本地预览等，不能拼接服务器域名
  if (/^(https?:\/\/|data:|blob:)/i.test(value)) {
    return value
  }

  return `${IMAGE_BASE_URL}${value.startsWith('/') ? '' : '/'}${value}`
}
