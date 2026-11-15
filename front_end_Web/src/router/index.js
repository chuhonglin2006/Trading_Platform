import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user.js'

import HomeView from '../views/HomeView.vue'
import AuthView from '../views/AuthView.vue'
import DetailView from '../views/DetailView.vue'
import PublishView from '../views/PublishView.vue'
import ProfileView from '../views/ProfileView.vue'
import EditProductView from '../views/EditProductView.vue'
import SellerView from '../views/SellerView.vue'

const routes = [
  { path: '/', name: 'home', component: HomeView },
  { path: '/auth', name: 'auth', component: AuthView, meta: { hideChrome: true } },
  { path: '/product/:id', name: 'detail', component: DetailView, props: true },
  { path: '/seller/:id', name: 'seller', component: SellerView, props: true },
  { path: '/publish', name: 'publish', component: PublishView, meta: { requiresAuth: true } },
  { path: '/product/:id/edit', name: 'edit-product', component: EditProductView, props: true, meta: { requiresAuth: true } },
  { path: '/profile', name: 'profile', component: ProfileView, meta: { requiresAuth: true } },
  { path: '/orders/:id', name: 'order-detail', component: () => import('../views/OrderDetailView.vue'), props: true, meta: { requiresAuth: true } },
  {path: '/chat/:conversationId', name: 'chat', component: () => import('../views/ChatView.vue'), props: true,meta: {requiresAuth: true,},},
  { path: '/download', name: 'download', component: () => import('../views/DownloadView.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

router.beforeEach((to) => {
  const userStore = useUserStore()

  if (to.meta.requiresAuth && !userStore.currentUser) {
    return {
      name: 'auth',
      query: { redirect: to.fullPath },
    }
  }

  return true
})

export default router
