export const ORDER_STATUS_TEXT = {
  pending: '待确认收货',
  received: '待交易完成',
  completed: '已完成',
  cancelled: '已取消',
}

export function orderStatusText(status) {
  return ORDER_STATUS_TEXT[status] || status || '未知状态'
}
