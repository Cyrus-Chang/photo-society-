<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ArrowLeft, Bell, ChevronDown, Compass, LogOut, Plus, Search, UserRound } from 'lucide-vue-next'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import IdentityModal from './components/IdentityModal.vue'
import StartBookingPrompt from './components/StartBookingPrompt.vue'
import CursorCamera from './components/CursorCamera.vue'
import WallpaperLayer from './components/WallpaperLayer.vue'
import WallpaperPicker from './components/WallpaperPicker.vue'
import { brand } from './utils/brand'
import { personalize } from './utils/personalize'
import { requestBookingFilter } from './utils/bookingFlow'
import { hasRole, isAuthed, roleLabel, session, signOut } from './utils/session'

const route = useRoute()
const router = useRouter()
const showProfile = ref(false)
const askStart = ref(false)
let startTimer = 0

const navItems = [
  { label: '约拍', to: '/discover' },
  { label: '接拍', to: '/market' },
  { label: '圈子', to: '/circle' }
]

const activeLabel = computed(() => {
  if (route.path.startsWith('/market')) return '接拍'
  if (route.path.startsWith('/discover') || route.path.startsWith('/works') || route.path.startsWith('/photographers')) return '约拍'
  if (route.path.startsWith('/circle')) return '圈子'
  return ''
})

// 文档型页面（工作台 / 订单 / 发布 / 作品详情 / 摄影师主页 / 圈子 / 个人信息）走深色主题。
const docPageNames = new Set(['orders', 'studio', 'publish', 'work', 'photographer', 'circle', 'profile'])
const isDocPage = computed(() => docPageNames.has(String(route.name ?? '')))

// 只有在登录之后、且不是首页/登录页时，才出现常规导航。
const showChrome = computed(() => isAuthed.value && route.meta.chrome !== false)
// 身份弹窗只在需要登录的产品页出现；登录页/首页不叠，避免登录瞬间闪一下。
const showIdentity = computed(() => isAuthed.value && !hasRole.value && Boolean(route.meta.requiresAuth))
const initial = computed(() => (session.name || '拍').slice(0, 1).toUpperCase())

// 2026-11-16 用户：壁纸「全局一张」，只铺在个人信息 / 摄影工作台 / 我的约拍
const wallpaperPageNames = new Set(['profile', 'studio', 'orders'])
const isWallpaperPage = computed(() => wallpaperPageNames.has(String(route.name ?? '')))

// 相机光标只在「看照片」的语境里启用：首页 + 作品详情
const camCursorPage = computed(() => route.name === 'home' || route.name === 'work')

function closePopover() { showProfile.value = false }

watch(() => route.fullPath, closePopover)

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') closePopover()
}

function onDocumentClick(event: MouseEvent) {
  const target = event.target as HTMLElement | null
  if (!target?.closest('.topbar-actions')) closePopover()
}

function onIdentityDone() {
  window.clearTimeout(startTimer)
  // 等身份弹窗的离场动画走完再问下一步，避免两个弹窗叠在一起闪
  startTimer = window.setTimeout(() => { askStart.value = true }, 320)
}

function onStartBooking() {
  askStart.value = false
  if (route.name === 'discover') requestBookingFilter()
  else router.push({ name: 'discover', query: { filter: '1' } })
}

function logout() {
  signOut()
  showProfile.value = false
  router.push('/')
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  document.addEventListener('click', onDocumentClick)
})
onBeforeUnmount(() => {
  window.clearTimeout(startTimer)
  window.removeEventListener('keydown', onKeydown)
  document.removeEventListener('click', onDocumentClick)
})
</script>

<template>
  <div class="app-shell cinema-shell" :class="{ 'doc-shell': isDocPage }">
    <WallpaperLayer v-if="isWallpaperPage" />
    <header v-if="showChrome" class="topbar">
      <RouterLink class="brand" to="/" aria-label="回到拍社首页">
        <span class="brand-mark">拍</span>
        <span class="brand-copy"><strong>{{ brand.cn }}</strong><small>{{ brand.en }}</small></span>
      </RouterLink>
      <!-- 2026-11-16 用户：返回首页要贴在「拍社」右边，且每一页都能回 -->
      <RouterLink v-if="route.name !== 'home'" class="home-back" to="/"><ArrowLeft :size="14" aria-hidden="true" />返回首页</RouterLink>

      <nav class="main-nav" aria-label="主导航">
        <span class="nav-chapter">/ FIELD JOURNAL</span>
        <RouterLink v-for="(item, index) in navItems" :key="item.to" :to="item.to" :class="{ active: activeLabel === item.label }"><small>0{{ index + 1 }}</small>{{ item.label }}</RouterLink>
      </nav>

      <div class="topbar-actions">
        <RouterLink class="location-chip" to="/discover"><Compass :size="15" /> 西安 <ChevronDown :size="14" /></RouterLink>
        <button class="icon-button notification" aria-label="查看通知"><Bell :size="18" /><i /></button>
        <button class="avatar-button" aria-label="打开个人菜单" :aria-expanded="showProfile" aria-haspopup="menu" @click="showProfile = !showProfile">
          <img v-if="personalize.avatar" class="avatar-photo" :src="personalize.avatar" alt="" />
          <span v-else class="avatar-initial" aria-hidden="true">{{ initial }}</span>
          <ChevronDown :size="14" />
        </button>
        <Transition name="pop-fade">
          <div v-if="showProfile" class="profile-popover" role="menu">
            <p class="eyebrow">当前身份</p>
            <strong>{{ session.name }}<span v-if="roleLabel"> · {{ roleLabel }}</span></strong>
            <RouterLink class="profile-menu-item" to="/profile" role="menuitem"><UserRound :size="14" />个人信息</RouterLink>
            <RouterLink to="/orders" role="menuitem">我的约拍</RouterLink>
            <RouterLink to="/studio" role="menuitem">摄影师工作台</RouterLink>
            <button type="button" class="profile-logout" role="menuitem" @click="logout"><LogOut :size="14" /> 退出登录</button>
          </div>
        </Transition>
      </div>
    </header>

    <main class="page-wrap">
      <RouterView v-slot="{ Component, route: viewRoute }">
        <Transition :name="viewRoute.name === 'home' || viewRoute.name === 'login' ? 'page-morph' : 'page-fade'" mode="out-in">
          <component :is="Component" :key="viewRoute.fullPath" />
        </Transition>
      </RouterView>
    </main>

    <nav v-if="showChrome" class="mobile-nav" aria-label="移动端导航">
      <RouterLink to="/discover"><Search :size="18" /><span>约拍</span></RouterLink>
      <RouterLink to="/market"><Compass :size="18" /><span>接拍</span></RouterLink>
      <RouterLink class="mobile-publish" to="/publish"><Plus :size="20" /></RouterLink>
      <RouterLink to="/orders"><UserRound :size="18" /><span>我的</span></RouterLink>
    </nav>

    <IdentityModal :open="showIdentity" @done="onIdentityDone" />
    <StartBookingPrompt :open="askStart" @start="onStartBooking" @close="askStart = false" />
    <WallpaperPicker />
    <CursorCamera v-if="camCursorPage" />
  </div>
</template>

<style scoped>
.profile-menu-item { display: flex; align-items: center; gap: 7px; }
/* 顶栏头像：上传过就显示照片，未上传仍用首字母块 */
.avatar-photo { width: 30px; height: 30px; border-radius: 50%; object-fit: cover; box-shadow: 0 0 0 1px rgba(242, 238, 231, .25), 0 6px 16px rgba(0, 0, 0, .35); }
</style>
