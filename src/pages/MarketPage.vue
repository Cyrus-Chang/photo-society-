<script setup lang="ts">
import { ArrowRight, Plus, Search, Sparkles } from 'lucide-vue-next'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import MarketPostCard from '../components/MarketPostCard.vue'
import BaseModal from '../components/BaseModal.vue'
import ChatSheet from '../components/ChatSheet.vue'
import PageAtmosphere from '../components/PageAtmosphere.vue'
import { getMarketPosts } from '../services/api'
import type { MarketPost } from '../types'
import { uiUrl } from '../utils/media'

const posts = ref<MarketPost[]>([])
const loading = ref(true)
const error = ref('')
// 2026-11-16 用户：「接拍是想被拍的人发的，为什么有摄影师？」→ 摄影师开放的档期帖不上这页。
// 同一轮又要「在接拍中添加个搭子帖」，所以分两个口径：
//   need      = 想被拍的人发的需求帖（默认）
//   companion = 搭子帖，但排除「顺路带拍」那种摄影师视角的（mode === 'paid-companion'）
const scope = ref<'need' | 'companion'>('need')
const city = ref('全部城市')
const search = ref('')
const listRef = ref<HTMLElement | null>(null)
const boardImage = uiUrl('board-empty.webp')
// 2026-11-16 用户：点「查看详情」点不开。整行点击 → 打开详情弹层。
const activePost = ref<MarketPost | null>(null)
// 2026-11-16 第七轮 P0：接拍页的 AI 入口——把这条需求丢给 AI，让它用摄影师口吻起草一句回复
const chatOpen = ref(false)
const chatPost = ref<MarketPost | null>(null)
const chatOpening = computed(() => {
  const post = chatPost.value
  if (!post) return ''
  const money = post.budget ? `，${post.budget}` : ''
  return `我想接「${post.title}」，${post.city} · ${post.location}，${post.date} ${post.time}${money}。帮我起个头回复 TA。`
})
function openChatDraft(post: MarketPost) {
  chatPost.value = post
  activePost.value = null
  chatOpen.value = true
}
const kindLabel = (kind: MarketPost['kind']) => ({ requirement: '需求帖', availability: '档期帖', companion: '搭子帖' }[kind])

onMounted(async () => {
  try {
    posts.value = await getMarketPosts()
  } catch {
    error.value = '接拍暂时没有加载出来，稍后再试一次。'
  } finally {
    loading.value = false
  }
})

const scopes = [
  { key: 'need', label: '想被拍的' },
  { key: 'companion', label: '搭子' }
] as const

const matchScope = (post: MarketPost, key: 'need' | 'companion') => key === 'need'
  ? post.kind === 'requirement'
  : post.kind === 'companion' && post.mode !== 'paid-companion'

const filteredPosts = computed(() => posts.value.filter((post) => matchScope(post, scope.value) && (city.value === '全部城市' || post.city === city.value) && (!search.value || post.title.includes(search.value) || post.location.includes(search.value))))

const scopeCount = (key: 'need' | 'companion') => posts.value.filter((post) => matchScope(post, key)).length

const hasFilter = computed(() => city.value !== '全部城市' || Boolean(search.value))

function clearFilters() {
  city.value = '全部城市'
  search.value = ''
}

let observer: IntersectionObserver | null = null

function armRows() {
  if (typeof window === 'undefined') return
  if (typeof IntersectionObserver === 'undefined') return
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  const list = listRef.value
  if (!list) return
  observer?.disconnect()
  list.classList.add('is-armed')
  try {
    observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return
        // data 属性不会被 Vue 的 :class 补丁覆盖（见 DiscoverPage 同处注释）
        entry.target.setAttribute('data-revealed', '')
        observer?.unobserve(entry.target)
      })
    }, { threshold: 0.1, rootMargin: '0px 0px -6% 0px' })
  } catch {
    list.classList.remove('is-armed')
    return
  }
  list.querySelectorAll('.market-post-card').forEach((el) => observer?.observe(el))
}

watch([filteredPosts, loading], async () => {
  if (loading.value) return
  await nextTick()
  armRows()
})

onBeforeUnmount(() => observer?.disconnect())
</script>

<template>
  <div class="market-page ps-market">
    <PageAtmosphere variant="market" />
    <h1 class="sr-only">接拍</h1>

    <section class="market-toolbar" aria-label="筛选接拍信息">
      <div class="tabs" role="group" aria-label="接拍信息类型">
        <button v-for="item in scopes" :key="item.key" :class="{ active: scope === item.key }" :aria-pressed="scope === item.key" @click="scope = item.key">
          {{ item.label }}<sup>{{ loading ? '–' : scopeCount(item.key) }}</sup>
        </button>
      </div>
      <div class="toolbar-actions">
        <label class="compact-search"><Search :size="16" aria-hidden="true" /><span class="sr-only">搜索地点或关键词</span><input v-model="search" placeholder="搜地点或关键词" /></label>
        <label class="city-select"><span class="sr-only">选择城市</span><select v-model="city"><option>全部城市</option><option>西安</option><option>成都</option><option>青岛</option></select></label>
        <router-link class="ps-publish" to="/publish"><span class="ps-publish-badge"><Plus :size="16" aria-hidden="true" /></span>发布信息</router-link>
      </div>
    </section>

    <div class="ps-filterbar" aria-label="当前筛选">
      <div class="ps-filters">
        <span v-if="city !== '全部城市'" class="ps-chip">{{ city }}</span>
        <span v-if="search" class="ps-chip">「{{ search }}」</span>
        <button v-if="hasFilter" class="ps-clear" @click="clearFilters">清除</button>
      </div>
      <span :key="filteredPosts.length" class="ps-result">{{ loading ? '读取中' : `${filteredPosts.length} 条结果` }}</span>
    </div>

    <p v-if="error" class="inline-error">{{ error }}</p>

    <section ref="listRef" class="market-list ps-list" aria-label="现场信息列表">
      <div v-if="loading" class="market-skeleton" aria-hidden="true"><div v-for="i in 3" :key="i" class="market-skeleton-row"><span /><div><i /><i /></div></div></div>
      <template v-else>
        <template v-for="(post, index) in filteredPosts" :key="post.id">
          <MarketPostCard :post="post" :index="index" @open="activePost = $event" />
          <div v-if="(index + 1) % 3 === 0 && index + 1 < filteredPosts.length" class="ps-perf" aria-hidden="true" />
        </template>
      </template>
    </section>

    <div v-if="!loading && !filteredPosts.length" class="ps-empty market-empty">
      <div class="ps-empty-media" aria-hidden="true">
        <img v-if="boardImage" :src="boardImage" alt="夜间街边一块被撕空的城市公告板" loading="lazy" />
        <span v-else class="ps-blank" />
      </div>
      <div class="ps-empty-copy">
        <span class="ps-empty-kicker">NO POSTS YET</span>
        <h3>还没有符合条件的现场信息</h3>
        <p>换个城市或关键词，也可以发布一条需求让摄影师来找你。</p>
        <router-link class="ps-empty-link" to="/publish">发布一条信息 <ArrowRight :size="15" aria-hidden="true" /></router-link>
      </div>
    </div>

    <BaseModal :open="Boolean(activePost)" labelled-by="post-dialog-title" size="lg" @close="activePost = null">
      <div v-if="activePost" class="post-dialog">
        <p class="post-dialog-kicker">{{ kindLabel(activePost.kind) }} · {{ activePost.city }}</p>
        <h2 id="post-dialog-title">{{ activePost.title }}</h2>
        <p class="post-dialog-meta">{{ activePost.location }} · {{ activePost.date }} {{ activePost.time }}</p>
        <p class="post-dialog-desc">{{ activePost.description }}</p>
        <dl class="post-dialog-facts">
          <div><dt>发起人</dt><dd>{{ activePost.author }}</dd></div>
          <div v-if="activePost.budget"><dt>费用</dt><dd>{{ activePost.budget }}</dd></div>
          <div v-if="activePost.spots"><dt>名额</dt><dd>{{ activePost.spots }}</dd></div>
          <div><dt>状态</dt><dd>{{ activePost.status }}</dd></div>
        </dl>
        <div class="post-dialog-actions">
          <button class="ps-publish post-dialog-primary" type="button" @click="activePost && openChatDraft(activePost)">
            <Sparkles :size="16" aria-hidden="true" />AI 帮我回一句
          </button>
          <RouterLink class="text-button" to="/publish"><Plus :size="16" aria-hidden="true" />发一条类似的</RouterLink>
          <button class="text-button" type="button" @click="activePost = null">关闭</button>
        </div>
      </div>
    </BaseModal>

    <ChatSheet
      :open="chatOpen"
      persona="zhaoye"
      mode="draft"
      :name="chatPost?.author || '对方'"
      :city="chatPost?.city"
      :price="chatPost?.budget"
      :next-slot="chatPost ? `${chatPost.date} ${chatPost.time}` : undefined"
      :scene="chatPost?.title"
      :title="chatPost ? `帮你回 ${chatPost.author}` : '帮你回一句'"
      :opening="chatOpening"
      @close="chatOpen = false"
    />
  </div>
</template>
