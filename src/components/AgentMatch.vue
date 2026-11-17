<script setup lang="ts">
/**
 * 撮合 Agent 面板（2026-11-15）
 * 一句话需求 → 后端真调工具（向量检索 + 查档期）→ 候选摄影师。
 * 这里不做任何"看起来像 AI"的假动画：没结果就是没结果，异地就标异地，工具调用可展开核对。
 */
import { computed, ref } from 'vue'
import { AlertTriangle, ChevronDown, LoaderCircle, Sparkles } from 'lucide-vue-next'
import { matchPhotographers, type AgentResult } from '../services/api'
import { resolveWorkImage } from '../utils/media'

const presets = [
  '西安，预算 800，下周末，想要港风街拍',
  '北京，周六，想拍古风汉服，预算 1200',
  '成都周末想拍日系清新，预算 600'
]

const request = ref(presets[0])
const loading = ref(false)
const error = ref('')
const result = ref<AgentResult | null>(null)
const showTrace = ref(false)

const slotChips = computed(() => {
  const slots = result.value?.slots
  if (!slots) return []
  return [
    slots.city || '不限城市',
    slots.when || '时间待定',
    slots.budgetRange?.label || (slots.budget !== undefined && slots.budget !== '' ? `预算 ${slots.budget}` : '预算未说'),
    slots.people ? `${slots.people} 人` : '',
    slots.theme || '',
    ...(slots.styles || [])
  ].filter(Boolean)
})
const traceLine = computed(() => (result.value?.toolTrace || []).map((step) => step.tool).join(' → '))
const plannerLabel = computed(() => {
  const planner = result.value?.planner || result.value?.mode
  return planner === 'llm' ? 'LLM 规划' : '规则规划'
})
const plannerMetric = computed(() => {
  const item = result.value
  if (!item) return ''
  const latency = item.plannerLatencyMs ?? item.plannerStats?.latencyMs
  const success = item.plannerSuccess ?? item.plannerStats?.success
  const suffix = typeof latency === 'number' ? ` · 规划 ${Math.round(latency)}ms` : ''
  return `${plannerLabel.value}${suffix}${success === false ? ' · 失败后已回退' : ''}`
})
const missingFields = computed(() => result.value?.missingFields || [])
const openingLine = computed(() => result.value?.openingLine || result.value?.reply || '')
const communicationPoints = computed(() => result.value?.communicationPoints || [])
const priceReference = computed(() => result.value?.priceReference)

function scoreLabel(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(3) : '—'
}

function availabilityLabel(person: AgentResult['candidates'][number]) {
  if (Array.isArray(person.availability)) return person.availability.join('、') || '需向对方确认'
  return person.availability || person.nextSlot || '需向对方确认'
}

function matchedTags(person: AgentResult['candidates'][number]) {
  return person.matchedTags?.length ? person.matchedTags : person.tags || []
}

function overlapLabel(person: AgentResult['candidates'][number]) {
  if (typeof person.tagOverlap === 'number') return `${person.tagOverlap} 个标签`
  const tags = matchedTags(person)
  return tags.length ? `${tags.length} 个标签` : '—'
}

function availabilityState(person: AgentResult['candidates'][number]) {
  if (person.available === false) return '不可约/待确认'
  return person.available === true ? '可约' : '需确认'
}

async function run() {
  if (loading.value) return
  const text = request.value.trim()
  if (text.length < 4) {
    error.value = '至少写一句想拍什么，例如「西安 周末 港风街拍」'
    return
  }
  loading.value = true
  error.value = ''
  result.value = null
  try {
    result.value = await matchPhotographers(text)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '撮合服务没有响应'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="agent-match">
    <div class="agent-input">
      <label class="agent-label" for="agent-request">一句话说清想拍什么</label>
      <textarea
        id="agent-request"
        v-model="request"
        class="agent-textarea"
        rows="2"
        placeholder="例如：西安，预算 800，下周末，想要港风街拍"
        @keydown.ctrl.enter="run"
      />
      <div class="agent-presets">
        <button v-for="preset in presets" :key="preset" type="button" class="agent-preset" @click="request = preset">
          {{ preset }}
        </button>
      </div>
      <div class="agent-actions">
        <button class="agent-run" type="button" :disabled="loading" @click="run">
          <LoaderCircle v-if="loading" class="spin" :size="16" />
          <Sparkles v-else :size="16" />
          {{ loading ? '正在检索作品并核对档期…' : '让 AI 帮我找人' }}
        </button>
        <small v-if="result" class="agent-meta">{{ plannerMetric }} · 总计 {{ Math.round(result.latencyMs) }}ms</small>
      </div>
    </div>

    <p v-if="error" class="agent-error" role="alert"><AlertTriangle :size="15" />{{ error }}</p>

    <div v-if="result" class="agent-result">
      <div class="agent-slots">
        <span v-for="chip in slotChips" :key="chip" class="agent-slot">{{ chip }}</span>
      </div>
      <p v-if="missingFields.length" class="agent-followup agent-warning" role="status">
        还需要确认：{{ missingFields.join('、') }}。{{ result.reply || '请补充后再继续匹配。' }}
      </p>
      <p v-else class="agent-reply">{{ result.reply }}</p>
      <p v-for="warn in result.warnings" :key="warn" class="agent-warning">
        <AlertTriangle :size="14" />{{ warn }}
      </p>

      <div v-if="priceReference" class="agent-price-reference" style="display:grid;gap:5px;padding:10px 12px;border:1px solid rgba(224,178,92,.3);border-radius:10px;background:rgba(224,178,92,.06);font-size:12px">
        <strong>预算参考</strong>
        <span v-if="priceReference.low !== undefined || priceReference.high !== undefined">
          {{ priceReference.currency || '¥' }}{{ priceReference.low ?? '—' }}—{{ priceReference.high ?? '—' }}
        </span>
        <span>{{ priceReference.source || '来源：集市公开需求' }}</span>
        <small>{{ priceReference.note || '仅作公开需求参考，具体报价与档期需向对方确认。' }}</small>
      </div>

      <div v-if="openingLine || communicationPoints.length" class="agent-communication" style="display:grid;gap:6px;padding:12px;border:1px solid rgba(238,242,245,.1);border-radius:10px;background:rgba(238,242,245,.025);font-size:12px;line-height:1.7">
        <strong>开场话术</strong>
        <p>{{ openingLine || '可先从作品风格、日期和预算向对方确认。' }}</p>
        <template v-if="communicationPoints.length">
          <strong>沟通要点</strong>
          <ul>
            <li v-for="point in communicationPoints" :key="point">{{ point }}</li>
          </ul>
        </template>
      </div>

      <div v-if="result.candidates.length" class="agent-compare" style="overflow-x:auto">
        <table style="width:100%;border-collapse:collapse;min-width:680px;font-size:11px">
          <thead>
            <tr style="text-align:left;color:rgba(238,242,245,.48)">
              <th style="padding:8px">摄影师</th>
              <th style="padding:8px">城市</th>
              <th style="padding:8px">可约时间</th>
              <th style="padding:8px">标签重合</th>
              <th style="padding:8px">向量分</th>
              <th style="padding:8px">状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="person in result.candidates" :key="`compare-${person.photographerId}`" style="border-top:1px solid rgba(238,242,245,.08)">
              <td style="padding:8px;color:rgba(238,242,245,.88)">{{ person.name }}</td>
              <td style="padding:8px">{{ person.city }} · {{ person.crossCity ? '异地' : '同城' }}</td>
              <td style="padding:8px">{{ availabilityLabel(person) }}</td>
              <td style="padding:8px">{{ overlapLabel(person) }}</td>
              <td style="padding:8px">{{ scoreLabel(person.vectorScore ?? person.score) }}</td>
              <td style="padding:8px">{{ availabilityState(person) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <ol v-if="result.candidates.length" class="agent-candidates">
        <li v-for="(person, index) in result.candidates" :key="person.photographerId" class="agent-candidate">
          <div class="agent-candidate-head">
            <span class="agent-rank">{{ String(index + 1).padStart(2, '0') }}</span>
            <div class="agent-candidate-id">
              <strong>{{ person.name }}</strong>
              <small>{{ person.city }} · {{ (person.tags || []).join(' / ') || '标签待补充' }}</small>
            </div>
            <span class="agent-flag" :class="{ 'is-local': !person.crossCity }">{{ person.crossCity ? '异地' : '同城' }}</span>
          </div>

          <div class="agent-works">
            <figure v-for="work in person.works" :key="work.id" class="agent-work">
              <img :src="resolveWorkImage(work.imageUrl)" :alt="work.title" loading="lazy" />
              <figcaption>
                <strong>{{ work.title }}</strong>
                <span>{{ work.reason }}</span>
              </figcaption>
            </figure>
          </div>

          <p class="agent-slot-line">档期：{{ availabilityLabel(person) }} · 回复：{{ person.responseTime || '需向对方确认' }} · 标签重合：{{ matchedTags(person).join(' / ') || '待补充' }}</p>
        </li>
      </ol>

      <button class="agent-trace-toggle" type="button" @click="showTrace = !showTrace">
        <ChevronDown :size="14" :style="{ transform: showTrace ? 'rotate(180deg)' : 'none' }" />
        这次 Agent 调了哪些工具
      </button>
      <pre v-if="showTrace" class="agent-trace">{{ traceLine }}

{{ JSON.stringify(result.toolTrace || [], null, 2) }}</pre>
    </div>
  </section>
</template>
