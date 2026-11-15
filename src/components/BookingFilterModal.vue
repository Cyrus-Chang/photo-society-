<script setup lang="ts">
import { CalendarDays, LoaderCircle, MapPin, Sparkles, Wallet } from 'lucide-vue-next'
import { reactive, ref, watch } from 'vue'
import BaseModal from './BaseModal.vue'
import type { FilterPayload } from '../types'

const props = defineProps<{ open: boolean; initial?: Partial<FilterPayload> }>()
const emit = defineEmits<{ (event: 'close'): void; (event: 'submit', payload: FilterPayload): void }>()

const cities = ['西安', '成都', '青岛', '北京', '上海']
const types = ['人像', '情侣 / 朋友', '旅拍', '活动记录', '主题创作']
const styles = ['夜景', '古风', '胶片', '纪实', '日系', '高饱和']

function tomorrow() {
  const date = new Date()
  date.setDate(date.getDate() + 1)
  return date.toISOString().slice(0, 10)
}

const form = reactive<FilterPayload>({
  date: tomorrow(),
  city: '西安',
  address: '小寨 / 大雁塔',
  budget: 900,
  type: '人像',
  styles: ['夜景'],
  ai: true
})

const submitting = ref(false)

watch(() => props.open, (open) => {
  if (!open) return
  submitting.value = false
  if (props.initial) Object.assign(form, props.initial)
})

function toggleStyle(style: string) {
  const index = form.styles.indexOf(style)
  if (index >= 0) form.styles.splice(index, 1)
  else form.styles.push(style)
}

function submit() {
  if (submitting.value) return
  submitting.value = true
  window.setTimeout(() => {
    submitting.value = false
    emit('submit', { ...form, styles: [...form.styles] })
  }, 720)
}
</script>

<template>
  <BaseModal :open="open" labelled-by="filter-title" size="lg" @close="emit('close')">
    <header class="filter-head">
      <span class="filter-eyebrow">BRIEF / ONE STEP</span>
      <h2 id="filter-title">这次想怎么拍？</h2>
      <p>把地点、时间、预算和风格说清楚，剩下的交给作品。</p>
    </header>

    <form class="filter-grid" @submit.prevent="submit">
      <label class="filter-field">
        <span><CalendarDays :size="13" />拍摄日期</span>
        <input v-model="form.date" type="date" required />
      </label>

      <label class="filter-field">
        <span><MapPin :size="13" />城市</span>
        <select v-model="form.city">
          <option v-for="city in cities" :key="city" :value="city">{{ city }}</option>
        </select>
      </label>

      <label class="filter-field filter-wide">
        <span><MapPin :size="13" />具体地点或集合点</span>
        <input v-model="form.address" placeholder="例如：小寨 / 大雁塔北广场" />
      </label>

      <label class="filter-field">
        <span>拍摄类型</span>
        <select v-model="form.type">
          <option v-for="item in types" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>

      <label class="filter-field filter-wide">
        <span><Wallet :size="13" />预算区间 · ¥ {{ form.budget }}</span>
        <input v-model.number="form.budget" type="range" min="200" max="3000" step="100" />
        <div class="filter-scale"><small>¥ 200</small><small>¥ 3000</small></div>
      </label>

      <fieldset class="filter-field filter-wide filter-styles">
        <legend>想要的风格（可多选）</legend>
        <div class="filter-chips">
          <button v-for="style in styles" :key="style" type="button" :class="{ active: form.styles.includes(style) }" :aria-pressed="form.styles.includes(style)" @click="toggleStyle(style)">{{ style }}</button>
        </div>
      </fieldset>

      <label class="filter-toggle filter-wide">
        <input v-model="form.ai" type="checkbox" />
        <span class="filter-toggle-track"><i /></span>
        <span class="filter-toggle-copy"><strong>接受 AI 推荐</strong><small>在条件之外，参考作品风格给出一小段推荐理由。</small></span>
      </label>

      <div class="filter-actions filter-wide">
        <button class="filter-ghost" type="button" @click="emit('close')">先不筛选</button>
        <button class="filter-submit" type="submit" :disabled="submitting">
          <LoaderCircle v-if="submitting" class="spin" :size="16" />
          <Sparkles v-else :size="16" />
          {{ submitting ? '正在匹配…' : '看看谁刚好有空' }}
        </button>
      </div>
    </form>
  </BaseModal>
</template>

<style scoped>
.filter-head { display: grid; gap: 8px; margin-bottom: 20px; }
.filter-eyebrow { font: 9px/1 ui-monospace, monospace; letter-spacing: .22em; color: #e98b6b; }
.filter-head h2 { margin: 0; font-family: 'Noto Serif SC', 'Songti SC', serif; font-size: clamp(22px, 2.6vw, 30px); font-weight: 600; letter-spacing: -.02em; }
.filter-head p { margin: 0; color: #94a2a8; font-size: 12px; }
.filter-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.filter-wide { grid-column: 1 / -1; }
.filter-field { display: grid; gap: 7px; }
.filter-field > span { display: inline-flex; align-items: center; gap: 6px; color: #8b999f; font-size: 11px; letter-spacing: .02em; }
.filter-field input[type="date"], .filter-field input[type="text"], .filter-field input:not([type]), .filter-field select, .filter-field input[type="range"] {
  width: 100%; min-height: 42px; padding: 0 12px; border-radius: 10px;
  border: 1px solid rgba(237, 241, 244, .14); background: rgba(237, 241, 244, .04);
  color: #eef3f5; font-size: 12px; outline: none;
  transition: border-color .2s ease, background .2s ease;
}
.filter-field input:focus, .filter-field select:focus { border-color: rgba(233, 139, 107, .7); background: rgba(233, 139, 107, .06); }
.filter-field input[type="range"] { padding: 0; min-height: 30px; accent-color: #e98b6b; background: transparent; border: 0; }
.filter-scale { display: flex; justify-content: space-between; color: #6f7d83; font-size: 10px; margin-top: -4px; }
.filter-styles { border: 0; padding: 0; margin: 0; }
.filter-styles legend { color: #8b999f; font-size: 11px; padding: 0 0 7px; }
.filter-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.filter-chips button {
  padding: 7px 13px; border-radius: 999px; border: 1px solid rgba(237, 241, 244, .14);
  background: transparent; color: #b9c4c9; font-size: 11px; cursor: pointer;
  transition: all .22s ease;
}
.filter-chips button:hover { border-color: rgba(233, 139, 107, .5); color: #f3d9cd; }
.filter-chips button.active { border-color: #e98b6b; background: rgba(233, 139, 107, .14); color: #ffd9c9; }
.filter-toggle { display: flex; align-items: flex-start; gap: 12px; cursor: pointer; border-radius: 14px; border: 1px solid rgba(237, 241, 244, .1); padding: 12px; background: rgba(237, 241, 244, .02); }
.filter-toggle input { position: absolute; opacity: 0; pointer-events: none; }
.filter-toggle-track { position: relative; width: 38px; height: 22px; border-radius: 999px; background: rgba(237, 241, 244, .16); flex: 0 0 auto; transition: background .25s ease; }
.filter-toggle-track i { position: absolute; left: 3px; top: 3px; width: 16px; height: 16px; border-radius: 50%; background: #cfd9dd; transition: transform .25s cubic-bezier(.2, .8, .2, 1); }
.filter-toggle input:checked + .filter-toggle-track { background: rgba(233, 139, 107, .85); }
.filter-toggle input:checked + .filter-toggle-track i { transform: translateX(16px); background: #1b2225; }
.filter-toggle-copy { display: grid; gap: 2px; }
.filter-toggle-copy strong { font-size: 12px; }
.filter-toggle-copy small { color: #7f8d93; font-size: 10px; line-height: 1.5; }
.filter-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 6px; }
.filter-ghost { min-height: 44px; padding: 0 18px; border-radius: 999px; border: 1px solid rgba(237, 241, 244, .16); background: transparent; color: #b9c4c9; font-size: 12px; cursor: pointer; }
.filter-ghost:hover { border-color: rgba(237, 241, 244, .3); color: #edf1f4; }
.filter-submit {
  display: inline-flex; align-items: center; gap: 8px; min-height: 44px; padding: 0 20px;
  border: 0; border-radius: 999px; cursor: pointer;
  background: linear-gradient(135deg, #f2a080, #e98b6b 60%, #d9734f);
  color: #1b2225; font-size: 12px; font-weight: 700;
  box-shadow: 0 16px 36px rgba(233, 139, 107, .26);
  transition: transform .22s ease, opacity .22s ease;
}
.filter-submit:hover:not(:disabled) { transform: translateY(-2px); }
.filter-submit:disabled { opacity: .7; cursor: wait; }
@media (max-width: 620px) { .filter-grid { grid-template-columns: 1fr; } }
</style>
