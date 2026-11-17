import { computed, reactive } from 'vue'
import { canonicalName } from './account'

/**
 * 极简会话层：只为演示「未登录 → 登录 → 选身份 → 进入产品」这条链路。
 * 真实接入后端时，把 login / register 换成接口调用即可，组件不用改。
 */

export type RoleKey = 'visitor' | 'enthusiast' | 'photographer' | 'creator' | 'partner'

export interface Identity {
  key: RoleKey
  label: string
  hint: string
  entry: string
}

export const identities: Identity[] = [
  { key: 'visitor', label: '影像体验者', hint: '想被拍，先看作品再约人', entry: '约拍 · 摄影师推荐' },
  { key: 'enthusiast', label: '摄影爱好者', hint: '想拍别人，也想找人一起拍', entry: '作品流 · 约拍 · 搭子' },
  { key: 'photographer', label: '摄影师', hint: '开放档期，接单，管理作品', entry: '工作台 · 接单' },
  { key: 'creator', label: '主题创作者', hint: '有明确的角色或主题想法', entry: '主题共创 · 搭子匹配' },
  { key: 'partner', label: '拍摄搭档', hint: '想在同一场拍摄里遇见同好', entry: '搭子 · 现场' }
]

interface SessionState {
  authed: boolean
  name: string
  role: RoleKey | ''
  since: number
  /** MBTI：登录/注册后第一次填资料时可填，用于「搭子匹配」；没填就不参与性格加权 */
  mbti: string
}

const STORAGE_KEY = 'paishe.session.v1'

function read(): SessionState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) throw new Error('empty')
    const parsed = JSON.parse(raw) as Partial<SessionState>
    return {
      authed: Boolean(parsed.authed),
      // 旧会话里的「小满」跟着账号一起改名成 cyrus，避免刷新后还显示旧称呼
      name: typeof parsed.name === 'string' ? canonicalName(parsed.name) : '',
      role: (parsed.role as RoleKey) || '',
      since: Number(parsed.since) || 0,
      mbti: typeof parsed.mbti === 'string' ? parsed.mbti : ''
    }
  } catch {
    return { authed: false, name: '', role: '', since: 0, mbti: '' }
  }
}

export const session = reactive<SessionState>(read())

function persist() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session))
  } catch {
    /* 隐私模式下忽略，不影响本次会话 */
  }
}

export const isAuthed = computed(() => session.authed)
export const hasRole = computed(() => Boolean(session.role))
export const roleLabel = computed(() => identities.find((item) => item.key === session.role)?.label ?? '')

export function signIn(name: string, mbti = '') {
  session.authed = true
  session.name = name.trim() || '访客'
  session.role = ''
  session.since = Date.now()
  session.mbti = mbti
  persist()
}

/** 资料页改「显示称呼」用；只改当前会话里的展示名，密码登录的账号名仍以手机号为准 */
export function setName(name: string) {
  session.name = name.trim() || '访客'
  persist()
}

export function chooseRole(role: RoleKey) {
  session.role = role
  persist()
}

/** 首次填资料时补 MBTI；传空字符串表示「先不填」，之后还能在资料里改 */
export function setMbti(mbti: string) {
  session.mbti = mbti.trim().toUpperCase()
  persist()
}

export function signOut() {
  session.authed = false
  session.name = ''
  session.role = ''
  session.since = 0
  session.mbti = ''
  persist()
}
