<script setup lang="ts">
import { computed } from 'vue'
import { personalize, wallpaperStyle } from '../utils/personalize'

/**
 * 全局壁纸层（2026-11-16 用户选「全局一张 / 本机存」）。
 *
 * 只挂一次：App.vue 里按路由判断，只在个人信息 / 摄影工作台 / 我的约拍出现。
 * 铺满视口、压在内容下面；暗角保证正文可读。没设壁纸时整层不渲染。
 * 组件本身不写 localStorage，状态在 utils/personalize.ts。
 */

const style = computed(() => wallpaperStyle(personalize.wallpaper))
</script>

<template>
  <div v-if="style" class="ps-wallpaper" aria-hidden="true">
    <div class="ps-wallpaper-media" :style="style" />
    <div class="ps-wallpaper-veil" />
  </div>
</template>

<style scoped>
.ps-wallpaper {
  position: fixed;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
}
.ps-wallpaper-media {
  position: absolute;
  inset: -2%;
  background-position: center;
  background-size: cover;
  background-repeat: no-repeat;
  filter: saturate(.92);
  transform: scale(1.01);
}
.ps-wallpaper-veil {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(115% 80% at 50% 0%, rgba(5, 8, 12, .30), rgba(5, 8, 12, .62) 58%, rgba(4, 6, 9, .82) 100%),
    linear-gradient(180deg, rgba(7, 10, 14, .35), rgba(7, 10, 14, .55));
}
@media (prefers-reduced-motion: reduce) {
  .ps-wallpaper-media { transform: none; }
}
</style>
