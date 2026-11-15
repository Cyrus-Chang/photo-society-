<script setup lang="ts">
import { ArrowLeft, ArrowRight, ArrowUpRight, CalendarDays, Check, Clock3, MapPin, RotateCcw, Sparkles } from 'lucide-vue-next'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BookingFilterModal from '../components/BookingFilterModal.vue'
import { getWorks } from '../services/api'
import type { DiscoverQuery, FilterPayload, WorkCard as WorkCardType } from '../types'
import { resolveWorkImage } from '../utils/media'

const route = useRoute()
const router = useRouter()
const query = ref<DiscoverQuery>({
  location: String(route.query.location || '西安 · 小寨'),
  scene: String(route.query.scene || '周六出古风角色，想拍夜景灯笼感'),
  shootAt: String(route.query.shootAt || '周六 · 11 月 14 日')
})
const budget = ref(String(route.query.budget || ''))
const works = ref<WorkCardType[]>([])
const loading = ref(true)
const selectedId = ref('')
const error = ref('')
const filterOpen = ref(false)
const selected = computed(() => works.value.find((work) => work.id === selectedId.value))
const locationParts = computed(() => query.value.location.split('·').map((part) => part.trim()).filter(Boolean))
const load = async () => {
  loading.value = true
  error.value = ''
  try {
    const result = await getWorks(query.value)
    works.value = result.data
  } catch {
    error.value = '这次筛选没有成功，先用附近作品给你展示。'
  } finally {
    loading.value = false
  }
}
const selectWork = (id: string) => { selectedId.value = id }
const continueToPhotographer = () => selected.value && router.push(`/photographers/${selected.value.photographerId}?work=${selected.value.id}`)

function applyFilter(payload: FilterPayload) {
  query.value = {
    location: `${payload.city} · ${payload.address}`.replace(' · ', ' · ') || payload.city,
    scene: `${payload.type} · ${payload.styles.join(' / ') || '不限风格'}`,
    shootAt: payload.date
  }
  budget.value = String(payload.budget)
  filterOpen.value = false
  router.replace({ name: 'discover', query: { location: query.value.location, scene: query.value.scene, shootAt: query.value.shootAt, budget: budget.value } })
  void load()
}

watch(() => route.query.filter, (value) => { if (value === '1') filterOpen.value = true }, { immediate: true })
onMounted(load)
</script>

<template>
  <div class="discover-v2">
    <div class="discover-v2-noise" aria-hidden="true" />
    <header class="discover-v2-head">
      <div class="discover-brand-row">
        <div class="discover-brand"><span class="discover-brand-mark">拍</span><span>FIELD REPORT / 07</span></div>
        <router-link class="discover-back" to="/"><ArrowLeft :size="15" />回到首页</router-link>
      </div>
      <span class="discover-code">SEARCH / 0007</span>
    </header>

    <div class="discover-v2-progress"><span class="done">01 地点</span><i /><span class="done">02 场景</span><i /><span class="active">03 选作品</span><i /><span>04 看作者</span><i /><span>05 约 TA</span></div>

    <div class="discover-v2-layout">
      <aside class="field-brief-v2">
        <div class="field-brief-kicker"><Sparkles :size="14" />你的拍摄通告</div>
        <h1>{{ locationParts[0] || '西安' }}<em>{{ locationParts[1] || '现场' }}</em></h1>
        <div class="field-brief-line" />
        <dl>
          <div><dt><MapPin :size="14" />地点</dt><dd>{{ query.location }}</dd></div>
          <div><dt><CalendarDays :size="14" />时间</dt><dd>{{ query.shootAt }}</dd></div>
          <div><dt><Clock3 :size="14" />现场感觉</dt><dd>{{ query.scene }}</dd></div>
          <div v-if="budget"><dt>预算</dt><dd>¥ {{ budget }}</dd></div>
        </dl>
        <button class="discover-edit" @click="filterOpen = true"><RotateCcw :size="14" />修改条件</button>
        <div class="field-brief-note"><span>WHY THESE FRAMES</span><p>先按地点、时间和档期过滤，再从真实作品的光线、气质与现场感里匹配。</p></div>
      </aside>

      <main class="discover-v2-main">
        <div class="discover-v2-titlebar"><h2>先看作品，<em>再决定约谁。</em></h2></div>
        <p v-if="error" class="inline-error discover-error">{{ error }}</p>

        <div v-if="loading" class="discover-v2-grid">
          <div v-for="i in 6" :key="i" class="discover-v2-skeleton"><div /><span /><span /></div>
        </div>
        <div v-else-if="works.length" class="discover-v2-grid">
          <button v-for="(work, index) in works" :key="work.id" class="discover-v2-card" :class="{ selected: selectedId === work.id }" :style="{ '--card-delay': `${index * .08}s` }" @click="selectWork(work.id)">
            <div class="discover-v2-image"><img :src="resolveWorkImage(work.imageUrl)" :alt="work.title" loading="lazy" /><span class="discover-v2-status"><i />{{ work.canBook ? 'OPEN / 可约' : 'FULL / 档期紧' }}</span><span class="discover-v2-index">0{{ index + 1 }}</span><span class="discover-v2-open"><ArrowUpRight :size="16" /></span><span v-if="selectedId === work.id" class="discover-v2-selected"><Check :size="13" />已选</span></div>
            <div class="discover-v2-card-body"><div><small>{{ work.city }} / {{ work.styles.join(' · ') }}</small><h3>{{ work.title }}</h3></div><ArrowRight class="discover-v2-card-arrow" :size="16" /><p>{{ work.photographerName }} · {{ work.shootDate }}</p><span v-if="work.matchReason" class="discover-v2-reason">{{ work.matchReason }}</span></div>
          </button>
        </div>
        <div v-else class="discover-v2-empty"><span>NO FRAME FOUND</span><h3>暂时没有同时满足地点和风格的作品</h3><p>可以扩大地点范围，或者先去集市发布一条需求帖。</p><div><button class="discover-v2-primary" @click="router.push('/market')">去发布需求 <ArrowRight :size="15" /></button><button class="discover-edit" @click="filterOpen = true">扩大地点范围</button></div></div>
      </main>
    </div>

    <div v-if="selected" class="selection-v2"><div><span>SELECTED FRAME / {{ selected.id }}</span><strong>{{ selected.title }}</strong><small>{{ selected.photographerName }} · {{ selected.location }}</small></div><button class="discover-v2-primary" @click="continueToPhotographer">看作者与档期 <ArrowRight :size="16" /></button></div>

    <BookingFilterModal :open="filterOpen" @close="filterOpen = false" @submit="applyFilter" />
  </div>
</template>
