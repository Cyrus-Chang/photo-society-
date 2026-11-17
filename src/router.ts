import { createRouter, createWebHistory } from 'vue-router'
import { isAuthed } from './utils/session'

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: (to, _from, saved) => {
    if (saved) return saved
    if (to.hash) return { el: to.hash, top: 0, behavior: 'smooth' }
    return { top: 0 }
  },
  routes: [
    { path: '/', name: 'home', component: () => import('./pages/HomePage.vue'), meta: { chrome: false } },
    { path: '/login', name: 'login', component: () => import('./pages/LoginPage.vue'), meta: { chrome: false } },
    { path: '/discover', name: 'discover', component: () => import('./pages/DiscoverPage.vue'), meta: { requiresAuth: true } },
    // AI 撮合台（2026-11-15）：一句话需求 → 真调工具检索作品 + 查档期
    { path: '/match', name: 'match', component: () => import('./pages/MatchPage.vue'), meta: { requiresAuth: true } },
    { path: '/market', name: 'market', component: () => import('./pages/MarketPage.vue'), meta: { requiresAuth: true } },
    // 作品详情公开：未登录可以看作品介绍，摄影师个人信息在页面里按登录态隐藏（2026-11-14 用户确认）
    { path: '/works/:id', name: 'work', component: () => import('./pages/WorkDetailPage.vue') },
    { path: '/circle', name: 'circle', component: () => import('./pages/CirclePage.vue'), meta: { requiresAuth: true } },
    { path: '/photographers/:id', name: 'photographer', component: () => import('./pages/PhotographerPage.vue'), meta: { requiresAuth: true } },
    { path: '/orders', name: 'orders', component: () => import('./pages/OrdersPage.vue'), meta: { requiresAuth: true } },
    { path: '/profile', name: 'profile', component: () => import('./pages/ProfilePage.vue'), meta: { requiresAuth: true } },
    { path: '/studio', name: 'studio', component: () => import('./pages/StudioPage.vue'), meta: { requiresAuth: true } },
    { path: '/publish', name: 'publish', component: () => import('./pages/PublishPage.vue'), meta: { requiresAuth: true } },
    { path: '/:pathMatch(.*)*', redirect: '/' }
  ]
})

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !isAuthed.value) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && isAuthed.value && !to.query.redirect) {
    return { name: 'discover' }
  }
  return true
})

export default router
