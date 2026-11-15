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
