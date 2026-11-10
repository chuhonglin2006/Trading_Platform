import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router/index.js'
import { useUserStore } from './stores/user.js'
import './style.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// 先挂载页面，再在后台校验登录状态。
// 以前要等 /auth/me 返回才显示页面，接口慢时用户看到的是白屏（最长 10 秒）。
// 页面渲染用的是本地缓存的用户信息，校验结果回来后再更新。
app.mount('#app')

const userStore = useUserStore(pinia)

userStore
  .restoreSession()
  .then(async (user) => {
    // 登录状态已经失效，但当前正停留在需要登录的页面：跳转到登录页
    await router.isReady()
    const route = router.currentRoute.value

    if (!user && route.meta.requiresAuth) {
      router.replace({
        name: 'auth',
        query: { redirect: route.fullPath },
      })
    }
  })
  .catch((error) => {
    console.error('恢复登录状态失败:', error)
  })