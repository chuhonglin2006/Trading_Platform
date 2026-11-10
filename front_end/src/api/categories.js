import request from './request.js'

export const categoriesApi = {
  list() {
    return request.get('/products/categories')
  },
}