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

async function bootstrap() {
  const userStore = useUserStore(pinia)

  try {
    await userStore.restoreSession()
  } catch (error) {
    console.error('恢复登录状态失败:', error)
  }

  app.mount('#app')
}

bootstrap()

