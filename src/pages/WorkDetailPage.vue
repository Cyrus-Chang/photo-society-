<script setup lang="ts">
import { ArrowLeft, ArrowRight, CalendarDays, Camera, CheckCircle2, Clock3, MapPin, ShieldCheck } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getWork } from '../services/api'
import { posts } from '../data/mock'
import type { WorkCard } from '../types'
import { resolveWorkImage } from '../utils/media'
import { isAuthed } from '../utils/session'

const route = useRoute(); const router = useRouter(); const work = ref<WorkCard | null>(null); const bookingOpen = ref(false); const sent = ref(false)
onMounted(async () => { work.value = await getWork(String(route.params.id)) })
const sendBooking = () => { sent.value = true; bookingOpen.value = false }
// 2026-11-16 用户：作品详情也要看得到价位。
// 数据里没有独立价格字段，就取这位摄影师本人帖子里报过的价；没有就写「面议」，不编数字。
const priceNote = computed(() => {
  const own = posts.find((post) => post.author === work.value?.photographerName && post.budget)
  return own?.budget ?? '面议'
})
// 未登录也能看作品介绍，但约拍要先登录（2026-11-14 用户确认）
const onBook = () => {
  if (!isAuthed.value) { router.push({ name: 'login', query: { redirect: route.fullPath } }); return }
  bookingOpen.value = true
}
</script>

<template>
  <div v-if="work" class="detail-page"><router-link class="back-link" :to="isAuthed ? '/discover' : '/'"><ArrowLeft :size="16" />{{ isAuthed ? '返回作品墙' : '返回首页' }}</router-link><section class="work-detail-layout"><div class="detail-image"><img :src="resolveWorkImage(work.imageUrl)" :alt="work.title" /><span class="image-caption">{{ work.location }} / {{ work.shootDate }}</span></div><div class="detail-copy"><p class="eyebrow">作品详情 · {{ work.city }}</p><h1>{{ work.title }}</h1><div v-if="isAuthed" class="detail-author"><img :src="work.photographerAvatar" :alt="work.photographerName" /><div><strong>{{ work.photographerName }}</strong><span>{{ work.photographerId === 'p-cyrus' ? '摄影爱好者' : '摄影师' }} · {{ work.city }}</span><span class="detail-price">参考价 {{ priceNote }}</span></div><router-link :to="`/photographers/${work.photographerId}`">看主页 <ArrowRight :size="15" /></router-link></div><p v-else class="detail-author-locked">登录后可以看到摄影师信息、档期和价格。</p><div class="detail-facts"><div><MapPin :size="16" /><span>拍摄地<strong>{{ work.location }}</strong></span></div><div><CalendarDays :size="16" /><span>最近档期<strong>{{ work.shootDate }}</strong></span></div><div><Clock3 :size="16" /><span>现场状态<strong :class="{ good: work.canBook }">{{ work.canBook ? '现在可约' : '作品参考' }}</strong></span></div></div><div v-if="work.device" class="detail-device"><Camera :size="15" /><span>拍摄设备<strong>{{ work.device }}</strong></span></div><div class="detail-tags"><span v-for="tag in work.styles" :key="`style-${tag}`">风格 · {{ tag }}</span><span v-for="tag in work.types || []" :key="`type-${tag}`" class="detail-type-tag">类型 · {{ tag }}</span></div><p class="detail-reason">命中你的描述：<strong>{{ work.matchReason }}</strong></p><button class="button button-primary detail-book" :disabled="!work.canBook" @click="onBook">{{ work.canBook ? (isAuthed ? '约 TA 拍同款感觉' : '登录后约拍') : '查看相近摄影师' }} <ArrowRight :size="17" /></button><div class="detail-trust"><ShieldCheck :size="16" /><span>平台记录时间、地点和最终价格，线下完成付款</span></div></div></section><div v-if="bookingOpen" class="modal-backdrop" @click.self="bookingOpen = false"><div class="booking-modal"><button class="modal-close" @click="bookingOpen = false">×</button><p class="eyebrow">发起约拍</p><h2>把这张作品，变成你的现场</h2><p class="modal-subtitle">{{ work.photographerName }} · {{ work.location }}</p><label>期望日期<input value="周六 · 11 月 14 日" /></label><label>大概时段<input value="18:30—20:30" /></label><div class="booking-summary"><span>参考作品服务价</span><strong>¥ 780</strong></div><button class="button button-primary" @click="sendBooking">发送约拍请求 <ArrowRight :size="17" /></button></div></div><div v-if="sent" class="toast"><CheckCircle2 :size="18" />请求已发出，等摄影师确认时间</div></div><div v-else class="loading-page">正在打开作品现场…</div>
</template>
