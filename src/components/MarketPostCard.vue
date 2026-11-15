<script setup lang="ts">
import { CalendarDays, MapPin, UsersRound } from 'lucide-vue-next'
import type { MarketPost } from '../types'

defineProps<{ post: MarketPost }>()

const kindLabel = (kind: MarketPost['kind']) => ({ requirement: '需求帖', availability: '档期帖', companion: '搭子帖' }[kind])
</script>

<template>
  <article class="market-post-card">
    <div class="post-marker" :class="post.kind"><span>{{ kindLabel(post.kind) }}</span><strong>{{ post.date.replace(' 月 ', '/').replace(' 日', '') }}</strong></div>
    <div class="post-main"><div class="post-heading"><h3>{{ post.title }}</h3><span v-if="post.mode" class="mode-label" :class="post.mode">{{ post.mode === 'pure-companion' ? '纯搭子' : '顺路带拍' }}</span></div>
      <p class="post-meta"><MapPin :size="14" />{{ post.location }} <span>·</span> <CalendarDays :size="14" />{{ post.time }}</p>
      <p class="post-description">{{ post.description }}</p>
      <div class="post-footer"><div class="post-author"><img :src="post.avatar" :alt="post.author" /><span>{{ post.author }}</span></div><span v-if="post.budget" class="post-budget">{{ post.budget }}</span><span v-if="post.spots" class="post-spots"><UsersRound :size="14" />{{ post.spots }}</span><span class="post-status">{{ post.status }}</span><button class="text-button">查看详情 →</button></div>
    </div>
  </article>
</template>
