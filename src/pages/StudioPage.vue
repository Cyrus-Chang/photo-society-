<script setup lang="ts">
import { ArrowRight, CalendarDays, Camera, Check, CheckCircle2, ImagePlus, MapPin, Plus, Send, Upload, Wallpaper, X } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { photographers, works } from '../data/mock'
import { resolveWorkImage } from '../utils/media'
import WorkCoveragePanel from '../components/WorkCoveragePanel.vue'
import { openWallpaperPicker } from '../utils/personalize'

const enabled = ref(true); const published = ref(false)
const account = photographers.find((photographer) => photographer.id === 'p-cyrus')
const devices = ref(account?.devices || ['小米 15', '大疆 Osmo Pocket 3'])
const newDevice = ref('')
const uploadOpen = ref(false)
const uploadInput = ref<HTMLInputElement | null>(null)
const pendingUploads = ref<{ name: string; url: string }[]>([])
const selectedStyles = ref(['蓝调'])
const selectedTypes = ref(['人像'])
const styleOptions = ['蓝调', '暖调', '纪实', '夜景', '旅行', '高饱和', '自然光', '生活感']
const typeOptions = ['人像', '建筑', '风景', '活动', '街头', '静物', '美食', '户外']
const portfolioWorks = computed(() => works.filter((work) => work.photographerId === 'p-cyrus').slice(0, 3))
const addDevice = () => { const value = newDevice.value.trim(); if (value && !devices.value.includes(value)) devices.value.push(value); newDevice.value = '' }
const removeDevice = (device: string) => { const index = devices.value.indexOf(device); if (index >= 0) devices.value.splice(index, 1) }
const toggleTag = (list: string[], tag: string) => { const next = list.includes(tag) ? list.filter((item) => item !== tag) : [...list, tag]; if (list === selectedStyles.value) selectedStyles.value = next; else selectedTypes.value = next }
const openPicker = () => uploadInput.value?.click()
const handleFiles = (event: Event) => {
  const files = Array.from((event.target as HTMLInputElement).files || []).slice(0, 6)
  pendingUploads.value = files.map((file) => ({ name: file.name, url: URL.createObjectURL(file) }))
}
const removeUpload = (index: number) => { const removed = pendingUploads.value.splice(index, 1)[0]; if (removed) URL.revokeObjectURL(removed.url) }
const saveUploads = () => { uploadOpen.value = false }
</script>

<template>
  <div class="studio-page"><section class="simple-page-head studio-head"><div><p class="kicker"><span class="kicker-line" />摄影师工作台</p><h1>让别人知道，<br /><em>你什么时候在现场。</em></h1><p>打开接单状态，发布一段可到场的档期。作品会先替你说话。</p><button class="wallpaper-entry" type="button" @click="openWallpaperPicker()"><Wallpaper :size="14" aria-hidden="true" />换壁纸</button></div><div class="studio-status" :class="{ on: enabled }"><span class="status-orb" /><div><strong>{{ enabled ? '正在接单' : '暂不接单' }}</strong><small>{{ enabled ? '附近的人可以在作品里找到你' : '你可以随时重新打开' }}</small></div><button @click="enabled = !enabled" :aria-label="enabled ? '关闭接单' : '开启接单'"><span /></button></div></section><section class="studio-grid"><div class="studio-main"><div class="studio-section-head"><div><span class="section-index">01 / AVAILABILITY</span><h2>发布一段档期</h2></div><span class="muted-copy">让时间和地点先被看见</span></div><div class="availability-form"><label><span>在哪儿</span><div><MapPin :size="16" /><input value="西安 · 曲江池附近" /></div></label><label><span>哪天</span><div><CalendarDays :size="16" /><input value="周日 · 11 月 15 日" /></div></label><label><span>什么时间</span><div><input value="15:00—18:00" /></div></label><label class="wide"><span>补充一句</span><div><input value="自然光人像，不赶场，可以一起看参考图。" /></div></label><button class="button button-primary" @click="published = true"><Send :size="16" />发布这段档期</button></div><div v-if="published" class="success-panel"><CheckCircle2 :size="18" /><span><strong>档期已发布</strong>附近的人现在可以在接拍里看到它。</span></div><div class="studio-section-head studio-works-head"><div><span class="section-index">02 / PORTFOLIO · CYRUS_CHANG</span><h2>公开作品集</h2></div><button class="button button-ghost button-small" @click="uploadOpen = true"><ImagePlus :size="15" />上传作品</button></div><div class="mini-works"><div v-for="work in portfolioWorks" :key="work.id"><img :src="resolveWorkImage(work.imageUrl)" :alt="work.title" /><span>{{ work.location }}</span></div><button class="add-work" @click="uploadOpen = true"><Plus :size="20" /><span>添加新作品</span></button></div><WorkCoveragePanel /></div><aside class="studio-aside"><div class="aside-card dark-card"><span class="eyebrow">本周现场</span><strong>3</strong><span>段可约档期</span><div class="aside-line" /><div class="aside-stat"><span>作品被看见</span><b>128</b></div><div class="aside-stat"><span>收到约拍请求</span><b>6</b></div><router-link to="/market">去看附近需求 <ArrowRight :size="15" /></router-link></div><div class="aside-card device-card"><div class="device-card-head"><Camera :size="18" /><span><strong>账号设备</strong><small>会展示在主页和每张作品下</small></span></div><div class="device-chips"><span v-for="device in devices" :key="device">{{ device }}<button @click="removeDevice(device)" :aria-label="`移除 ${device}`">×</button></span></div><div class="device-add"><input v-model="newDevice" placeholder="添加机型，如 Fujifilm X-T5" @keyup.enter="addDevice" /><button @click="addDevice"><Plus :size="14" /></button></div><router-link class="device-profile-link" to="/photographers/p-cyrus">查看 Cyrus_chang 公开主页 <ArrowRight :size="14" /></router-link></div><div class="aside-card"><Camera :size="20" /><h3>作品标签已就绪</h3><p>风格和类型分开记录，找人拍照的人可以按“蓝调”“人像”“建筑”等关键词找到你。</p><span class="tag-row"><i>蓝调</i><i>建筑</i><i>人像</i></span></div></aside></section><div v-if="uploadOpen" class="modal-backdrop" @click.self="uploadOpen = false"><div class="upload-modal"><button class="modal-close" @click="uploadOpen = false"><X :size="21" /></button><p class="eyebrow">PORTFOLIO / UPLOAD</p><h2>上传作品并打标签</h2><p class="modal-subtitle">风格和类型会分别展示，设备会跟随账号同步到作品下方。</p><input ref="uploadInput" class="sr-only" type="file" accept="image/jpeg,image/png" multiple @change="handleFiles" /><div v-if="!pendingUploads.length" class="upload-dropzone" @click="openPicker"><Upload :size="22" /><strong>点击选择图片</strong><span>最多 6 张 · JPG / PNG</span></div><div v-else class="upload-previews"><div v-for="(file, index) in pendingUploads" :key="file.url"><img :src="file.url" :alt="file.name" /><button @click="removeUpload(index)" :aria-label="`移除 ${file.name}`"><X :size="14" /></button></div><button class="upload-add-more" @click="openPicker"><Plus :size="18" />继续添加</button></div><div class="tag-editor"><div><span>风格标签</span><div class="tag-options"><button v-for="tag in styleOptions" :key="tag" :class="{ selected: selectedStyles.includes(tag) }" @click="toggleTag(selectedStyles, tag)"><Check v-if="selectedStyles.includes(tag)" :size="12" />{{ tag }}</button></div></div><div><span>类型标签</span><div class="tag-options"><button v-for="tag in typeOptions" :key="tag" :class="{ selected: selectedTypes.includes(tag) }" @click="toggleTag(selectedTypes, tag)"><Check v-if="selectedTypes.includes(tag)" :size="12" />{{ tag }}</button></div></div></div><div class="upload-modal-footer"><span>{{ pendingUploads.length || 0 }} 张待上传</span><button class="button button-primary" :disabled="!pendingUploads.length" @click="saveUploads">保存到作品集 <ArrowRight :size="16" /></button></div></div></div></div>
</template>

<style scoped>
/* 壁纸层在 App.vue 里是 fixed 的 z-index:0 节点，页面内容抬到它上面 */
.studio-page { position: relative; z-index: 1; }
/* 2026-11-16 用户：全局壁纸入口（个人信息 / 摄影工作台 / 我的约拍共用一张） */
.wallpaper-entry {
  display: inline-flex; align-items: center; gap: 6px; min-height: 36px;
  margin-top: 16px; padding: 0 14px; border-radius: 999px; cursor: pointer;
  border: 1px solid rgba(238, 242, 245, .16); background: rgba(238, 242, 245, .04);
  color: rgba(238, 242, 245, .72); font-size: 11.5px;
  transition: border-color .2s ease, color .2s ease, background .2s ease;
}
.wallpaper-entry:hover { border-color: rgba(233, 139, 107, .55); background: rgba(233, 139, 107, .12); color: #ffd9c9; }
.wallpaper-entry:focus-visible { outline: 2px solid rgba(233, 139, 107, .7); outline-offset: 2px; }

/* ===== 2026-11-16 用户：圆角 + 液态渐变玻璃（替换原来的灰面） ===== */
.studio-page {
  --lg-line: rgba(255, 255, 255, .16);
  --lg-warm: rgba(233, 139, 107, .22);
  --lg-cool: rgba(112, 146, 214, .20);
  --lg-teal: rgba(108, 188, 176, .16);
}
.studio-page .wallpaper-entry {
  border-color: rgba(255, 255, 255, .18);
  background: linear-gradient(160deg, rgba(255, 255, 255, .09), rgba(255, 255, 255, .03));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .16);
}
.studio-page .studio-status {
  position: relative; isolation: isolate; overflow: hidden;
  min-width: 250px; padding: 15px 17px;
  border: 1px solid var(--lg-line); border-radius: 20px;
  background:
    radial-gradient(125% 150% at 0% 0%, var(--lg-warm), transparent 58%),
    radial-gradient(120% 150% at 100% 115%, var(--lg-cool), transparent 62%),
    linear-gradient(160deg, rgba(255, 255, 255, .10), rgba(255, 255, 255, .035));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .18), 0 26px 60px -40px rgba(0, 0, 0, 1);
  backdrop-filter: blur(16px) saturate(150%);
  -webkit-backdrop-filter: blur(16px) saturate(150%);
}
.studio-page .studio-status .status-orb { box-shadow: 0 0 0 4px rgba(143, 201, 168, .14), 0 0 16px rgba(143, 201, 168, .55); }
.studio-page .availability-form label > span { color: rgba(238, 242, 245, .55); }
.studio-page .availability-form label > div {
  display: flex; align-items: center; gap: 8px; height: 50px; padding: 0 14px;
  border: 1px solid rgba(255, 255, 255, .16); border-radius: 14px;
  background:
    radial-gradient(120% 160% at 0% 0%, rgba(112, 146, 214, .14), transparent 62%),
    linear-gradient(180deg, rgba(255, 255, 255, .085), rgba(255, 255, 255, .03));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .14);
  transition: border-color .2s ease, box-shadow .2s ease, background .2s ease;
}
.studio-page .availability-form label > div:focus-within {
  border-color: rgba(233, 139, 107, .72);
  box-shadow: 0 0 0 3px rgba(233, 139, 107, .14), inset 0 1px 0 rgba(255, 255, 255, .16);
}
.studio-page .availability-form input { color: #f2f6f9; font-size: 12.5px; }
.studio-page .availability-form .button-primary {
  min-height: 46px; padding: 0 22px; border: 0; border-radius: 999px;
  background: linear-gradient(135deg, #f6b092 0%, #ee946f 52%, #d9734f 100%);
  color: #1b2225; font-weight: 700;
  box-shadow: 0 18px 40px -18px rgba(233, 139, 107, .65), inset 0 1px 0 rgba(255, 255, 255, .45);
}
.studio-page .mini-works > div { border-radius: 14px; overflow: hidden; border: 1px solid rgba(255, 255, 255, .12); background: rgba(255, 255, 255, .04); }
.studio-page .mini-works img { filter: none; }
.studio-page .mini-works .add-work { border: 1px dashed rgba(255, 255, 255, .22); border-radius: 14px; background: rgba(255, 255, 255, .05); }
.studio-page .studio-aside .aside-card {
  padding: 20px; border: 1px solid rgba(255, 255, 255, .14); border-radius: 20px;
  background:
    radial-gradient(120% 140% at 0% 0%, rgba(233, 139, 107, .14), transparent 58%),
    radial-gradient(120% 150% at 100% 110%, rgba(112, 146, 214, .14), transparent 60%),
    linear-gradient(160deg, rgba(255, 255, 255, .09), rgba(255, 255, 255, .032));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .16), 0 26px 60px -40px rgba(0, 0, 0, 1);
  backdrop-filter: blur(14px) saturate(140%);
  -webkit-backdrop-filter: blur(14px) saturate(140%);
}
.studio-page .studio-aside .dark-card {
  border: 1px solid rgba(255, 255, 255, .18);
  background:
    radial-gradient(125% 150% at 0% 0%, rgba(233, 139, 107, .28), transparent 58%),
    radial-gradient(120% 150% at 100% 115%, rgba(112, 146, 214, .23), transparent 62%),
    linear-gradient(160deg, rgba(255, 255, 255, .10), rgba(255, 255, 255, .035));
  color: #f2f6f9;
}
.studio-page .studio-aside .dark-card .aside-line { background: rgba(255, 255, 255, .16); }
.studio-page .studio-aside .dark-card .aside-stat { color: rgba(238, 242, 245, .62); }
.studio-page .device-chips > span { border-radius: 999px; border: 1px solid rgba(255, 255, 255, .12); background: rgba(255, 255, 255, .08); color: #eef2f5; }
.studio-page .device-add { border-radius: 12px; border: 1px solid rgba(255, 255, 255, .16); background: rgba(255, 255, 255, .05); overflow: hidden; }
.studio-page .device-add button { background: rgba(255, 255, 255, .08); color: #eef2f5; }
.studio-page .tag-row i { border-radius: 999px; border: 1px solid rgba(255, 255, 255, .10); background: rgba(255, 255, 255, .07); color: rgba(238, 242, 245, .7); }
.studio-page .button-ghost { border-radius: 999px; border-color: rgba(255, 255, 255, .18); background: rgba(255, 255, 255, .05); }
@media (max-width: 720px) {
  .studio-page .studio-status { min-width: 0; width: 100%; }
  .studio-page .availability-form label > div { height: 48px; }
}
</style>



