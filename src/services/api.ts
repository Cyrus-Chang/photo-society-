import { orders, photographers, posts, searchWorks, works } from '../data/mock'
import type { DiscoverQuery } from '../types'

const pause = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))
const apiBase = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) }
  })
  if (!response.ok) throw new Error(`API ${response.status}`)
  const payload = await response.json()
  return (payload?.data ?? payload) as T
}

/* ===== 约拍页作品检索（2026-11-16 修断点）=====
   原来这里调 `/ai/work-search`：8100 上没有这条路由，请求固定 404 → catch 后回落本地 mock，
   界面上看着像「AI 筛选」，其实全是假数据（等于伪造 AI 结果，违反 C2）。
   现在改调真实检索：POST /api/v1/ai/search  body { text, k, weights?, tags?, city }
   · text  —— 用 DiscoverQuery + 预算/类型/风格拼一句中文描述（后端负责翻译成英文提示词）
   · k     —— 12（约拍页一次展示的候选量）
   · city  —— 从「西安 · 小寨」这种 location 里取城市段
   · tags  —— 检索标签：词表直接取本地作品的 styles/types，不另造一份词表
   返回体 hits[].id 就是本地 mock 作品的 id，用它回填卡片字段；
   matchReason 取 explanation 里最可读的一句（结构化拼句），没有就用向量相似度百分比。
   请求失败 / 超时 / 200 但一命中都没有 → 保留本地关键词回退，并把 degraded + note 透传给页面。 */
export interface WorksQuerySignals {
  /** 强制指定城市；默认从 query.location 的「城市 · 地点」里取 */
  city?: string
  /** 拍摄类型（人像 / 风景 …），只拼进检索文本 */
  type?: string
  /** 风格词，既拼进文本也作为检索标签 */
  styles?: string[]
  /** 预算区间，只拼进检索文本（后端目前不做价格过滤，别当成硬筛） */
  budgetMin?: number | string
  budgetMax?: number | string
}

export interface WorksResult {
  data: typeof works
  /** 结果是否来自 AI 检索服务（true）还是本地兜底（false） */
  aiUsed: boolean
  /** true = 走的是本地关键词回退，页面必须如实标注，不能写「AI 筛选」 */
  degraded: boolean
  mode: 'vector' | 'mock'
  /** 一句人话的来源说明，直接给页面展示 */
  note: string
  indexed?: number
}

/** 检索标签词表：取本地作品自己的 styles/types，避免和作者实际填的词漂移 */
const WORK_TAGS = Array.from(new Set(works.flatMap((item) => [...item.styles, ...(item.types || [])]))).filter(Boolean)

function budgetText(min?: number | string, max?: number | string) {
  const usable = (value: string) => value !== '' && value !== '0' && value !== '不限'
  const low = String(min ?? '').trim()
  const high = String(max ?? '').trim()
  const lowOk = usable(low)
  const highOk = usable(high)
  if (lowOk && highOk) return `预算 ${low}-${high}`
  if (highOk) return `预算 ${high}`
  if (lowOk) return `预算 ${low} 起`
  return ''
}

/** DiscoverQuery（+ 预算/类型/风格） → 一句中文检索描述 */
export function buildWorksSearchText(query: DiscoverQuery, signals?: WorksQuerySignals) {
  const parts = [
    query.location,
    query.scene,
    query.shootAt,
    signals?.type || '',
    ...(signals?.styles || []),
    budgetText(signals?.budgetMin, signals?.budgetMax)
  ]
  const seen = new Set<string>()
  const tokens: string[] = []
  for (const part of parts) {
    const value = String(part || '').replace(/\s+/g, ' ').trim()
    if (!value || seen.has(value)) continue
    seen.add(value)
    tokens.push(value)
  }
  return tokens.join(' ')
}

function worksSearchTags(text: string, extra?: string[]) {
  const haystack = text.toLowerCase()
  const tags = WORK_TAGS.filter((tag) => haystack.includes(tag.toLowerCase()))
  for (const tag of extra || []) {
    const value = String(tag || '').trim()
    if (value && !tags.includes(value)) tags.push(value)
  }
  return tags.slice(0, 8)
}

function cityOfLocation(location: string) {
  return String(location || '').split('·')[0].trim()
}

export interface AiSearchHit {
  id: string
  score?: number
  vectorSimilarity?: number
  vectorScore?: number
  tagScore?: number
  colorScore?: number
  tagOverlap?: string[]
  tags?: string[]
  colorEvidence?: string[]
  /** 8100 返回的是结构化对象（sources/matchedTags/colorFeatures），不是一句话 */
  explanation?: {
    sources?: string[]
    matchedTags?: string[]
    colorFeatures?: string[]
    queryContext?: Record<string, unknown>
  } | string
}

export interface AiSearchResponse {
  ok?: boolean
  count?: number
  indexed?: number
  weights?: Record<string, number>
  query?: Record<string, unknown>
  hits?: AiSearchHit[]
  error?: string
}

function hitPercent(hit: AiSearchHit) {
  const value = typeof hit.vectorSimilarity === 'number'
    ? hit.vectorSimilarity
    : typeof hit.score === 'number' ? hit.score : undefined
  if (typeof value !== 'number' || !Number.isFinite(value)) return ''
  return `${Math.round(value * 100)}%`
}

/** explanation 拼成一句能读的话；实在没有可说的就退回向量相似度 */
export function hitMatchReason(hit: AiSearchHit) {
  const explanation = hit.explanation
  if (explanation && typeof explanation === 'object') {
    const tags = (explanation.matchedTags || []).filter(Boolean)
    const colors = (explanation.colorFeatures || []).filter(Boolean)
    if (tags.length && colors.length) return `命中标签：${tags.join('、')} · 色彩接近：${colors.join('、')}`
    if (tags.length) return `命中标签：${tags.join('、')}`
    if (colors.length) return `色彩接近：${colors.join('、')}`
  }
  const percent = hitPercent(hit)
  if (!percent) return ''
  // 只对真的 vectorSimilarity 写「向量相似度」；拿 blend 后的 score 充当就是编数字
  return typeof hit.vectorSimilarity === 'number' ? `向量相似度 ${percent}` : `综合匹配度 ${percent}`
}

/** hits[].id → 本地作品；本地没有对应图/作品的条目直接跳过，不编一张卡片出来 */
function joinSearchHits(hits: AiSearchHit[]) {
  const byId = new Map(works.map((item) => [item.id, item]))
  const seen = new Set<string>()
  const data: typeof works = []
  for (const hit of hits) {
    const id = typeof hit?.id === 'string' ? hit.id : ''
    if (!id || seen.has(id)) continue
    const work = byId.get(id)
    if (!work) continue
    seen.add(id)
    const score = typeof hit.score === 'number'
      ? hit.score
      : typeof hit.vectorScore === 'number'
        ? hit.vectorScore
        : typeof hit.vectorSimilarity === 'number'
          ? hit.vectorSimilarity
          : undefined
    data.push({ ...work, matchReason: hitMatchReason(hit) || work.matchReason, score })
  }
  return data
}

const SEARCH_TIMEOUT = 15000

export async function getWorks(query: DiscoverQuery, signals?: WorksQuerySignals): Promise<WorksResult> {
  const text = buildWorksSearchText(query, signals)
  const city = String(signals?.city || cityOfLocation(query.location) || '').trim()
  const tags = worksSearchTags(text, signals?.styles)
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), SEARCH_TIMEOUT)
  let note = ''
  try {
    const response = await fetch(`${apiBase}/ai/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, k: 12, city, tags }),
      signal: controller.signal
    })
    if (!response.ok) throw new Error(`检索服务返回 ${response.status}`)
    const payload = await response.json()
    const result = (payload?.data ?? payload) as AiSearchResponse
    if (result?.ok === false && result.error) throw new Error(result.error)
    const data = joinSearchHits(Array.isArray(result?.hits) ? result.hits : [])
    if (data.length) {
      return {
        data,
        aiUsed: true,
        degraded: false,
        mode: 'vector',
        note: `向量检索 · 命中 ${result.count ?? data.length} 张 / 索引 ${result.indexed ?? '—'} 张`,
        indexed: typeof result.indexed === 'number' ? result.indexed : undefined
      }
    }
    // 200 但一命中都没有：不假装成功，落到本地回退并说明原因
    note = '检索服务没有返回可用的作品，已用本地关键词兜底'
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') note = '检索超时，已用本地关键词兜底'
    else if (error instanceof TypeError) note = '连不上检索服务（确认 8100 已启动、dev 代理生效），已用本地关键词兜底'
    else note = `${error instanceof Error ? error.message : '检索失败'}，已用本地关键词兜底`
  } finally {
    window.clearTimeout(timer)
  }
  await pause(380)
  const fallback = searchWorks(query)
  const data = fallback.length ? fallback : works.filter((item) => !query.location || item.city === '西安').slice(0, 4)
  return { data, aiUsed: false, degraded: true, mode: 'mock', note }
}

export async function getWork(id: string) {
  try { return await request<typeof works[number]>(`/works/${id}`) } catch { await pause(120); return works.find((item) => item.id === id) ?? works[0] }
}

export async function getPhotographer(id: string) {
  try { return await request<typeof photographers[number]>(`/photographers/${id}`) } catch { await pause(120); return photographers.find((item) => item.id === id) ?? photographers[0] }
}

export async function getMarketPosts() {
  try { const result = await request<{ items?: typeof posts; posts?: typeof posts }>('/posts?cursor=&pageSize=50'); return result.items || result.posts || posts } catch { await pause(220); return posts }
}

export async function getOrders() {
  try { const result = await request<{ items?: typeof orders; bookings?: typeof orders }>('/bookings?cursor=&pageSize=50'); return result.items || result.bookings || orders } catch { await pause(180); return orders }
}

export async function createBooking(payload: { workId: string; date: string; time: string }) {
  try { return await request<{ id: string; status: string }>('/bookings', { method: 'POST', headers: { 'Idempotency-Key': `demo-${payload.workId}-${payload.date}` }, body: JSON.stringify(payload) }) } catch { await pause(480); return { id: 'order-new', ...payload, status: 'pending' } }
}

/* ===== AI 图片识别（2026-11-15 接入真实模型服务）=====
   走 `/api/v1/ai/classify`：开发期由 vite proxy 转给 127.0.0.1:8100 的 FastAPI 薄 BFF。
   不能复用上面的 request()，因为它固定 Content-Type: application/json，而这里是 multipart。
   失败不静默回退假标签——识别没成就要如实告诉用户，否则等于伪造 AI 结果（C2）。 */
export interface AiTag {
  code: string
  confidence?: number
  aboveThreshold?: boolean
  confidenceSource?: string
  needsReview?: boolean
  source?: string
}

export interface AiConfidenceCalibration {
  method?: string
  binCenters?: number[]
  binAccuracies?: number[]
  looAccuracy?: number
  reviewThreshold?: number
  gateConfidence?: number
  maxPortraitProbability?: number
}

export interface AiClassifyResult {
  style?: AiTag[]
  tone?: AiTag[]
  subject?: AiTag[]
  subjectRaw?: AiTag[]
  subjectVisible?: AiTag[]
  fallback?: string
  latencyMs?: number
  modelVersion?: Record<string, string>
  /** 来源说明：锚图风格的置信度来自留一法间隔分档实测正确率。 */
  confidenceSource?: string | Record<string, string>
  /** 低于服务端业务阈值时为 true，前端应提示人工确认。 */
  needsReview?: boolean
  confidenceThreshold?: number
  confidenceCalibration?: {
    style?: AiConfidenceCalibration
    subject?: AiConfidenceCalibration
  }
  reviewReasons?: string[]
  subjectGate?: {
    passed?: boolean
    reason?: string
    needsReview?: boolean
    personProbability?: number | null
    nonPersonProbability?: number | null
  }
}

/** 冷启动（torch + CLIP）约 45s，留 30s 让用户先看到超时提示而不是无限转圈 */
const CLASSIFY_TIMEOUT = 30000

export async function classifyImage(file: File): Promise<AiClassifyResult> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), CLASSIFY_TIMEOUT)
  const form = new FormData()
  form.append('file', file)
  try {
    const response = await fetch(`${apiBase}/ai/classify`, { method: 'POST', body: form, signal: controller.signal })
    if (!response.ok) throw new Error(`识别服务返回 ${response.status}`)
    const payload = await response.json()
    return (payload?.data ?? payload) as AiClassifyResult
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('识别超时（模型可能正在冷启动，首次约 45 秒）')
    }
    if (error instanceof TypeError) {
      throw new Error('连不上识别服务：确认 8100 已启动，且 dev 代理生效')
    }
    throw error instanceof Error ? error : new Error('识别失败')
  } finally {
    window.clearTimeout(timer)
  }
}

/* ===== 撮合 Agent（2026-11-15）=====
   一句话需求 → 后端真调工具（向量检索 / 查档期）→ 候选摄影师 + 理由。
   返回体带 toolTrace，前端可以原样展示「它到底调了什么」，不做黑箱。 */
export interface AgentWorkHit {
  id: string
  title: string
  imageUrl: string
  city: string
  styles: string[]
  shootDate: string
  score: number
  reason: string
}

export interface AgentCandidate {
  photographerId: string
  name: string
  city: string
  tags: string[]
  nextSlot: string
  responseTime: string
  verified: boolean
  crossCity: boolean
  score: number
  works: AgentWorkHit[]
  /** 与需求标签直接重合的标签；后端未返回时由 tags 兜底展示。 */
  matchedTags?: string[]
  tagOverlap?: number
  /** 向量检索原始分数，允许缺省以避免伪造分数。 */
  vectorScore?: number
  /** check_slot 的可约结果；nextSlot 保留兼容旧返回。 */
  availability?: string | string[]
  available?: boolean
}

export interface AgentToolStep {
  tool: string
  args: Record<string, unknown>
  result: unknown
}

export interface AgentResult {
  ok: boolean
  mode: string
  slots: {
    city?: string
    budget?: number | string
    budgetRange?: { min?: number; max?: number; label?: string; source?: string }
    when?: string
    styles?: string[]
    people?: number | string
    theme?: string
    raw: string
  }
  query: string
  candidates: AgentCandidate[]
  reply: string
  summary: string
  warnings: string[]
  toolTrace: AgentToolStep[]
  latencyMs: number
  planner?: 'llm' | 'rule' | string
  plannerLatencyMs?: number
  plannerSuccess?: boolean
  plannerError?: string
  plannerStats?: { mode?: string; latencyMs?: number; success?: boolean }
  missingFields?: string[]
  openingLine?: string
  communicationPoints?: string[]
  priceReference?: {
    low?: number
    high?: number
    currency?: string
    source?: string
    note?: string
  }
}

const AGENT_TIMEOUT = 30000
export async function matchPhotographers(text: string, topN = 3): Promise<AgentResult> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), AGENT_TIMEOUT)
  try {
    const response = await fetch(`${apiBase}/ai/agent/match`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, topN }),
      signal: controller.signal
    })
    if (!response.ok) throw new Error(`撮合服务返回 ${response.status}`)
    const payload = await response.json()
    return (payload?.data ?? payload) as AgentResult
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw new Error('撮合超时，稍后再试')
    if (error instanceof TypeError) throw new Error('连不上撮合服务：确认 8100 已启动，且 dev 代理生效')
    throw error instanceof Error ? error : new Error('撮合失败')
  } finally {
    window.clearTimeout(timer)
  }
}

/* ===== 作品文案生成（2026-11-15）=====
   把分类器输出的结构化标签喂给 LLM，产出 3 个标题备选 + 一句话简介。
   没配 LLM key 时后端返回 mode='rule' 的模板兜底，界面必须标明来源（不伪装成模型）。 */
export interface CopyResult {
  mode: 'llm' | 'rule'
  titles: string[]
  intro: string
  tags: string[]
  note: string
  promptVersion?: string
  model?: string
  latencyMs?: number
  usage?: {
    promptTokens?: number
    completionTokens?: number
    totalTokens?: number
    prompt_tokens?: number
    completion_tokens?: number
    total_tokens?: number
  }
  tokenUsage?: number
  degraded?: boolean
  attempts?: number
  errorCode?: string
}

export type CopyInput = { title?: string; styles?: string[]; tones?: string[] }

function copyPayload(input: CopyInput) {
  return { title: input.title ?? '', styles: input.styles ?? [], tones: input.tones ?? [] }
}

export async function writeCopy(input: CopyInput): Promise<CopyResult> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), AGENT_TIMEOUT)
  try {
    const response = await fetch(`${apiBase}/ai/copywrite`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(copyPayload(input)),
      signal: controller.signal
    })
    if (!response.ok) throw new Error(`文案服务返回 ${response.status}`)
    const payload = await response.json()
    return (payload?.data ?? payload) as CopyResult
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw new Error('文案生成超时')
    if (error instanceof TypeError) throw new Error('连不上文案服务：确认 8100 已启动，且 dev 代理生效')
    throw error instanceof Error ? error : new Error('文案生成失败')
  } finally {
    window.clearTimeout(timer)
  }
}

/**
 * Consume the copywriter SSE endpoint. The server emits small text deltas while
 * it is generating and a final `done` payload containing the validated result.
 * Keeping the parser here means the upload dialog can render immediately while
 * still using the same CopyResult contract as the non-streaming endpoint.
 */
export async function writeCopyStream(input: CopyInput, onDelta?: (text: string) => void, onReset?: () => void): Promise<CopyResult> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), AGENT_TIMEOUT)
  let response: Response
  try {
    response = await fetch(`${apiBase}/ai/copywrite/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      body: JSON.stringify(copyPayload(input)),
      signal: controller.signal
    })
    if (!response.ok) throw new Error(`文案服务返回 ${response.status}`)
    if (!response.body) throw new Error('文案流式响应为空')

    const contentType = response.headers.get('content-type') || ''
    if (!contentType.includes('text/event-stream')) {
      const payload = await response.json()
      return (payload?.data ?? payload) as CopyResult
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let finalResult: CopyResult | null = null
    const consumeEvent = (rawEvent: string) => {
      const lines = rawEvent.split(/\r?\n/)
      let eventName = ''
      const dataLines: string[] = []
      for (const line of lines) {
        if (line.startsWith('event:')) eventName = line.slice(6).trim()
        else if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart())
      }
      if (!dataLines.length) return
      const raw = dataLines.join('\n')
      if (raw === '[DONE]') return
      let payload: any = raw
      try { payload = JSON.parse(raw) } catch { /* plain text delta */ }

      const result = payload?.result ?? payload?.data
      if (result && typeof result === 'object' && Array.isArray(result.titles)) {
        finalResult = result as CopyResult
      } else if (payload && typeof payload === 'object' && Array.isArray(payload.titles)) {
        finalResult = payload as CopyResult
      }

      if (eventName === 'reset') onReset?.()

      const delta = typeof payload === 'string'
        ? payload
        : payload?.delta ?? payload?.text ?? payload?.content ?? payload?.token ?? payload?.choices?.[0]?.delta?.content
      if (typeof delta === 'string' && delta && eventName !== 'done') onDelta?.(delta)
    }

    while (true) {
      const { value, done } = await reader.read()
      buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done })
      let separator = buffer.search(/\r?\n\r?\n/)
      while (separator >= 0) {
        const event = buffer.slice(0, separator)
        const separatorLength = buffer.slice(separator).startsWith('\r\n\r\n') ? 4 : 2
        buffer = buffer.slice(separator + separatorLength)
        consumeEvent(event)
        separator = buffer.search(/\r?\n\r?\n/)
      }
      if (done) break
    }
    if (buffer.trim()) consumeEvent(buffer)
    if (!finalResult) throw new Error('文案流式响应未返回最终结果')
    return finalResult
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw new Error('文案生成超时')
    if (error instanceof TypeError) throw new Error('连不上文案服务：确认 8100 已启动，且 dev 代理生效')
    throw error instanceof Error ? error : new Error('文案生成失败')
  } finally {
    window.clearTimeout(timer)
  }
}

/* =========================================================================
   以图搜图：样片 → 口味最接近的摄影师（2026-11-16，任务 2）
   后端契约（服务尚未实现，先按契约写，404/超时必须优雅降级）：
     POST /api/v1/ai/similar   multipart 字段 file，query topK（默认 3）
     → { ok, styleMatch:{code,name,confidence},
         matches:[{ photographerId, name, city, matchPercent, styleOverlap,
                    tags, sameCity, works:[{id,title,imageUrl,score}] }],
         warnings, latencyMs }
   这里刻意**不 throw**：「样片检索服务未就绪」是一等公民分支。
   组件拿到 available:false 后改调 classify 拿风格标签 + 本地作品标签近似匹配，
   并在界面上明确标注，绝不假装是全站向量比对。
   ========================================================================= */
export interface SimilarWork {
  id: string
  title: string
  imageUrl: string
  score?: number
}

export interface SimilarStyleMatch {
  code?: string
  name?: string
  confidence?: number
}

export interface SimilarMatch {
  photographerId: string
  name: string
  city?: string
  /** 与样片的重合度百分比（0—100）。只有真接口会给；降级路径由标签重合度算出并另行标注。 */
  matchPercent?: number
  styleOverlap?: string[] | number
  tags?: string[]
  sameCity?: boolean
  works?: SimilarWork[]
}

export interface SimilarResponse {
  ok?: boolean
  styleMatch?: SimilarStyleMatch
  matches?: SimilarMatch[]
  warnings?: string[]
  latencyMs?: number
}

export interface SimilarUnavailableReason {
  /** HTTP 状态码；网络层失败给 'network'，超时给 'timeout' */
  status: number | 'timeout' | 'network'
  message: string
}

export type SimilarOutcome =
  | { available: true; data: SimilarResponse }
  | { available: false; reason: SimilarUnavailableReason }

const SIMILAR_TIMEOUT = 30000

export async function findSimilarPhotographers(file: File, topK = 3): Promise<SimilarOutcome> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), SIMILAR_TIMEOUT)
  const form = new FormData()
  form.append('file', file)
  try {
    const response = await fetch(`${apiBase}/ai/similar?topK=${encodeURIComponent(String(topK))}`, {
      method: 'POST',
      body: form,
      signal: controller.signal
    })
    if (!response.ok) {
      return { available: false, reason: { status: response.status, message: `样片检索服务返回 ${response.status}` } }
    }
    const payload = await response.json()
    const data = (payload?.data ?? payload) as SimilarResponse
    if (!data || data.ok === false || !Array.isArray(data.matches)) {
      return { available: false, reason: { status: 200, message: '样片检索服务返回体不是约定结构' } }
    }
    return { available: true, data }
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      return { available: false, reason: { status: 'timeout', message: '样片检索超时' } }
    }
    if (error instanceof TypeError) {
      return { available: false, reason: { status: 'network', message: '连不上样片检索服务' } }
    }
    return { available: false, reason: { status: 'network', message: error instanceof Error ? error.message : '样片检索失败' } }
  } finally {
    window.clearTimeout(timer)
  }
}

/**
 * 降级路径专用：按风格标签在**本地作品**上做近似匹配。
 * 这不是向量比对——重合度 = 样片标签里能在该作者作品上找到对应标签的比例。
 * 界面必须照实标注，不能写成「全站向量比对」。
 */
export function matchPhotographersByTags(labels: string[], topK = 3, city?: string): SimilarMatch[] {
  const wanted = Array.from(new Set(labels.map((label) => String(label || '').trim()).filter(Boolean)))
  if (!wanted.length) return []
  const byId = new Map(photographers.map((item) => [item.id, item]))
  const buckets = new Map<string, {
    hits: Set<string>
    works: Array<{ work: (typeof works)[number]; score: number }>
  }>()
  for (const work of works) {
    const own = [...work.styles, ...(work.types || [])]
    const hits: string[] = []
    let score = 0
    for (const label of wanted) {
      let exact = false
      let partial = false
      for (const tag of own) {
        if (tag === label) { exact = true; break }
        if (tag.includes(label) || label.includes(tag)) partial = true
      }
      if (exact) { hits.push(label); score += 2 }
      else if (partial) { hits.push(label); score += 1 }
    }
    if (!hits.length) continue
    const bucket = buckets.get(work.photographerId) || { hits: new Set<string>(), works: [] }
    hits.forEach((hit) => bucket.hits.add(hit))
    bucket.works.push({ work, score })
    buckets.set(work.photographerId, bucket)
  }
  return Array.from(buckets.entries())
    .map(([photographerId, bucket]) => {
      const person = byId.get(photographerId)
      const matched = Array.from(bucket.hits)
      // 重合度口径：命中标签数 ÷ 样片标签数。这是标签覆盖率，不是「像不像」的概率。
      const matchPercent = Math.round((matched.length / wanted.length) * 100)
      const topWorks = bucket.works
        .slice()
        .sort((a, b) => b.score - a.score)
        .slice(0, 2)
        .map(({ work }) => ({ id: work.id, title: work.title, imageUrl: work.imageUrl }))
      return {
        photographerId,
        name: person?.name || bucket.works[0].work.photographerName,
        city: person?.city || bucket.works[0].work.city,
        matchPercent,
        styleOverlap: matched,
        tags: matched,
        sameCity: Boolean(city && person?.city === city),
        works: topWorks
      } satisfies SimilarMatch
    })
    .sort((a, b) => {
      const diff = (b.matchPercent ?? 0) - (a.matchPercent ?? 0)
      if (diff !== 0) return diff
      return (b.works?.length ?? 0) - (a.works?.length ?? 0)
    })
    .slice(0, topK)
}

/* =========================================================================
   摄影师场景覆盖（2026-11-16，任务 3）
   GET /api/v1/ai/photographer/:id/scene-share → 200 就用服务端统计；
   否则组件回落到 computeSceneShare() 的本地词频，并把统计口径写在界面上。
   服务端结构尚未定稿，所以这里只做宽松类型 + 交给组件校验，不编字段。
   ========================================================================= */
export interface SceneShareEntry {
  name: string
  count: number
  /** 0—1 的占比；服务端若给百分比字段，组件侧统一归一 */
  ratio?: number
}

export interface SceneShareResponse {
  photographerId?: string
  total?: number
  totalWorks?: number
  scenes?: SceneShareEntry[]
  topScenes?: SceneShareEntry[]
  note?: string
  source?: string
  computedAt?: string
}

export type SceneShareOutcome =
  | { available: true; data: SceneShareResponse }
  | { available: false; status: number | 'network'; message: string }

const SCENE_SHARE_TIMEOUT = 8000

export async function getPhotographerSceneShare(photographerId: string): Promise<SceneShareOutcome> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), SCENE_SHARE_TIMEOUT)
  try {
    const response = await fetch(`${apiBase}/ai/photographer/${encodeURIComponent(photographerId)}/scene-share`, {
      method: 'GET',
      signal: controller.signal
    })
    if (!response.ok) {
      return { available: false, status: response.status, message: `场景统计接口返回 ${response.status}` }
    }
    const payload = await response.json()
    const data = (payload?.data ?? payload) as SceneShareResponse
    if (!data || typeof data !== 'object') {
      return { available: false, status: 200, message: '场景统计接口返回体不是约定结构' }
    }
    return { available: true, data }
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      return { available: false, status: 'network', message: '场景统计超时' }
    }
    return { available: false, status: 'network', message: error instanceof Error ? error.message : '场景统计失败' }
  } finally {
    window.clearTimeout(timer)
  }
}

/**
 * 本地回退：按作者的本地作品逐张统计 styles 词频。
 * 口径（界面要照抄）：按该作者 N 张作品的 styles 标签逐张计数，
 * 占比 = 命中张数 ÷ 作品总数；同一张作品可带多个标签，所以各项占比之和可能超过 100%。
 */
export function computeSceneShare(photographerId: string, topN = 3): { total: number; scenes: SceneShareEntry[] } {
  const person = photographers.find((item) => item.id === photographerId)
  const owned: typeof works = []
  if (person) {
    for (const id of person.works) {
      const work = works.find((item) => item.id === id)
      if (work) owned.push(work)
    }
  } else {
    owned.push(...works.filter((item) => item.photographerId === photographerId))
  }
  if (!owned.length) return { total: 0, scenes: [] }
  const counts = new Map<string, number>()
  for (const work of owned) {
    for (const style of new Set(work.styles)) counts.set(style, (counts.get(style) || 0) + 1)
  }
  const scenes = Array.from(counts.entries())
    .map(([name, count]) => ({ name, count, ratio: count / owned.length }))
    .sort((a, b) => (b.count - a.count) || a.name.localeCompare(b.name))
    .slice(0, topN)
  return { total: owned.length, scenes }
}

/* =========================================================================
   AI 约拍对话框（2026-11-16，第七轮 P0）
   POST /api/v1/ai/chat/reply
     body { message, persona?, context?, history? }
     → { reply, mode: 'model' | 'fallback', persona, intent, promptVersion, modelReady, modelError, latencyMs }
   用户口径：这是「AI 助手帮你起个头」，用摄影师的口吻，但界面上要标明是 AI，
   不冒充真人。mode='fallback' 说明后端还没有本地学生模型，走的是人设模板，界面同样要照实说。
   ========================================================================= */
export interface ChatContext {
  name?: string
  city?: string
  price?: string
  nextSlot?: string
  count?: string
  scene?: string
}

export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatReply {
  reply: string
  mode: 'model' | 'fallback' | string
  persona: string
  intent?: string
  promptVersion?: string
  modelReady?: boolean
  modelError?: string
  latencyMs?: number
}

const CHAT_TIMEOUT = 30000

export async function replyChat(input: {
  message: string
  persona?: string
  /** chat=约拍页对话；draft=接拍页让 AI 起草一句回复 */
  mode?: 'chat' | 'draft'
  context?: ChatContext
  history?: ChatTurn[]
}): Promise<ChatReply> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), CHAT_TIMEOUT)
  try {
    const response = await fetch(`${apiBase}/ai/chat/reply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: input.message,
        persona: input.persona || 'zhaoye',
        mode: input.mode || 'chat',
        context: input.context || {},
        history: (input.history || []).slice(-8)
      }),
      signal: controller.signal
    })
    if (!response.ok) throw new Error(`对话服务返回 ${response.status}`)
    const payload = await response.json()
    const data = (payload?.data ?? payload) as ChatReply
    if (!data || typeof data.reply !== 'string' || !data.reply.trim()) throw new Error('对话服务没有返回内容')
    return data
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw new Error('AI 回复超时（模型可能正在冷启动）')
    if (error instanceof TypeError) throw new Error('连不上对话服务：确认 8100 已启动且 dev 代理生效')
    throw error instanceof Error ? error : new Error('AI 回复失败')
  } finally {
    window.clearTimeout(timer)
  }
}
