import request from './request.js'

export const authApi = {
  login(data) {
    return request.post('/auth/login', data)
  },

  register(data) {
    return request.post('/auth/register', data)
  },

  sendCode(email, captchaId, captchaCode) {
    return request.post('/auth/send-code', {
      user_email: email,
      captcha_id: captchaId,
      captcha_code: captchaCode,
    })
  },

  me() {
    return request.get('/auth/me')
  },
}
