<script setup lang="ts">
import { ArrowRight, SlidersHorizontal } from 'lucide-vue-next'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BookingFilterModal from '../components/BookingFilterModal.vue'
import PageAtmosphere from '../components/PageAtmosphere.vue'
import StyleFinder from '../components/StyleFinder.vue'
import { getWorks } from '../services/api'
import { bookingFilterRequest } from '../utils/bookingFlow'
import { hasRole } from '../utils/session'
import type { DiscoverQuery, FilterPayload, WorkCard as WorkCardType } from '../types'
import { resolveWorkImage, uiUrl } from '../utils/media'

const route = useRoute()
const router = useRouter()
const query = ref<DiscoverQuery>({
  location: String(route.query.location || '西安 · 小寨'),
  scene: String(route.query.scene || '周六出古风角色，想拍夜景灯笼感'),
  shootAt: String(route.query.shootAt || '周六 · 11 月 14 日')
})
const budgetMin = ref(String(route.query.budgetMin || '0'))
const budgetMax = ref(String(route.query.budgetMax || route.query.budget || ''))
const works = ref<WorkCardType[]>([])
const aiUsed = ref(false)
const loading = ref(true)
const selectedId = ref('')
const error = ref('')
const filterOpen = ref(false)
const hoverIndex = ref(-1)
const gridRef = ref<HTMLDivElement | null>(null)
const continueRef = ref<HTMLButtonElement | null>(null)
const chairImage = uiUrl('chair-rain.webp')

const selected = computed(() => works.value.find((work) => work.id === selectedId.value))
const locationParts = computed(() => query.value.location.split('·').map((part) => part.trim()).filter(Boolean))

const pad = (value: number) => String(value).padStart(2, '0')

// 数据里没有真实长宽比：用固定的「竖幅 / 方幅 / 横幅」节奏把三种跨度铺开，
// 避免所有格子同高（横幅 6 栏、其余 4 栏，12 栏栅格）。
const aspectCycle = ['is-portrait', 'is-square', 'is-square', 'is-landscape', 'is-landscape']
const spanOf = (index: number) => (index % 5 === 3 || index % 5 === 4 ? 6 : 4)
const aspectClass = (index: number) => aspectCycle[index % aspectCycle.length]

function framePos(index: number) {
  let col = 0
  let row = 0
  for (let i = 0; i < index; i += 1) {
    const width = spanOf(i)
    if (col + width > 12) {
      row += 1
      col = 0
    }
    col += width
    if (col >= 12) {
      row += 1
      col = 0
    }
  }
  return { col, row }
}

function frameStyle(index: number, total: number): Record<string, string> {
  const { col, row } = framePos(index)
  const style: Record<string, string> = { '--ps-delay': `${row * 60 + Math.round(col / 4) * 40}ms` }
  // 末张吃掉整行剩下的栏位：不留半行空洞，也不再用「END / 张数」补丁。
  if (total > 1 && index === total - 1) {
    const remaining = 12 - (col + spanOf(index))
    if (remaining > 1) style.gridColumn = `span ${spanOf(index) + remaining}`
  }
  return style
}

let observer: IntersectionObserver | null = null

function clearReveal() {
  observer?.disconnect()
  observer = null
  gridRef.value?.classList.remove('is-armed')
}

// 只播一次：进入视口后立刻 unobserve；JS 失效或不支持时保持默认可见态。
function armReveal() {
  if (typeof window === 'undefined') return
  if (typeof IntersectionObserver === 'undefined') return
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  const grid = gridRef.value
  if (!grid) return
  observer?.disconnect()
  grid.classList.add('is-armed')
  try {
    observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return
        // 用 data 属性而不是 class：Vue 重渲染 :class 时会整段覆盖 className，
        // 选中态一变，命令式加上的 is-in 会被抹掉（卡片会瞬间消失）。
        entry.target.setAttribute('data-revealed', '')
        observer?.unobserve(entry.target)
      })
    }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' })
  } catch {
    grid.classList.remove('is-armed')
    return
  }
  grid.querySelectorAll('.ps-frame').forEach((el) => observer?.observe(el))
}

const load = async () => {
  loading.value = true
  error.value = ''
  aiUsed.value = false
  try {
    const result = await getWorks(query.value)
    if (result.aiUsed) {
      aiUsed.value = true
      const usable = result.data.filter((work) => !work.imageUrl.startsWith('http'))
      const selected: WorkCardType[] = []
      const selectedIds = new Set<string>()
      const seenPhotographers = new Set<string>()

      // 真接口首屏先按命中顺序保留最多 6 位作者各一张。
      for (const work of usable) {
        if (selected.length >= 6 || seenPhotographers.has(work.photographerId)) continue
        seenPhotographers.add(work.photographerId)
        selected.push(work)
        selectedIds.add(work.id)
      }

      // 剩余名额仍从同一批真实命中中按 score 补齐，避免引入本地 mock 结果。
      const ranked = usable
        .filter((work) => !selectedIds.has(work.id))
        .sort((a, b) => (b.score ?? Number.NEGATIVE_INFINITY) - (a.score ?? Number.NEGATIVE_INFINITY))
      const target = Math.min(10, usable.length)
      works.value = selected.concat(ranked.slice(0, Math.max(0, target - selected.length)))
      return
    }
    // 一个摄影师只留一张：本地兜底路径保持原有行为不变。
    const seen = new Set<string>()
    works.value = result.data.filter((work) => {
      // 2026-11-16 用户：「外链那张太难看了，撤了吧」——选作品页只留已入库的本地图。
      if (work.imageUrl.startsWith('http')) return false
      if (seen.has(work.photographerId)) return false
      seen.add(work.photographerId)
      return true
    })
  } catch {
    error.value = '这次筛选没有成功，先用附近作品给你展示。'
  } finally {
    loading.value = false
  }
}

function selectWork(id: string, event?: MouseEvent | KeyboardEvent) {
  selectedId.value = id
  // 键盘选中（Enter / Space 的 click detail 为 0）后把焦点交给左栏「继续」：
  // 按钮在 DOM 里排在作品网格之前，键盘用户否则要 Shift+Tab 才能回到它。
  if (event && event.detail === 0) nextTick(() => continueRef.value?.focus())
}

const continueToPhotographer = () => selected.value && router.push(`/photographers/${selected.value.photographerId}?work=${selected.value.id}`)

function prettyDate(iso: string) {
  const parts = iso.split('-')
  return parts.length === 3 ? `${Number(parts[1])} 月 ${Number(parts[2])} 日` : iso
}

function applyFilter(payload: FilterPayload) {
  query.value = {
    location: payload.address ? `${payload.city} · ${payload.address}` : payload.city,
    scene: `${payload.type} · ${payload.styles.join(' / ') || '不限风格'}`,
    shootAt: `${prettyDate(payload.date)}${payload.slot ? ` · ${payload.slot}` : ''}`
  }
  budgetMin.value = String(payload.budgetMin)
  budgetMax.value = String(payload.budgetMax)
  filterOpen.value = false
  router.replace({
    name: 'discover',
    query: {
      location: query.value.location,
      scene: query.value.scene,
      shootAt: query.value.shootAt,
      budgetMin: budgetMin.value,
      budgetMax: budgetMax.value
    }
  })
  void load()
}

watch([() => route.query.filter, hasRole], ([value, role]) => {
  // 2026-11-16 用户：不要一打开约拍页就弹筛选窗。
  // 只有显式带 ?filter=1（他真的点了「开始约拍」）才开一次，开完立刻把参数抹掉，
  // 避免刷新 / 后退 / 从别处回来时又弹。平时的入口是页面上的「条件筛选」按钮。
  if (value !== '1' || !role) return
  filterOpen.value = true
  const cleaned = { ...route.query }
  delete cleaned.filter
  void router.replace({ name: 'discover', query: cleaned })
}, { immediate: true })

// 「要不要开始约拍」里点开始：只递增信号，不改 query，页面不重挂载
watch(bookingFilterRequest, () => { filterOpen.value = true })
watch([loading, works], async () => {
  if (loading.value) {
    clearReveal()
    return
  }
  await nextTick()
  armReveal()
})
onMounted(load)
onBeforeUnmount(clearReveal)
</script>

<template>
  <div class="discover-v2 ps-discover">
    <PageAtmosphere variant="discover" />
    <div class="discover-v2-noise" aria-hidden="true" />

    <div class="discover-v2-layout">
      <aside class="field-brief-v2 ps-call-sheet" :class="{ 'is-linked': hoverIndex >= 0 }">
        <div class="ps-sheet-head"><span>CALL SHEET</span><b>{{ pad(works.length) }} 张</b></div>
        <h1>{{ locationParts[0] || '西安' }}<em>{{ locationParts[1] || '现场' }}</em></h1>
        <dl>
          <div data-field="place"><dt>地点</dt><dd>{{ query.location }}</dd></div>
          <div data-field="time"><dt>时间</dt><dd>{{ query.shootAt }}</dd></div>
          <div data-field="scene"><dt>现场感觉</dt><dd>{{ query.scene }}</dd></div>
          <div v-if="budgetMax" data-field="budget"><dt>预算</dt><dd>¥ {{ budgetMin }} – {{ budgetMax }}</dd></div>
        </dl>
        <button class="ps-filter-open" type="button" @click="filterOpen = true">
          <SlidersHorizontal :size="16" aria-hidden="true" />
          条件筛选
        </button>

        <div class="ps-sheet-cta">
          <button
            ref="continueRef"
            class="discover-v2-primary ps-continue"
            :disabled="!selected"
            :aria-label="selected ? `继续，查看 ${selected.title} 的作者与档期` : '先选一张作品'"
            @click="continueToPhotographer"
          >
            {{ selected ? '继续 · 看作者与档期' : '先选一张作品' }}
            <ArrowRight :size="15" aria-hidden="true" />
          </button>
          <small v-if="selected">已选 · {{ selected.title }}</small>
        </div>
      </aside>

      <main class="discover-v2-main">
        <StyleFinder :city="locationParts[0] || ''" />
        <p v-if="error" class="inline-error discover-error">{{ error }}</p>
        <small v-if="aiUsed && works.length" class="ps-diversity-note">已按作者去重，其余按相似度补齐</small>

        <div v-if="loading" class="ps-loading" aria-busy="true" aria-label="正在加载作品">
          <div class="discover-v2-grid ps-grid">
            <div v-for="i in 6" :key="i" class="ps-skel" :class="aspectClass(i - 1)" />
          </div>
          <span class="ps-loading-label">LOADING 03 / 06</span>
        </div>

        <div v-else-if="works.length" ref="gridRef" class="discover-v2-grid ps-grid">
          <div
            v-for="(work, index) in works"
            :key="work.id"
            class="discover-v2-card ps-frame"
            :class="[aspectClass(index), { selected: selectedId === work.id }]"
            :style="frameStyle(index, works.length)"
            role="button"
            tabindex="0"
            :aria-pressed="selectedId === work.id"
            @click="selectWork(work.id, $event)"
            @keydown.enter.prevent="selectWork(work.id, $event)"
            @keydown.space.prevent="selectWork(work.id, $event)"
            @mouseenter="hoverIndex = index"
            @mouseleave="hoverIndex = -1"
          >
            <span class="ps-frame-inner">
              <span class="ps-frame-media">
                <img :src="resolveWorkImage(work.imageUrl)" :alt="work.title" loading="lazy" />
                <span class="ps-frame-num"><b aria-hidden="true">—</b> {{ pad(index + 1) }} / {{ pad(works.length) }}</span>
                <span class="ps-frame-status" :class="work.canBook ? 'is-open' : 'is-tight'"><i aria-hidden="true" />{{ work.canBook ? '可约' : '档期紧' }}</span>
                <span class="ps-crop ps-crop-tl" aria-hidden="true" />
                <span class="ps-crop ps-crop-tr" aria-hidden="true" />
                <span class="ps-crop ps-crop-bl" aria-hidden="true" />
                <span class="ps-crop ps-crop-br" aria-hidden="true" />
                <router-link class="ps-frame-open" :to="`/works/${work.id}`" @click.stop>看作品</router-link>
              </span>
              <span class="ps-frame-body">
                <small>{{ work.city }} / {{ work.styles.join(' · ') }}</small>
                <h3>{{ work.title }}</h3>
                <p>{{ work.photographerName }} · {{ work.shootDate }}</p>
                <span v-if="work.matchReason" class="ps-frame-reason">{{ work.matchReason }}</span>
              </span>
              <span v-if="selectedId === work.id" class="ps-frame-selected">已选 · {{ work.title }}</span>
            </span>
          </div>
        </div>

        <div v-else class="discover-v2-empty ps-empty">
          <div class="ps-empty-media" aria-hidden="true">
            <img v-if="chairImage" :src="chairImage" alt="雨后石板路上的一张空木椅" loading="lazy" />
            <span v-else class="ps-blank" />
          </div>
          <div class="ps-empty-copy">
            <span class="ps-empty-kicker">NO FRAME FOUND</span>
            <h3>暂时没有同时满足地点和风格的作品</h3>
            <p>可以扩大地点范围，或者先去接拍发布一条需求帖。</p>
            <div class="ps-empty-actions">
              <button class="discover-v2-primary" @click="router.push('/market')">去发布需求 <ArrowRight :size="15" /></button>
              <button class="discover-edit ps-link" @click="filterOpen = true">扩大地点范围</button>
            </div>
          </div>
        </div>
      </main>
    </div>

    <p class="sr-only" aria-live="polite">{{ selected ? `已选 ${selected.title}` : '' }}</p>

    <BookingFilterModal :open="filterOpen && hasRole" @close="filterOpen = false" @submit="applyFilter" />
  </div>
</template>

<style scoped>
.ps-diversity-note {
  display: block;
  margin: 0 0 12px;
  color: rgba(242, 238, 231, .54);
  font-size: 11px;
  letter-spacing: .04em;
}
</style>
