<script setup lang="ts">
/**
 * 螺旋照片墙（2026-11-15）
 * 几何来自 .spiral-ref/demo/index.html，按用户要求改了三处：
 *   1. 两端延伸：turns 1.75→2.15、count 14→16、淡出从 0.34/0.50 推到 0.42/0.62
 *   2. 层次感：前景不透明、中间那张最亮、投影按深度分档
 *   3. 越靠近两端越虚化：新增 blur（桌面 3.2px 封顶，移动 1.8px，减弱动效时 0）
 * 交互（用户指定）：平时自己转、不抢滚轮；点击后图片按原比例放大、此时滚轮才驱动螺旋；退出后交还滚轮。
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

export interface SpiralItem {
  id: string
  image: string
  title: string
  author: string
  place: string
  device?: string
  styles?: string[]
  story?: string
}

const props = defineProps<{ items: SpiralItem[] }>()
const emit = defineEmits<{
  (event: 'select', item: SpiralItem): void
  (event: 'close'): void
}>()

const GEO = {
  count: 16,
  turns: 2.15,
  // 按正式站舞台（约 657×560，比 demo 的 885×670 窄）重算过：
  // 卡片缩小、半径与纵深放大，纵向步进压到 0.13，视野里才是一串螺旋而不是一坨
  cardW: 0.24,
  aspect: 1.3,
  pitch: 0.1,
  radius: 0.27,
  depth: 0.22,
  persp: 1.0734,
  rotY: 45,
  rotX: 6,
  rotZ: 3,
  scaleDrop: 0.16,
  fadeFrom: 0.46,
  fadeTo: 0.7,
  drift: 0.007
}

const stageRef = ref<HTMLElement | null>(null)
const sceneRef = ref<HTMLElement | null>(null)
const selected = ref<SpiralItem | null>(null)
const cardEls: HTMLElement[] = []

const isSelected = computed(() => Boolean(selected.value))

let W = 0, H = 0, cardW = 0, cardH = 0, pitch = 0, radius = 0, depth = 0, loop = 0
let progress = 0
let raf = 0
let lastNow = 0
let dragging = false
let moved = 0
let lastY = 0
let glide = 0
let snapTo: number | null = null
let blurMax = 3.2
let reduced = false
let wheelHandler: ((event: WheelEvent) => void) | null = null
let wheelStamp = 0

const mod = (v: number, m: number) => ((v % m) + m) % m
const clamp01 = (x: number) => Math.max(0, Math.min(1, x))
function smoothstep(x: number, a: number, b: number) {
  const t = clamp01((x - a) / (b - a))
  return t * t * (3 - 2 * t)
}

function setCard(el: unknown, index: number) {
  if (el instanceof HTMLElement) cardEls[index] = el
}

function measure() {
  const stage = stageRef.value
  const scene = sceneRef.value
  if (!stage || !scene) return
  const rect = stage.getBoundingClientRect()
  W = rect.width
  H = rect.height
  if (!W || !H) return
  cardW = W * GEO.cardW
  cardH = cardW * GEO.aspect
  pitch = H * GEO.pitch
  radius = W * GEO.radius
  depth = W * GEO.depth
  loop = GEO.count * pitch
  scene.style.perspective = `${(W * GEO.persp).toFixed(1)}px`
  // 舞台中心与整页中心的垂直差：介绍态要把大图对到「整页居中」，而不是对到舞台中心
  const offsetY = rect.top + H / 2 - window.innerHeight / 2
  stage.style.setProperty('--sw-vdy', `${(-offsetY).toFixed(1)}px`)
  cardEls.forEach((el) => {
    if (!el) return
    el.style.width = `${cardW.toFixed(1)}px`
    el.style.height = `${cardH.toFixed(1)}px`
    el.style.marginLeft = `${(-cardW / 2).toFixed(1)}px`
    el.style.marginTop = `${(-cardH / 2).toFixed(1)}px`
  })
}

function render() {
  if (!H) return
  for (let i = 0; i < cardEls.length; i += 1) {
    const el = cardEls[i]
    if (!el) continue
    const raw = i * pitch - progress * loop
    const yDown = mod(raw + loop / 2, loop) - loop / 2
    const yUp = -yDown
    const ang = Math.PI / 2 + (yUp / loop) * GEO.turns * Math.PI * 2
    const x = radius * Math.cos(ang)
    const z = depth * Math.sin(ang)
    const dist = Math.abs(yDown) / pitch
    const sc = Math.max(0.42, Math.min(1, 1 - GEO.scaleDrop * dist))
    const op = 1 - smoothstep(Math.abs(yDown), H * GEO.fadeFrom, H * GEO.fadeTo)
    const ry = -Math.cos(ang) * GEO.rotY
    const rx = Math.sin(ang) * GEO.rotX
    const rz = -Math.sin(ang) * GEO.rotZ
    const bright = 0.3 + (0.7 * ((z / depth) + 1)) / 2
    const shade = Math.max(0, Math.min(0.78, 1 - bright))
    const front = Math.abs(yDown) < pitch * 0.4 && op > 0.55
    // 越靠两端越虚化
    const t = Math.min(1, Math.abs(yDown) / (H / 2))
    const blur = blurMax ? Math.min(blurMax, t * t * blurMax) : 0

    el.style.transform = `translate3d(${x.toFixed(2)}px, ${yDown.toFixed(2)}px, ${z.toFixed(2)}px) rotateX(${rx.toFixed(2)}deg) rotateY(${ry.toFixed(2)}deg) rotateZ(${rz.toFixed(2)}deg) scale(${sc.toFixed(3)})`
    // 介绍态：墙压暗，只留一点轮廓（切换作品靠滚轮/方向键，不靠点背景卡片）
    el.style.opacity = isSelected.value ? (front ? Math.min(op, 0.28) : op * 0.22).toFixed(3) : op.toFixed(3)
    el.style.zIndex = String(Math.round(z + 1000))
    el.style.filter = blur > 0.08 ? `blur(${blur.toFixed(2)}px)` : 'none'
    el.style.setProperty('--shade', shade.toFixed(3))
    el.classList.toggle('is-front', front && !isSelected.value)
    if (op < 0.02 || isSelected.value) {
      el.style.visibility = op < 0.02 ? 'hidden' : 'visible'
      el.tabIndex = op < 0.02 ? -1 : 0
    } else {
      el.style.visibility = 'visible'
      el.tabIndex = 0
    }
  }
}

function tick(now: number) {
  const dt = lastNow ? Math.min(0.05, (now - lastNow) / 1000) : 0
  lastNow = now
  if (!dragging) {
    if (snapTo !== null) {
      let d = snapTo - progress
      d -= Math.round(d)
      if (Math.abs(d) < 0.0008) {
        progress = mod(snapTo, 1)
        snapTo = null
      } else {
        progress += d * Math.min(1, dt * 9)
      }
    } else if (Math.abs(glide) > 0.02) {
      progress += glide * dt
      glide *= Math.exp(-6 * dt)
    } else {
      if (glide !== 0) {
        glide = 0
        snapTo = Math.round(progress * GEO.count) / GEO.count
      } else if (!reduced && !isSelected.value) {
        progress += dt * GEO.drift
      }
    }
    progress = mod(progress, 1)
  }
  render()
  raf = window.requestAnimationFrame(tick)
}

function open(item: SpiralItem) {
  selected.value = item
  emit('select', item)
  // 父组件会先把页面钉回墙顶，等它滚完再量一次，--sw-vdy 才是对的
  window.requestAnimationFrame(() => measure())
}

/** 介绍态里前后切换：滚轮、↓↑ 都走这里 */
function step(direction: number) {
  const current = selected.value
  const total = props.items.length
  if (!current || total < 2) return
  const index = props.items.findIndex((item) => item.id === current.id)
  if (index < 0) return
  const next = props.items[(index + direction + total) % total]
  if (next) open(next)
}

function close() {
  if (!selected.value) return
  selected.value = null
  emit('close')
}

// 外面（右侧介绍面板的叉号）也要能把大图层一起关掉，否则会剩一张大图在屏幕上
defineExpose({ close })

function onKeydown(event: KeyboardEvent) {
  if (!selected.value) return
  if (event.key === 'Escape') { close(); return }
  if (event.key === 'ArrowDown' || event.key === 'ArrowRight') { event.preventDefault(); step(1); return }
  if (event.key === 'ArrowUp' || event.key === 'ArrowLeft') { event.preventDefault(); step(-1) }
}

function onPointerDown(event: PointerEvent) {
  if (isSelected.value) return
  if (event.button !== 0 && event.pointerType === 'mouse') return
  dragging = true
  moved = 0
  lastY = event.clientY
  glide = 0
  snapTo = null
}

function onPointerMove(event: PointerEvent) {
  if (!dragging) return
  const dy = event.clientY - lastY
  lastY = event.clientY
  moved += Math.abs(dy)
  progress = mod(progress - dy / loop, 1)
  glide = Math.max(-4, Math.min(4, -dy / loop))
}

function onPointerUp(event: PointerEvent) {
  if (!dragging) return
  dragging = false
  if (moved >= 8) {
    snapTo = Math.round(progress * GEO.count) / GEO.count
  }
}

/** 点卡片：拖拽过后不误触 */
function onCardClick(index: number) {
  if (moved > 8) return
  const item = props.items[index]
  if (item) open(item)
}

onMounted(() => {
  reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  blurMax = reduced ? 0 : window.innerWidth <= 900 ? 1.8 : 3.2
  measure()
  render()
  raf = window.requestAnimationFrame(tick)
  window.addEventListener('resize', measure)
  window.addEventListener('keydown', onKeydown)

  // 关键：只有「点开作品介绍」这一态才吃滚轮，平时完全不碰页面滚动。
  // 挂在 window 上而不是舞台上：右侧作品介绍面板在舞台外，滚轮落在那儿也要能切换。
  wheelHandler = (event: WheelEvent) => {
    if (!isSelected.value) return
    event.preventDefault()
    const now = performance.now()
    if (now - wheelStamp < 180) return
    wheelStamp = now
    glide = 0
    snapTo = null
    step(event.deltaY > 0 ? 1 : -1)
  }
  window.addEventListener('wheel', wheelHandler, { passive: false })
})

onBeforeUnmount(() => {  window.cancelAnimationFrame(raf)
  window.removeEventListener('resize', measure)
  window.removeEventListener('keydown', onKeydown)
  if (wheelHandler) window.removeEventListener('wheel', wheelHandler)
})
</script>

<template>
  <div ref="stageRef" class="sw-stage" :class="{ 'is-focus': isSelected }" @pointerdown="onPointerDown" @pointermove="onPointerMove" @pointerup="onPointerUp" @pointercancel="onPointerUp">
    <div ref="sceneRef" class="sw-scene">
      <button
        v-for="(item, index) in props.items"
        :key="item.id"
        :ref="(el) => setCard(el, index)"
        class="sw-card"
        type="button"
        :data-index="index"
        :aria-label="`打开作品介绍：${item.title}`"
        @click.stop="onCardClick(index)"
      >
        <img :src="item.image" :alt="item.title" loading="eager" decoding="async" draggable="false" />
        <span class="sw-card-shade" />
        <span class="sw-card-index">{{ String(index + 1).padStart(2, '0') }}</span>
      </button>
    </div>

    <Transition name="sw-focus">
      <div v-if="selected" class="sw-focus" @click.self="close">
        <figure class="sw-figure" :key="selected.id">
          <img :src="selected.image" :alt="selected.title" />
        </figure>
        <button class="sw-focus-close" type="button" aria-label="关闭作品介绍" @click="close">×</button>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.sw-stage {
  position: absolute;
  inset: 0;
  overflow: hidden;
  z-index: 3;
  cursor: grab;
  touch-action: pan-y;
}
.sw-stage.is-focus {
  cursor: default;
  /* 放大后的图会超出舞台范围，这里必须放行，否则上下会被裁掉 */
  overflow: visible;
}
.sw-scene {
  position: absolute;
  inset: 0;
  transform-style: preserve-3d;
}
.sw-card {
  position: absolute;
  left: 50%;
  top: 50%;
  margin: 0;
  padding: 0;
  display: block;
  border: 1px solid rgba(242, 238, 231, 0.17);
  border-radius: 12px;
  background: #0b131a;
  overflow: hidden;
  box-shadow: 0 22px 54px rgba(0, 0, 0, 0.42);
  will-change: transform, opacity, filter;
  backface-visibility: hidden;
  transform-origin: 50% 50%;
  cursor: pointer;
  color: inherit;
  transition: border-color 0.35s ease, box-shadow 0.35s ease;
}
.sw-card.is-front {
  border-color: rgba(242, 238, 231, 0.5);
  box-shadow: 0 34px 84px rgba(0, 0, 0, 0.58);
}
.sw-card img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
  filter: saturate(0.92) contrast(1.03);
  pointer-events: none;
  user-select: none;
}
.sw-card-shade {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: #050a0e;
  opacity: var(--shade, 0);
}
.sw-card-index {
  position: absolute;
  z-index: 2;
  top: 9px;
  right: 11px;
  font: 9px/1 ui-monospace, Consolas, monospace;
  letter-spacing: 0.12em;
  color: rgba(255, 255, 255, 0.72);
  text-shadow: 0 1px 8px rgba(0, 0, 0, 0.7);
  pointer-events: none;
}
.sw-focus {
  position: absolute;
  inset: 0;
  z-index: 20;
  display: grid;
  place-items: center;
  /* 用径向渐变而不是整块半透明：舞台左右边会随选中状态平移，硬边会露出来 */
  background: radial-gradient(ellipse 80% 74% at 38% 50%, rgba(5, 10, 14, .92) 0%, rgba(5, 10, 14, .7) 55%, rgba(5, 10, 14, 0) 100%);
  cursor: zoom-out;
}
.sw-figure {
  position: relative;
  margin: 0;
  width: 58%;
  height: 86%;
  display: grid;
  place-items: center;
  /* 左移 50px；纵向用 --sw-vdy 对齐「整页中心」而非舞台中心（竖图会偏高/偏低） */
  transform: translateX(calc(-28% - 50px)) translateY(var(--sw-vdy, 0px));
  animation: sw-swap 0.34s cubic-bezier(.2, .8, .2, 1) both;
}
@keyframes sw-swap {
  from { opacity: 0; transform: translateX(calc(-28% - 50px)) translateY(calc(var(--sw-vdy, 0px) + 14px)) scale(.985); }
  to { opacity: 1; transform: translateX(calc(-28% - 50px)) translateY(var(--sw-vdy, 0px)) scale(1); }
}
.sw-figure img {
  /* 绝对居中：竖图比 figure 盒还高时，普通 grid 居中会向下溢，导致整张图偏下 */
  position: absolute;
  inset: 0;
  margin: auto;
  max-width: 100%;
  max-height: 100%;
  width: auto;
  height: auto;
  border-radius: 10px;
  border: 1px solid rgba(242, 238, 231, 0.28);
  box-shadow: 0 40px 90px rgba(0, 0, 0, 0.62);
  object-fit: contain;
  /* 长宽各 1.5 倍，等比；scale 不改布局，所以居中与 50px 位移都不受影响 */
  transform: scale(1.5);
}
.sw-focus-close {
  position: absolute;
  top: 14px;
  right: 16px;
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  border: 1px solid rgba(242, 238, 231, 0.28);
  background: rgba(9, 13, 17, 0.8);
  color: #eef3f5;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
}
.sw-focus-enter-active,
.sw-focus-leave-active { transition: opacity 0.28s ease; }
.sw-focus-enter-from,
.sw-focus-leave-to { opacity: 0; }
@media (max-width: 900px) {
  .sw-figure { max-width: 88%; }
  .sw-figure img { max-height: 62vh; }
}
@media (prefers-reduced-motion: reduce) {
  .sw-card { transition: none; }
  .sw-figure { animation: none; }
  .sw-focus-enter-active, .sw-focus-leave-active { transition: none; }
}
</style>
