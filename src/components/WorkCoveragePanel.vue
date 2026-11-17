<script setup lang="ts">
/**
 * 作品覆盖面板（2026-11-16 · 接拍线）
 *
 * 为什么是「统计」而不是「分类判定」：
 * 平台没有权力把一位摄影师塞进某个固定类别（这个批评是对的）。这里只做一件事——
 * 把作者自己填在作品上的标签数出来，让他看见自己的作品覆盖了哪些现场。
 * 换一组作品，分布就跟着变；不存在「系统认定你是哪一类人」。
 *
 * 数据来源（全部来自本地作品数据，不发请求、不编造数字）：
 *   · 风格分布 ← 作品 styles（作者自由填的影调/风格标签，如 蓝调 / 纪实 / 低饱和）
 *   · 场景分布 ← 作品 types（题材标签，如 人像 / 建筑 / 风景）
 *   · 占比分母 = 作品总数（同一件作品重复填同一个标签只算一次）
 *
 * 三档建议是中性描述：覆盖窄 / 偏科 / 均衡，不做评级、不承诺曝光。
 */
import { computed } from 'vue'
import { works as mockWorks } from '../data/mock'
import type { WorkCard } from '../types'

const props = defineProps<{
  /** 统计哪一位摄影师的作品；默认工作台账号 p-cyrus */
  photographerId?: string
  /** 外部传入作品列表时优先使用（便于联调 / 复用），默认按作者从 mock 里筛 */
  works?: WorkCard[]
}>()

interface DistItem {
  name: string
  count: number
  share: number
}

const sourceWorks = computed<WorkCard[]>(() => {
  if (props.works) return props.works
  const id = props.photographerId ?? 'p-cyrus'
  return mockWorks.filter((work) => work.photographerId === id)
})

const total = computed(() => sourceWorks.value.length)
const photographerName = computed(() => sourceWorks.value[0]?.photographerName ?? '当前账号')

/** 标签词频统计：同一件作品里重复出现的标签只算一次，避免作者叠词抬高占比 */
function tally(list: WorkCard[], pick: (work: WorkCard) => string[] | undefined, denominator: number, limit = 5): DistItem[] {
  const bucket = new Map<string, number>()
  for (const work of list) {
    const seen = new Set<string>()
    for (const raw of pick(work) ?? []) {
      if (typeof raw !== 'string') continue
      const name = raw.trim()
      if (!name || seen.has(name)) continue
      seen.add(name)
      bucket.set(name, (bucket.get(name) ?? 0) + 1)
    }
  }
  return Array.from(bucket, ([name, count]) => ({
    name,
    count,
    share: denominator > 0 ? count / denominator : 0
  }))
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name, 'zh-Hans-CN'))
    .slice(0, limit)
}

const styleDist = computed(() => tally(sourceWorks.value, (work) => work.styles, total.value))
const sceneDist = computed(() => tally(sourceWorks.value, (work) => work.types, total.value))
const countUniqueLabels = (list: WorkCard[], pick: (work: WorkCard) => string[] | undefined) => {
  const labels = list.flatMap((work) => pick(work) ?? [])
  return new Set(labels.filter((label) => typeof label === 'string').map((label) => label.trim()).filter(Boolean)).size
}
const styleKinds = computed(() => countUniqueLabels(sourceWorks.value, (work) => work.styles))
const sceneKinds = computed(() => countUniqueLabels(sourceWorks.value, (work) => work.types))
const cityKinds = computed(() => new Set(sourceWorks.value.map((work) => work.city).filter(Boolean)).size)
const topStyle = computed(() => styleDist.value[0])
const topScene = computed(() => sceneDist.value[0])

const pct = (value: number) => Math.round(value * 100)
const barWidth = (item: DistItem) => `${Math.max(item.share * 100, 2).toFixed(1)}%`

/** 三档：Top1 场景 > 60% 记「覆盖窄」；Top1 风格 ≥ 50% 记「偏科」；其余记「均衡」 */
const tier = computed<'narrow' | 'skew' | 'balanced'>(() => {
  if (!total.value || !topScene.value) return 'balanced'
  if (topScene.value.share > 0.6) return 'narrow'
  if (topStyle.value && topStyle.value.share >= 0.5) return 'skew'
  return 'balanced'
})

const advice = computed<{ tag: string; title: string; body: string }>(() => {
  if (!total.value) {
    return { tag: 'NO DATA', title: '还没有作品可以统计', body: '上传第一组作品后，这里会按标签自动汇总覆盖情况。' }
  }
  if (tier.value === 'narrow' && topScene.value) {
    return {
      tag: '覆盖窄',
      title: '场景覆盖偏窄，可补充其他场景作品',
      body: `Top1 场景「${topScene.value.name}」占 ${pct(topScene.value.share)}%，目前只有 ${sceneKinds.value} 类场景。补几组别的场景，找不同拍摄的人也能对上号。`
    }
  }
  if (tier.value === 'skew' && topStyle.value) {
    return {
      tag: '偏科',
      title: '风格集中，覆盖不算均衡',
      body: `Top1 风格「${topStyle.value.name}」占 ${pct(topStyle.value.share)}%。这不是缺点，只是被检索时容易只出现在一类结果里。`
    }
  }
  return {
    tag: '均衡',
    title: '风格与场景的分布比较均衡',
    body: `覆盖 ${styleKinds.value} 类风格标签、${sceneKinds.value} 类场景，Top1 场景「${topScene.value?.name ?? '—'}」占 ${topScene.value ? pct(topScene.value.share) : 0}%。`
  }
})
</script>

<template>
  <section class="wa-panel wa-coverage" aria-labelledby="wa-coverage-title">
    <header class="wa-head">
      <p class="wa-kicker">03 / COVERAGE · 作品覆盖</p>
      <h2 id="wa-coverage-title" class="wa-title">你的作品，<em>覆盖了哪些现场</em></h2>
      <p class="wa-sub">按 {{ photographerName }} 的 {{ total }} 件作品标签汇总，不套模版。</p>
    </header>

    <div class="wa-stats">
      <div class="wa-stat"><b>{{ total }}</b><span>件作品 / WORKS</span></div>
      <div class="wa-stat"><b>{{ styleKinds }}</b><span>风格标签 / STYLES</span></div>
      <div class="wa-stat"><b>{{ sceneKinds }}</b><span>场景类型 / SCENES</span></div>
      <div class="wa-stat"><b>{{ cityKinds }}</b><span>拍摄城市 / CITIES</span></div>
    </div>

    <div v-if="total" class="wa-cols">
      <div class="wa-col">
        <div class="wa-col-head"><strong>风格分布</strong><span>STYLE · TOP 5</span></div>
        <div v-for="(item, index) in styleDist" :key="`style-${item.name}`" class="wa-row">
          <span class="wa-row-name"><i>{{ String(index + 1).padStart(2, '0') }}</i><b>{{ item.name }}</b></span>
          <span class="wa-row-num">{{ item.count }} 件 · {{ pct(item.share) }}%</span>
          <span class="wa-row-bar"><span :style="{ width: barWidth(item) }" /></span>
        </div>
        <p v-if="!styleDist.length" class="wa-note">还没有填风格标签。</p>
      </div>

      <div class="wa-col">
        <div class="wa-col-head"><strong>场景分布</strong><span>SCENE · TOP 5</span></div>
        <div v-for="(item, index) in sceneDist" :key="`scene-${item.name}`" class="wa-row">
          <span class="wa-row-name"><i>{{ String(index + 1).padStart(2, '0') }}</i><b>{{ item.name }}</b></span>
          <span class="wa-row-num">{{ item.count }} 件 · {{ pct(item.share) }}%</span>
          <span class="wa-row-bar"><span :style="{ width: barWidth(item) }" /></span>
        </div>
        <p v-if="!sceneDist.length" class="wa-note">还没有填场景/题材标签。</p>
      </div>
    </div>
    <p v-else class="wa-note">作品上传后，这里会自动汇总。</p>

    <div class="wa-advice" :class="`is-${tier}`">
      <header><span class="wa-advice-tag">{{ advice.tag }}</span><strong>{{ advice.title }}</strong></header>
      <p>{{ advice.body }}</p>
    </div>

    <p class="wa-method">
      <b>统计自作品标签，不做固定分类判定。</b>
      风格取自作品 styles 标签，场景取自作品题材标签（人像 / 建筑 / 风景…）；统计只描述当前这批作品，不给人贴类别。
    </p>
  </section>
</template>

<style scoped>
.wa-panel {
  box-sizing: border-box;
  width: 100%;
  max-width: 100%;
  min-width: 0;
}

.wa-panel *,
.wa-panel *::before,
.wa-panel *::after {
  box-sizing: border-box;
}

.wa-title,
.wa-sub,
.wa-method,
.wa-note,
.wa-advice p {
  overflow-wrap: anywhere;
}

@media (max-width: 390px) {
  .wa-panel {
    padding-inline: 12px;
  }

  .wa-col-head {
    align-items: flex-start;
  }

  .wa-col-head span {
    white-space: normal;
    text-align: right;
  }

  .wa-row-num {
    white-space: normal;
    text-align: right;
  }
}
</style>
