<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { bgUrl } from '../utils/media'

/**
 * 页面氛围层：整屏背景图 + 暗角 + 粒子。
 *
 * 2026-11-16 用户口径：约拍用「雪原星轨」，接拍用「星云」，两张图各做各的粒子。
 * 约束（用户 C 系列）：不加依赖、不裸写图片路径（走 utils/media.ts）、可读性优先。
 *
 * 性能：
 *  - 粒子数按视口面积算，上限 120；devicePixelRatio 封顶 2；
 *  - 页面不可见时停 rAF；prefers-reduced-motion 时只画一帧静态星点；
 *  - 纯 Canvas 2D + 小半径圆，不用滤镜/阴影（那两样在低端机上最贵）。
 */
const props = defineProps<{ variant: 'discover' | 'market' }>()

const FILE: Record<'discover' | 'market', string> = {
  discover: 'discover-star-trail.webp',
  market: 'market-nebula.webp'
}

const mediaStyle = computed(() => {
  const url = bgUrl(FILE[props.variant])
  return url ? { backgroundImage: `url("${url}")` } : {}
})

const wrapRef = ref<HTMLElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)

type Star = { x: number; y: number; r: number; a: number; phase: number; speed: number; drift: number }
type Meteor = { x: number; y: number; vx: number; vy: number; life: number; max: number; len: number }

let teardown: (() => void) | null = null

function start() {
  const wrap = wrapRef.value
  const canvas = canvasRef.value
  if (!wrap || !canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const isDiscover = props.variant === 'discover'
  const reduce = typeof window !== 'undefined'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches

  let w = 0
  let h = 0
  let stars: Star[] = []
  let meteor: Meteor | null = null
  let meteorWait = 2.5 + Math.random() * 3
  let time = 0
  let last = 0
  let raf = 0
  let running = false

  const colorOf = (alpha: number) => isDiscover
    ? `rgba(206,224,255,${alpha.toFixed(3)})`
    : `rgba(255,208,190,${alpha.toFixed(3)})`

  const build = () => {
    const count = Math.max(36, Math.min(120, Math.round((w * h) / (isDiscover ? 26000 : 20000))))
    stars = Array.from({ length: count }, () => ({
      x: Math.random() * w,
      y: Math.random() * h,
      r: (isDiscover ? 0.9 : 0.7) + Math.random() * 1.9,
      a: (isDiscover ? 0.3 : 0.24) + Math.random() * 0.55,
      phase: Math.random() * Math.PI * 2,
      speed: 0.25 + Math.random() * 0.6,
      drift: isDiscover ? 4 + Math.random() * 10 : 3 + Math.random() * 9
    }))
  }

  const resize = () => {
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    // 这一层是 fixed 满屏，直接跟视口走；用 wrap.clientHeight 会被挂载时机/父级高度影响
    w = Math.max(1, window.innerWidth)
    h = Math.max(1, window.innerHeight)
    canvas.width = Math.round(w * dpr)
    canvas.height = Math.round(h * dpr)
    canvas.style.width = `${w}px`
    canvas.style.height = `${h}px`
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    build()
    if (reduce) paintStatic()
  }

  const paintStatic = () => {
    ctx.clearRect(0, 0, w, h)
    ctx.globalCompositeOperation = 'lighter'
    for (const s of stars) {
      ctx.fillStyle = colorOf(s.a * 0.55)
      ctx.beginPath()
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2)
      ctx.fill()
    }
    ctx.globalCompositeOperation = 'source-over'
  }

  const drawStars = () => {
    for (const s of stars) {
      let x = s.x
      let y = s.y
      if (isDiscover) {
        // 整片星空极缓慢地向左平移（按深度分速度），像长曝光时天球在转
        const span = w + 40
        x = (((s.x - time * s.drift) % span) + span) % span - 20
        const twinkle = 0.55 + 0.45 * Math.sin(time * s.speed + s.phase)
        ctx.fillStyle = colorOf(s.a * twinkle * 0.9)
        ctx.beginPath()
        ctx.arc(x, y, s.r, 0, Math.PI * 2)
        ctx.fill()
        // 极少数亮星带一点点辉光，仍只用一个小圆叠一次，不用 shadowBlur
        if (s.a > 0.56) {
          ctx.fillStyle = colorOf(s.a * twinkle * 0.16)
          ctx.beginPath()
          ctx.arc(x, y, s.r * 3.2, 0, Math.PI * 2)
          ctx.fill()
        }
      } else {
        // 星云：尘埃缓慢上升 + 横向摆动，像气体在流动
        const span = h + 48
        y = (((s.y - time * s.drift) % span) + span) % span - 24
        x = s.x + Math.sin(time * 0.22 + s.phase) * 9
        const breathe = 0.6 + 0.4 * Math.sin(time * s.speed * 0.7 + s.phase)
        ctx.fillStyle = colorOf(s.a * breathe * 0.72)
        ctx.beginPath()
        ctx.arc(x, y, s.r, 0, Math.PI * 2)
        ctx.fill()
      }
    }
  }

  const drawMeteor = (dt: number) => {
    if (!meteor) {
      meteorWait -= dt
      if (meteorWait > 0) return
      const speed = 540 + Math.random() * 260
      meteor = {
        x: w * (0.55 + Math.random() * 0.4),
        y: h * (0.02 + Math.random() * 0.26),
        vx: -speed * (0.95 + Math.random() * 0.06),
        vy: speed * (0.16 + Math.random() * 0.14),
        life: 0,
        max: 1.05 + Math.random() * 0.55,
        len: 130 + Math.random() * 90
      }
      return
    }
    const m = meteor
    m.life += dt
    m.x += m.vx * dt
    m.y += m.vy * dt
    const progress = m.life / m.max
    if (progress >= 1) {
      meteor = null
      meteorWait = 3.5 + Math.random() * 4
      return
    }
    const fade = progress < 0.18 ? progress / 0.18 : 1 - (progress - 0.18) / 0.82
    const alpha = Math.max(0, Math.min(1, fade)) * 0.5
    const vx = m.vx
    const vy = m.vy
    const norm = Math.hypot(vx, vy) || 1
    const tailX = m.x - (vx / norm) * m.len
    const tailY = m.y - (vy / norm) * m.len
    const grad = ctx.createLinearGradient(m.x, m.y, tailX, tailY)
    grad.addColorStop(0, colorOf(alpha))
    grad.addColorStop(1, colorOf(0))
    ctx.strokeStyle = grad
    ctx.lineWidth = 1.6
    ctx.beginPath()
    ctx.moveTo(m.x, m.y)
    ctx.lineTo(tailX, tailY)
    ctx.stroke()
  }

  const loop = (now: number) => {
    if (!running) return
    const dt = last ? Math.min((now - last) / 1000, 0.05) : 0
    last = now
    time += dt
    ctx.clearRect(0, 0, w, h)
    ctx.globalCompositeOperation = 'lighter'
    drawStars()
    if (isDiscover) drawMeteor(dt)
    ctx.globalCompositeOperation = 'source-over'
    raf = window.requestAnimationFrame(loop)
  }

  const play = () => {
    if (reduce || running) return
    running = true
    last = 0
    raf = window.requestAnimationFrame(loop)
  }

  const pause = () => {
    running = false
    if (raf) window.cancelAnimationFrame(raf)
    raf = 0
  }

  const onVisibility = () => {
    if (document.visibilityState === 'hidden') pause()
    else play()
  }

  resize()
  if (reduce) paintStatic()
  else play()

  window.addEventListener('resize', resize, { passive: true })
  document.addEventListener('visibilitychange', onVisibility)

  teardown = () => {
    pause()
    window.removeEventListener('resize', resize)
    document.removeEventListener('visibilitychange', onVisibility)
  }
}

onMounted(start)
onBeforeUnmount(() => {
  teardown?.()
  teardown = null
})
</script>

<template>
  <div ref="wrapRef" class="ps-atmos" :class="`ps-atmos-${variant}`" aria-hidden="true">
    <div class="ps-atmos-media" :style="mediaStyle" />
    <div class="ps-atmos-scrim" />
    <canvas ref="canvasRef" class="ps-atmos-canvas" />
  </div>
</template>

<style scoped>
.ps-atmos {
  position: fixed;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
}

.ps-atmos-media {
  position: absolute;
  inset: -2px;
  background-position: center;
  background-size: cover;
  background-repeat: no-repeat;
  transform: scale(1.015);
}

.ps-atmos-discover .ps-atmos-media {
  background-position: center 42%;
  filter: saturate(0.92);
  /* 这张图底部自带版权条（用户已决定不裁原图）。
     这里只做构图：往上放大一点、锚点偏上，把版权条推出画面，不动素材本身。 */
  transform: scale(1.16);
  transform-origin: 50% 6%;
}

.ps-atmos-market .ps-atmos-media {
  background-position: center 46%;
}

.ps-atmos-scrim {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(118% 88% at 50% 18%, rgba(10, 12, 15, 0.06), rgba(10, 12, 15, 0.58) 72%),
    linear-gradient(180deg, rgba(10, 12, 15, 0.88), rgba(10, 12, 15, 0.34) 34%, rgba(10, 12, 15, 0.4) 68%, rgba(10, 12, 15, 0.9));
}

.ps-atmos-canvas {
  position: absolute;
  inset: 0;
  display: block;
}

@media (max-width: 760px) {
  .ps-atmos-discover .ps-atmos-media {
    background-position: center 46%;
  }

  .ps-atmos-scrim {
    background:
      radial-gradient(120% 90% at 50% 16%, rgba(10, 12, 15, 0.34), rgba(10, 12, 15, 0.8) 72%),
      linear-gradient(180deg, rgba(10, 12, 15, 0.95), rgba(10, 12, 15, 0.62) 32%, rgba(10, 12, 15, 0.66) 66%, rgba(10, 12, 15, 0.95));
  }
}
</style>
