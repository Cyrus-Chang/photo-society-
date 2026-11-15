<script setup lang="ts">
import { ArrowRight, Filter, Plus, Search } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import MarketPostCard from '../components/MarketPostCard.vue'
import { getMarketPosts } from '../services/api'
import type { MarketPost, PostKind } from '../types'

const posts = ref<MarketPost[]>([])
const loading = ref(true)
const error = ref('')
const activeTab = ref<PostKind | 'all'>('all')
const city = ref('全部城市')
const search = ref('')

onMounted(async () => {
  try {
    posts.value = await getMarketPosts()
  } catch {
    error.value = '集市暂时没有加载出来，稍后再试一次。'
  } finally {
    loading.value = false
  }
})

const tabs = [
  { key: 'all', label: '全部' },
  { key: 'requirement', label: '需求帖' },
  { key: 'availability', label: '档期帖' },
  { key: 'companion', label: '搭子帖' }
] as const

const filteredPosts = computed(() => posts.value.filter((post) => (activeTab.value === 'all' || post.kind === activeTab.value) && (city.value === '全部城市' || post.city === city.value) && (!search.value || post.title.includes(search.value) || post.location.includes(search.value))))

const today = computed(() => {
  const now = new Date()
  return `${String(now.getMonth() + 1).padStart(2, '0')}.${String(now.getDate()).padStart(2, '0')}`
})
</script>

<template>
  <div class="market-page">
    <section class="market-hero">
      <div class="market-hero-copy">
        <p class="kicker"><span class="kicker-line" />拍摄集市</p>
        <h1>有人在等一位摄影师，<br /><em>也有人正好有一段空档。</em></h1>
        <p class="market-hero-lede">把需求、档期和搭子放在同一张城市公告栏上。关系先说清楚，再决定要不要一起出发。</p>
        <div class="market-hero-stats" aria-label="集市信息概览">
          <span><strong>{{ loading ? '…' : posts.length }}</strong> 条现场信息</span>
          <span><strong>3</strong> 种合作关系</span>
          <span><strong>今日</strong> 持续更新</span>
        </div>
      </div>
      <div class="market-hero-note">
        <span>LIVE BOARD · {{ today }}</span>
        <strong>西安</strong>
        <small>{{ loading ? '正在读取现场信息…' : `今天有 ${posts.length} 条现场信息正在寻找回应` }}</small>
        <ArrowRight :size="18" aria-hidden="true" />
      </div>
    </section>

    <section class="market-toolbar" aria-label="筛选集市信息">
      <div class="tabs" role="group" aria-label="信息类型">
        <button v-for="tab in tabs" :key="tab.key" :class="{ active: activeTab === tab.key }" :aria-pressed="activeTab === tab.key" @click="activeTab = tab.key">
          {{ tab.label }}<sup v-if="tab.key !== 'all'">{{ posts.filter((post) => post.kind === tab.key).length }}</sup>
        </button>
      </div>
      <div class="toolbar-actions">
        <label class="compact-search"><Search :size="16" aria-hidden="true" /><span class="sr-only">搜索地点或关键词</span><input v-model="search" placeholder="搜地点或关键词" /></label>
        <label class="city-select"><span class="sr-only">选择城市</span><select v-model="city"><option>全部城市</option><option>西安</option><option>成都</option><option>青岛</option></select></label>
        <router-link class="button button-primary button-small" to="/publish"><Plus :size="16" aria-hidden="true" />发布信息</router-link>
      </div>
    </section>

    <div class="market-tip">
      <Filter :size="15" aria-hidden="true" />
      <span>搭子帖关系</span>
      <span class="market-legend-item"><b class="orange-dot" />顺路带拍</span>
      <span class="market-legend-item"><b class="blue-dot" />纯搭子</span>
      <span class="tip-space" />
      <span class="market-tip-note">地点、时间、预算与可约状态已整理在每条信息里</span>
    </div>

    <p v-if="error" class="inline-error">{{ error }}</p>

    <section class="market-list" aria-label="现场信息列表">
      <div class="market-list-heading"><span>现场信息</span><strong>{{ loading ? '读取中' : `${filteredPosts.length} 条结果` }}</strong></div>
      <div v-if="loading" class="market-skeleton" aria-hidden="true"><div v-for="i in 3" :key="i" class="market-skeleton-row"><span /><div><i /><i /></div></div></div>
      <template v-else>
        <MarketPostCard v-for="post in filteredPosts" :key="post.id" :post="post" />
      </template>
    </section>

    <div v-if="!loading && !filteredPosts.length" class="empty-state market-empty">
      <h3>还没有符合条件的现场信息</h3>
      <p>换个城市或关键词，也可以发布一条需求让摄影师来找你。</p>
      <router-link class="button button-secondary" to="/publish">发布一条信息 <ArrowRight :size="16" /></router-link>
    </div>
  </div>
</template>
