/**
 * 演示用的本地账号表：只为了跑通「注册设密码 → 退出 → 密码登录」这条链路。
 * 真接后端时整份替换成接口调用，组件不用改。
 *
 * 安全说明（重要）：
 * - 密码不落明文，只存 SHA-256 摘要；没有后端就没有真实的盐与限流，这是演示级方案。
 * - 数据只在本机 localStorage，手机号仅作 key，不上传任何地方。
 */

export type AccountResult = { ok: true; name: string } | { ok: false; reason: string }

interface AccountRecord {
  name: string
  hash: string
  at: number
}

const STORAGE_KEY = 'paishe.accounts.v1'

function read(): Record<string, AccountRecord> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw) as Record<string, AccountRecord>
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {}
  }
}

function write(next: Record<string, AccountRecord>) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  } catch {
    /* 隐私模式下写不进去，不影响本次会话 */
  }
}

/** crypto.subtle 只在安全上下文（https / localhost）可用，取不到时退化成非加密摘要 */
async function hashPassword(phone: string, password: string): Promise<string> {
  const data = `${phone}::${password}::paishe`
  if (globalThis.crypto?.subtle) {
    const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(data))
    return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('')
  }
  let h1 = 0x811c9dc5
  let h2 = 0x01000193
  for (let i = 0; i < data.length; i += 1) {
    h1 = Math.imul(h1 ^ data.charCodeAt(i), 0x01000193) >>> 0
    h2 = Math.imul(h2 + data.charCodeAt(i), 0x85ebca6b) >>> 0
  }
  return `demo-${h1.toString(16)}${h2.toString(16)}`
}

export function hasAccount(phone: string): boolean {
  return Boolean(read()[phone])
}

export function accountName(phone: string): string {
  return read()[phone]?.name ?? ''
}

export async function registerAccount(phone: string, name: string, password: string): Promise<AccountResult> {
  const cleanPhone = phone.trim()
  const cleanName = name.trim()
  if (!/^1\d{10}$/.test(cleanPhone)) return { ok: false, reason: '手机号要 11 位、以 1 开头。' }
  if (!cleanName) return { ok: false, reason: '先留个称呼吧。' }
  if (password.length < 6 || password.length > 20) return { ok: false, reason: '密码需要 6–20 位。' }

  const all = read()
  if (all[cleanPhone]) return { ok: false, reason: '这个手机号已经注册过，直接登录就行。' }

  all[cleanPhone] = { name: cleanName, hash: await hashPassword(cleanPhone, password), at: Date.now() }
  write(all)
  return { ok: true, name: cleanName }
}

export async function verifyAccount(phone: string, password: string): Promise<AccountResult> {
  const cleanPhone = phone.trim()
  if (!/^1\d{10}$/.test(cleanPhone)) return { ok: false, reason: '手机号要 11 位、以 1 开头。' }
  const record = read()[cleanPhone]
  if (!record) return { ok: false, reason: '这个手机号还没注册过，先用验证码登录，或去注册。' }
  if (password.length < 6) return { ok: false, reason: '密码至少 6 位。' }
  const hash = await hashPassword(cleanPhone, password)
  if (hash !== record.hash) return { ok: false, reason: '密码不对，再试一次。' }
  return { ok: true, name: record.name }
}
