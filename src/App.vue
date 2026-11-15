<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Bell, ChevronDown, Compass, LogOut, Plus, Search, UserRound } from 'lucide-vue-next'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import IdentityModal from './components/IdentityModal.vue'
import CursorCamera from './components/CursorCamera.vue'
import { brand } from './utils/brand'
import { hasRole, isAuthed, roleLabel, session, signOut } from './utils/session'

const route = useRoute()
const router = useRouter()
const showProfile = ref(false)

const navItems = [
  { label: '约拍', to: '/discover' },
  { label: '集市', to: '/market' },
  { label: '圈子', to: '/circle' }
]

const activeLabel = computed(() => {
  if (route.path.startsWith('/market')) return '集市'
  if (route.path.startsWith('/discover') || route.path.startsWith('/works') || route.path.startsWith('/photographers')) return '约拍'
  if (route.path.startsWith('/circle')) return '圈子'
  return ''
})

// 文档型页面（工作台 / 订单 / 发布 / 作品详情 / 摄影师主页 / 圈子）走深色主题。
const docPageNames = new Set(['orders', 'studio', 'publish', 'work', 'photographer', 'circle'])
const isDocPage = computed(() => docPageNames.has(String(route.name ?? '')))

// 只有在登录之后、且不是首页/登录页时，才出现常规导航。
const showChrome = computed(() => isAuthed.value && route.meta.chrome !== false)
const showIdentity = computed(() => isAuthed.value && !hasRole.value)
const initial = computed(() => (session.name || '拍').slice(0, 1).toUpperCase())

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
  const current = route.name === 'discover' ? { filter: '1' } : null
  if (current) router.replace({ name: 'discover', query: current })
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
  window.removeEventListener('keydown', onKeydown)
  document.removeEventListener('click', onDocumentClick)
})
</script>

<template>
  <div class="app-shell cinema-shell" :class="{ 'doc-shell': isDocPage }">
    <header v-if="showChrome" class="topbar">
      <RouterLink class="brand" to="/" aria-label="回到拍社首页">
        <span class="brand-mark">拍</span>
        <span class="brand-copy"><strong>{{ brand.cn }}</strong><small>{{ brand.en }}</small></span>
      </RouterLink>

      <nav class="main-nav" aria-label="主导航">
        <span class="nav-chapter">/ FIELD JOURNAL</span>
        <RouterLink v-for="(item, index) in navItems" :key="item.to" :to="item.to" :class="{ active: activeLabel === item.label }"><small>0{{ index + 1 }}</small>{{ item.label }}</RouterLink>
      </nav>

      <div class="topbar-actions">
        <RouterLink class="location-chip" to="/discover"><Compass :size="15" /> 西安 <ChevronDown :size="14" /></RouterLink>
        <button class="icon-button notification" aria-label="查看通知"><Bell :size="18" /><i /></button>
        <button class="avatar-button" aria-label="打开个人菜单" :aria-expanded="showProfile" aria-haspopup="menu" @click="showProfile = !showProfile">
          <span class="avatar-initial" aria-hidden="true">{{ initial }}</span>
          <ChevronDown :size="14" />
        </button>
        <Transition name="pop-fade">
          <div v-if="showProfile" class="profile-popover" role="menu">
            <p class="eyebrow">当前身份</p>
            <strong>{{ session.name }}<span v-if="roleLabel"> · {{ roleLabel }}</span></strong>
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
      <RouterLink to="/market"><Compass :size="18" /><span>集市</span></RouterLink>
      <RouterLink class="mobile-publish" to="/publish"><Plus :size="20" /></RouterLink>
      <RouterLink to="/orders"><UserRound :size="18" /><span>我的</span></RouterLink>
    </nav>

    <IdentityModal :open="showIdentity" @done="onIdentityDone" />
    <CursorCamera v-if="camCursorPage" />
  </div>
</template>
