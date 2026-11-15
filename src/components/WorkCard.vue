<script setup lang="ts">
import { ArrowUpRight, CalendarDays, Camera, MapPin } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'
import type { WorkCard } from '../types'
import { resolveWorkImage } from '../utils/media'

defineProps<{ work: WorkCard; featured?: boolean }>()
</script>

<template>
  <RouterLink :to="`/works/${work.id}`" class="work-card" :class="{ featured }">
    <div class="work-image-wrap">
      <img :src="resolveWorkImage(work.imageUrl)" :alt="work.title" loading="lazy" />
      <span v-if="work.canBook" class="availability-pill"><i />可约</span>
      <span v-else class="availability-pill muted"><i />档期紧呢</span>
      <span class="work-arrow"><ArrowUpRight :size="17" /></span>
    </div>
    <div class="work-card-body">
      <div class="work-title-row"><h3>{{ work.title }}</h3><span class="work-date"><CalendarDays :size="13" />{{ work.shootDate }}</span></div>
      <p class="work-location"><MapPin :size="13" />{{ work.location }}</p>
      <div class="tag-row"><span v-for="tag in work.styles" :key="`style-${tag}`">{{ tag }}</span><span v-for="tag in work.types || []" :key="`type-${tag}`" class="type-tag">{{ tag }}</span></div>
      <div class="work-author"><img :src="work.photographerAvatar" :alt="work.photographerName" /><span>{{ work.photographerName }}</span><span v-if="work.device" class="work-device"><Camera :size="11" />{{ work.device }}</span><span class="book-cta">约 TA</span></div>
    </div>
  </RouterLink>
</template>
