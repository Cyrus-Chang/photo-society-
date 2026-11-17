<script setup lang="ts">
import { ArrowRight, Check } from 'lucide-vue-next'
import BaseModal from './BaseModal.vue'
import { roleLabel } from '../utils/session'

defineProps<{ open: boolean }>()
const emit = defineEmits<{ (event: 'start'): void; (event: 'close'): void }>()
</script>

<template>
  <BaseModal :open="open" labelled-by="start-title" size="md" @close="emit('close')">
    <div class="start">
      <span class="start-eyebrow">ONE MORE STEP</span>
      <h2 id="start-title">资料存好了。<br />现在开始第一场约拍？</h2>
      <p class="start-copy">下一步只需要说清地点、时间和预算，我们会先把对得上条件的作品排给你。</p>

      <ol class="start-steps">
        <li class="is-done">
          <span class="start-step-index">01</span>
          <div><strong>身份与资料</strong><small>{{ roleLabel || '已选择身份' }} · 已完成</small></div>
          <Check :size="15" />
        </li>
        <li>
          <span class="start-step-index">02</span>
          <div><strong>拍摄条件</strong><small>地点 / 日期 / 预算 / 风格</small></div>
        </li>
        <li>
          <span class="start-step-index">03</span>
          <div><strong>先看作品，再约人</strong><small>从真实作品的光线与气质里挑</small></div>
        </li>
      </ol>

      <div class="start-actions">
        <button class="start-ghost" type="button" @click="emit('close')">先自己逛逛</button>
        <button class="start-primary" type="button" @click="emit('start')">开始筛选条件<ArrowRight :size="15" /></button>
      </div>
      <p class="start-note">之后随时能从约拍页的「修改条件」重新打开筛选。</p>
    </div>
  </BaseModal>
</template>

<style scoped>
.start { display: grid; gap: 0; }
.start-eyebrow { font: 9px/1 ui-monospace, SFMono-Regular, Menlo, monospace; letter-spacing: .22em; color: #e98b6b; }
.start h2 { margin: 12px 0 10px; font-family: 'Noto Serif SC', 'Songti SC', serif; font-size: clamp(24px, 3vw, 32px); font-weight: 600; line-height: 1.24; letter-spacing: -.03em; color: #eef2f5; }
.start-copy { margin: 0; color: rgba(238, 242, 245, .56); font-size: 12px; line-height: 1.75; }

.start-steps { display: grid; gap: 0; margin: 20px 0 0; padding: 0; list-style: none; border-top: 1px solid rgba(238, 242, 245, .12); }
.start-steps li { display: grid; grid-template-columns: 24px 1fr 18px; align-items: center; gap: 10px; padding: 11px 0; border-bottom: 1px solid rgba(238, 242, 245, .09); }
.start-step-index { font: 9px/1 ui-monospace, SFMono-Regular, Menlo, monospace; letter-spacing: .06em; color: rgba(238, 242, 245, .34); }
.start-steps li div { display: grid; gap: 2px; }
.start-steps strong { font-size: 12px; font-weight: 500; color: rgba(238, 242, 245, .8); }
.start-steps small { font-size: 10px; color: rgba(238, 242, 245, .4); }
.start-steps .is-done .start-step-index, .start-steps .is-done svg { color: #e9896b; }
.start-steps .is-done strong { color: #eef2f5; }

.start-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }
.start-ghost { min-height: 44px; padding: 0 18px; border-radius: 999px; border: 1px solid rgba(238, 242, 245, .2); background: transparent; color: rgba(238, 242, 245, .72); font-size: 12px; transition: border-color .2s ease, color .2s ease; }
.start-ghost:hover { border-color: rgba(238, 242, 245, .4); color: #eef2f5; }
.start-primary { display: inline-flex; align-items: center; gap: 8px; min-height: 44px; padding: 0 20px; border: 0; border-radius: 999px; background: linear-gradient(135deg, #f2a080, #e98b6b 60%, #d9734f); color: #1b2225; font-size: 12px; font-weight: 700; box-shadow: 0 16px 36px rgba(233, 139, 107, .24); transition: transform .22s ease; }
.start-primary:hover { transform: translateY(-2px); }
.start-note { margin: 12px 0 0; color: rgba(238, 242, 245, .34); font-size: 10px; text-align: center; }

@media (max-width: 620px) {
  .start-actions { flex-direction: column-reverse; }
  .start-primary, .start-ghost { width: 100%; justify-content: center; }
}
@media (prefers-reduced-motion: reduce) {
  .start-primary:hover { transform: none; }
}
</style>
