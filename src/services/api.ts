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
