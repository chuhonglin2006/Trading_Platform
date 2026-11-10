// 和登录用户相关的本地缓存。退出登录 / 登录过期时必须清掉。
// 注意：主题（cm_theme）不是用户隐私数据，不在这里清。

// 业务数据缓存：订单、销售记录、举报、收藏
export const USER_DATA_KEYS = ['cm_favs', 'cm_orders', 'cm_mysales', 'cm_reports']

// 登录凭证：令牌和用户信息
export const SESSION_KEYS = ['cm_token', 'cm_user']

function removeKeys(keys) {
  for (const key of keys) {
    try {
      localStorage.removeItem(key)
    } catch {
      // 隐私模式等场景下 localStorage 可能不可用，忽略
    }
  }
}

// 只清业务数据（换账号时用，不能删掉新账号刚写入的令牌）
export function clearUserData() {
  removeKeys(USER_DATA_KEYS)
}

// 清掉所有和登录用户相关的本地数据（退出登录 / 登录过期时用）
export function clearUserStorage() {
  removeKeys(SESSION_KEYS)
  removeKeys(USER_DATA_KEYS)
}