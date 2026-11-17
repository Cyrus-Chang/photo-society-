<script setup lang="ts">
import { computed, ref } from 'vue'
import { Check, RotateCcw, Upload } from 'lucide-vue-next'
import BaseModal from './BaseModal.vue'
import { fileToCompressedDataUrl } from '../utils/imageTools'
import {
  WALLPAPER_PRESETS,
  closeWallpaperPicker,
  personalize,
  setWallpaper,
  wallpaperPickerOpen,
  type WallpaperPreset
} from '../utils/personalize'

/**
 * 壁纸选择器（2026-11-16 用户：内置图库 + 自己上传，全局一张）。
 * 只挂在 App.vue 一次；三个页面通过 openWallpaperPicker() 打开。
 * 选完立即生效并写入本机 localStorage；写不进去就回滚并如实报错。
 */

const busy = ref(false)
const error = ref('')
const uploadInput = ref<HTMLInputElement | null>(null)

const current = computed(() => personalize.wallpaper)

function isActive(id: string) {
  const value = current.value
  return value?.kind === 'preset' && value.id === id
}

function isCustomActive() {
  return current.value?.kind === 'custom'
}

function presetStyle(preset: WallpaperPreset) {
  return { backgroundImage: preset.kind === 'gradient' ? preset.value : `url("${preset.value}")` }
}

function apply(id: string) {
  error.value = ''
  if (!setWallpaper({ kind: 'preset', id })) error.value = '本机写不进去（可能是隐私模式或存储满了），这张壁纸只在这次会话里生效。'
}

function reset() {
  error.value = ''
  if (!setWallpaper(null)) error.value = '本机写不进去，恢复默认只在这次会话里生效。'
}

async function onFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  error.value = ''
  busy.value = true
  try {
    const dataUrl = await fileToCompressedDataUrl(file, { maxEdge: 1920, quality: 0.8 })
    if (!setWallpaper({ kind: 'custom', dataUrl })) {
      error.value = '这张图压完还是太大，本机存不下；换一张小一点的。'
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : '这张图没有处理成功，换一张试试'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <BaseModal :open="wallpaperPickerOpen" labelled-by="wp-title" size="lg" @close="closeWallpaperPicker">
    <div class="wp">
      <span class="wp-kicker">PERSONAL / WALLPAPER</span>
      <h2 id="wp-title">换一张壁纸</h2>
      <p class="wp-copy">一张，用在个人信息、摄影工作台和我的约拍。只保存在这台设备，换设备或清缓存会回到默认。</p>

      <div class="wp-grid">
        <button
          v-for="preset in WALLPAPER_PRESETS"
          :key="preset.id"
          class="wp-tile"
          :class="{ 'is-active': isActive(preset.id) }"
          type="button"
          :aria-pressed="isActive(preset.id)"
          @click="apply(preset.id)"
        >
          <span class="wp-thumb" :style="presetStyle(preset)">
            <Check v-if="isActive(preset.id)" :size="14" aria-hidden="true" />
          </span>
          <span class="wp-meta"><strong>{{ preset.name }}</strong><small>{{ preset.note }}</small></span>
        </button>

        <button class="wp-tile" :class="{ 'is-active': isCustomActive() }" type="button" :aria-pressed="isCustomActive()" @click="uploadInput?.click()">
          <span class="wp-thumb wp-thumb--empty"><Upload :size="18" aria-hidden="true" /></span>
          <span class="wp-meta"><strong>{{ busy ? '正在处理…' : '上传自己的图' }}</strong><small>自动裁到长边 1920 · 只存本机</small></span>
        </button>
      </div>

      <input ref="uploadInput" type="file" accept="image/*" hidden @change="onFile" />

      <p v-if="error" class="wp-error" role="status">{{ error }}</p>

      <div class="wp-foot">
        <button class="wp-reset" type="button" @click="reset"><RotateCcw :size="14" aria-hidden="true" />恢复默认（不设壁纸）</button>
        <button class="wp-done" type="button" @click="closeWallpaperPicker">好了</button>
      </div>
    </div>
  </BaseModal>
</template>

<style scoped>
.wp-kicker { font: 9px/1 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; letter-spacing: .22em; color: #e98b6b; }
.wp h2 { margin: 10px 0 8px; font-family: 'Noto Serif SC', 'Songti SC', serif; font-size: clamp(24px, 3vw, 32px); font-weight: 600; line-height: 1.2; letter-spacing: -.03em; color: #eef2f5; }
.wp-copy { margin: 0 0 18px; color: rgba(238, 242, 245, .56); font-size: 12px; line-height: 1.75; }

.wp-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.wp-tile {
  display: grid; gap: 0; padding: 0; overflow: hidden; text-align: left;
  border: 1px solid rgba(238, 242, 245, .12); border-radius: 14px;
  background: rgba(238, 242, 245, .03); color: #eef2f5;
  transition: border-color .2s ease, transform .2s ease, background .2s ease;
}
.wp-tile:hover { border-color: rgba(233, 139, 107, .5); transform: translateY(-1px); }
.wp-tile.is-active { border-color: rgba(233, 139, 107, .92); background: rgba(233, 139, 107, .08); box-shadow: 0 0 0 1px rgba(233, 139, 107, .45); }
.wp-thumb { position: relative; display: grid; place-items: center; aspect-ratio: 16 / 10; background-color: #0d1218; background-position: center; background-size: cover; }
.wp-thumb svg { box-sizing: content-box; padding: 3px; border-radius: 50%; background: #e9896b; color: #12181c; }
.wp-thumb--empty { background: rgba(238, 242, 245, .05); color: rgba(238, 242, 245, .62); }
.wp-meta { display: grid; gap: 2px; padding: 8px 10px 10px; }
.wp-meta strong { font-size: 12px; font-weight: 500; }
.wp-meta small { font-size: 10px; color: rgba(238, 242, 245, .42); }

.wp-error { margin: 12px 0 0; color: #f0a48f; font-size: 11.5px; line-height: 1.6; }

.wp-foot { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 20px; }
.wp-reset {
  display: inline-flex; align-items: center; gap: 7px; min-height: 40px; padding: 0 14px;
  border: 1px solid rgba(238, 242, 245, .16); border-radius: 999px; background: transparent;
  color: rgba(238, 242, 245, .7); font-size: 12px; transition: border-color .2s ease, color .2s ease;
}
.wp-reset:hover { border-color: rgba(238, 242, 245, .34); color: #eef2f5; }
.wp-done {
  min-height: 40px; padding: 0 22px; border: 0; border-radius: 999px;
  background: linear-gradient(135deg, #f2a080, #e98b6b 60%, #d9734f); color: #1b2225;
  font-size: 12px; font-weight: 700;
}

@media (max-width: 620px) {
  .wp-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .wp-foot { flex-direction: column-reverse; align-items: stretch; }
  .wp-reset, .wp-done { justify-content: center; text-align: center; }
}
@media (prefers-reduced-motion: reduce) {
  .wp-tile:hover { transform: none; }
}
</style>
