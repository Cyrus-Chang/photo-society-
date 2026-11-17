<script setup lang="ts">
/**
 * 摄影师主页 · 场景覆盖块 SceneShare（2026-11-16，任务 3）
 *
 * 数据优先级（用户定的，不许颠倒）：
 *   ① GET /api/v1/ai/photographer/:id/scene-share → 200 且结构可用 → 用服务端统计
 *   ② 否则（404 / 超时 / 结构不符）→ 本地 computeSceneShare()：该作者作品的 styles 词频
 *
 * 硬规则：界面上必须写清「数据来源」和「统计口径」，前端不编任何数字。
 * 占比 >60% 时给一句中性提示「场景覆盖偏窄」，只陈述事实，不做价值判断。
 */
import { computed, ref, watch } from 'vue'
import { BarChart3, Info } from 'lucide-vue-next'
import { computeSceneShare, getPhotographerSceneShare, type SceneShareResponse } from '../services/api'

const props = defineProps<{
  photographerId: string
  /** 只在空态文案里用，不参与统计 */
  photographerName?: string
}>()

interface SceneRow {
  name: string
  count: number
  ratio: number | null
}

/** 服务端结构尚未定稿：逐字段校验，任何一个字段对不上就整段不用，绝不半信半疑地拼数字 */
type RawScene = { name?: unknown; count?: unknown; ratio?: unknown; percent?: unknown }

const NARROW_THRESHOLD = 0.6

const loading = ref(true)
const rows = ref<SceneRow[]>([])
const total = ref(0)
const source = ref<'api' | 'local'>('local')
const serverNote = ref('')
const unavailableReason = ref('')

const hasData = computed(() => total.value > 0 && rows.value.length > 0)
const narrow = computed(() => {
  if (!hasData.value) return null
  const top = rows.value[0]
  if (top.ratio === null || top.ratio <= NARROW_THRESHOLD) return null
  return { name: top.name, ratio: top.ratio }
})

const sourceText = computed(() => source.value === 'api'
  ? 'GET /api/v1/ai/photographer/:id/scene-share（服务端统计）'
  : '本地作品样张作者的 styles 标签（词频统计）')

const caliberText = computed(() => {
  if (source.value === 'api') {
    return serverNote.value
      ? `统计口径（服务端）：${serverNote.value}`
      : '统计口径由服务端提供，前端只做展示、未二次计算。'
  }
  return `统计口径：按该作者 ${total.value} 张作品的 styles 标签逐张计数，占比＝命中张数÷作品总数；同一张作品可带多个标签，所以各项占比之和可能超过 100%。`
})

function ratioText(ratio: number | null) {
  if (ratio === null || !Number.isFinite(ratio)) return '—'
  return `${Math.round(ratio * 100)}%`
}

function barWidth(ratio: number | null) {
  if (ratio === null || !Number.isFinite(ratio)) return '0%'
  return `${Math.min(100, Math.max(2, Math.round(ratio * 100)))}%`
}

/** 解析服务端返回；不可用返回 null（组件转而走本地统计） */
function readServerScenes(data: SceneShareResponse): { rows: SceneRow[]; total: number } | null {
  const list = Array.isArray(data.scenes) ? data.scenes : Array.isArray(data.topScenes) ? data.topScenes : null
  if (!list || !list.length) return null
  const totalCount = Number(data.total ?? data.totalWorks)
  if (!Number.isFinite(totalCount) || totalCount <= 0) return null

  const parsed: SceneRow[] = []
  for (const item of list as RawScene[]) {
    const name = typeof item?.name === 'string' ? item.name.trim() : ''
    const count = Number(item?.count)
    if (!name || !Number.isFinite(count) || count < 0) return null
    const rawRatio = Number(item?.ratio)
    const rawPercent = Number(item?.percent)
    let ratio: number | null = null
    if (Number.isFinite(rawRatio) && rawRatio >= 0) ratio = rawRatio > 1 ? rawRatio / 100 : rawRatio
    else if (Number.isFinite(rawPercent) && rawPercent >= 0) ratio = rawPercent > 1 ? rawPercent / 100 : rawPercent
    // 服务端没给占比时用「服务端给的张数 ÷ 服务端给的总数」换算，不引入任何额外假设
    if (ratio === null) ratio = count / totalCount
    parsed.push({ name, count, ratio })
  }
  if (!parsed.length) return null
  return { rows: parsed.slice(0, 3), total: totalCount }
}

async function load(id: string) {
  loading.value = true
  rows.value = []
  total.value = 0
  serverNote.value = ''
  unavailableReason.value = ''
  if (!id) {
    loading.value = false
    return
  }
  const outcome = await getPhotographerSceneShare(id)
  if (outcome.available) {
    const parsed = readServerScenes(outcome.data)
    if (parsed) {
      rows.value = parsed.rows
      total.value = parsed.total
      serverNote.value = typeof outcome.data.note === 'string' ? outcome.data.note : ''
      source.value = 'api'
      loading.value = false
      return
    }
    unavailableReason.value = '场景统计接口返回结构不可用'
  } else {
    unavailableReason.value = outcome.status === 404
      ? '场景统计接口未实现（404）'
      : outcome.message
  }

  const local = computeSceneShare(id, 3)
  rows.value = local.scenes.map((item) => ({
    name: item.name,
    count: item.count,
    ratio: typeof item.ratio === 'number' ? item.ratio : local.total ? item.count / local.total : null
  }))
  total.value = local.total
  source.value = 'local'
  loading.value = false
}

watch(() => props.photographerId, (id) => { void load(id) }, { immediate: true })
</script>

<template>
  <section class="sf-scene" aria-live="polite">
    <div class="sf-scene-head">
      <span class="sf-scene-kicker">SCENE COVERAGE / 场景覆盖</span>
      <h2>这位作者都拍些什么场景</h2>
      <p class="sf-scene-lede">
        把作品里的场景标签数一遍，看重心落在哪。偏窄不等于不好——只是先让你心里有数，再决定要不要聊。
      </p>
    </div>

    <div v-if="loading" class="sf-scene-loading">
      <span class="sf-scene-skel" />
      <span class="sf-scene-skel is-short" />
      <small>正在统计场景分布…</small>
    </div>

    <template v-else-if="hasData">
      <div class="sf-scene-figures">
        <div class="sf-scene-figure">
          <span>作品总数</span>
          <b>{{ total }}</b>
          <small>张（可统计的作品）</small>
        </div>
        <div class="sf-scene-figure">
          <span>Top {{ rows.length }} 场景</span>
          <b>{{ rows.map((row) => row.name).join(' / ') }}</b>
          <small>按张数降序</small>
        </div>
      </div>

      <ul class="sf-scene-list">
        <li v-for="(row, index) in rows" :key="row.name" class="sf-scene-row">
          <span class="sf-scene-rank">{{ String(index + 1).padStart(2, '0') }}</span>
          <span class="sf-scene-name">{{ row.name }}</span>
          <span class="sf-scene-bar"><i :style="{ width: barWidth(row.ratio) }" /></span>
          <span class="sf-scene-count">{{ row.count }} 张</span>
          <span class="sf-scene-ratio">{{ ratioText(row.ratio) }}</span>
        </li>
      </ul>

      <p v-if="narrow" class="sf-scene-narrow">
        <Info :size="14" />
        场景覆盖偏窄：{{ ratioText(narrow.ratio) }} 的作品集中在「{{ narrow.name }}」，其他场景样本较少。
      </p>

      <footer class="sf-scene-foot">
        <span class="sf-scene-source"><BarChart3 :size="13" />数据来源：{{ sourceText }}</span>
        <small v-if="unavailableReason" class="sf-scene-reason">回退原因：{{ unavailableReason }}</small>
        <small class="sf-scene-caliber">{{ caliberText }}</small>
      </footer>
    </template>

    <div v-else class="sf-scene-empty">
      <p>还没有可统计的作品，等作者上传样张后再看场景分布。</p>
      <footer class="sf-scene-foot">
        <span class="sf-scene-source"><BarChart3 :size="13" />数据来源：{{ sourceText }}</span>
        <small v-if="unavailableReason" class="sf-scene-reason">回退原因：{{ unavailableReason }}</small>
        <small class="sf-scene-caliber">{{ caliberText }}</small>
      </footer>
    </div>
  </section>
</template>
