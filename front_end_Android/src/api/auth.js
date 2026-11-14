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

  logout(refreshToken) {
    return request.post('/auth/logout', { refresh_token: refreshToken })
  },

  // 忘记密码：发送邮箱验证码（后端不会透露邮箱是否已注册）
  forgotSendCode(email, captchaId, captchaCode) {
    return request.post('/auth/forgot-password/send-code', {
      user_email: email,
      captcha_id: captchaId,
      captcha_code: captchaCode,
    })
  },

  // 忘记密码：验证码 + 新密码一起提交，data = { email, code, new_password }
  resetPassword(data) {
    return request.post('/auth/reset-password', data)
  },

  me() {
    return request.get('/auth/me')
  },
}
