<script setup lang="ts">
import { ArrowRight, CalendarDays, Camera, Check, CheckCircle2, ImagePlus, MapPin, Plus, Send, Upload, X } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { photographers, works } from '../data/mock'
import { resolveWorkImage } from '../utils/media'

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
  <div class="studio-page"><section class="simple-page-head studio-head"><div><p class="kicker"><span class="kicker-line" />摄影师工作台</p><h1>让别人知道，<br /><em>你什么时候在现场。</em></h1><p>打开接单状态，发布一段可到场的档期。作品会先替你说话。</p></div><div class="studio-status" :class="{ on: enabled }"><span class="status-orb" /><div><strong>{{ enabled ? '正在接单' : '暂不接单' }}</strong><small>{{ enabled ? '附近的人可以在作品里找到你' : '你可以随时重新打开' }}</small></div><button @click="enabled = !enabled" :aria-label="enabled ? '关闭接单' : '开启接单'"><span /></button></div></section><section class="studio-grid"><div class="studio-main"><div class="studio-section-head"><div><span class="section-index">01 / AVAILABILITY</span><h2>发布一段档期</h2></div><span class="muted-copy">让时间和地点先被看见</span></div><div class="availability-form"><label><span>在哪儿</span><div><MapPin :size="16" /><input value="西安 · 曲江池附近" /></div></label><label><span>哪天</span><div><CalendarDays :size="16" /><input value="周日 · 11 月 15 日" /></div></label><label><span>什么时间</span><div><input value="15:00—18:00" /></div></label><label class="wide"><span>补充一句</span><div><input value="自然光人像，不赶场，可以一起看参考图。" /></div></label><button class="button button-primary" @click="published = true"><Send :size="16" />发布这段档期</button></div><div v-if="published" class="success-panel"><CheckCircle2 :size="18" /><span><strong>档期已发布</strong>附近的人现在可以在集市里看到它。</span></div><div class="studio-section-head studio-works-head"><div><span class="section-index">02 / PORTFOLIO · CYRUS_CHANG</span><h2>公开作品集</h2></div><button class="button button-ghost button-small" @click="uploadOpen = true"><ImagePlus :size="15" />上传作品</button></div><div class="mini-works"><div v-for="work in portfolioWorks" :key="work.id"><img :src="resolveWorkImage(work.imageUrl)" :alt="work.title" /><span>{{ work.location }}</span></div><button class="add-work" @click="uploadOpen = true"><Plus :size="20" /><span>添加新作品</span></button></div></div><aside class="studio-aside"><div class="aside-card dark-card"><span class="eyebrow">本周现场</span><strong>3</strong><span>段可约档期</span><div class="aside-line" /><div class="aside-stat"><span>作品被看见</span><b>128</b></div><div class="aside-stat"><span>收到约拍请求</span><b>6</b></div><router-link to="/market">去看附近需求 <ArrowRight :size="15" /></router-link></div><div class="aside-card device-card"><div class="device-card-head"><Camera :size="18" /><span><strong>账号设备</strong><small>会展示在主页和每张作品下</small></span></div><div class="device-chips"><span v-for="device in devices" :key="device">{{ device }}<button @click="removeDevice(device)" :aria-label="`移除 ${device}`">×</button></span></div><div class="device-add"><input v-model="newDevice" placeholder="添加机型，如 Fujifilm X-T5" @keyup.enter="addDevice" /><button @click="addDevice"><Plus :size="14" /></button></div><router-link class="device-profile-link" to="/photographers/p-cyrus">查看 Cyrus_chang 公开主页 <ArrowRight :size="14" /></router-link></div><div class="aside-card"><Camera :size="20" /><h3>作品标签已就绪</h3><p>风格和类型分开记录，找人拍照的人可以按“蓝调”“人像”“建筑”等关键词找到你。</p><span class="tag-row"><i>蓝调</i><i>建筑</i><i>人像</i></span></div></aside></section><div v-if="uploadOpen" class="modal-backdrop" @click.self="uploadOpen = false"><div class="upload-modal"><button class="modal-close" @click="uploadOpen = false"><X :size="21" /></button><p class="eyebrow">PORTFOLIO / UPLOAD</p><h2>上传作品并打标签</h2><p class="modal-subtitle">风格和类型会分别展示，设备会跟随账号同步到作品下方。</p><input ref="uploadInput" class="sr-only" type="file" accept="image/jpeg,image/png" multiple @change="handleFiles" /><div v-if="!pendingUploads.length" class="upload-dropzone" @click="openPicker"><Upload :size="22" /><strong>点击选择图片</strong><span>最多 6 张 · JPG / PNG</span></div><div v-else class="upload-previews"><div v-for="(file, index) in pendingUploads" :key="file.url"><img :src="file.url" :alt="file.name" /><button @click="removeUpload(index)" :aria-label="`移除 ${file.name}`"><X :size="14" /></button></div><button class="upload-add-more" @click="openPicker"><Plus :size="18" />继续添加</button></div><div class="tag-editor"><div><span>风格标签</span><div class="tag-options"><button v-for="tag in styleOptions" :key="tag" :class="{ selected: selectedStyles.includes(tag) }" @click="toggleTag(selectedStyles, tag)"><Check v-if="selectedStyles.includes(tag)" :size="12" />{{ tag }}</button></div></div><div><span>类型标签</span><div class="tag-options"><button v-for="tag in typeOptions" :key="tag" :class="{ selected: selectedTypes.includes(tag) }" @click="toggleTag(selectedTypes, tag)"><Check v-if="selectedTypes.includes(tag)" :size="12" />{{ tag }}</button></div></div></div><div class="upload-modal-footer"><span>{{ pendingUploads.length || 0 }} 张待上传</span><button class="button button-primary" :disabled="!pendingUploads.length" @click="saveUploads">保存到作品集 <ArrowRight :size="16" /></button></div></div></div></div>
</template>



