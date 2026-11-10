import request from './request.js'

export const chatApi = {
  getOrCreate(orderId) {
    return request.post('/chat/conversations', null, {
      params: {
        order_id: orderId,
      },
    })
  },

  getMessages(conversationId) {
    return request.get(
      `/chat/conversations/${conversationId}/messages`
    )
  },

  sendMessage(conversationId, content) {
    return request.post(
      `/chat/conversations/${conversationId}/messages`,
      {
        content,
      }
    )
  },

  readMessage(messageId) {
    return request.post(
      `/chat/messages/${messageId}/read`
    )
  },
}