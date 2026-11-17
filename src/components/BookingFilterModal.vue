<script setup lang="ts">
import {
  CalendarDays,
  ChevronDown,
  LoaderCircle,
  MapPin,
  Sparkles,
  Volume2,
  VolumeX,
  Wallet,
  X
} from 'lucide-vue-next'
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import BaseModal from './BaseModal.vue'
import { playPop } from '../utils/popSound'
import type { FilterPayload } from '../types'

const props = defineProps<{ open: boolean; initial?: Partial<FilterPayload> }>()
const emit = defineEmits<{ (event: 'close'): void; (event: 'submit', payload: FilterPayload): void }>()

/* ---------------------------------------------------------------- 选项数据 */

/** 城市 → 默认集合点（只在用户没改过地址时跟着城市切换） */
const CITY_AREAS: Record<string, string> = {
  西安: '小寨 / 大雁塔',
  成都: '玉林 / 东郊记忆',
  青岛: '八大关 / 海边',
  北京: '胡同 / 红墙',
  上海: '外滩 / 武康路',
  杭州: '西湖 / 龙井',
  广州: '东山口 / 沙面',
  深圳: '海边 / 城中村',
  重庆: '洪崖洞 / 山城步道',
  南京: '梧桐道 / 老门东',
  武汉: '江滩 / 昙华林',
  厦门: '鼓浪屿 / 沙坡尾'
}
const cities = Object.keys(CITY_AREAS)

const slots = ['清晨', '上午', '午后', '黄昏', '夜晚']
const types = ['人像', '情侣 / 朋友', '旅拍', '活动记录', '主题创作']

/**
 * 26 个风格：前 6 个是原来就有的，后面 20 个是这次补的。
 * ai=true 的 14 个与 ai-classifier 的 13 类锚图 + 高饱和影调同名，作品库能直接对上；
 * 其余是场景词（模型没有这一层），不要把它们说成「AI 识别」。
 */
const STYLE_LABELS = new Set(['日系', '韩系', 'ins风', '清新', '胶片', '复古', '电影感', '暗调', '黑白', '蓝调', '港风', '赛博', '欧美', '高饱和'])
const styleCatalog = ['夜景', '古风', '胶片', '纪实', '日系', '高饱和', '韩系', 'ins风', '清新', '复古', '电影感', '暗调', '黑白', '蓝调', '港风', '赛博', '欧美', '国风', '街头', '校园', '森系', '甜酷', '极简', '油画', '旅拍', '城市'].map((name) => ({
  name,
  ai: STYLE_LABELS.has(name)
}))

/* ---------------------------------------------------------------- 日期选项 */

const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六']

function isoOf(date: Date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function dayFromNow(offset: number) {
  const date = new Date()
  date.setHours(12, 0, 0, 0)
  date.setDate(date.getDate() + offset)
  return date
}

const dayOptions = Array.from({ length: 14 }, (_, index) => {
  const date = dayFromNow(index)
  return {
    iso: isoOf(date),
    day: date.getDate(),
    month: date.getMonth() + 1,
    weekday: `周${WEEKDAYS[date.getDay()]}`,
    badge: index === 0 ? '今天' : index === 1 ? '明天' : ''
  }
})

/* ---------------------------------------------------------------- 表单状态 */

const form = reactive<FilterPayload>({
  date: isoOf(dayFromNow(1)),
  slot: '黄昏',
  city: '西安',
  address: CITY_AREAS['西安'],
  budgetMin: 0,
  budgetMax: 900,
  type: '人像',
  styles: ['夜景'],
  ai: true
})

const submitting = ref(false)
const customDate = ref(false)
const customDateInput = ref<HTMLInputElement | null>(null)

const dateLabel = computed(() => {
  const preset = dayOptions.find((day) => day.iso === form.date)
  if (preset) return `${preset.month} 月 ${preset.day} 日 · ${preset.badge || preset.weekday}`
  const parts = form.date.split('-')
  return parts.length === 3 ? `${Number(parts[1])} 月 ${Number(parts[2])} 日` : form.date
})

function pickDate(iso: string) {
  form.date = iso
  customDate.value = false
}

async function toggleCustomDate() {
  customDate.value = !customDate.value
  if (!customDate.value) return
  await nextTick()
  customDateInput.value?.focus()
}

/* ---------------------------------------------------------------- 城市选择器 */

const cityOpen = ref(false)
const cityWrap = ref<HTMLElement | null>(null)
const cityTrigger = ref<HTMLButtonElement | null>(null)
const cityList = ref<HTMLElement | null>(null)

function cityOptions() {
  return Array.from(cityList.value?.querySelectorAll<HTMLButtonElement>('button[role="option"]') ?? [])
}

async function toggleCity() {
  if (cityOpen.value) {
    cityOpen.value = false
    return
  }
  cityOpen.value = true
  await nextTick()
  const options = cityOptions()
  const active = options.find((option) => option.classList.contains('active'))
  ;(active ?? options[0])?.focus()
}

function closeCity(refocus = false) {
  cityOpen.value = false
  if (refocus) cityTrigger.value?.focus()
}

function pickCity(name: string) {
  const previousDefault = CITY_AREAS[form.city] ?? ''
  if (!form.address.trim() || form.address === previousDefault) form.address = CITY_AREAS[name] ?? ''
  form.city = name
  closeCity(true)
}

function onCityKey(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    event.preventDefault()
    closeCity(true)
    return
  }
  if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp' && event.key !== 'Home' && event.key !== 'End') return
  const options = cityOptions()
  if (!options.length) return
  event.preventDefault()
  const current = options.indexOf(document.activeElement as HTMLButtonElement)
  let next = current
  if (event.key === 'ArrowDown') next = (current + 1) % options.length
  if (event.key === 'ArrowUp') next = (current - 1 + options.length) % options.length
  if (event.key === 'Home') next = 0
  if (event.key === 'End') next = options.length - 1
  options[next]?.focus()
}

function onDocumentPointer(event: PointerEvent) {
  if (!cityOpen.value) return
  if (!cityWrap.value?.contains(event.target as Node)) cityOpen.value = false
}

function onCityBlur(event: FocusEvent) {
  const next = event.relatedTarget as Node | null
  if (next && cityWrap.value?.contains(next)) return
  cityOpen.value = false
}

/* ---------------------------------------------------------------- 预算双轨 */

const BUDGET_MIN = 0
const BUDGET_MAX = 3000
const BUDGET_STEP = 50

const budgetPresets = [
  { label: '不限', min: 0, max: 3000 },
  { label: '¥ 800 内', min: 0, max: 800 },
  { label: '¥ 800–1500', min: 800, max: 1500 },
  { label: '¥ 1500 起', min: 1500, max: 3000 }
]

const budgetMin = computed({
  get: () => form.budgetMin,
  set: (value: number) => {
    form.budgetMin = Math.max(BUDGET_MIN, Math.min(Number(value) || 0, form.budgetMax))
  }
})
const budgetMax = computed({
  get: () => form.budgetMax,
  set: (value: number) => {
    form.budgetMax = Math.min(BUDGET_MAX, Math.max(Number(value) || 0, form.budgetMin))
  }
})

const budgetFill = computed(() => ({
  left: `${(form.budgetMin / BUDGET_MAX) * 100}%`,
  width: `${((form.budgetMax - form.budgetMin) / BUDGET_MAX) * 100}%`
}))
const budgetTicks = [0, 500, 1000, 1500, 2000, 2500, 3000]
const minThumbZ = computed(() => (form.budgetMax - form.budgetMin < 300 ? 6 : 3))

function setBudgetRange(range: { min: number; max: number }) {
  form.budgetMin = range.min
  form.budgetMax = range.max
}

function onRailClick(event: MouseEvent) {
  const target = event.currentTarget as HTMLElement
  const rect = target.getBoundingClientRect()
  if (!rect.width) return
  const ratio = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width))
  const value = Math.round((ratio * BUDGET_MAX) / BUDGET_STEP) * BUDGET_STEP
  const toMin = Math.abs(value - form.budgetMin)
  const toMax = Math.abs(value - form.budgetMax)
  if (toMin < toMax) budgetMin.value = value
  else budgetMax.value = value
}

/* ---------------------------------------------------------------- 风格泡泡 */

const SOUND_KEY = 'paishe.filter.sound.v1'
const soundOn = ref(true)
const bursts = ref<Array<{ id: number; x: number; y: number; size: number }>>([])
let burstId = 0
if (typeof window !== 'undefined') {
  try {
    if (window.localStorage.getItem(SOUND_KEY) === '0') soundOn.value = false
  } catch {
    /* 隐私模式下读不到就保持默认开启 */
  }
}

function toggleSound() {
  soundOn.value = !soundOn.value
  try {
    window.localStorage.setItem(SOUND_KEY, soundOn.value ? '1' : '0')
  } catch {
    /* 写不进去只影响下次打开 */
  }
  if (soundOn.value) playPop(true, 2)
}

function bubbleStyle(index: number, name: string): Record<string, string> {
  const three = name.length >= 3
  const size = three ? 74 : [68, 62, 66][index % 3]
  const offset = ((index * 7) % 9) - 4
  return {
    '--bubble-size': `${size}px`,
    '--bubble-offset': `${offset}px`,
    '--bubble-dur': `${(5.4 + (index % 6) * 0.62).toFixed(2)}s`,
    '--bubble-delay': `${(-((index % 7) * 0.57)).toFixed(2)}s`,
    '--bubble-lift': `${(-(3 + (index % 4) * 1.4)).toFixed(1)}px`,
    '--bubble-drift': `${index % 2 === 0 ? 2.4 : -2.4}px`,
    fontSize: three ? '11px' : '12.5px'
  }
}

function toggleStyle(name: string, index: number, event: MouseEvent) {
  const existing = form.styles.indexOf(name)
  if (existing >= 0) form.styles.splice(existing, 1)
  else form.styles.push(name)

  const target = event.currentTarget as HTMLElement | null
  const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  if (target && !reduce) {
    target.animate(
      [
        { transform: 'scale(1)' },
        { transform: 'scale(1.16)', offset: 0.28 },
        { transform: 'scale(0.94)', offset: 0.62 },
        { transform: 'scale(1)' }
      ],
      { duration: 440, easing: 'cubic-bezier(.22,.9,.28,1.25)' }
    )
    const cloud = target.closest('.bubble-cloud') as HTMLElement | null
    if (cloud) {
      const bubbleRect = target.getBoundingClientRect()
      const cloudRect = cloud.getBoundingClientRect()
      const id = ++burstId
      bursts.value.push({
        id,
        x: bubbleRect.left - cloudRect.left,
        y: bubbleRect.top - cloudRect.top,
        size: bubbleRect.width
      })
      window.setTimeout(() => {
        bursts.value = bursts.value.filter((burst) => burst.id !== id)
      }, 520)
    }
  }

  playPop(soundOn.value, index, existing >= 0)
}

function clearStyles() {
  form.styles.splice(0, form.styles.length)
}

/* ---------------------------------------------------------------- 提交 */

let popTimer = 0

watch(() => props.open, (open) => {
  cityOpen.value = false
  customDate.value = false
  if (!open) return
  submitting.value = false
  if (props.initial) Object.assign(form, props.initial)
})

onMounted(() => document.addEventListener('pointerdown', onDocumentPointer))
onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onDocumentPointer)
  window.clearTimeout(popTimer)
})

function submit() {
  if (submitting.value) return
  submitting.value = true
  popTimer = window.setTimeout(() => {
    submitting.value = false
    emit('submit', { ...form, styles: [...form.styles] })
  }, 720)
}
</script>

<template>
  <BaseModal :open="open" labelled-by="filter-title" size="xl" @close="emit('close')">
    <div class="brief">
      <header class="brief-head">
        <span class="brief-eyebrow">BRIEF / ONE STEP</span>
        <h2 id="filter-title">这次想怎么拍？</h2>
        <p>把地点、时间、预算和风格说清楚，剩下的交给作品。</p>
      </header>

      <form class="brief-form" @submit.prevent="submit">
        <div class="brief-body">
          <div class="brief-col">
            <section class="brief-sec">
              <div class="brief-sec-head">
                <span class="brief-index">01</span>
                <h3><CalendarDays :size="12" />日期与时段</h3>
                <span class="brief-current">{{ dateLabel }}</span>
                <button class="brief-link" type="button" @click="toggleCustomDate">{{ customDate ? '收起' : '其他日期' }}</button>
              </div>
              <div class="date-grid" role="group" aria-label="拍摄日期">
                <button
                  v-for="day in dayOptions"
                  :key="day.iso"
                  type="button"
                  class="date-chip"
                  :class="{ active: form.date === day.iso }"
                  :aria-pressed="form.date === day.iso"
                  @click="pickDate(day.iso)"
                >
                  <small>{{ day.badge || day.weekday }}</small>
                  <strong>{{ day.day }}</strong>
                </button>
              </div>
              <div v-if="customDate" class="date-custom">
                <CalendarDays :size="14" />
                <input ref="customDateInput" v-model="form.date" type="date" :min="dayOptions[0].iso" aria-label="指定拍摄日期" />
              </div>
              <div class="slot-row" role="group" aria-label="拍摄时段">
                <button
                  v-for="slot in slots"
                  :key="slot"
                  type="button"
                  class="slot-chip"
                  :class="{ active: form.slot === slot }"
                  :aria-pressed="form.slot === slot"
                  @click="form.slot = slot"
                >{{ slot }}</button>
              </div>
            </section>

            <section class="brief-sec">
              <div class="brief-sec-head">
                <span class="brief-index">02</span>
                <h3><MapPin :size="12" />城市与集合点</h3>
              </div>
              <div class="place-row">
                <div ref="cityWrap" class="city-picker">
                  <button
                    ref="cityTrigger"
                    class="city-trigger"
                    type="button"
                    aria-haspopup="listbox"
                    :aria-expanded="cityOpen"
                    @click="toggleCity"
                    @keydown.esc.prevent="closeCity(true)"
                  >
                    <MapPin :size="14" />
                    <span>{{ form.city }}</span>
                    <ChevronDown class="city-chev" :class="{ open: cityOpen }" :size="14" />
                  </button>
                  <Transition name="city-pop">
                    <div v-if="cityOpen" ref="cityList" class="city-pop" role="listbox" aria-label="选择城市" @keydown="onCityKey" @focusout="onCityBlur">
                      <button
                        v-for="city in cities"
                        :key="city"
                        type="button"
                        role="option"
                        :aria-selected="form.city === city"
                        :class="{ active: form.city === city }"
                        @click="pickCity(city)"
                      >{{ city }}</button>
                    </div>
                  </Transition>
                </div>
                <label class="place-input">
                  <span class="sr-only">具体地点或集合点</span>
                  <input v-model="form.address" type="text" placeholder="具体地点 / 集合点" />
                </label>
              </div>
            </section>

            <section class="brief-sec">
              <div class="brief-sec-head">
                <span class="brief-index">03</span>
                <h3><Wallet :size="12" />预算区间</h3>
                <span class="brief-current">拖两端 · 最低 ¥0</span>
              </div>
              <div class="budget-presets" role="group" aria-label="预算快捷选择">
                <button
                  v-for="preset in budgetPresets"
                  :key="preset.label"
                  type="button"
                  :class="{ active: form.budgetMin === preset.min && form.budgetMax === preset.max }"
                  @click="setBudgetRange(preset)"
                >{{ preset.label }}</button>
              </div>
              <div class="range-wrap">
                <div class="range-track" @click="onRailClick">
                  <span class="range-rail" />
                  <span class="range-fill" :style="budgetFill" />
                  <i v-for="tick in budgetTicks" :key="tick" class="range-tick" :style="{ left: `${(tick / BUDGET_MAX) * 100}%` }" />
                  <input
                    v-model.number="budgetMin"
                    class="range-input"
                    type="range"
                    :min="BUDGET_MIN"
                    :max="BUDGET_MAX"
                    :step="BUDGET_STEP"
                    aria-label="最低预算"
                    :aria-valuetext="`${form.budgetMin} 元`"
                    :style="{ zIndex: minThumbZ }"
                  />
                  <input
                    v-model.number="budgetMax"
                    class="range-input"
                    type="range"
                    :min="BUDGET_MIN"
                    :max="BUDGET_MAX"
                    :step="BUDGET_STEP"
                    aria-label="最高预算"
                    :aria-valuetext="`${form.budgetMax} 元`"
                  />
                </div>
                <div class="range-readout">
                  <span><small>最低</small><b>¥ {{ form.budgetMin }}</b></span>
                  <i class="range-dash" />
                  <span><small>最高</small><b>¥ {{ form.budgetMax }}</b></span>
                </div>
              </div>
            </section>

            <section class="brief-sec">
              <div class="brief-sec-head">
                <span class="brief-index">04</span>
                <h3>拍摄类型</h3>
              </div>
              <div class="type-chips" role="group" aria-label="拍摄类型">
                <button
                  v-for="item in types"
                  :key="item"
                  type="button"
                  :class="{ active: form.type === item }"
                  :aria-pressed="form.type === item"
                  @click="form.type = item"
                >{{ item }}</button>
              </div>
            </section>
          </div>

          <section class="brief-col brief-styles">
            <div class="brief-sec-head">
              <span class="brief-index">05</span>
              <h3><Sparkles :size="12" />想要的风格</h3>
              <span class="brief-current">{{ form.styles.length }} / {{ styleCatalog.length }}</span>
              <button class="sound-toggle" type="button" :aria-pressed="soundOn" :aria-label="soundOn ? '关闭泡泡音效' : '开启泡泡音效'" @click="toggleSound">
                <Volume2 v-if="soundOn" :size="13" />
                <VolumeX v-else :size="13" />
                {{ soundOn ? '啵啵开' : '静音' }}
              </button>
            </div>

            <div class="bubble-field">
              <span class="bubble-orbit" aria-hidden="true" />
              <div class="bubble-cloud" role="group" aria-label="风格，可多选">
                <button
                  v-for="(item, index) in styleCatalog"
                  :key="item.name"
                  type="button"
                  class="style-bubble"
                  :class="{ active: form.styles.includes(item.name) }"
                  :style="bubbleStyle(index, item.name)"
                  :aria-pressed="form.styles.includes(item.name)"
                  :data-ai="item.ai || undefined"
                  @click="toggleStyle(item.name, index, $event)"
                >
                  <span>{{ item.name }}</span>
                </button>
                <span
                  v-for="burst in bursts"
                  :key="burst.id"
                  class="bubble-burst"
                  :style="{ left: `${burst.x}px`, top: `${burst.y}px`, width: `${burst.size}px`, height: `${burst.size}px` }"
                  aria-hidden="true"
                />
              </div>
            </div>

            <div class="bubble-foot">
              <span class="bubble-legend"><i />带点 · AI 可识别</span>
              <button v-if="form.styles.length" class="brief-link" type="button" @click="clearStyles">清空</button>
            </div>

            <label class="brief-ai">
              <input v-model="form.ai" type="checkbox" />
              <span class="brief-ai-track"><i /></span>
              <span class="brief-ai-copy">
                <strong>接受 AI 推荐</strong>
                <small>在条件之外，参考作品风格给出一小段推荐理由。</small>
              </span>
            </label>
          </section>
        </div>

        <div class="brief-actions">
          <div class="brief-summary">
            <span>{{ dateLabel }}</span>
            <span v-if="form.slot">· {{ form.slot }}</span>
            <span v-if="form.styles.length">· {{ form.styles.length }} 个风格</span>
          </div>
          <button class="brief-ghost" type="button" @click="emit('close')">先不筛选</button>
          <button class="brief-submit" type="submit" :disabled="submitting">
            <LoaderCircle v-if="submitting" class="spin" :size="16" />
            <Sparkles v-else :size="16" />
            {{ submitting ? '正在匹配…' : '看看谁刚好有空' }}
          </button>
        </div>
      </form>
      <button class="brief-close" type="button" aria-label="关闭筛选" @click="emit('close')">
        <X :size="16" />
      </button>
    </div>
  </BaseModal>
</template>

<style scoped>
.brief {
  --b-ink: #eef2f5;
  --b-ink-2: rgba(238, 242, 245, .78);
  --b-ink-3: rgba(238, 242, 245, .56);
  --b-line: rgba(238, 242, 245, .12);
  --b-line-2: rgba(238, 242, 245, .24);
  --b-coral: #e9896b;
  --b-coral-2: #f4a688;
  --b-mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  position: relative;
  color: var(--b-ink);
}

.brief-close {
  position: absolute;
  top: -14px;
  right: -16px;
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  padding: 0;
  border-radius: 50%;
  border: 1px solid transparent;
  background: transparent;
  color: var(--b-ink-3);
  transition: color .18s ease, background .18s ease, border-color .18s ease;
}
.brief-close:hover { color: var(--b-ink); background: rgba(238, 242, 245, .06); border-color: var(--b-line); }

.brief-head { display: grid; gap: 8px; padding-right: 36px; }
.brief-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font: 9px/1 var(--b-mono);
  letter-spacing: .22em;
  color: var(--b-coral);
}
.brief-head h2 {
  margin: 0;
  font-family: 'Noto Serif SC', 'Songti SC', serif;
  font-size: clamp(23px, 2.4vw, 31px);
  font-weight: 600;
  letter-spacing: -.03em;
  line-height: 1.16;
}
.brief-head p { margin: 0; color: var(--b-ink-3); font-size: 12px; line-height: 1.7; }

.brief-form { display: block; }
.brief-body {
  display: grid;
  grid-template-columns: minmax(0, 380px) minmax(0, 1fr);
  gap: 24px;
  margin-top: 18px;
}
.brief-col { display: grid; align-content: start; gap: 14px; min-width: 0; }

.brief-sec { padding-top: 12px; border-top: 1px solid var(--b-line); min-width: 0; }
.brief-body > .brief-col > .brief-sec:first-child { padding-top: 0; border-top: 0; }

.brief-sec-head { display: flex; align-items: center; gap: 7px; min-height: 22px; margin-bottom: 9px; }
.brief-index { font: 9.5px/1 var(--b-mono); letter-spacing: .08em; color: var(--b-coral); opacity: .9; }
.brief-sec-head h3 {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin: 0;
  font-size: 11.5px;
  font-weight: 500;
  letter-spacing: .04em;
  color: var(--b-ink-2);
}
.brief-sec-head h3 svg { color: var(--b-ink-3); }
.brief-current { margin-left: auto; font: 9.5px/1 var(--b-mono); letter-spacing: .04em; color: var(--b-ink-3); white-space: nowrap; }
.brief-link {
  min-height: 32px;
  padding: 0 2px;
  border: 0;
  background: transparent;
  color: var(--b-coral-2);
  font-size: 10.5px;
  border-bottom: 1px solid rgba(244, 166, 136, .35);
  transition: color .18s ease, border-color .18s ease;
}
.brief-link:hover { color: #ffd9c9; border-color: #ffd9c9; }

/* 日期 */
.date-grid { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 5px; }
.date-chip {
  display: grid;
  place-items: center;
  align-content: center;
  gap: 1px;
  min-height: 48px;
  padding: 4px 0;
  border-radius: 9px;
  border: 1px solid var(--b-line);
  background: rgba(238, 242, 245, .025);
  color: var(--b-ink-2);
  transition: border-color .18s ease, background .18s ease, color .18s ease, transform .18s ease;
}
.date-chip small { font-size: 9px; line-height: 1.2; color: var(--b-ink-3); letter-spacing: .02em; }
.date-chip strong { font: 500 15px/1.2 var(--b-mono); letter-spacing: .01em; }
.date-chip:hover { border-color: var(--b-line-2); color: var(--b-ink); transform: translateY(-1px); }
.date-chip.active { border-color: rgba(233, 139, 107, .8); background: rgba(233, 139, 107, .15); color: #ffd9c9; }
.date-chip.active small { color: rgba(255, 217, 201, .78); }

.date-custom { display: flex; align-items: center; gap: 8px; margin-top: 7px; padding: 0 10px; border: 1px solid var(--b-line); border-radius: 9px; background: rgba(238, 242, 245, .025); color: var(--b-ink-3); }
.date-custom input {
  flex: 1;
  min-width: 0;
  height: 40px;
  border: 0;
  background: transparent;
  color: var(--b-ink);
  font-size: 12px;
  outline: none;
  color-scheme: dark;
}

.slot-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.slot-chip,
.type-chips button,
.budget-presets button {
  min-height: 44px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid var(--b-line);
  background: transparent;
  color: var(--b-ink-3);
  font-size: 10.5px;
  letter-spacing: .02em;
  transition: border-color .18s ease, background .18s ease, color .18s ease;
}
.slot-chip:hover,
.type-chips button:hover,
.budget-presets button:hover { border-color: rgba(233, 139, 107, .45); color: #f3d9cd; }
.slot-chip.active,
.type-chips button.active,
.budget-presets button.active { border-color: rgba(233, 139, 107, .72); background: rgba(233, 139, 107, .14); color: #ffd9c9; }

/* 城市 + 地址 */
.place-row { display: flex; gap: 8px; align-items: stretch; }
.city-picker { position: relative; flex: 0 0 136px; }
.city-trigger {
  display: flex;
  align-items: center;
  gap: 7px;
  width: 100%;
  min-height: 42px;
  padding: 0 11px;
  border-radius: 9px;
  border: 1px solid var(--b-line);
  background: rgba(238, 242, 245, .025);
  color: var(--b-ink);
  font-size: 12px;
  transition: border-color .18s ease, background .18s ease;
}
.city-trigger:hover,
.city-trigger[aria-expanded="true"] { border-color: rgba(233, 139, 107, .6); background: rgba(233, 139, 107, .06); }
.city-trigger > span { flex: 1; text-align: left; }
.city-trigger > svg:first-child { color: var(--b-coral-2); }
.city-chev { color: var(--b-ink-3); transition: transform .2s ease; }
.city-chev.open { transform: rotate(180deg); }

.city-pop {
  position: absolute;
  z-index: 24;
  top: calc(100% + 6px);
  left: 0;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 5px;
  width: 306px;
  padding: 9px;
  border-radius: 14px;
  border: 1px solid var(--b-line-2);
  background: #12191f;
  box-shadow: 0 26px 60px rgba(0, 0, 0, .6), inset 0 1px 0 rgba(255, 255, 255, .05);
}
.city-pop button {
  min-height: 40px;
  padding: 0 6px;
  border-radius: 8px;
  border: 1px solid transparent;
  background: rgba(238, 242, 245, .03);
  color: var(--b-ink-2);
  font-size: 11.5px;
  transition: border-color .15s ease, background .15s ease, color .15s ease;
}
.city-pop button:hover { border-color: var(--b-line-2); color: var(--b-ink); }
.city-pop button.active { border-color: rgba(233, 139, 107, .7); background: rgba(233, 139, 107, .16); color: #ffd9c9; }
.city-pop-enter-active,
.city-pop-leave-active { transition: opacity .16s ease, transform .18s ease; }
.city-pop-enter-from,
.city-pop-leave-to { opacity: 0; transform: translateY(-4px); }

.place-input {
  flex: 1;
  display: flex;
  align-items: center;
  min-width: 0;
  padding: 0 12px;
  border-radius: 9px;
  border: 1px solid var(--b-line);
  background: rgba(238, 242, 245, .025);
  transition: border-color .18s ease, background .18s ease;
}
.place-input:focus-within { border-color: rgba(233, 139, 107, .62); background: rgba(233, 139, 107, .05); }
.place-input input {
  width: 100%;
  min-width: 0;
  height: 40px;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--b-ink);
  font-size: 12px;
  outline: none;
}
.place-input input::placeholder { color: rgba(238, 242, 245, .46); }

/* 预算 */
.budget-presets { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 5px; }
.budget-presets button { padding: 0 4px; font-size: 9.5px; white-space: nowrap; }

.range-wrap { margin-top: 8px; }
.range-track {
  position: relative;
  display: flex;
  align-items: center;
  height: 44px;
  cursor: pointer;
  touch-action: none;
}
.range-rail {
  position: absolute;
  left: 0;
  right: 0;
  height: 4px;
  border-radius: 999px;
  background: rgba(238, 242, 245, .13);
}
.range-fill {
  position: absolute;
  height: 4px;
  border-radius: 999px;
  background: linear-gradient(90deg, #f4a688, #e9896b);
  box-shadow: 0 0 16px rgba(233, 139, 107, .32);
}
.range-tick {
  position: absolute;
  top: 50%;
  width: 1px;
  height: 8px;
  margin-top: -4px;
  background: rgba(238, 242, 245, .13);
}
.range-input {
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 44px;
  margin: 0;
  padding: 0;
  border: 0;
  background: transparent;
  appearance: none;
  -webkit-appearance: none;
  pointer-events: none;
  outline: none;
}
.range-input::-webkit-slider-runnable-track { height: 4px; background: transparent; }
.range-input::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  margin-top: -7px;
  border-radius: 50%;
  border: 3px solid #0c1116;
  background: #f6f1ec;
  box-shadow: 0 0 0 1px rgba(238, 242, 245, .5), 0 6px 14px rgba(0, 0, 0, .5);
  pointer-events: auto;
  cursor: grab;
  transition: transform .15s ease, box-shadow .15s ease;
}
.range-input:active::-webkit-slider-thumb { cursor: grabbing; transform: scale(1.12); }
.range-input:focus-visible::-webkit-slider-thumb { box-shadow: 0 0 0 3px rgba(233, 139, 107, .5), 0 6px 14px rgba(0, 0, 0, .5); }
.range-input::-moz-range-track { height: 4px; background: transparent; }
.range-input::-moz-range-thumb {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 3px solid #0c1116;
  background: #f6f1ec;
  box-shadow: 0 0 0 1px rgba(238, 242, 245, .5);
  pointer-events: auto;
  cursor: grab;
}
.range-input:focus-visible::-moz-range-thumb { box-shadow: 0 0 0 3px rgba(233, 139, 107, .5); }

.range-readout { display: flex; align-items: baseline; gap: 10px; margin-top: -2px; }
.range-readout span { display: inline-flex; align-items: baseline; gap: 6px; }
.range-readout small { font-size: 9px; letter-spacing: .08em; color: var(--b-ink-3); }
.range-readout b { font: 500 15px/1 var(--b-mono); letter-spacing: .01em; color: var(--b-ink); }
.range-dash { flex: 1; height: 1px; background: repeating-linear-gradient(90deg, var(--b-line) 0 5px, transparent 5px 9px); }

.type-chips { display: flex; flex-wrap: wrap; gap: 6px; }

/* 风格泡泡 */
.brief-styles { min-width: 0; }
.bubble-field {
  position: relative;
  margin-top: 2px;
  padding: 18px 14px;
  border-radius: 20px;
  border: 1px solid var(--b-line);
  background:
    radial-gradient(72% 62% at 50% 0%, rgba(233, 139, 107, .07), transparent 66%),
    linear-gradient(180deg, rgba(238, 242, 245, .032), rgba(238, 242, 245, .008));
  overflow: hidden;
}
.bubble-orbit {
  position: absolute;
  left: 50%;
  top: 52%;
  width: 300px;
  height: 300px;
  margin: -150px 0 0 -150px;
  border: 1px dashed rgba(238, 242, 245, .09);
  border-radius: 50%;
  pointer-events: none;
}
.bubble-cloud {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 9px 8px;
}
.style-bubble {
  position: relative;
  display: grid;
  place-items: center;
  width: var(--bubble-size);
  height: var(--bubble-size);
  padding: 0;
  border-radius: 50%;
  border: 1px solid rgba(238, 242, 245, .16);
  background:
    radial-gradient(circle at 30% 20%, rgba(255, 255, 255, .38) 0 2%, rgba(255, 255, 255, .16) 7%, rgba(255, 255, 255, .03) 16%, transparent 32%),
    radial-gradient(circle at 72% 84%, rgba(157, 183, 198, .18), transparent 48%),
    conic-gradient(from 200deg, rgba(233, 139, 107, .17), rgba(143, 201, 168, .07), rgba(157, 183, 198, .18), rgba(233, 139, 107, .17));
  color: var(--b-ink-2);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, .22),
    inset 0 -9px 16px rgba(0, 0, 0, .18),
    inset -2px -2px 7px rgba(157, 183, 198, .12),
    0 10px 22px rgba(0, 0, 0, .24);
  margin-top: var(--bubble-offset, 0);
  animation: bubble-float var(--bubble-dur, 7s) ease-in-out var(--bubble-delay, 0s) infinite alternate;
  will-change: transform;
  transition: color .2s ease, border-color .2s ease, background .2s ease, box-shadow .25s ease;
}
.style-bubble span { position: relative; z-index: 1; white-space: nowrap; line-height: 1; }
.style-bubble:hover { color: #fff; border-color: rgba(244, 166, 136, .5); }
.style-bubble.active {
  border-color: transparent;
  color: #22120c;
  background: radial-gradient(circle at 32% 24%, #ffd6c4 0%, #ef9a78 42%, #c9603c 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .42), 0 0 0 4px rgba(233, 139, 107, .12), 0 16px 30px rgba(233, 139, 107, .2);
}
.style-bubble[data-ai]::before {
  content: '';
  position: absolute;
  top: 10px;
  right: 14px;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--b-coral-2);
  opacity: .9;
}
.style-bubble.active[data-ai]::before { background: rgba(34, 18, 12, .55); }
.bubble-burst {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(244, 166, 136, .85);
  pointer-events: none;
  animation: bubble-ring .5s ease-out forwards;
}

.bubble-foot { display: flex; align-items: center; gap: 10px; margin-top: 8px; min-height: 30px; }
.bubble-legend { display: inline-flex; align-items: center; gap: 6px; font-size: 9px; letter-spacing: .06em; color: var(--b-ink-3); }
.bubble-legend i { width: 4px; height: 4px; border-radius: 50%; background: var(--b-coral-2); }
.bubble-foot .brief-link { margin-left: auto; }

.brief-ai {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--b-line);
  background: rgba(238, 242, 245, .02);
  cursor: pointer;
}
.brief-ai input { position: absolute; opacity: 0; pointer-events: none; }
.brief-ai-track { position: relative; flex: 0 0 auto; width: 34px; height: 20px; margin-top: 2px; border-radius: 999px; background: rgba(238, 242, 245, .16); transition: background .25s ease; }
.brief-ai-track i { position: absolute; left: 3px; top: 3px; width: 14px; height: 14px; border-radius: 50%; background: #cfd9dd; transition: transform .25s cubic-bezier(.2, .8, .2, 1); }
.brief-ai input:checked + .brief-ai-track { background: rgba(233, 139, 107, .85); }
.brief-ai input:checked + .brief-ai-track i { transform: translateX(14px); background: #1b2225; }
.brief-ai input:focus-visible + .brief-ai-track { outline: 2px solid var(--b-coral); outline-offset: 3px; }
.brief-ai-copy { display: grid; gap: 2px; }
.brief-ai-copy strong { font-size: 11.5px; font-weight: 600; }
.brief-ai-copy small { color: var(--b-ink-3); font-size: 9.5px; line-height: 1.5; }

.sound-toggle {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-height: 32px;
  padding: 0 9px;
  margin-left: 2px;
  border-radius: 999px;
  border: 1px solid var(--b-line);
  background: transparent;
  color: var(--b-ink-3);
  font-size: 9.5px;
  transition: color .18s ease, border-color .18s ease, background .18s ease;
}
.sound-toggle:hover { color: #ffd9c9; border-color: rgba(233, 139, 107, .45); }
.sound-toggle[aria-pressed="true"] { color: var(--b-coral-2); border-color: rgba(233, 139, 107, .32); background: rgba(233, 139, 107, .08); }

/* 底栏 */
.brief-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 16px;
  padding-top: 15px;
  border-top: 1px solid var(--b-line);
}
.brief-summary { display: flex; flex-wrap: wrap; gap: 4px 6px; margin-right: auto; font: 9.5px/1.5 var(--b-mono); letter-spacing: .04em; color: var(--b-ink-3); }
.brief-ghost {
  min-height: 44px;
  padding: 0 18px;
  border-radius: 999px;
  border: 1px solid var(--b-line-2);
  background: transparent;
  color: var(--b-ink-2);
  font-size: 12px;
  transition: border-color .18s ease, color .18s ease;
}
.brief-ghost:hover { border-color: rgba(238, 242, 245, .4); color: var(--b-ink); }
.brief-submit {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 44px;
  padding: 0 20px;
  border: 0;
  border-radius: 999px;
  background: linear-gradient(135deg, #f2a080, #e98b6b 60%, #d9734f);
  color: #1b2225;
  font-size: 12px;
  font-weight: 700;
  box-shadow: 0 16px 36px rgba(233, 139, 107, .24);
  transition: transform .22s ease, opacity .22s ease;
}
.brief-submit:hover:not(:disabled) { transform: translateY(-2px); }
.brief-submit:disabled { opacity: .7; cursor: wait; }

@keyframes bubble-float {
  from { transform: translate3d(0, 0, 0); }
  to { transform: translate3d(var(--bubble-drift, 2px), var(--bubble-lift, -4px), 0); }
}
@keyframes bubble-ring {
  from { transform: scale(.94); opacity: .8; }
  to { transform: scale(1.55); opacity: 0; }
}

@media (max-width: 860px) {
  .brief-body { grid-template-columns: 1fr; gap: 18px; }
  .brief-styles { order: 2; }
  .bubble-field { padding: 16px 12px; }
  .city-pop { width: min(306px, calc(100vw - 96px)); }
}

@media (max-width: 620px) {
  .brief-close { top: -8px; right: -6px; }
  .brief-head h2 { font-size: 23px; }
  .date-grid { gap: 4px; }
  .date-chip { min-height: 48px; }
  .date-chip strong { font-size: 14px; }
  .style-bubble { width: calc(var(--bubble-size) * .82); height: calc(var(--bubble-size) * .82); }
  .style-bubble[data-ai]::before { top: 8px; right: 10px; }
  .brief-actions { flex-wrap: wrap; }
  .brief-summary { width: 100%; }
  .brief-submit { flex: 1; }
  .place-row { flex-wrap: wrap; }
  .city-picker { flex: 1 1 100%; }
  .city-pop { width: 100%; }
  .budget-presets button { font-size: 9px; }
}

@media (prefers-reduced-motion: reduce) {
  .style-bubble { animation: none; }
  .bubble-burst { display: none; }
  .date-chip:hover { transform: none; }
}
</style>
