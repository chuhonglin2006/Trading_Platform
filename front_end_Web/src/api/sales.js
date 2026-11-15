import request from './request.js'

export const salesApi = {
  listMine(params = {}) {
    return request.get('/sales/my', { params })
  },
}
