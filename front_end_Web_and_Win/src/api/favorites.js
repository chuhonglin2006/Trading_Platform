import request from './request.js'

export const favoritesApi = {
  list() {
    return request.get('/favorite')
  },

  add(productId) {
    return request.post(`/favorite/${encodeURIComponent(productId)}`)
  },

  remove(productId) {
    return request.delete(`/favorite/${encodeURIComponent(productId)}`)
  },
}
