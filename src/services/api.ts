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

export async function getWorks(query: DiscoverQuery) {
  try {
    const result = await request<{ items?: typeof works; works?: typeof works; aiUsed?: boolean; degraded?: boolean }>('/ai/work-search', { method: 'POST', body: JSON.stringify(query) })
    const data = result.items || result.works || []
    if (data.length) return { data, aiUsed: result.aiUsed ?? true, degraded: result.degraded ?? false }
  } catch {
    // The local demo intentionally falls back to the same shape when Spring Boot is not running.
  }
  await pause(380)
  const fallback = searchWorks(query)
  return { data: fallback.length ? fallback : works.filter((item) => !query.location || item.city === '西安').slice(0, 4), aiUsed: true, degraded: true }
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
  source?: string
}

export interface AiClassifyResult {
  style?: AiTag[]
  tone?: AiTag[]
  subject?: AiTag[]
  fallback?: string
  latencyMs?: number
  modelVersion?: Record<string, string>
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
}

export interface AgentToolStep {
  tool: string
  args: Record<string, unknown>
  result: unknown
}

export interface AgentResult {
  ok: boolean
  mode: string
  slots: { city: string; budget: number; when: string; styles: string[]; raw: string }
  query: string
  candidates: AgentCandidate[]
  reply: string
  summary: string
  warnings: string[]
  toolTrace: AgentToolStep[]
  latencyMs: number
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
}

export async function writeCopy(input: { title?: string; styles?: string[]; tones?: string[] }): Promise<CopyResult> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), AGENT_TIMEOUT)
  try {
    const response = await fetch(`${apiBase}/ai/copywrite`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: input.title ?? '', styles: input.styles ?? [], tones: input.tones ?? [] }),
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
