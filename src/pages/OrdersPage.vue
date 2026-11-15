<script setup lang="ts">
import { ArrowRight, CalendarDays, CheckCircle2, Clock3, MapPin, MessageCircle } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { getOrders } from '../services/api'
import type { BookingOrder } from '../types'

const orders = ref<BookingOrder[]>([]); const active = ref('全部')
onMounted(async () => { orders.value = await getOrders() })
const filters = ['全部', '待确认', '已确认', '待结清']
const filtered = () => orders.value.filter((order) => active.value === '全部' || order.statusLabel === active.value)
</script>

<template>
  <div class="orders-page"><section class="simple-page-head"><div><p class="kicker"><span class="kicker-line" />我的约拍</p><h1>把每一次见面，<br /><em>留在同一条时间线上。</em></h1></div><router-link class="button button-secondary" to="/discover">继续找摄影师 <ArrowRight :size="16" /></router-link></section><div class="order-filters"><button v-for="filter in filters" :key="filter" :class="{ active: active === filter }" @click="active = filter">{{ filter }}</button></div><section class="orders-list"><article v-for="order in filtered()" :key="order.id" class="order-card"><div class="order-card-main"><div class="order-status" :class="order.status"><i />{{ order.statusLabel }}</div><h2>{{ order.title }}</h2><div class="order-meta"><span><MapPin :size="14" />{{ order.location }}</span><span><CalendarDays :size="14" />{{ order.date }}</span><span><Clock3 :size="14" />{{ order.time }}</span></div><div class="order-photographer"><img :src="order.photographerAvatar" :alt="order.photographerName" /><span>摄影师 <strong>{{ order.photographerName }}</strong></span></div></div><div class="order-card-side"><span class="order-id">{{ order.id }} · {{ order.updatedAt }}</span><strong>{{ order.price }}</strong><div><button class="button button-ghost button-small"><MessageCircle :size="15" />联系 TA</button><button class="text-button">查看详情 <ArrowRight :size="14" /></button></div></div></article><div v-if="!filtered().length" class="empty-state"><h3>这里还没有对应状态的约拍</h3><p>去作品墙看看谁在附近有空档。</p><router-link class="button button-primary" to="/discover">开始找摄影师</router-link></div></section><section class="order-timeline"><div><CheckCircle2 :size="18" /><strong>状态可追溯</strong><span>确认后的时间、地点和价格会一直保留在订单里</span></div><div><Clock3 :size="18" /><strong>线下完成付款</strong><span>平台不代收款，拍摄完成后双方线下结清</span></div></section></div>
</template>
