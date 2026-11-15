<script setup lang="ts">
/**
 * 相机光标（2026-11-15）
 * - 形态：圆角小卡（整台相机），常态 = 图一，按住 = 图二（快门合），松开 = 图一
 * - 只在 / 与 /works/:id 挂载（App.vue 控制），触屏与粗指针设备直接不启用
 * - 输入框 / 文本域 / 下拉 / contenteditable 上让位给系统光标（I 型、手型都不抢）
 * - 尺寸：24px（用户要求「相机缩小五倍」，B 形态原尺寸 118px ÷ 5 ≈ 24）
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import camOpen from '../assets/cursor/cam-open.png'
import camClick from '../assets/cursor/cam-click.png'

const enabled = ref(false)
const visible = ref(false)
const down = ref(false)
const overField = ref(false)
const x = ref(-200)
const y = ref(-200)

const CAM_SIZE = 24 // px；改大小只改这一个数
const className = 'has-cam-cursor'

let frame = 0
let nextX = 0
let nextY = 0

const source = computed(() => (down.value ? camClick : camOpen))

function isField(px: number, py: number) {
  const el = document.elementFromPoint(px, py) as HTMLElement | null
  if (!el) return false
  const target = el.closest('input, textarea, [contenteditable="true"], [contenteditable=""]') as HTMLElement | null
  if (!target) return false
  if (target.tagName === 'INPUT') {
    const type = (target.getAttribute('type') || 'text').toLowerCase()
    return !['checkbox', 'radio', 'button', 'submit', 'reset', 'file', 'range'].includes(type)
  }
  return true
}

function flush() {
  frame = 0
  x.value = nextX
  y.value = nextY
  const field = isField(nextX, nextY)
  overField.value = field
  visible.value = !field
}

function onMove(event: MouseEvent) {
  nextX = event.clientX
  nextY = event.clientY
  if (frame) return
  frame = window.requestAnimationFrame(flush)
}

function onDown() {
  down.value = true
}

function onUp() {
  down.value = false
}

function onLeave() {
  visible.value = false
  down.value = false
}

function onBlur() {
  down.value = false
}

let media: MediaQueryList | undefined

function teardown() {
  window.removeEventListener('mousemove', onMove)
  window.removeEventListener('mousedown', onDown)
  window.removeEventListener('mouseup', onUp)
  window.removeEventListener('blur', onBlur)
  document.documentElement.removeEventListener('mouseleave', onLeave)
  document.documentElement.classList.remove(className)
  if (frame) window.cancelAnimationFrame(frame)
  frame = 0
}

function boot() {
  if (media?.matches === false) {
    teardown()
    enabled.value = false
    return
  }
  enabled.value = true
  document.documentElement.classList.add(className)
  window.addEventListener('mousemove', onMove, { passive: true })
  window.addEventListener('mousedown', onDown)
  window.addEventListener('mouseup', onUp)
  window.addEventListener('blur', onBlur)
  document.documentElement.addEventListener('mouseleave', onLeave)
}

onMounted(() => {
  media = window.matchMedia('(hover: hover) and (pointer: fine)')
  if (!media.matches) return
  boot()
  media.addEventListener?.('change', () => (media?.matches ? boot() : teardown()))
})

onBeforeUnmount(teardown)
</script>

<template>
  <div
    v-if="enabled"
    class="cam-cursor"
    :class="{ 'is-visible': visible, 'is-down': down, 'is-over-field': overField }"
    :style="{ transform: `translate3d(${x}px, ${y}px, 0)`, '--cam-size': `${CAM_SIZE}px` }"
    aria-hidden="true"
  >
    <img :src="source" alt="" draggable="false" />
  </div>
</template>

<style>
/* 隐藏系统光标：只在启用相机光标的页面生效。
   注意：这里不恢复任何「小手」，按钮/链接/勾选框/下拉一律由相机接管 ——
   用户要求按钮上不要再出现手型指针；只有文字输入类恢复系统 I 型光标。 */
html.has-cam-cursor,
html.has-cam-cursor * {
  cursor: none !important;
}
html.has-cam-cursor input:not([type='checkbox']):not([type='radio']):not([type='button']):not([type='submit']):not([type='reset']):not([type='file']):not([type='range']),
html.has-cam-cursor textarea,
html.has-cam-cursor [contenteditable='true'],
html.has-cam-cursor [contenteditable=''] {
  cursor: text !important;
}

.cam-cursor {
  position: fixed;
  left: 0;
  top: 0;
  z-index: 2147483000;
  pointer-events: none;
  will-change: transform;
  opacity: 0;
  transition: opacity 0.18s ease;
}
.cam-cursor.is-visible {
  opacity: 1;
}
.cam-cursor img {
  display: block;
  width: var(--cam-size, 24px);
  height: auto;
  border-radius: 3px;
  transform: translate(-50%, -50%) scale(1);
  transition: transform 0.11s ease, filter 0.11s ease;
  box-shadow: 0 2px 7px rgba(0, 0, 0, 0.5);
  user-select: none;
  -webkit-user-drag: none;
}
.cam-cursor.is-down img {
  transform: translate(-50%, -50%) scale(0.88);
  filter: drop-shadow(0 0 6px rgba(229, 163, 131, 0.75));
}
@media (prefers-reduced-motion: reduce) {
  .cam-cursor img {
    transition: none;
  }
}
</style>
