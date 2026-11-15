<script setup>
const year = new Date().getFullYear()
</script>

<template>
  <footer class="site-footer">
    <div class="site-footer-inner">
      <p class="site-footer-line">© {{ year }} 校园个人二手物品展示平台</p>
      <p class="site-footer-line">
        <a
          class="site-footer-link"
          href="https://beian.miit.gov.cn/"
          target="_blank"
          rel="noopener noreferrer"
        >鄂ICP备2026033606号-1</a>
      </p>
    </div>
  </footer>
</template>
