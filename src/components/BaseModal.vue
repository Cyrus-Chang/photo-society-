<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = withDefaults(defineProps<{
  open: boolean
  labelledBy?: string
  closeOnBackdrop?: boolean
  size?: 'md' | 'lg' | 'xl'
}>(), {
  closeOnBackdrop: true,
  size: 'md'
})

const emit = defineEmits<{ (event: 'close'): void }>()

const panel = ref<HTMLElement | null>(null)
let lastFocus: HTMLElement | null = null
const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'

function focusables() {
  return Array.from(panel.value?.querySelectorAll<HTMLElement>(FOCUSABLE) ?? [])
}

async function openModal() {
  lastFocus = document.activeElement as HTMLElement | null
  document.body.classList.add('has-modal')
  await nextTick()
  // 焦点先落在弹窗容器（tabindex=-1）而不是第一个控件：
  // 避免直接聚焦「其他日期」这类次级按钮，Tab 再进入表单。
  panel.value?.focus()
}

function closeModal() {
  document.body.classList.remove('has-modal')
  lastFocus?.focus?.()
}

watch(() => props.open, (value) => { if (value) void openModal(); else closeModal() })

function onKeydown(event: KeyboardEvent) {
  if (!props.open) return
  if (event.key === 'Escape') {
    event.stopPropagation()
    emit('close')
    return
  }
  if (event.key !== 'Tab') return
  const list = focusables()
  if (!list.length) { event.preventDefault(); return }
  const first = list[0]
  const last = list[list.length - 1]
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
}

function onBackdrop() {
  if (props.closeOnBackdrop) emit('close')
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  // 带 ?filter=1 直接打开时 watch 不会触发，挂载时也要把焦点送进弹窗
  if (props.open) void openModal()
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  document.body.classList.remove('has-modal')
})
</script>

<template>
  <Teleport to="body">
    <Transition name="p-modal">
      <div v-if="open" class="p-modal" @click.self="onBackdrop">
        <div ref="panel" class="p-modal-panel" :class="`is-${size}`" role="dialog" aria-modal="true" :aria-labelledby="labelledBy" tabindex="-1">
          <slot />
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.p-modal {
  position: fixed; inset: 0; z-index: 200;
  display: grid; place-items: center; padding: 24px;
  background: rgba(3, 6, 9, .72);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}
.p-modal-panel {
  position: relative; width: min(560px, 100%); max-height: min(86vh, 760px); overflow-y: auto; overflow-x: hidden;
  border-radius: 24px;
  border: 1px solid rgba(237, 241, 244, .16);
  background:
    radial-gradient(120% 90% at 12% 0%, rgba(233, 139, 107, .10), transparent 46%),
    linear-gradient(160deg, #12191f 0%, #0b1015 100%);
  box-shadow: 0 40px 100px rgba(0, 0, 0, .55), inset 0 1px 0 rgba(255, 255, 255, .05);
  color: #edf1f4;
  padding: 30px;
  outline: none;
}
.p-modal-panel.is-lg { width: min(760px, 100%); }
/* 筛选弹窗的两栏（条件 + 风格泡泡）需要更宽；只加档位，不动 md / lg 的既有宽度 */
.p-modal-panel.is-xl { width: min(1000px, 100%); max-height: min(92vh, 900px); padding: 32px 34px; }
.p-modal-enter-active, .p-modal-leave-active { transition: opacity .28s cubic-bezier(.2, .8, .2, 1); }
.p-modal-enter-active .p-modal-panel, .p-modal-leave-active .p-modal-panel { transition: transform .34s cubic-bezier(.2, .8, .2, 1), opacity .28s ease; }
.p-modal-enter-from, .p-modal-leave-to { opacity: 0; }
.p-modal-enter-from .p-modal-panel, .p-modal-leave-to .p-modal-panel { transform: translateY(18px) scale(.97); opacity: 0; }
@media (max-width: 620px) {
  .p-modal { padding: 12px; align-items: end; }
  .p-modal-panel { border-radius: 20px; padding: 22px; max-height: 90vh; }
}
@media (prefers-reduced-motion: reduce) {
  .p-modal-enter-active, .p-modal-leave-active,
  .p-modal-enter-active .p-modal-panel, .p-modal-leave-active .p-modal-panel { transition-duration: .01ms; }
}
</style>
