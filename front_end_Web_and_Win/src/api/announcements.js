import request from './request.js'

export const announcementsApi = {
  list() {
    return request.get('/announcements')
  },
}
