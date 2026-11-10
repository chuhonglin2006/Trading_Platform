import request from './request.js'

export const productsApi = {
  list(params = {}) {
    return request.get('/products', { params })
  },

  search(productName) {
    return request.get('/products/search', {
      params: {
        product_name: productName,
      },
    })
  },

  detail(productId) {
    return request.get(
      `/products/${encodeURIComponent(productId)}`
    )
  },

  my(params = {}) {
    return request.get('/my', { params })
  },

  create(formData) {
    return request.post('/products', formData)
  },

  offShelf(productId) {
    return request.patch(
      `/products/${encodeURIComponent(productId)}/off-shelf`
    )
  },

  update(productId, data) {
    return request.patch(
      `/products/${encodeURIComponent(productId)}`,
      data
    )
  },

  myDetail(productId) {
    return request.get(
      `/my/products/${encodeURIComponent(productId)}`
    )
  },

  // 查询指定卖家的商品
  bySeller(sellerId, params = {}) {
    return request.get(
      `/users/${encodeURIComponent(sellerId)}/products`,
      { params }
    )
  },

  markSold(productId) {
    return request.patch(
      `/products/${encodeURIComponent(productId)}/sold`
    )
  },

  delete(productId) {
  return request.delete(
    `/products/${encodeURIComponent(productId)}`
  )
},
}