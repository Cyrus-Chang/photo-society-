<script setup lang="ts">
import { ArrowLeft, ArrowRight, CalendarDays, Camera, CheckCircle2, Clock3, MapPin, MessageCircle } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import WorkCard from '../components/WorkCard.vue'
import { getPhotographer } from '../services/api'
import { works } from '../data/mock'
import type { Photographer } from '../types'

const route = useRoute(); const router = useRouter(); const photographer = ref<Photographer | null>(null); const booked = ref(false)
onMounted(async () => { photographer.value = await getPhotographer(String(route.params.id)) })
const photographerWorks = computed(() => photographer.value ? works.filter((work) => photographer.value?.works.includes(work.id)) : [])
</script>

<template>
  <div v-if="photographer" class="photographer-page"><router-link class="back-link" to="/discover"><ArrowLeft :size="16" />返回作品墙</router-link><section class="profile-header"><div class="profile-avatar-wrap"><img :src="photographer.avatar" :alt="photographer.name" /><span v-if="photographer.verified"><CheckCircle2 :size="14" /></span></div><div class="profile-intro"><div class="profile-name"><h1>{{ photographer.name }}</h1><span class="verified-label">{{ photographer.role === 'enthusiast' ? '摄影爱好者' : '已认证' }}</span></div><p><MapPin :size="15" />{{ photographer.city }} · {{ photographer.responseTime }}</p><p class="profile-bio">{{ photographer.bio }}</p><div class="tag-row"><span v-for="tag in photographer.tags" :key="tag">{{ tag }}</span></div><div class="device-list"><span><Camera :size="14" />常用设备</span><b v-for="device in photographer.devices" :key="device">{{ device }}</b></div></div><div class="profile-actions"><button class="button button-primary" @click="booked = true">{{ photographer.role === 'enthusiast' ? '联系这位摄友' : '约这个摄影师' }} <ArrowRight :size="16" /></button><button class="button button-ghost"><MessageCircle :size="16" />先聊两句</button></div></section><section class="availability-banner"><div><span class="eyebrow">NEXT OPEN SLOT</span><strong><CalendarDays :size="18" />{{ photographer.nextSlot }}</strong><span>地点可在确认时一起商量</span></div><div class="availability-note"><Clock3 :size="15" />平台只展示摄影师主动打开的档期</div></section><section class="profile-works"><div class="section-heading"><div><span class="section-index">WORKS / {{ photographerWorks.length }}</span><h2>最近在现场拍到的</h2></div><span class="muted-copy">作品来自真实拍摄记录 · 可按风格与类型理解</span></div><div class="works-grid"><WorkCard v-for="work in photographerWorks" :key="work.id" :work="work" /></div></section><div v-if="booked" class="toast"><CheckCircle2 :size="18" />已选中 {{ photographer.name }}，下一步确认你的时间</div></div><div v-else class="loading-page">正在打开摄影师主页…</div>
</template>
