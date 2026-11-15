import { ref } from 'vue'

const isNight = ref(localStorage.getItem('cm_theme') === 'dark')

function applyTheme() {
  document.documentElement.setAttribute('data-theme', isNight.value ? 'dark' : 'light')
  localStorage.setItem('cm_theme', isNight.value ? 'dark' : 'light')
}

// 应用启动时先套用一次已保存的偏好
applyTheme()

export function useTheme() {
  function toggle() {
    isNight.value = !isNight.value
    applyTheme()
  }
  return { isNight, toggle }
}
