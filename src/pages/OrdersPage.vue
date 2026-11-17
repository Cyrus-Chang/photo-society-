<script setup lang="ts">
import { ArrowRight, CalendarDays, CheckCircle2, Clock3, MapPin, MessageCircle, Wallpaper } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { getOrders } from '../services/api'
import type { BookingOrder } from '../types'
import { openWallpaperPicker } from '../utils/personalize'

const orders = ref<BookingOrder[]>([]); const active = ref('全部')
onMounted(async () => { orders.value = await getOrders() })
const filters = ['全部', '待确认', '已确认', '待结清']
const filtered = () => orders.value.filter((order) => active.value === '全部' || order.statusLabel === active.value)
</script>

<template>
  <div class="orders-page"><section class="simple-page-head"><div><p class="kicker"><span class="kicker-line" />我的约拍</p><h1>把每一次见面，<br /><em>留在同一条时间线上。</em></h1></div><div class="orders-head-actions"><button class="wallpaper-entry" type="button" @click="openWallpaperPicker()"><Wallpaper :size="14" aria-hidden="true" />换壁纸</button><router-link class="button button-secondary" to="/discover">继续找摄影师 <ArrowRight :size="16" /></router-link></div></section><div class="order-filters"><button v-for="filter in filters" :key="filter" :class="{ active: active === filter }" @click="active = filter">{{ filter }}</button></div><section class="orders-list"><article v-for="order in filtered()" :key="order.id" class="order-card"><div class="order-card-main"><div class="order-status" :class="order.status"><i />{{ order.statusLabel }}</div><h2>{{ order.title }}</h2><div class="order-meta"><span><MapPin :size="14" />{{ order.location }}</span><span><CalendarDays :size="14" />{{ order.date }}</span><span><Clock3 :size="14" />{{ order.time }}</span></div><div class="order-photographer"><img :src="order.photographerAvatar" :alt="order.photographerName" /><span>摄影师 <strong>{{ order.photographerName }}</strong></span></div></div><div class="order-card-side"><span class="order-id">{{ order.id }} · {{ order.updatedAt }}</span><strong>{{ order.price }}</strong><div><button class="button button-ghost button-small"><MessageCircle :size="15" />联系 TA</button><button class="text-button">查看详情 <ArrowRight :size="14" /></button></div></div></article><div v-if="!filtered().length" class="empty-state"><h3>这里还没有对应状态的约拍</h3><p>去作品墙看看谁在附近有空档。</p><router-link class="button button-primary" to="/discover">开始找摄影师</router-link></div></section><section class="order-timeline"><div><CheckCircle2 :size="18" /><strong>状态可追溯</strong><span>确认后的时间、地点和价格会一直保留在订单里</span></div><div><Clock3 :size="18" /><strong>线下完成付款</strong><span>平台不代收款，拍摄完成后双方线下结清</span></div></section></div>
</template>

<style scoped>
/* 壁纸层在 App.vue 里是 fixed 的 z-index:0 节点，页面内容抬到它上面 */
.orders-page { position: relative; z-index: 1; }
/* 2026-11-16 用户：全局壁纸入口（和个人信息、摄影工作台共用一张） */
.orders-head-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.wallpaper-entry {
  display: inline-flex; align-items: center; gap: 6px; min-height: 36px;
  padding: 0 14px; border-radius: 999px; cursor: pointer;
  border: 1px solid rgba(238, 242, 245, .16); background: rgba(238, 242, 245, .04);
  color: rgba(238, 242, 245, .72); font-size: 11.5px;
  transition: border-color .2s ease, color .2s ease, background .2s ease;
}
.wallpaper-entry:hover { border-color: rgba(233, 139, 107, .55); background: rgba(233, 139, 107, .12); color: #ffd9c9; }
.wallpaper-entry:focus-visible { outline: 2px solid rgba(233, 139, 107, .7); outline-offset: 2px; }

/* ===== 2026-11-16 用户：圆角 + 液态渐变玻璃（替换原来的灰底分行） ===== */
.orders-page {
  --lg-line: rgba(255, 255, 255, .17);
  --lg-warm: rgba(233, 139, 107, .24);
  --lg-cool: rgba(112, 146, 214, .22);
  --lg-teal: rgba(108, 188, 176, .16);
}
.orders-page .wallpaper-entry {
  border-color: rgba(255, 255, 255, .18);
  background: linear-gradient(160deg, rgba(255, 255, 255, .09), rgba(255, 255, 255, .03));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .16);
}
.orders-page .orders-head-actions .button-secondary {
  border-radius: 999px; border: 1px solid rgba(255, 255, 255, .18);
  background: linear-gradient(160deg, rgba(255, 255, 255, .10), rgba(255, 255, 255, .035));
  color: #eef2f5; box-shadow: inset 0 1px 0 rgba(255, 255, 255, .16);
}
.orders-page .orders-head-actions .button-secondary:hover { border-color: rgba(233, 139, 107, .55); color: #ffd9c9; }

.orders-page .order-filters {
  width: fit-content; max-width: 100%; margin: 16px 3vw 4px;
  padding: 6px; gap: 4px; flex-wrap: nowrap; overflow-x: auto;
  border: 1px solid var(--lg-line); border-radius: 999px;
  background:
    radial-gradient(130% 170% at 0% 0%, rgba(233, 139, 107, .18), transparent 56%),
    radial-gradient(130% 170% at 100% 120%, var(--lg-cool), transparent 62%),
    linear-gradient(160deg, rgba(255, 255, 255, .09), rgba(255, 255, 255, .035));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .18), 0 22px 55px -36px rgba(0, 0, 0, 1);
  backdrop-filter: blur(16px) saturate(150%);
  -webkit-backdrop-filter: blur(16px) saturate(150%);
}
.orders-page .order-filters button {
  padding: 8px 17px; border: 1px solid transparent; border-radius: 999px;
  color: rgba(238, 242, 245, .6); font-size: 11.5px; white-space: nowrap;
  transition: color .2s ease, background .2s ease, border-color .2s ease;
}
.orders-page .order-filters button:hover { color: #eef2f5; background: rgba(255, 255, 255, .06); }
.orders-page .order-filters button.active {
  color: #1b2225; border-color: transparent;
  background: linear-gradient(135deg, #f4a688 0%, #e9896b 56%, #d9734f 100%);
  box-shadow: 0 10px 26px -12px rgba(233, 139, 107, .6), inset 0 1px 0 rgba(255, 255, 255, .38);
}

.orders-page .orders-list { padding-top: 20px; }
.orders-page .order-card {
  position: relative; isolation: isolate; overflow: hidden;
  margin: 0 0 14px; padding: 24px 26px;
  border: 1px solid var(--lg-line); border-radius: 24px;
  background:
    radial-gradient(120% 150% at 4% -10%, var(--lg-warm), transparent 55%),
    radial-gradient(110% 130% at 104% 112%, var(--lg-cool), transparent 62%),
    linear-gradient(158deg, rgba(255, 255, 255, .105), rgba(255, 255, 255, .038) 46%, rgba(255, 255, 255, .072));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .20), inset 0 -1px 0 rgba(255, 255, 255, .05), 0 34px 80px -44px rgba(0, 0, 0, 1);
  backdrop-filter: blur(18px) saturate(150%);
  -webkit-backdrop-filter: blur(18px) saturate(150%);
  transition: border-color .25s ease, transform .25s ease, box-shadow .25s ease;
}
.orders-page .order-card::before {
  content: ''; position: absolute; inset: -35% -18%; z-index: -1; pointer-events: none;
  background:
    radial-gradient(36% 42% at 28% 30%, rgba(244, 166, 136, .32), transparent 62%),
    radial-gradient(34% 40% at 74% 70%, rgba(112, 146, 214, .30), transparent 64%),
    radial-gradient(28% 34% at 58% 8%, rgba(108, 188, 176, .16), transparent 66%);
  filter: blur(40px); opacity: .9;
  animation: ps-glass-drift 18s ease-in-out infinite alternate;
}
.orders-page .order-card:hover {
  border-color: rgba(255, 255, 255, .28); transform: translateY(-2px);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .24), 0 40px 90px -44px rgba(0, 0, 0, 1);
}
@keyframes ps-glass-drift {
  from { transform: translate3d(-3%, -2%, 0) scale(1); }
  to { transform: translate3d(4%, 3%, 0) scale(1.12); }
}
.orders-page .order-status {
  display: inline-flex; align-items: center; gap: 6px; width: fit-content;
  padding: 3px 10px; margin-bottom: 9px; border-radius: 999px;
  background: rgba(255, 255, 255, .07); border: 1px solid rgba(255, 255, 255, .12);
  color: #a7d8bb; font-size: 10px; letter-spacing: .02em;
}
.orders-page .order-status.pending { color: #e8c58a; }
.orders-page .order-status.confirmed { color: #a7d8bb; }
.orders-page .order-status.shooting-done { color: #f2a080; }
.orders-page .order-status.settled { color: #9fb3c8; }
.orders-page .order-card-side strong { color: #ffd9c9; font-family: 'Noto Serif SC', 'Songti SC', serif; font-size: 25px; letter-spacing: -.02em; }
.orders-page .order-card-side .button-ghost {
  min-height: 38px; padding: 0 16px; border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, .20);
  background: linear-gradient(160deg, rgba(255, 255, 255, .10), rgba(255, 255, 255, .035));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .16); color: #eef2f5;
}
.orders-page .order-card-side .button-ghost:hover { border-color: rgba(233, 139, 107, .6); background: rgba(233, 139, 107, .14); }

.orders-page .order-timeline {
  display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px;
  margin: 44px 3vw 0; background: none;
}
.orders-page .order-timeline > div {
  padding: 22px; border: 1px solid rgba(255, 255, 255, .14); border-radius: 20px;
  background:
    radial-gradient(130% 150% at 0% 0%, rgba(112, 146, 214, .16), transparent 60%),
    linear-gradient(160deg, rgba(255, 255, 255, .085), rgba(255, 255, 255, .03));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .14);
  backdrop-filter: blur(14px) saturate(140%);
  -webkit-backdrop-filter: blur(14px) saturate(140%);
}
@media (max-width: 720px) {
  .orders-page .order-filters { margin-left: 0; margin-right: 0; max-width: 100%; }
  .orders-page .order-card { padding: 20px; border-radius: 20px; }
  .orders-page .order-timeline { grid-template-columns: 1fr; margin: 32px 0 0; }
}
@media (prefers-reduced-motion: reduce) {
  .orders-page .order-card::before { animation: none; }
  .orders-page .order-card:hover { transform: none; }
}
</style>
