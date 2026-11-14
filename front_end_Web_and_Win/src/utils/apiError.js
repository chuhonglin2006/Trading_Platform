/**
 * 把接口错误统一转成可以直接展示给用户的文字
 * 处理：字符串 detail / FastAPI 422 数组 / message 字段 / 超时 / 断网
 */
const FIELD_NAMES = {
  user_email: '邮箱',
  email: '邮箱',
  password: '密码',
  new_password: '新密码',
  username: '用户名',
  student_id: '学号',
  code: '邮箱验证码',
  captcha_code: '图片验证码',
  reason: '举报原因',
  content: '内容',
  meeting_location: '交易地点',
}

export function getApiErrorMessage(error, fallback = '请求失败，请稍后重试') {
  // 没有响应：超时或断网
  if (!error?.response) {
    if (error?.code === 'ECONNABORTED') return '请求超时，请稍后重试'
    return '网络异常，请检查网络后重试'
  }

  const data = error.response.data
  const detail = data?.detail ?? data?.message

  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }

  // FastAPI 422：[{ loc: ['body','password'], msg: '...' }]
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((item) => {
        const key = Array.isArray(item?.loc) ? item.loc[item.loc.length - 1] : ''
        const name = FIELD_NAMES[key] || key
        return name ? `${name}格式不正确` : (item?.msg || '输入内容不正确')
      })
      .join('；')
  }

  return fallback
}