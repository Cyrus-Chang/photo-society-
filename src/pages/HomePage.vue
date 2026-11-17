<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  ArrowDownRight, ArrowLeft, ArrowRight, ArrowUpRight, Camera, Check, ChevronDown, Compass,
  Info, LoaderCircle, MapPin, MoveUpRight, Plus, ScanLine, Sparkles, Upload, Users, X
} from 'lucide-vue-next'
import { localWorkUrl } from '../utils/media'
import { classifyImage } from '../services/api'
import { writeCopyStream, type CopyResult } from '../services/api'
import {
  AI_LABEL_DICTIONARY,
  styleLabel, subjectLabel, toneLabel, type AiClassifyResult, type AiLabelDefinition
} from '../utils/aiLabels'
import { spiralWallWorks, works } from '../data/mock'
import heroBackground from '../assets/hero-stars.webp'
import bundBackground from '../assets/works/bund-night.jpg'
import wallBackground from '../assets/works/city-wall.jpg'
import { useRouter } from 'vue-router'
import SpiralWall, { type SpiralItem } from '../components/SpiralWall.vue'
import type { WorkCard } from '../types'
import { brand } from '../utils/brand'
import { isAuthed, session } from '../utils/session'

type GalleryItem = {
  id: string
  image: string
  title: string
  place: string
  author: string
  authorNote: string
  avatar: string
  style: string[]
  device: string
  story: string
  year: string
}

const gallerySources = [
  '20cd7d65c810bd3c1049832daf043ef6.jpg',
  '69ad5fc404908ee05df3d8da54713b72.jpg',
  '8a02ee6142c6a75362ca71196decbc0f.jpg',
  '4c70462bcc53c43cd1775790a5007ff4.jpg',
  '6383584ebff23e0a46860c6483194e6a.jpg',
  '7d3a27628dff43d7b262a6e87cd75d9e.jpg',
  '73def5f9b02dfb6bd6365c5f4bfed42b.jpg',
  '2d877e352b8d4982db812575933c8f59.jpg'
]

const galleryItems: GalleryItem[] = gallerySources.flatMap((filename, index) => {
  const image = localWorkUrl(filename)
  const source = works.find((work) => work.imageUrl === image)
  if (!source) return []
  return [{
    id: `field-${String(index + 1).padStart(3, '0')}`,
    image,
    title: source.title,
    place: source.location,
    author: source.photographerName,
    authorNote: '',
    avatar: source.photographerAvatar,
    style: source.styles,
    device: source.device ?? '待补充',
    story: '',
    year: `FIELD ${String(index + 1).padStart(3, '0')} / 2026`
  }]
})

const ghostA = localWorkUrl('city-night.jpg')
const ghostB = localWorkUrl('star-trail.jpg')

const activeIndex = ref(0)
const hasSelected = ref(false)
const wheelLock = ref(false)
const isChanging = ref(false)
const heroRef = ref<HTMLElement | null>(null)
const particleCanvasRef = ref<HTMLCanvasElement | null>(null)
const meteorCanvasRef = ref<HTMLCanvasElement | null>(null)
const pointer = ref({ x: 0, y: 0 })
const showUpload = ref(false)
const uploadInput = ref<HTMLInputElement | null>(null)
const uploadFile = ref<File | null>(null)
const uploadPreview = ref('')
const uploadTitle = ref('')
const uploadDescription = ref('')
const useAiCopy = ref(true)
const reviewState = ref<'idle' | 'checking' | 'approved' | 'submitted'>('idle')
/* AI 识别结果：风格走 13 类锚图原型、影调走 9 条色彩规则；题材 3 类内测中，不进界面 */
const aiResult = ref<AiClassifyResult | null>(null)
const aiError = ref('')
type ManualTagKind = 'style' | 'tone' | 'subject'
type ManualTag = { kind: ManualTagKind; code: string; label: string }
const removedAiTags = ref<Record<ManualTagKind, string[]>>({ style: [], tone: [], subject: [] })
const manualTags = ref<ManualTag[]>([])
const manualTagKind = ref<ManualTagKind>('style')
const manualTagInput = ref('')
const aiNeedsReview = computed(() => aiResult.value?.needsReview === true)
const aiStyleTags = computed(() => (aiResult.value?.style ?? []).slice(0, 2).map((tag) => ({
  code: tag.code,
  label: styleLabel(tag.code),
  percent: aiNeedsReview.value ? 0 : (tag.confidence ? Math.round(tag.confidence * 100) : 0),
  removed: removedAiTags.value.style.includes(tag.code)
})))
const aiToneTags = computed(() => (aiResult.value?.tone ?? []).map((tag) => ({
  code: tag.code,
  label: toneLabel(tag.code),
  removed: removedAiTags.value.tone.includes(tag.code)
})))
const aiSubjectTags = computed(() => (aiResult.value?.subject ?? []).map((tag) => ({
  code: tag.code,
  label: subjectLabel(tag.code),
  removed: removedAiTags.value.subject.includes(tag.code)
})))
const aiConfidenceSource = computed(() => {
  const method = aiResult.value?.confidenceCalibration?.style?.method
  if (method) return method
  const source = aiResult.value?.confidenceSource
  if (typeof source === 'string') return source
  return source?.style ?? ''
})
const aiSubjectGateNote = computed(() => {
  const gate = aiResult.value?.subjectGate
  if (!gate || aiSubjectTags.value.length || gate.passed) return ''
  if (gate.reason === 'person_evidence_or_confidence_below_gate') return '题材未展示：检测到人像证据或题材置信度不足。'
  if (gate.reason === 'person_evidence_unavailable') return '题材未展示：人像证据不可用，建议人工确认。'
  return '题材未展示：未通过安全门控，建议人工确认。'
})
const aiLatency = computed(() => (aiResult.value?.latencyMs ? `${Math.round(aiResult.value.latencyMs)}ms` : ''))
/* AI 文案：3 个标题备选 + 一句话简介；mode=rule 时必须显示「模板兜底」而不是假装模型生成 */
const copyResult = ref<CopyResult | null>(null)
const copyLoading = ref(false)
const copyError = ref('')
const copyStreamText = ref('')
let wheelTimer: number | undefined
let reviewTimer: number | undefined
let detailSwapTimer: number | undefined
let particleCleanup: (() => void) | undefined
let meteorCleanup: (() => void) | undefined
let particleRender: (() => void) | undefined
let revealObserver: IntersectionObserver | undefined
const router = useRouter()
const location = ref('西安 · 小寨')
const scene = ref('古风、夜景、灯笼感')
const shootAt = ref('周六 · 11 月 14 日')
const budget = ref('600-900')
const shootType = ref('人像')
const stylePick = ref('夜景')
/* 风格标签（2026-11-15 用户要求加 coser）：首页第 3 屏展示全部，第 4 屏表单取前 8 个 */
const styleTags = ['夜景', '古风', '胶片', '纪实', '日系', '高饱和', 'coser', '蓝调', '黑白', '建筑', '旅拍', '花卉']
const brandTags = ['富士', '尼康', '大疆', '索尼', '手机直出']
const matchState = ref<'idle' | 'loading' | 'error'>('idle')
const scrollCueVisible = ref(true)
// 首屏品牌动画：每个 session 只播一次；减弱动效时直接静态
const INTRO_KEY = 'paishe.intro.v1'
const playIntro = (() => {
  try {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return false
    if (sessionStorage.getItem(INTRO_KEY)) return false
    sessionStorage.setItem(INTRO_KEY, '1')
    return true
  } catch {
    return true
  }
})()
const pinyinChars = brand.pinyin.split('')
const featuredWorks = computed(() => works.filter((work) => work.photographerId === 'p-cyrus').slice(0, 4))
const scrollToWorks = () => document.querySelector('#intro')?.scrollIntoView({ behavior: 'smooth', block: 'start' })

const activeItem = computed(() => galleryItems[activeIndex.value])
const progress = computed(() => `${String(activeIndex.value + 1).padStart(2, '0')} / ${String(galleryItems.length).padStart(2, '0')}`)

/* 螺旋照片墙（2026-11-15）：16 张用户实拍，打散混排，数据来自 mock.spiralWorks
   2026-11-16：用户 Q5 拍板「进」，改用 mock.spiralWallWorks（原 28 张 + 薛定谔三张 = 31） */
const spiralItems: SpiralItem[] = spiralWallWorks.map((work) => ({
  id: work.id,
  image: work.imageUrl,
  title: work.title,
  author: work.photographerName,
  place: work.location,
  device: work.device,
  styles: work.styles,
  story: work.story
}))
const selectedSpiral = ref<WorkCard | null>(null)
const spiralWallRef = ref<{ close: () => void } | null>(null)

/**
 * 把页面钉回螺旋墙顶部（第一屏）。
 * 用户可能先往下滚了一点才点照片，那时打开详情会让关闭按钮贴到甚至跑出视口；
 * 关闭后页面又停在滚动位置，看起来就像「关不掉 / 回不到照片墙」。
 */
function pinToWall() {
  if (window.scrollY === 0) return
  const root = document.documentElement
  const previous = root.style.scrollBehavior
  root.style.scrollBehavior = 'auto'
  window.scrollTo(0, 0)
  root.style.scrollBehavior = previous
}

function onSpiralSelect(item: SpiralItem) {
  selectedSpiral.value = spiralWallWorks.find((work) => work.id === item.id) ?? null
  hasSelected.value = Boolean(selectedSpiral.value)
  pinToWall()
}

function onSpiralClose() {
  selectedSpiral.value = null
  hasSelected.value = false
  pinToWall()
}

/** 右侧介绍面板自己的叉号：面板 + 大图层必须一起关，否则屏幕上会剩一张大图 */
function closeSpiralDetail() {
  spiralWallRef.value?.close()
  onSpiralClose()
}

// 介绍态 = 模态态：滚动条拖动、空格/PageDown 都不许把页面带走
watch(selectedSpiral, (value) => {
  if (value) window.addEventListener('scroll', pinToWall, { passive: true })
  else window.removeEventListener('scroll', pinToWall)
})

function goTo(index: number, revealDetail = false) {
  const next = (index + galleryItems.length) % galleryItems.length
  if (revealDetail) hasSelected.value = true
  if (next === activeIndex.value) return
  activeIndex.value = next
  isChanging.value = true
  window.setTimeout(() => { isChanging.value = false }, 720)
}

function handleWheel(event: WheelEvent) {
  // 竖向滚轮属于页面滚动，不再劫持；只有横向 / 触控板左右滑才翻卡。
  if (Math.abs(event.deltaX) <= Math.abs(event.deltaY) || Math.abs(event.deltaX) < 8) return
  event.preventDefault()
  if (wheelLock.value) return
  wheelLock.value = true
  goTo(activeIndex.value + (event.deltaX > 0 ? 1 : -1))
  window.clearTimeout(wheelTimer)
  wheelTimer = window.setTimeout(() => { wheelLock.value = false }, 420)
}

// 螺旋轨迹：中心最大，向外依次缩小 / 变淡 / 虚化。
// 位置表沿用原有 9 个角度，±5 两张是向外延伸的尾部，让左上→右上、右下→左下各多出一截。
const spiralPositions = [
  { x: 66, y: -16, w: 22, h: 17, rotate: 9, scale: .36, opacity: .16, blur: 3.4 },   // -5 右上尾
  { x: 42, y: -10, w: 25, h: 20, rotate: 5, scale: .42, opacity: .22, blur: 2.6 },   // -4
  { x: 9, y: -2, w: 27, h: 21, rotate: -6, scale: .5, opacity: .3, blur: 1.8 },      // -3
  { x: -8, y: 20, w: 28, h: 23, rotate: -9, scale: .58, opacity: .4, blur: 1.1 },    // -2
  { x: -2, y: 60, w: 28, h: 23, rotate: -5, scale: .66, opacity: .52, blur: .5 },    // -1
  { x: 23, y: 22, w: 54, h: 56, rotate: -1.2, scale: 1, opacity: 1, blur: 0 },       // 0 中心
  { x: 61, y: 62, w: 28, h: 23, rotate: 5, scale: .66, opacity: .54, blur: .5 },     // +1
  { x: 79, y: 36, w: 27, h: 22, rotate: 8, scale: .58, opacity: .42, blur: 1.1 },    // +2
  { x: 69, y: 7, w: 28, h: 22, rotate: 5, scale: .5, opacity: .3, blur: 1.8 },       // +3
  { x: 30, y: 92, w: 23, h: 18, rotate: -10, scale: .36, opacity: .16, blur: 3.4 }   // +4 左下尾
]

function cardStyle(index: number) {
  const length = galleryItems.length
  let offset = index - activeIndex.value
  if (offset > length / 2) offset -= length
  if (offset < -length / 2) offset += length
  const slot = Math.max(-5, Math.min(4, offset))
  const position = spiralPositions[slot + 5]
  const isActive = offset === 0
  return {
    left: `${position.x}%`,
    top: `${position.y}%`,
    width: `${position.w}%`,
    height: `${position.h}%`,
    '--card-rotate': `${position.rotate}deg`,
    '--card-scale': `${isActive ? 1 : position.scale}`,
    opacity: position.opacity,
    filter: `blur(${position.blur}px)`,
    zIndex: isActive ? 12 : 10 - Math.abs(offset),
    pointerEvents: Math.abs(offset) > 4 ? ('none' as const) : ('auto' as const)
  }
}

function selectCard(index: number) {
  if (index === activeIndex.value) { hasSelected.value = true; return }
  hasSelected.value = false
  window.clearTimeout(detailSwapTimer)
  detailSwapTimer = window.setTimeout(() => { goTo(index, true) }, 220)
}

function ensureAuth(target: Record<string, string>) {
  if (isAuthed.value) {
    router.push({ name: 'discover', query: target })
    return
  }
  router.push({ name: 'login', query: { redirect: router.resolve({ name: 'discover', query: target }).fullPath } })
}

function startMatching() {
  matchState.value = 'loading'
  window.setTimeout(() => {
    matchState.value = 'idle'
    ensureAuth({
      location: location.value,
      shootAt: shootAt.value,
      scene: `${shootType.value} · ${stylePick.value}`,
      budget: `${budget.value}`
    })
  }, 620)
}

function enterSociety() {
  // 2026-11-16 用户：进入拍社不该顺手把筛选窗弹出来，先落到约拍页，要筛再点按钮。
  if (isAuthed.value) {
    router.push({ name: 'discover' })
    return
  }
  router.push({ name: 'login', query: { redirect: '/discover' } })
}
function closeDetail() { hasSelected.value = false }

/* ===== 整页翻屏（2026-11-15 第二轮）=====
   用户要求：滚轮哪怕只动一点，也要立刻翻到下一屏/上一屏。
   所以不用 scroll-snap，改成 JS 拦截 wheel；螺旋介绍态时滚轮归螺旋，不翻页。 */
let screenLock = false

function screenEls() {
  return Array.from(document.querySelectorAll<HTMLElement>('.spiral-page > section'))
}

function currentScreen() {
  const els = screenEls()
  const probe = window.scrollY + window.innerHeight * 0.5
  let index = 0
  els.forEach((el, i) => { if (el.offsetTop <= probe) index = i })
  return index
}

function goScreen(index: number) {
  const els = screenEls()
  if (!els.length) return
  const target = els[Math.max(0, Math.min(els.length - 1, index))]
  if (!target) return
  screenLock = true
  window.scrollTo({ top: target.offsetTop, behavior: 'smooth' })
  window.setTimeout(() => { screenLock = false }, 620)
}

function onWheelToSnap(event: WheelEvent) {
  // 螺旋介绍态：滚轮交给 SpiralWall 切上一张/下一张，同时把页面滚动锁死
  // （否则滚轮落在右侧介绍面板上时页面会往上跑，关闭按钮被顶出视口，看起来像「关不掉」）
  if (selectedSpiral.value) {
    event.preventDefault()
    return
  }
  // 表单控件里放行（下拉、多行输入）
  const target = event.target as HTMLElement | null
  if (target?.closest('select, textarea, input')) return
  if (Math.abs(event.deltaY) < 0.4) return
  event.preventDefault()
  if (screenLock) return
  goScreen(currentScreen() + (event.deltaY > 0 ? 1 : -1))
}
function updatePointer(event: MouseEvent) {
  if (!heroRef.value) return
  const rect = heroRef.value.getBoundingClientRect()
  pointer.value = { x: (event.clientX - rect.left) / rect.width - .5, y: (event.clientY - rect.top) / rect.height - .5 }
  particleRender?.()
}

const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches

function setupParticles() {
  const canvas = particleCanvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  const particles = Array.from({ length: 105 }, (_, index) => ({ x: Math.random(), y: Math.random(), r: index % 11 === 0 ? 1.8 : Math.random() * 1.35 + .35, alpha: Math.random() * .55 + .18 }))
  let width = 0; let height = 0
  const resize = () => { const rect = canvas.getBoundingClientRect(); width = rect.width; height = rect.height; canvas.width = width * dpr; canvas.height = height * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0) }
  const draw = () => { ctx.clearRect(0, 0, width, height); particles.forEach((particle, index) => { const x = particle.x * width + pointer.value.x * (index % 5 === 0 ? 12 : 4); const y = particle.y * height + pointer.value.y * (index % 4 === 0 ? 9 : 3); ctx.beginPath(); ctx.arc(x, y, particle.r, 0, Math.PI * 2); ctx.fillStyle = `rgba(230, 232, 214, ${particle.alpha})`; ctx.fill() }) }
  const handleResize = () => { resize(); draw() }
  particleRender = draw
  resize(); draw(); window.addEventListener('resize', handleResize); particleCleanup = () => { particleRender = undefined; window.removeEventListener('resize', handleResize) }
}

function setupMeteors() {
  const canvas = meteorCanvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  let width = 0; let height = 0; let raf = 0; let last = performance.now(); let spawnIn = 1.4
  const lowPower = reducedMotion() || new URLSearchParams(window.location.search).get('quality') === 'low'
  const meteors = Array.from({ length: lowPower ? 2 : 4 }, () => ({ active: false, x: 0, y: 0, vx: 0, vy: 0, age: 0, life: 0, length: 0 }))
  const resize = () => { const rect = canvas.getBoundingClientRect(); width = rect.width; height = rect.height; canvas.width = width * dpr; canvas.height = height * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0) }
  const spawn = () => { const meteor = meteors.find((item) => !item.active); if (!meteor) return; meteor.active = true; meteor.x = .72 + Math.random() * .28; meteor.y = .02 + Math.random() * .17; meteor.vx = -(.16 + Math.random() * .05); meteor.vy = .08 + Math.random() * .035; meteor.age = 0; meteor.life = 1.8 + Math.random() * 1.2; meteor.length = 45 + Math.random() * 45 }
  let running = true
  const frame = (now: number) => {
    if (!running) return
    const delta = Math.min((now - last) / 1000, .1); last = now
    spawnIn -= delta
    if (spawnIn <= 0) { spawn(); spawnIn = 2.3 + Math.random() * 2.4 }
    meteors.forEach((meteor) => {
      if (!meteor.active) return
      meteor.age += delta; meteor.x += meteor.vx * delta; meteor.y += meteor.vy * delta
      if (meteor.age > meteor.life || meteor.x < -.1 || meteor.y > 1) meteor.active = false
    })
    ctx.clearRect(0, 0, width, height)
    ctx.globalCompositeOperation = 'lighter'
    meteors.forEach((meteor) => {
      if (!meteor.active) return
      const fade = Math.min(1, meteor.age * 5) * Math.min(1, (1 - meteor.age / meteor.life) * 5)
      const headX = meteor.x * width; const headY = meteor.y * height
      const angle = Math.atan2(meteor.vy * height, meteor.vx * width)
      const tailX = headX - Math.cos(angle) * meteor.length; const tailY = headY - Math.sin(angle) * meteor.length
      ctx.globalAlpha = fade * .25; ctx.lineWidth = 3; ctx.strokeStyle = 'rgba(126, 170, 218, .42)'
      ctx.beginPath(); ctx.moveTo(tailX, tailY); ctx.lineTo(headX, headY); ctx.stroke()
      ctx.globalAlpha = fade; ctx.lineWidth = 1; ctx.strokeStyle = 'rgba(255, 247, 220, .95)'
      ctx.beginPath(); ctx.moveTo(tailX, tailY); ctx.lineTo(headX, headY); ctx.stroke()
      ctx.beginPath(); ctx.arc(headX, headY, 1.8, 0, Math.PI * 2); ctx.fillStyle = 'rgba(255, 252, 224, .95)'; ctx.fill()
    })
    ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over'
    raf = window.requestAnimationFrame(frame)
  }
  const onVisibility = () => {
    if (document.hidden) { running = false; window.cancelAnimationFrame(raf) }
    else if (!running) { running = true; last = performance.now(); raf = window.requestAnimationFrame(frame) }
  }
  resize()
  if (lowPower) { ctx.clearRect(0, 0, width, height) } else { raf = window.requestAnimationFrame(frame) }
  window.addEventListener('resize', resize)
  document.addEventListener('visibilitychange', onVisibility)
  meteorCleanup = () => {
    running = false
    window.cancelAnimationFrame(raf)
    window.removeEventListener('resize', resize)
    document.removeEventListener('visibilitychange', onVisibility)
  }
}

function openUpload() {
  showUpload.value = true
  reviewState.value = 'idle'
}

function resetAiEdits() {
  removedAiTags.value = { style: [], tone: [], subject: [] }
  manualTags.value = []
  manualTagInput.value = ''
}

function closeUpload() {
  if (reviewState.value === 'checking') return
  showUpload.value = false
  if (uploadPreview.value.startsWith('blob:')) URL.revokeObjectURL(uploadPreview.value)
  uploadPreview.value = ''
  uploadFile.value = null
  uploadTitle.value = ''
  uploadDescription.value = ''
  reviewState.value = 'idle'
  aiResult.value = null
  aiError.value = ''
  resetAiEdits()
  copyResult.value = null
  copyError.value = ''
  copyStreamText.value = ''
}

function chooseFile() { uploadInput.value?.click() }

function handleFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  uploadFile.value = file
  if (uploadPreview.value.startsWith('blob:')) URL.revokeObjectURL(uploadPreview.value)
  uploadPreview.value = URL.createObjectURL(file)
  reviewState.value = 'idle'
  aiResult.value = null
  aiError.value = ''
  resetAiEdits()
  copyResult.value = null
  copyError.value = ''
  copyStreamText.value = ''
}

function toggleAiTag(kind: ManualTagKind, code: string) {
  const list = removedAiTags.value[kind]
  const index = list.indexOf(code)
  if (index >= 0) list.splice(index, 1)
  else list.push(code)
}

function resolveKnownTag(kind: ManualTagKind, raw: string) {
  const value = raw.trim().toLowerCase()
  const group = kind === 'style' ? 'STYLE' : kind === 'tone' ? 'TONE' : 'SUBJECT'
  const match = (Object.entries(AI_LABEL_DICTIONARY[group]) as Array<[string, AiLabelDefinition]>).find(([code, item]) => (
    code.toLowerCase() === value
    || item.name.toLowerCase() === value
    || item.aliases.some((alias) => alias.toLowerCase() === value)
  ))
  return match ? { code: match[0], label: match[1].name } : null
}

function addManualTag() {
  const raw = manualTagInput.value.trim()
  if (!raw) return
  const known = resolveKnownTag(manualTagKind.value, raw)
  const label = known?.label ?? raw
  const code = known?.code ?? `MANUAL_${raw.toUpperCase().replace(/[^A-Z0-9\u4e00-\u9fff]+/g, '_').slice(0, 32)}`
  if (!manualTags.value.some((tag) => tag.kind === manualTagKind.value && tag.code === code)) {
    manualTags.value.push({ kind: manualTagKind.value, code, label })
  }
  manualTagInput.value = ''
}

function removeManualTag(tag: ManualTag) {
  manualTags.value = manualTags.value.filter((item) => !(item.kind === tag.kind && item.code === tag.code))
}

function effectiveTagCodes(kind: ManualTagKind) {
  const aiCodes = (aiResult.value?.[kind] ?? [])
    .map((tag) => tag.code)
    .filter((code) => !removedAiTags.value[kind].includes(code))
  const manualCodes = manualTags.value.filter((tag) => tag.kind === kind).map((tag) => tag.code)
  return [...aiCodes, ...manualCodes]
}

async function generateCopy() {
  if (copyLoading.value || !useAiCopy.value) return
  copyLoading.value = true
  copyError.value = ''
  copyResult.value = null
  copyStreamText.value = ''
  try {
    const result = await writeCopyStream({
      title: uploadTitle.value,
      styles: effectiveTagCodes('style'),
      tones: effectiveTagCodes('tone')
    }, (delta) => { copyStreamText.value += delta }, () => { copyStreamText.value = '' })
    copyResult.value = result
    if (!uploadTitle.value && result.titles[0]) uploadTitle.value = result.titles[0]
    uploadDescription.value = result.intro
  } catch (error) {
    copyError.value = error instanceof Error ? error.message : '文案生成失败'
  } finally {
    copyLoading.value = false
  }
}

function runReview() {
  if (!uploadFile.value) { chooseFile(); return }
  reviewState.value = 'checking'
  aiResult.value = null
  aiError.value = ''
  resetAiEdits()
  void classifyImage(uploadFile.value)
    .then((result) => {
      aiResult.value = result
      reviewState.value = 'approved'
    })
    .catch((error: unknown) => {
      reviewState.value = 'idle'
      aiError.value = error instanceof Error ? error.message : '识别失败'
    })
}

function submitForReview() {
  if (reviewState.value !== 'approved') return
  reviewState.value = 'submitted'
}

function setupReveals() {
  const targets = Array.from(document.querySelectorAll<HTMLElement>('.reveal-on-scroll'))
  if (!targets.length) return
  if (reducedMotion()) {
    targets.forEach((el) => el.classList.add('is-visible'))
    return
  }
  revealObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return
      entry.target.classList.add('is-visible')
      revealObserver?.unobserve(entry.target)
    })
  }, { rootMargin: '0px 0px -12% 0px', threshold: .12 })
  targets.forEach((el) => revealObserver?.observe(el))
}

function onScroll() {
  scrollCueVisible.value = window.scrollY < 120
}

onBeforeUnmount(() => {
  window.clearTimeout(wheelTimer)
  window.clearTimeout(reviewTimer)
  window.clearTimeout(detailSwapTimer)
  if (uploadPreview.value.startsWith('blob:')) URL.revokeObjectURL(uploadPreview.value)
  particleCleanup?.()
  meteorCleanup?.()
  revealObserver?.disconnect()
  window.removeEventListener('scroll', onScroll)
  window.removeEventListener('wheel', onWheelToSnap)
  window.removeEventListener('scroll', pinToWall)
})

onMounted(async () => {
  await nextTick()
  setupParticles()
  setupMeteors()
  setupReveals()
  window.addEventListener('scroll', onScroll, { passive: true })
  window.addEventListener('wheel', onWheelToSnap, { passive: false })
})
</script>

<template>
  <div class="spiral-page" :style="{ '--hero-bg': `url(${heroBackground})` }">
    <div class="spiral-noise" aria-hidden="true" />
    <div class="spiral-stars" aria-hidden="true" />

    <section ref="heroRef" class="spiral-hero" :class="{ 'has-selection': hasSelected }" :style="{ '--pointer-x': `${pointer.x * 20}px`, '--pointer-y': `${pointer.y * 20}px` }" @mousemove="updatePointer">
      <img class="hero-bg-image" :src="heroBackground" alt="" aria-hidden="true" fetchpriority="high" />
      <div class="home-brand" :class="{ 'is-intro': playIntro }" :aria-label="`${brand.cn} ${brand.en}`">
        <span class="home-brand-cn" aria-hidden="true">
          <span v-for="(char, index) in ['拍', '社']" :key="index" class="home-brand-char" :style="{ '--i': index }">{{ char }}</span>
        </span>
        <span class="home-brand-py" aria-hidden="true">
          <span v-for="(char, index) in pinyinChars" :key="index" class="home-brand-py-char" :style="{ '--i': index }">{{ char }}</span>
        </span>
      </div>
      <div class="spiral-heading">
        <div class="spiral-kicker"><span class="kicker-line" />FIELD JOURNAL <b>2026</b></div>
        <p class="spiral-overline">让AI读懂你的审美。</p>
        <h1>让每一双爱美的眼睛<br /><em>都能找到</em>独属于<span class="pupil-highlight">瞳孔</span>的风景线。</h1>
        <p>把时空和感觉说给AI，将技术与保障托付给平台，赠予一知己。</p>
        <div class="spiral-heading-meta"><i />6 位摄影师正在附近拍摄</div>
        <!-- 2026-11-16 用户：登录后回到首页，第一页下方要有「进入拍社」 -->
        <RouterLink v-if="isAuthed" class="home-enter spiral-enter" to="/discover">
          进入拍社
          <MoveUpRight :size="17" aria-hidden="true" />
        </RouterLink>
        <!-- 2026-11-16 用户：已登录回首页只留「进入拍社」，不再显示滑动提示（未登录才显示） -->
        <button v-if="!isAuthed" class="spiral-scroll-hint" type="button" @click="goScreen(1)">
          <span>向下滑动进入拍社</span>
          <ChevronDown :size="15" />
        </button>
      </div>

      <div class="spiral-stage-wrap">
        <div class="spiral-stage" :class="{ 'is-changing': isChanging }">
          <canvas ref="particleCanvasRef" class="spiral-particle-canvas" aria-hidden="true" />
          <canvas ref="meteorCanvasRef" class="spiral-meteor-canvas" aria-hidden="true" />
          <svg class="spiral-trace" viewBox="0 0 100 100" aria-hidden="true"><path d="M86 9C55-6 18 2 12 25c-7 26 18 43 48 38 26-4 34-26 18-40-14-12-40-8-45 8-4 13 10 22 23 18 11-3 12-13 4-18-7-4-16 0-16 7" /></svg>
          <div class="orbit-line orbit-line-one" aria-hidden="true" />
          <div class="orbit-line orbit-line-two" aria-hidden="true" />
          <div class="orbit-line orbit-line-three" aria-hidden="true" />
          <span class="stage-axis stage-axis-top">CLICK OR SWIPE TO MOVE</span>
          <span class="stage-axis stage-axis-bottom">THE COIL KEEPS TURNING</span>

          <div class="spiral-ghost ghost-a" aria-hidden="true"><img :src="ghostA" alt="" loading="lazy" /></div>
          <div class="spiral-ghost ghost-b" aria-hidden="true"><img :src="ghostB" alt="" loading="lazy" /></div>

          <SpiralWall ref="spiralWallRef" :items="spiralItems" @select="onSpiralSelect" @close="onSpiralClose" />
        </div>
      </div>

      <Transition name="detail-fade">
      <aside v-if="selectedSpiral" class="spiral-detail" :key="selectedSpiral.id">
        <div class="detail-topline"><span>NOW IN FOCUS</span><span>{{ selectedSpiral.shootDate }}</span><button class="detail-close" type="button" aria-label="收起详情" @click="closeSpiralDetail"><X :size="15" /></button></div>
        <div class="detail-author"><img :src="selectedSpiral.photographerAvatar" :alt="selectedSpiral.photographerName" /><div><span>作者</span><strong>{{ selectedSpiral.photographerName }}</strong><small>{{ selectedSpiral.city }}</small></div></div>
        <div class="detail-copy"><p class="detail-place">{{ selectedSpiral.location }}</p><h2>{{ selectedSpiral.title }}</h2><p v-if="selectedSpiral.story">{{ selectedSpiral.story }}</p></div>
        <dl class="detail-facts"><div><dt>PHOTO STYLE</dt><dd><span v-for="tag in selectedSpiral.styles" :key="tag">{{ tag }}</span></dd></div><div><dt>CAPTURED WITH</dt><dd>{{ selectedSpiral.device ?? '待补充' }}</dd></div></dl>
        <div class="detail-note"><Info :size="14" /><span>照片展示作者署名与设备信息，详细介绍非强制填写项。</span></div>
        <div class="detail-upload-row">
          <button class="detail-upload" type="button" @click="openUpload"><Plus :size="14" />把你的回忆放进照片墙</button>
        </div>
      </aside>
      </Transition>
      <button class="screen-cue" type="button" aria-label="向下浏览下一屏" @click="goScreen(1)">
        <ChevronDown :size="20" />
      </button>
    </section>

    <!-- 第 2 屏：平台是干什么的（背景：上海外滩） -->
    <section id="intro" class="hp-screen hp-screen--platform reveal-on-scroll">
      <img class="hp-bg" :src="bundBackground" alt="" aria-hidden="true" loading="lazy" decoding="async" />
      <div class="hp-veil" aria-hidden="true" />
      <div class="hp-inner">
        <header class="home-section-head">
          <div><span class="home-eyebrow">01 / WHAT WE DO</span><h2>是摄影社区，<br /><em>也是摄影伙伴。</em></h2></div>
          <p>只需要将「想拍什么、在哪天、什么预算」说清楚，平台自动为你推荐合口味的摄影师/摄影爱好者/摄影搭子。</p>
        </header>
        <div class="home-intro-grid">
          <article><span>01</span><h3>找一位摄影师</h3><p>按城市、日期、预算、风格以及你的性格MBTI，为你推荐懂你的摄影人</p></article>
          <article><span>02</span><h3>摄影师接单</h3><p>打开档期开关、上传作品与个人信息，让need you的人看到你。</p></article>
          <article><span>03</span><h3>找拍摄搭档</h3><p>同一场主题、同一个地点，互相组队，互相掌机，让coser找到team，为相机找到伙伴。</p></article>
          <article><span>04</span><h3>发布一条需求</h3><p>把地点、时间和预算写清楚，让有空的人直接来回应。</p></article>
        </div>
      </div>
      <button class="screen-cue" type="button" aria-label="下一屏：我们能做什么" @click="goScreen(2)">
        <ChevronDown :size="20" />
      </button>
    </section>

    <!-- 第 3 屏：亮点（背景：南京城墙） -->
    <section class="hp-screen hp-screen--highlight reveal-on-scroll">
      <img class="hp-bg" :src="wallBackground" alt="" aria-hidden="true" loading="lazy" decoding="async" />
      <div class="hp-veil" aria-hidden="true" />
      <div class="hp-inner">
        <header class="home-section-head">
          <div><span class="home-eyebrow">02 / WHAT WE DO BETTER</span><h2>把「审美与遇见」<br /><em>交给AI。</em></h2></div>
          <p>通过上传你喜欢的摄影作品，让AI读懂你的审美。</p>
        </header>

        <div class="hp-highlights">
          <article>
            <span class="hp-hl-index">A</span>
            <h3>AI 帮你选摄影师</h3>
            <p>说清想拍什么，AI从作品的光线、风格、机位和档期里挑出最适合你的摄影佬。</p>
          </article>
          <article>
            <span class="hp-hl-index">B</span>
            <h3>AI 帮你找搭子</h3>
            <p>注册时填一次 MBTI、星座以及自我介绍，系统按性格相容度 × 所在城市 × 拍摄题材排序。互补组合优先（比如 INFP 配 ENFJ、INTJ 配 ENTP，火象与风象等）审美至上，题材重合再加分。</p>
          </article>
          <article>
            <span class="hp-hl-index">C</span>
            <h3>作品自带风格标签</h3>
            <p>每张作品入库时自动设置标签，按标签找人（有图有真相，有标签真的香）标签会随你的拍摄意图加权，越用越准。</p>
          </article>
        </div>

        <div class="hp-tags-row">
          <div class="hp-tags" aria-label="风格标签">
            <span v-for="tag in styleTags" :key="tag">{{ tag }}</span>
          </div>
          <span class="hp-tags-divider" aria-hidden="true">|</span>
          <div class="hp-brands" aria-label="器材">
            <span v-for="item in brandTags" :key="item">{{ item }}</span>
          </div>
        </div>

        <!-- 原来独立的「条件匹配」页（03）作废，标题与说明并入本屏 -->
        <div class="hp-bridge">
          <div class="hp-bridge-head">
            <h3>地点、日期、预算、风格，先说清楚。</h3>
          </div>
          <p>我们只根据你给的条件和作品本身的风格做匹配，不会替你编造摄影师的经历或故事。</p>
          <div class="home-match-note"><Sparkles :size="15" /><span>匹配理由（地点对、预算对、风格近、时间刚好、性格适合）可筛选。</span></div>
        </div>
      </div>
      <button class="screen-cue" type="button" aria-label="下一屏：开始匹配" @click="goScreen(3)">
        <ChevronDown :size="20" />
      </button>
    </section>

    <!-- 第 4 屏：进入拍社（2026-11-15 用户要求：删去条件匹配表单，只保留邀约块并居中） -->
    <section id="finder" class="hp-screen hp-screen--invite reveal-on-scroll">
      <div class="hp-inner hp-final">
        <div class="home-invite">
          <span class="home-eyebrow">03 / ENTER</span>
          <h2>先看照片，<br /><em>再进拍社。</em></h2>
          <p>{{ isAuthed ? `欢迎回来，${session.name}。` : '登录后可以约拍、发需求、找搭子，也可以先只逛作品。' }}</p>
          <button class="home-enter" type="button" @click="enterSociety">
            {{ isAuthed ? '继续浏览拍社' : '进入拍社' }}
            <MoveUpRight :size="18" />
          </button>
          <RouterLink class="home-ai-link" to="/match">说不清该找谁？让 AI 帮你撮合 <ArrowUpRight :size="15" /></RouterLink>
          <small>约拍 · 接拍 · 圈子 · 我的约拍 · 摄影师工作台</small>
        </div>
      </div>
      <button class="screen-cue is-up" type="button" aria-label="回到第一屏" @click="goScreen(0)">
        <ChevronDown :size="20" />
      </button>
    </section>

    <footer class="footer-v2 spiral-followup"><div class="footer-v2-brand"><span>拍</span><div><strong>{{ brand.cn }}</strong><small>{{ brand.en }}</small></div></div><p>让每一次想拍照，都遇见刚好能到场的人。</p><span>© 2026 拍社影像</span></footer>

    <Transition name="modal-fade"><div v-if="showUpload" class="upload-backdrop" @click.self="closeUpload"><section class="upload-modal" role="dialog" aria-modal="true" aria-labelledby="upload-title"><button class="modal-close" type="button" aria-label="关闭" @click="closeUpload"><X :size="19" /></button><div class="upload-modal-head"><span class="spiral-kicker"><span class="kicker-line" />ADD TO THE FIELD</span><h2 id="upload-title">把你的现场放进照片墙</h2><p>只需要一张照片。署名、标签和机型会被完整保留，其他文字交给你或 AI。</p></div><div class="upload-modal-body"><div class="upload-preview" :class="{ 'has-image': uploadPreview }" @click="chooseFile"><img v-if="uploadPreview" :src="uploadPreview" alt="待上传照片预览" /><div v-else><Upload :size="25" /><strong>拖入或选择一张照片</strong><small>JPG / PNG · 建议长边 1600px 以上</small></div><input ref="uploadInput" type="file" accept="image/jpeg,image/png,image/webp" hidden @change="handleFile" /></div><div class="upload-fields"><label><span>作品标题</span><input v-model="uploadTitle" placeholder="例如：雨停之后的街角" /></label><label><span>这张照片的介绍</span><textarea v-model="uploadDescription" rows="5" placeholder="写下你想留下的那句话，或交给 AI 帮你整理。" /></label><div class="ai-copy-row"><button class="ai-toggle" :class="{ active: useAiCopy }" type="button" @click="useAiCopy = !useAiCopy"><span class="toggle-dot" /><span>允许 AI 美化文字</span></button><button class="ai-generate" type="button" :disabled="!useAiCopy || copyLoading" @click="generateCopy"><Sparkles :size="14" /> {{ copyLoading ? '生成中…' : '生成介绍' }}</button></div><div class="upload-exclude"><ScanLine :size="15" /><span>AI 只生成照片相关描述，不会修改作者、标签和机型。</span></div></div></div><div v-if="aiError" class="ai-result-panel is-error" role="status"><p class="ai-result-error">{{ aiError }}</p><small class="ai-result-note">风格与影调来自本地模型；服务没起来时这里不会伪造标签。</small></div><div v-else-if="aiStyleTags.length || aiToneTags.length || aiSubjectTags.length || aiNeedsReview || aiSubjectGateNote" class="ai-result-panel" role="status"><div v-if="aiStyleTags.length" class="ai-tag-group"><span class="ai-tag-label">STYLE · AI 识别</span><span v-for="tag in aiStyleTags" :key="tag.code" class="ai-tag is-style" :class="{ 'is-muted': tag.removed }"><span>{{ tag.label }}</span><b v-if="tag.percent && !aiNeedsReview">{{ tag.percent }}%</b><button type="button" :aria-label="tag.removed ? '恢复 AI 风格标签' : '移除 AI 风格标签'" @click.stop="toggleAiTag('style', tag.code)">{{ tag.removed ? '恢复' : '移除' }}</button></span></div><div v-if="aiToneTags.length" class="ai-tag-group"><span class="ai-tag-label">TONE · AI 识别</span><span v-for="tag in aiToneTags" :key="tag.code" class="ai-tag is-tone" :class="{ 'is-muted': tag.removed }"><span>{{ tag.label }}</span><button type="button" :aria-label="tag.removed ? '恢复 AI 影调标签' : '移除 AI 影调标签'" @click.stop="toggleAiTag('tone', tag.code)">{{ tag.removed ? '恢复' : '移除' }}</button></span><span v-if="aiLatency" class="ai-tag is-meta">{{ aiLatency }}</span></div><div v-if="aiSubjectTags.length" class="ai-tag-group"><span class="ai-tag-label">SUBJECT · AI 识别</span><span v-for="tag in aiSubjectTags" :key="tag.code" class="ai-tag is-tone" :class="{ 'is-muted': tag.removed }"><span>{{ tag.label }}</span><button type="button" :aria-label="tag.removed ? '恢复 AI 题材标签' : '移除 AI 题材标签'" @click.stop="toggleAiTag('subject', tag.code)">{{ tag.removed ? '恢复' : '移除' }}</button></span></div><div class="ai-tag-group"><span class="ai-tag-label">人工修正</span><span v-for="tag in manualTags" :key="tag.kind + '-' + tag.code" class="ai-tag is-manual"><span>{{ tag.label }}</span><button type="button" aria-label="删除人工标签" @click.stop="removeManualTag(tag)">删除</button></span><span v-if="!manualTags.length" class="ai-result-note">暂无</span></div><div class="ai-tag-group"><select v-model="manualTagKind" aria-label="人工标签类型"><option value="style">风格</option><option value="tone">影调</option><option value="subject">题材</option></select><input v-model="manualTagInput" type="text" maxlength="40" placeholder="输入中文标签或 code" aria-label="输入人工标签" @keyup.enter="addManualTag" /><button type="button" class="ai-copy-title" @click="addManualTag"><Plus :size="13" /> 添加</button></div><small class="ai-result-note">AI 识别与人工修正分开记录；人工增删只保存在当前上传弹窗，不改模型结果。</small><small v-if="aiNeedsReview" class="ai-result-note">建议人工确认：当前置信度低于业务阈值。</small><small v-if="aiSubjectGateNote" class="ai-result-note">{{ aiSubjectGateNote }}</small><small v-else-if="aiConfidenceSource" class="ai-result-note">置信度来源：{{ aiConfidenceSource }}</small></div><div v-if="copyResult || copyError || copyLoading || copyStreamText" class="ai-copy-panel" role="status" aria-live="polite"><div v-if="copyResult" class="ai-copy-head"><span class="ai-tag-label">TITLE</span><button v-for="title in copyResult.titles" :key="title" type="button" class="ai-copy-title" @click="uploadTitle = title">{{ title }}</button></div><div v-if="copyLoading || copyStreamText" class="ai-copy-stream"><span class="ai-tag-label">INTRO</span><span class="ai-copy-stream-text">{{ copyStreamText || '正在整理照片相关描述' }}<i v-if="copyLoading" class="ai-copy-caret" aria-hidden="true" /></span></div><p v-if="copyError" class="ai-result-error">{{ copyError }}</p><p v-if="copyResult" class="ai-copy-note">{{ copyResult.mode === 'llm' ? 'AI 生成 · 已避开时间/地点/人物关系等画面外信息' : copyResult.note }}</p></div><div class="upload-review-bar"><div class="review-status" :class="`is-${reviewState}`"><template v-if="reviewState === 'idle'"><Info :size="16" /><span>上传后先通过识别图片模型检查</span></template><template v-else-if="reviewState === 'checking'"><LoaderCircle class="spin" :size="16" /><span>模型正在检查画面内容与敏感元素…</span></template><template v-else-if="reviewState === 'approved'"><Check :size="16" /><span>识别通过，可以提交人工审核</span></template><template v-else><Check :size="16" /><span>已提交，等待人工审核</span></template></div><div class="upload-actions"><button class="upload-ghost" type="button" @click="closeUpload">稍后再说</button><button class="upload-submit" type="button" :disabled="reviewState === 'checking'" @click="reviewState === 'approved' ? submitForReview() : runReview()">{{ reviewState === 'approved' ? '提交人工审核' : reviewState === 'checking' ? '检查中…' : '先检查这张照片' }}</button></div></div></section></div></Transition>
  </div>
</template>

<style scoped>
.spiral-scroll-hint {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  margin-top: 26px;
  padding: 0;
  border: 0;
  background: transparent;
  color: rgba(242, 238, 231, .58);
  font: 10px/1 'DM Mono', ui-monospace, monospace;
  letter-spacing: .16em;
  cursor: pointer;
  transition: color .2s ease;
}
.spiral-scroll-hint::before { content: ''; width: 26px; height: 1px; background: rgba(242, 238, 231, .22); }
.spiral-scroll-hint svg { color: #e5a383; animation: spiral-hint-bob 1.9s ease-in-out infinite; }
.spiral-scroll-hint:hover { color: #e5a383; }
@keyframes spiral-hint-bob { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(4px); } }

.detail-upload-row { display: flex; justify-content: flex-end; margin-top: 16px; }
.detail-upload {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 38px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid rgba(233, 139, 107, .55);
  background: rgba(233, 139, 107, .12);
  color: #ffd9c9;
  font-size: 10.5px;
  transition: border-color .2s ease, background .2s ease, transform .2s ease;
}
.detail-upload:hover { border-color: rgba(233, 139, 107, .9); background: rgba(233, 139, 107, .2); transform: translateY(-1px); }
.detail-upload:focus-visible { outline: 2px solid rgba(233, 139, 107, .7); outline-offset: 2px; }

@media (max-width: 720px) {
  .spiral-scroll-hint { margin-top: 20px; }
  .detail-upload-row { margin-top: 14px; }
}
@media (prefers-reduced-motion: reduce) {
  .spiral-scroll-hint svg { animation: none; }
  .detail-upload:hover { transform: none; }
}
</style>
