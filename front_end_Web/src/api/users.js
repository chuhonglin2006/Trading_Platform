import request from './request.js'


export const usersApi = {
  detail(userId) {
    return request.get(`/users/${encodeURIComponent(userId)}`)
  },
}
