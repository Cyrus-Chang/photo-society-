<script setup lang="ts">
import { UsersRound } from 'lucide-vue-next'
import { computed } from 'vue'
import type { MarketPost } from '../types'

const props = defineProps<{ post: MarketPost; index?: number }>()
// 2026-11-16 用户：点「查看详情」点不开。整行可点，交给页面开详情弹层。
const emit = defineEmits<{ (event: 'open', post: MarketPost): void }>()

const kindLabel = (kind: MarketPost['kind']) => ({ requirement: '需求帖', availability: '档期帖', companion: '搭子帖' }[kind])
const dateText = computed(() => props.post.date.replace(' 月 ', '/').replace(' 日', ''))
const modeText = computed(() => (props.post.mode === 'pure-companion' ? '纯搭子' : '顺路带拍'))
</script>

<template>
  <article
    class="market-post-card ps-row"
    :class="`ps-row--${post.kind}`"
    :style="{ '--ps-i': index ?? 0 }"
    role="button"
    tabindex="0"
    :aria-label="`${kindLabel(post.kind)}：${post.title}，查看详情`"
    @click="emit('open', post)"
    @keydown.enter.prevent="emit('open', post)"
    @keydown.space.prevent="emit('open', post)"
  >
    <div class="ps-row-aside" aria-hidden="true">
      <template v-if="post.kind === 'requirement'">
        <span class="ps-aside-rule" />
        <span class="ps-kind-mark">NEED</span>
        <span class="ps-aside-date">{{ dateText }}</span>
      </template>
      <template v-else-if="post.kind === 'availability'">
        <span class="ps-slot-rule" />
        <span class="ps-aside-date">{{ dateText }}</span>
        <span class="ps-aside-time">{{ post.time }}</span>
        <span class="ps-kind-mark">SLOT</span>
      </template>
      <template v-else>
        <span class="ps-pair-icon"><UsersRound :size="17" /></span>
        <span class="ps-pair-mode">{{ modeText }}</span>
        <span class="ps-aside-date">{{ dateText }}</span>
        <span class="ps-kind-mark">PAIR</span>
      </template>
    </div>

    <div class="ps-row-main">
      <div class="post-heading"><h3>{{ post.title }}</h3></div>
      <p class="post-meta"><span>{{ post.location }}</span><span class="ps-meta-sep" aria-hidden="true">·</span><span>{{ post.time }}</span></p>
      <p class="post-description">{{ post.description }}</p>
      <div class="post-footer">
        <div class="post-author"><img :src="post.avatar" :alt="post.author" /><span>{{ post.author }}</span></div>
        <span v-if="post.budget" class="post-budget">{{ post.budget }}</span>
        <span v-if="post.spots" class="post-spots"><UsersRound :size="13" aria-hidden="true" />{{ post.spots }}</span>
        <span class="post-status">{{ post.status }}</span>
        <span class="text-button">查看详情 →</span>
      </div>
    </div>
  </article>
</template>
