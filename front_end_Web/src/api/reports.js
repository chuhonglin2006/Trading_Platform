import request from './request.js'

export const reportsApi = {
  create(data) {
    return request.post('/reports', data)
  },
}
