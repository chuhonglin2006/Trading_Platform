import request from './request.js'

export const reviewsApi = {
  /**
   * 买家评价卖家
   *
   * POST /api/orders/{order_id}/review
   *
   * data: { rating: 1~5, comment: '可不填，最多200字' }
   */
  create(orderId, data) {
    return request.post(
      `/orders/${encodeURIComponent(orderId)}/review`,
      data
    )
  },

  /**
   * 获取订单的评价（没有评价时 data 为 null）
   *
   * GET /api/orders/{order_id}/review
   */
  getByOrder(orderId) {
    return request.get(
      `/orders/${encodeURIComponent(orderId)}/review`
    )
  },

  /**
   * 获取卖家收到的评价
   *
   * GET /api/users/{user_id}/reviews?page=1&page_size=10
   */
  listBySeller(userId, params = {}) {
    return request.get(
      `/users/${encodeURIComponent(userId)}/reviews`,
      { params }
    )
  }
}
