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
    slots.budget ? `预算 ${slots.budget}` : '预算未说',
    ...(slots.styles || [])
  ]
})
const traceLine = computed(() => (result.value?.toolTrace || []).map((step) => step.tool).join(' → '))
const modeLabel = computed(() => (result.value?.mode === 'rule' ? '规则撮合' : 'LLM + 规则'))

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
        <small v-if="result" class="agent-meta">{{ modeLabel }} · {{ Math.round(result.latencyMs) }}ms</small>
      </div>
    </div>

    <p v-if="error" class="agent-error" role="alert"><AlertTriangle :size="15" />{{ error }}</p>

    <div v-if="result" class="agent-result">
      <div class="agent-slots">
        <span v-for="chip in slotChips" :key="chip" class="agent-slot">{{ chip }}</span>
      </div>
      <p class="agent-reply">{{ result.reply }}</p>
      <p v-for="warn in result.warnings" :key="warn" class="agent-warning">
        <AlertTriangle :size="14" />{{ warn }}
      </p>

      <ol v-if="result.candidates.length" class="agent-candidates">
        <li v-for="(person, index) in result.candidates" :key="person.photographerId" class="agent-candidate">
          <div class="agent-candidate-head">
            <span class="agent-rank">{{ String(index + 1).padStart(2, '0') }}</span>
            <div class="agent-candidate-id">
              <strong>{{ person.name }}</strong>
              <small>{{ person.city }} · {{ person.tags.join(' / ') || '标签待补充' }}</small>
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

          <p class="agent-slot-line">档期：{{ person.nextSlot || '待补充' }} · 回复：{{ person.responseTime || '待补充' }}</p>
        </li>
      </ol>

      <button class="agent-trace-toggle" type="button" @click="showTrace = !showTrace">
        <ChevronDown :size="14" :style="{ transform: showTrace ? 'rotate(180deg)' : 'none' }" />
        这次 Agent 调了哪些工具
      </button>
      <pre v-if="showTrace" class="agent-trace">{{ traceLine }}</pre>
    </div>
  </section>
</template>
