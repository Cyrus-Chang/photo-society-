<script setup lang="ts">
import { ArrowLeft, ArrowRight, Camera, Check, ChevronDown, MapPin, ScanSearch, Sparkles } from 'lucide-vue-next'
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import WorkAuditPanel from '../components/WorkAuditPanel.vue'

const router = useRouter(); const type = ref('requirement'); const submitted = ref(false)
const options = [{ key: 'requirement', label: '我在找摄影师', hint: '说清楚你的时间、地点和想拍的感觉' }, { key: 'availability', label: '我有一段档期', hint: '告诉附近的人，你什么时候可以到场' }, { key: 'companion', label: '我想找搭子', hint: '一起去拍，先把关系和边界说清楚' }]
</script>

<template>
  <div class="publish-page"><router-link class="back-link" to="/market"><ArrowLeft :size="16" />返回拍摄接拍</router-link><section class="publish-layout"><div class="publish-intro"><p class="kicker"><span class="kicker-line" />发布现场信息</p><h1>把你要拍的，<br /><em>交给刚好有空的人。</em></h1><p>接拍里的每条信息都写清地点、时间和关系。你可以先发布，之后再决定要不要继续聊。</p><div class="publish-note"><Sparkles :size="16" /><span>小提示<br /><strong>参考图会让摄影师更快理解你的现场。</strong></span></div></div><div class="publish-form-card"><div class="publish-type-list"><button v-for="option in options" :key="option.key" :class="{ active: type === option.key }" @click="type = option.key"><span class="type-radio"><Check v-if="type === option.key" :size="13" /></span><span><strong>{{ option.label }}</strong><small>{{ option.hint }}</small></span><ArrowRight :size="16" /></button></div><div class="form-divider" /><div class="publish-fields"><label><span>标题</span><input :value="type === 'companion' ? '周六一起去城墙边拍秋天' : type === 'availability' ? '周日曲江自然光人像，有空档' : '周六小寨古风夜景，想找一位摄影师'" /></label><div class="two-fields"><label><span>地点</span><div><MapPin :size="16" /><input value="西安 · 小寨" /></div></label><label><span>时间</span><div><input value="周六 · 18:00—21:00" /><ChevronDown :size="16" /></div></label></div><label><span>说说现场</span><textarea rows="4">有服化，想拍 2 小时左右，喜欢灯笼、街巷和走动中的状态。</textarea></label><div class="upload-box"><Camera :size="21" /><div><strong>拖入参考图，或点击上传</strong><span>最多 6 张 · JPG / PNG · 每张 10MB 以内</span></div><button aria-label="选择图片">选择图片</button></div><WorkAuditPanel /><div class="wa-wall-note"><ScanSearch :size="14" /><span><strong>作品墙提示</strong>发布的作品会进入平台作品库，并参与「样片比对」——与约拍线的以图搜图形成闭环。</span></div><div class="publish-form-footer"><span><i />发布后可随时编辑或下架</span><button class="button button-primary" @click="submitted = true">发布到接拍 <ArrowRight :size="17" /></button></div></div></div></section><div v-if="submitted" class="modal-backdrop" @click.self="router.push('/market')"><div class="success-modal"><div class="success-icon"><Check :size="22" /></div><p class="eyebrow">POSTED / LIVE</p><h2>这条现场信息已经发布</h2><p>发布完成，你可以回到接拍查看这条信息，也可以继续编辑。</p><div><button class="button button-primary" @click="router.push('/market')">去看拍摄接拍 <ArrowRight :size="16" /></button><button class="quiet-link" @click="submitted = false">继续编辑</button></div></div></div></div>
</template>

<style scoped>
.wa-wall-note {
  min-width: 0;
  overflow-wrap: anywhere;
}
</style>
