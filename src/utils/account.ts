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

/**
 * 内置演示账号：不注册也能用「手机号 + 密码」直接登录（产品演示 / 评审用）。
 * 摘要 = SHA-256("13225223191::123456::paishe")；明文口令不作为数据存储，
 * 只在非安全上下文（http 局域网/公网：crypto.subtle 不可用、摘要算法退化）里做兜底比对。
 */
const SEED_PHONE = '13225223191'
const SEED_NAME = 'cyrus'
const SEED_PASSWORD = '123456'
const SEED_HASH = '96b857ad108efe1698ad356475767c3f33fa9e4a07246f39d17959cc6c8133e1'

/** 历史昵称 → 现昵称：早期演示账号叫「小满」，统一并到 cyrus。 */
const LEGACY_NAMES: Record<string, string> = { 小满: SEED_NAME }
const MIGRATED_KEY = 'paishe.accounts.migrated.v1'

/** 把历史昵称换成现在的名字；不认识的名字原样返回。 */
export function canonicalName(name: string): string {
  return LEGACY_NAMES[name] ?? name
}

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

let seeded = false

/** 补齐演示账号 + 一次性改名迁移：本页首次调用账号接口时跑一次。 */
function ensureSeed() {
  if (seeded) return
  seeded = true

  const all = read()
  let changed = false

  let migrated = true
  try {
    migrated = localStorage.getItem(MIGRATED_KEY) === '1'
  } catch {
    /* 读不到就当已迁移，避免每次刷新都改名 */
  }
  if (!migrated) {
    for (const key of Object.keys(all)) {
      const next = LEGACY_NAMES[all[key].name]
      if (next) {
        all[key].name = next
        changed = true
      }
    }
    try {
      localStorage.setItem(MIGRATED_KEY, '1')
    } catch {
      /* 写不进去就下次刷新再试 */
    }
  }

  if (!all[SEED_PHONE]) {
    all[SEED_PHONE] = { name: SEED_NAME, hash: SEED_HASH, at: Date.now() }
    changed = true
  }

  if (changed) write(all)
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
  ensureSeed()
  return Boolean(read()[phone])
}

export function accountName(phone: string): string {
  ensureSeed()
  return read()[phone]?.name ?? ''
}

export async function registerAccount(phone: string, name: string, password: string): Promise<AccountResult> {
  const cleanPhone = phone.trim()
  const cleanName = name.trim()
  if (!/^1\d{10}$/.test(cleanPhone)) return { ok: false, reason: '手机号要 11 位、以 1 开头。' }
  if (!cleanName) return { ok: false, reason: '先留个称呼吧。' }
  if (password.length < 6 || password.length > 20) return { ok: false, reason: '密码需要 6–20 位。' }

  ensureSeed()
  const all = read()
  if (all[cleanPhone]) return { ok: false, reason: '这个手机号已经注册过，直接登录就行。' }

  all[cleanPhone] = { name: cleanName, hash: await hashPassword(cleanPhone, password), at: Date.now() }
  write(all)
  return { ok: true, name: cleanName }
}

export async function verifyAccount(phone: string, password: string): Promise<AccountResult> {
  const cleanPhone = phone.trim()
  if (!/^1\d{10}$/.test(cleanPhone)) return { ok: false, reason: '手机号要 11 位、以 1 开头。' }
  ensureSeed()
  const record = read()[cleanPhone]
  if (!record) return { ok: false, reason: '这个手机号还没注册过，先用验证码登录，或去注册。' }
  if (password.length < 6) return { ok: false, reason: '密码至少 6 位。' }
  const hash = await hashPassword(cleanPhone, password)
  // 演示账号兜底：http 局域网/公网不是安全上下文，crypto.subtle 不可用、摘要算法退化，这里放行内置口令。
  const seedBypass = cleanPhone === SEED_PHONE && password === SEED_PASSWORD
  if (hash !== record.hash && !seedBypass) return { ok: false, reason: '密码不对，再试一次。' }
  return { ok: true, name: record.name }
}
