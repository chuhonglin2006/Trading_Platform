export function formatDateTime(value) {
  if (!value) return ''

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return String(value).replace('T', ' ').slice(0, 16)
  }

  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

export function formatPrice(value) {
  const number = Number(value)
  return Number.isFinite(number) ? number.toFixed(2) : '0.00'
}
