<script setup lang="ts">
/**
 * 作品体检面板（2026-11-16 · 接拍线）
 *
 * 两段式，每一段各自如实报状态，不互相美化：
 *   ① POST /api/v1/ai/classify（multipart 字段 file）→ 风格 / 影调 / 置信度
 *   ② 发布前 POST /api/v1/ai/works/audit（multipart 字段 file）；已有 workId 时保留 GET 兼容路径
 *
 * 铁律（这三条比好看重要）：
 *   · 识别没成功就不显示标签，不拿占位标签顶替；
 *   · 查重没返回就不显示分数。契约（/api/v1/ai/works/audit）尚未实现，
 *     任一路由未就绪都如实降级成「查重服务未就绪，仅展示风格标签」，绝不编一个分数；
 *   · 低置信（needsReview）只标「建议人工确认」并隐藏百分比，不把参考值包装成确定结论。
 *
 * 关于 fetch：本组件直接用 fetch 而不走 src/services/api.ts，是因为该文件由约拍线工程师统一管理。
 * 等 api.ts 补出 classifyWorkImage(file) / auditWork(workId) 之后，再把两段 fetch 迁入统一封装。
 */
import { computed, onBeforeUnmount, ref } from 'vue'
import { ScanSearch, TriangleAlert, Upload } from 'lucide-vue-next'
import { styleLabel, toneLabel, type AiClassifyResult } from '../utils/aiLabels'

const props = defineProps<{
  /**
   * 已落库作品 id。发布前没有 workId 时，查重改走 multipart file 的 POST 路由；
   * 发布成功后由上层传真实 id，即可继续使用 GET 兼容路径。
   */
  workId?: string
  /** 与发布页文案保持一致：单张 10MB 以内 */
  maxFileSizeMb?: number
}>()

const apiBase = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')
/** 与 api.ts 的 CLASSIFY_TIMEOUT 一致：冷启动（torch + CLIP）约 45s，留 30s 先给出提示 */
const CLASSIFY_TIMEOUT = 30000

const maxFileSizeMb = computed(() => props.maxFileSizeMb ?? 10)
const maxBytes = computed(() => maxFileSizeMb.value * 1024 * 1024)

const fileInput = ref<HTMLInputElement | null>(null)
const picked = ref<{ name: string; url: string } | null>(null)
const stage = ref<'idle' | 'classifying' | 'classified'>('idle')
const classifyResult = ref<AiClassifyResult | null>(null)
const classifyError = ref('')
const classifyLatency = ref(0)

type AuditState = 'idle' | 'pending' | 'unavailable'
const auditState = ref<AuditState>('idle')
const auditMessage = ref('')

const styleTags = computed(() => (classifyResult.value?.style ?? []).slice(0, 3))
const toneTags = computed(() => (classifyResult.value?.tone ?? []).slice(0, 4))
const needsReview = computed(() => classifyResult.value?.needsReview === true)
const styleNeedsReview = computed(() => needsReview.value || styleTags.value.some((tag) => tag.needsReview === true))
const confidenceThreshold = computed(() => {
  const value = classifyResult.value?.confidenceThreshold
  return typeof value === 'number' && value > 0 ? value : 0
})
const confidenceSource = computed(() => {
  const fromCalibration = classifyResult.value?.confidenceCalibration?.style?.method
  if (fromCalibration) return fromCalibration
  const source = classifyResult.value?.confidenceSource
  if (typeof source === 'string') return source
  return source?.style ?? ''
})

const auditHeadline = '查重服务未就绪，仅展示风格标签。'

function describeError(error: unknown): string {
  if (error instanceof DOMException && error.name === 'AbortError') {
    return '识别超时（模型冷启动首次约 45 秒），稍后重试，或先人工补标签。'
  }
  if (error instanceof TypeError) {
    return '连不上识别服务：确认 8100 已启动、dev 代理生效。'
  }
  return error instanceof Error ? error.message : '识别失败'
}

function reset() {
  if (picked.value) URL.revokeObjectURL(picked.value.url)
  picked.value = null
  stage.value = 'idle'
  classifyResult.value = null
  classifyError.value = ''
  classifyLatency.value = 0
  auditState.value = 'idle'
  auditMessage.value = ''
}

/** 第一段：POST /api/v1/ai/classify（multipart 字段 file，和 api.ts 的 classifyImage 同形） */
async function runClassify(file: File) {
  stage.value = 'classifying'
  classifyError.value = ''
  classifyResult.value = null
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), CLASSIFY_TIMEOUT)
  const form = new FormData()
  form.append('file', file)
  try {
    // @todo 等 api.ts 提供 classifyWorkImage(file) 后替换这一段
    const response = await fetch(`${apiBase}/ai/classify`, { method: 'POST', body: form, signal: controller.signal })
    if (!response.ok) throw new Error(`识别服务返回 HTTP ${response.status}`)
    const payload = await response.json()
    const data = (payload?.data ?? payload) as AiClassifyResult
    if (!data || (!data.style?.length && !data.tone?.length)) {
      classifyError.value = '识别服务没有返回风格或影调标签，请人工确认后手动打标签。'
      return
    }
    classifyResult.value = data
    classifyLatency.value = Math.round(Number(data.latencyMs) || 0)
  } catch (error) {
    classifyError.value = describeError(error)
  } finally {
    window.clearTimeout(timer)
    stage.value = 'classified'
  }
}

/** 第二段：无 workId 走 POST multipart file；有 workId 保留 GET 兼容路径。 */
async function runAudit(file: File) {
  auditState.value = 'pending'
  auditMessage.value = ''
  const workId = props.workId?.trim()
  try {
    let response: Response
    if (workId) {
      // 有落库 id 时保留旧路由，兼容发布后的作品复查。
      response = await fetch(`${apiBase}/ai/works/audit?workId=${encodeURIComponent(workId)}`, { method: 'GET' })
    } else {
      const form = new FormData()
      form.append('file', file)
      response = await fetch(`${apiBase}/ai/works/audit`, { method: 'POST', body: form })
    }
    if (!response.ok) {
      auditState.value = 'unavailable'
      auditMessage.value = `查重接口返回 HTTP ${response.status}`
      return
    }
    // 查重契约尚未接入前，任何响应都保持降级展示，避免把未经确认的分数带进发布流。
    auditState.value = 'unavailable'
    auditMessage.value = '查重接口已响应，但当前界面仅展示风格标签，不显示查重分数'
  } catch {
    auditState.value = 'unavailable'
    auditMessage.value = '请求没有到达查重服务（网络或代理错误）'
  }
}

async function handleFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = '' // 允许重复选同一张
  if (!file) return
  reset()
  if (!file.type.startsWith('image/')) {
    classifyError.value = '只支持图片文件（JPG / PNG / WebP）。'
    return
  }
  if (file.size > maxBytes.value) {
    classifyError.value = `这张图 ${(file.size / 1024 / 1024).toFixed(1)}MB，超过 ${maxFileSizeMb.value}MB，先压缩再体检。`
    return
  }
  picked.value = { name: file.name, url: URL.createObjectURL(file) }
  await runClassify(file)
  await runAudit(file)
}

const openPicker = () => fileInput.value?.click()

onBeforeUnmount(() => {
  if (picked.value) URL.revokeObjectURL(picked.value.url)
})
</script>

<template>
  <section class="wa-panel wa-audit" aria-labelledby="wa-audit-title">
    <header class="wa-head">
      <p class="wa-kicker">WORK AUDIT · 作品体检</p>
      <h2 id="wa-audit-title" class="wa-title">发布前，先看清<em>这张照片的属性</em></h2>
      <p class="wa-sub">先看 AI 认出的风格与影调，再确认查重服务是否就绪。两步结果各自独立，谁没回来就说谁没回来。</p>
    </header>

    <div class="wa-steps" aria-hidden="true">
      <span class="wa-step" :class="{ 'is-done': picked, 'is-on': stage === 'classifying' }">01 选图</span>
      <span class="wa-step" :class="{ 'is-on': stage === 'classifying', 'is-done': stage === 'classified' }">02 识别</span>
      <span class="wa-step" :class="{ 'is-on': auditState === 'pending', 'is-done': auditState === 'unavailable' }">03 查重</span>
    </div>

    <div class="wa-picker">
      <img v-if="picked" class="wa-picker-img" :src="picked.url" :alt="picked.name" />
      <div class="wa-picker-copy">
        <strong>{{ picked ? picked.name : '选一张准备发布的照片' }}</strong>
        <span>{{ picked ? `单张上限 ${maxFileSizeMb}MB · 只做识别与查重，不上传入库` : `JPG / PNG / WebP · 单张 ${maxFileSizeMb}MB 以内` }}</span>
      </div>
      <button class="wa-btn" type="button" @click="openPicker">
        <Upload :size="14" />{{ picked ? '换一张' : '选择照片' }}
      </button>
      <input ref="fileInput" class="sr-only" type="file" accept="image/jpeg,image/png,image/webp" @change="handleFile" />
    </div>

    <!-- STAGE 01 / 风格与影调 -->
    <div v-if="stage !== 'idle'" class="wa-stage">
      <p class="wa-stage-head">
        <span>STAGE 01 / 风格与影调 · AI 识别</span>
        <b v-if="classifyLatency">{{ classifyLatency }}ms</b>
      </p>

      <p v-if="stage === 'classifying'" class="wa-note">正在识别…（首次冷启动约 45 秒）</p>

      <template v-else-if="classifyError">
        <p class="wa-error"><TriangleAlert :size="14" /> {{ classifyError }}</p>
        <p class="wa-note">识别没返回结果时不显示标签，也不拿占位词顶替。</p>
      </template>

      <template v-else-if="classifyResult">
        <div v-if="styleTags.length" class="ai-tag-group">
          <span class="ai-tag-label">STYLE</span>
          <span v-for="tag in styleTags" :key="tag.code" class="ai-tag is-style" :class="{ 'wa-tag-review': needsReview || tag.needsReview }">
            <span>{{ styleLabel(tag.code) }}</span>
            <b v-if="!needsReview && !tag.needsReview && tag.confidence">{{ Math.round(tag.confidence * 100) }}%</b>
          </span>
          <span v-if="styleNeedsReview" class="wa-flag">建议人工确认</span>
        </div>
        <div v-if="toneTags.length" class="ai-tag-group">
          <span class="ai-tag-label">TONE</span>
          <span v-for="tag in toneTags" :key="tag.code" class="ai-tag is-tone"><span>{{ toneLabel(tag.code) }}</span></span>
        </div>
        <p v-if="styleNeedsReview" class="wa-note is-warn">
          置信度低于服务阈值{{ confidenceThreshold ? `（${confidenceThreshold}）` : '' }}，风格标签只作参考：低置信时本面板不显示百分比，避免把参考值读成确定结论。
        </p>
        <p v-else-if="confidenceSource" class="wa-note">置信度来源：{{ confidenceSource }}</p>
      </template>
    </div>

    <!-- STAGE 02 / 作品库查重 -->
    <div v-if="stage === 'classified'" class="wa-stage">
      <p class="wa-stage-head">
        <span>STAGE 02 / 作品库查重</span>
        <b v-if="auditState === 'pending'">CHECKING…</b>
      </p>

      <p v-if="auditState === 'pending'" class="wa-note">正在向平台作品库发起比对…</p>

      <template v-else>
        <p class="wa-note is-warn"><ScanSearch :size="13" /> {{ auditHeadline }}</p>
        <p v-if="auditMessage" class="wa-note">
          原因：{{ auditMessage }}。当前仅展示风格标签，不显示任何查重分数。
        </p>
      </template>
    </div>

    <p class="wa-method">
      <b>AI 识别与查重是两件独立的事，各自报各自的真实状态。</b>
      识别走本地模型（风格 13 类原型 + 影调 9 条规则）；查重服务未就绪时不显示任何分数。
    </p>
  </section>
</template>

<style scoped>
.wa-panel {
  box-sizing: border-box;
  width: 100%;
  max-width: 100%;
  min-width: 0;
}

.wa-panel *,
.wa-panel *::before,
.wa-panel *::after {
  box-sizing: border-box;
}

.wa-title,
.wa-sub,
.wa-method,
.wa-note,
.wa-error {
  overflow-wrap: anywhere;
}

.wa-stage-head {
  min-width: 0;
  flex-wrap: wrap;
}

@media (max-width: 390px) {
  .wa-panel {
    padding-inline: 12px;
  }

  .wa-col-head {
    align-items: flex-start;
  }

  .wa-col-head span {
    white-space: normal;
    text-align: right;
  }

  .wa-row-num {
    white-space: normal;
    text-align: right;
  }

  .wa-picker {
    align-items: flex-start;
  }

  .wa-btn {
    width: 100%;
  }

  .wa-flag {
    white-space: normal;
  }
}
</style>
