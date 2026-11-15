import request from './request.js'

export const ordersApi = {
  /**
   * 获取我的订单
   *
   * GET /api/orders/my
   */
  listMine(params = {}) {
    return request.get('/orders/my', {
      params
    })
  },

  /**
   * 创建订单
   *
   * POST /api/orders
   */
  create(data) {
    return request.post('/orders', data)
  },

  /**
   * 获取订单详情
   *
   * GET /api/orders/{order_id}
   */
  getDetail(orderId) {
    return request.get(
      `/orders/${encodeURIComponent(orderId)}`
    )
  },

  /**
   * 取消订单
   *
   * PATCH /api/orders/{order_id}/cancel
   */
  cancel(orderId) {
    return request.patch(
      `/orders/${encodeURIComponent(orderId)}/cancel`
    )
  },

  /**
   * 买家确认收货
   *
   * PATCH /api/orders/{order_id}/receive
   */
  receive(orderId) {
    return request.patch(
      `/orders/${encodeURIComponent(orderId)}/receive`
    )
  },

  /**
   * 卖家确认交易完成
   *
   * PATCH /api/orders/{order_id}/complete
   */
  complete(orderId) {
    return request.patch(
      `/orders/${encodeURIComponent(orderId)}/complete`
    )
  },

  /**
   * 获取交易安排
   *
   * GET /api/orders/{order_id}/meeting
   */
  getMeeting(orderId) {
    return request.get(
      `/orders/${encodeURIComponent(orderId)}/meeting`
    )
  },

  /**
   * 设置/修改交易时间和地点
   *
   * PUT /api/orders/{order_id}/meeting
   *
   * data:
   * {
   *   meeting_time: '2026-09-27T15:00:00',
   *   meeting_location: '关山校区东门'
   * }
   */
  setMeeting(orderId, data) {
    return request.put(
      `/orders/${encodeURIComponent(orderId)}/meeting`,
      data
    )
  },

  /**
   * 确认交易安排
   *
   * POST /api/orders/{order_id}/meeting/confirm
   */
  confirmMeeting(orderId) {
    return request.post(
      `/orders/${encodeURIComponent(orderId)}/meeting/confirm`
    )
  }
}