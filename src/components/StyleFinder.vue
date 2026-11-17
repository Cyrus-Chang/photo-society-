<script setup lang="ts">
/**
 * 以图搜图 · StyleFinder（2026-11-16，任务 2）
 *
 * 双轨原则：13 类风格标签那条路（看图说风格）原样不动，这里是第二条路「以图搜图」，
 * 两条并存互补，谁都不替换谁。
 *
 * 数据走向：
 *   1) 有真接口时 —— POST /api/v1/ai/similar（multipart: file, query: topK=3）
 *      展示 matchPercent（后端给的重合度），这就是「样片检索」。
 *   2) 接口 404 / 超时 / 返回空 —— 降级成 classify 风格标签 + 本地作品标签近似匹配，
 *      界面必须写明「基于风格标签的近似匹配（样片检索服务未就绪）」。
 *      这条路径**不是**全站向量比对，重合度是标签覆盖率，绝不冒充足量结果。
 *   3) classify 也失败 —— 直接报错，不给假结果（不编人也不编分数）。
 */
import { computed, onBeforeUnmount, ref } from 'vue'
import { AlertTriangle, ImagePlus, LoaderCircle, RotateCcw } from 'lucide-vue-next'
import {
  classifyImage,
  findSimilarPhotographers,
  matchPhotographersByTags,
  type SimilarMatch,
  type SimilarStyleMatch
} from '../services/api'
import { styleLabel, toneLabel } from '../utils/aiLabels'
import { resolveWorkImage } from '../utils/media'

const props = defineProps<{ city?: string }>()

type Phase = 'idle' | 'loading' | 'vector' | 'tags' | 'error'

const MAX_BYTES = 10 * 1024 * 1024

const phase = ref<Phase>('idle')
const statusText = ref('')
const errorText = ref('')
const matches = ref<SimilarMatch[]>([])
const styleMatch = ref<SimilarStyleMatch | null>(null)
const fallbackReason = ref('')
const styleLabels = ref<string[]>([])
const latency = ref<number | null>(null)
const fileName = ref('')
const previewUrl = ref('')
const inputRef = ref<HTMLInputElement | null>(null)
let objectUrl = ''

const busy = computed(() => phase.value === 'loading')
const hasResult = computed(() => matches.value.length > 0)
const isFallback = computed(() => phase.value === 'tags')

const styleMatchText = computed(() => {
  const item = styleMatch.value
  if (!item) return ''
  const name = item.name || item.code || ''
  if (!name) return ''
  const confidence = typeof item.confidence === 'number' ? ` · 置信度 ${Math.round(item.confidence * 100)}%` : ''
  return `样片风格：${name}${confidence}`
})

const sourceNote = computed(() => {
  if (phase.value === 'vector') {
    const time = latency.value === null ? '' : ` · ${Math.round(latency.value)}ms`
    return `数据来源：POST /api/v1/ai/similar（样片向量检索）${time}`
  }
  if (phase.value === 'tags') {
    const labels = styleLabels.value.join(' / ') || '—'
    const time = latency.value === null ? '' : ` · 共 ${(latency.value / 1000).toFixed(1)}s`
    return `数据来源：POST /api/v1/ai/classify 风格标签（${labels}）+ 本地作品标签匹配${time}`
  }
  return ''
})

function percentText(value?: number) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '—'
  return `${Math.round(value)}%`
}

function overlapTags(item: SimilarMatch) {
  if (Array.isArray(item.styleOverlap)) return item.styleOverlap.filter(Boolean)
  if (typeof item.styleOverlap === 'number') return []
  return Array.isArray(item.tags) ? item.tags.filter(Boolean) : []
}

function topWorks(item: SimilarMatch) {
  return (item.works || []).slice(0, 2)
}

function releasePreview() {
  if (objectUrl) {
    URL.revokeObjectURL(objectUrl)
    objectUrl = ''
  }
  previewUrl.value = ''
}

function reset() {
  releasePreview()
  phase.value = 'idle'
  statusText.value = ''
  errorText.value = ''
  matches.value = []
  styleMatch.value = null
  fallbackReason.value = ''
  styleLabels.value = []
  latency.value = null
  fileName.value = ''
  if (inputRef.value) inputRef.value.value = ''
}

function pickFile() {
  if (busy.value) return
  inputRef.value?.click()
}

async function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) {
    phase.value = 'error'
    errorText.value = '只能选图片文件（jpg / png / webp）。'
    return
  }
  if (file.size > MAX_BYTES) {
    phase.value = 'error'
    errorText.value = `这张图 ${(file.size / 1024 / 1024).toFixed(1)}MB，超过 10MB 上限，换一张小点的。`
    return
  }
  releasePreview()
  objectUrl = URL.createObjectURL(file)
  previewUrl.value = objectUrl
  fileName.value = file.name
  await run(file)
}

async function run(file: File) {
  phase.value = 'loading'
  errorText.value = ''
  matches.value = []
  styleMatch.value = null
  fallbackReason.value = ''
  styleLabels.value = []
  latency.value = null
  statusText.value = '正在把你的样片送去做样片检索…'
  const started = performance.now()

  const outcome = await findSimilarPhotographers(file, 3)

  if (outcome.available && outcome.data.matches && outcome.data.matches.length) {
    matches.value = outcome.data.matches
    styleMatch.value = outcome.data.styleMatch ?? null
    latency.value = typeof outcome.data.latencyMs === 'number'
      ? outcome.data.latencyMs
      : Math.round(performance.now() - started)
    phase.value = 'vector'
    statusText.value = ''
    return
  }

  // —— 降级：样片检索未就绪（404 / 超时 / 空结果）→ 风格标签近似匹配 ——
  fallbackReason.value = outcome.available
    ? '样片检索服务返回了空候选'
    : outcome.reason.message
  statusText.value = '样片检索未就绪，正在识别样片风格标签后近似匹配…'

  try {
    const classified = await classifyImage(file)
    const labels: string[] = []
    for (const item of classified.style || []) {
      const name = styleLabel(item.code)
      if (name && !labels.includes(name)) labels.push(name)
    }
    for (const item of classified.tone || []) {
      const name = toneLabel(item.code)
      if (name && !labels.includes(name)) labels.push(name)
    }
    styleLabels.value = labels
    if (!labels.length) {
      phase.value = 'error'
      statusText.value = ''
      errorText.value = '样片没能识别出可用的风格标签，做不了近似匹配（不给你编结果）。'
      return
    }
    const approximated = matchPhotographersByTags(labels, 3, props.city)
    if (!approximated.length) {
      phase.value = 'error'
      statusText.value = ''
      errorText.value = `识别出的标签（${labels.join('、')}）在本地作品里找不到对应的摄影师。`
      return
    }
    matches.value = approximated
    latency.value = Math.round(performance.now() - started)
    phase.value = 'tags'
    statusText.value = ''
  } catch (error) {
    phase.value = 'error'
    statusText.value = ''
    errorText.value = error instanceof Error ? error.message : '风格识别失败'
  }
}

onBeforeUnmount(releasePreview)
</script>

<template>
  <section class="sf-finder" :class="[`is-${phase}`]" aria-live="polite">
    <header class="sf-head">
      <span class="sf-kicker">STYLE FINDER / 以图搜图</span>
      <h2>上传一张心仪样片，找口味最接近的摄影师</h2>
      <p class="sf-lede">
        第二条路：不看关键词，看画面。风格标签那条 13 类分类照旧展示，这里只负责「这张样片像谁拍的」。
      </p>
    </header>

    <div class="sf-bar">
      <input ref="inputRef" class="sf-file" type="file" accept="image/*" @change="onFileChange" />
      <button class="sf-pick" type="button" :disabled="busy" @click="pickFile">
        <LoaderCircle v-if="busy" class="spin" :size="15" />
        <ImagePlus v-else :size="15" />
        {{ busy ? '检索中…' : previewUrl ? '换一张样片' : '选择样片' }}
      </button>

      <div v-if="previewUrl" class="sf-preview">
        <img :src="previewUrl" alt="你上传的样片" />
        <span class="sf-preview-name">{{ fileName }}</span>
      </div>

      <p v-if="statusText" class="sf-status"><LoaderCircle class="spin" :size="13" />{{ statusText }}</p>

      <button v-if="previewUrl && !busy" class="sf-reset" type="button" @click="reset">
        <RotateCcw :size="13" />清空
      </button>
    </div>

    <p v-if="errorText" class="sf-error" role="alert"><AlertTriangle :size="15" />{{ errorText }}</p>

    <div v-if="hasResult" class="sf-results">
      <div class="sf-source">
        <span v-if="phase === 'vector'" class="sf-badge is-real">样片检索 · 真接口</span>
        <span v-else class="sf-badge is-approx">基于风格标签的近似匹配（样片检索服务未就绪）</span>
        <small>{{ sourceNote }}</small>
      </div>

      <p v-if="isFallback" class="sf-approx-note">
        这次没有做全站向量比对：{{ fallbackReason }}。下面的重合度＝样片识别出的风格标签里，能在该作者作品上找到对应标签的比例，
        是标签覆盖率，不是「像不像」的相似度。真接口接通后这里会换成样片向量检索结果。
      </p>
      <p v-else-if="styleMatchText" class="sf-style-match">{{ styleMatchText }}</p>

      <ol class="sf-list">
        <li v-for="(item, index) in matches" :key="item.photographerId" class="sf-card">
          <div class="sf-card-head">
            <span class="sf-rank">{{ String(index + 1).padStart(2, '0') }}</span>
            <div class="sf-card-id">
              <strong>{{ item.name }}</strong>
              <small>{{ item.city || '城市待补充' }}<template v-if="item.sameCity"> · 同城</template></small>
            </div>
            <div class="sf-percent" :class="{ 'is-approx': isFallback }">
              <b>{{ percentText(item.matchPercent) }}</b>
              <small>{{ isFallback ? '标签重合' : '重合度' }}</small>
            </div>
          </div>

          <div v-if="overlapTags(item).length" class="sf-tags">
            <span v-for="tag in overlapTags(item)" :key="tag">{{ tag }}</span>
          </div>

          <div v-if="topWorks(item).length" class="sf-works">
            <figure v-for="work in topWorks(item)" :key="work.id" class="sf-work">
              <img :src="resolveWorkImage(work.imageUrl)" :alt="work.title" loading="lazy" />
              <figcaption>{{ work.title }}</figcaption>
            </figure>
          </div>
          <p v-else class="sf-no-work">这位作者没有可展示的代表作</p>
        </li>
      </ol>
    </div>
  </section>
</template>
