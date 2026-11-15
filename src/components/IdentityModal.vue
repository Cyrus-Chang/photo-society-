<script setup lang="ts">
import { Aperture, Camera, Eye, Sparkles, Users } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import BaseModal from './BaseModal.vue'
import { brand } from '../utils/brand'
import { chooseRole, identities, setMbti, type RoleKey } from '../utils/session'

defineProps<{ open: boolean }>()
const emit = defineEmits<{ (event: 'done'): void }>()

const MBTI_TYPES = ['INTJ', 'INTP', 'ENTJ', 'ENTP', 'INFJ', 'INFP', 'ENFJ', 'ENFP', 'ISTJ', 'ISFJ', 'ESTJ', 'ESFJ', 'ISTP', 'ISFP', 'ESTP', 'ESFP']

const picked = ref<RoleKey | ''>('')
const mbti = ref('')
const icons = { visitor: Eye, enthusiast: Camera, photographer: Aperture, creator: Sparkles, partner: Users }
const pickedLabel = computed(() => identities.find((item) => item.key === picked.value)?.label ?? '')

function confirm() {
  if (!picked.value) return
  chooseRole(picked.value)
  setMbti(mbti.value)
  emit('done')
}
</script>

<template>
  <BaseModal :open="open" labelled-by="identity-title" :close-on-backdrop="false" size="lg">
    <header class="identity-head">
      <span class="identity-eyebrow">WELCOME TO {{ brand.en }}</span>
      <h2 id="identity-title">先选一个身份，<br />我们好把首页交给你。</h2>
      <p>这一步只决定你进来先看到什么，之后可以在个人菜单里切换。</p>
    </header>

    <div class="identity-grid" role="radiogroup" aria-labelledby="identity-title">
      <button
        v-for="(item, index) in identities"
        :key="item.key"
        type="button"
        class="identity-card"
        :class="{ active: picked === item.key }"
        :style="{ '--i': index }"
        role="radio"
        :aria-checked="picked === item.key"
        @click="picked = item.key"
      >
        <span class="identity-icon"><component :is="icons[item.key]" :size="19" /></span>
        <span class="identity-copy">
          <strong>{{ item.label }}</strong>
          <small>{{ item.hint }}</small>
        </span>
        <span class="identity-entry">{{ item.entry }}</span>
      </button>
    </div>

    <div class="identity-extra">
      <span class="identity-extra-label">MBTI（可选 · 只用于搭子匹配）</span>
      <div class="identity-select">
        <Users :size="15" />
        <select v-model="mbti" aria-label="MBTI 类型">
          <option value="">先不填</option>
          <option v-for="type in MBTI_TYPES" :key="type" :value="type">{{ type }}</option>
        </select>
      </div>
      <small>填了才会按性格相容度排序；之后可以在资料里补或改。</small>
    </div>

    <footer class="identity-foot">
      <p>身份只影响推荐与入口，不会限制你能做什么。</p>
      <button class="identity-confirm" type="button" :disabled="!picked" @click="confirm">
        {{ picked ? `以「${pickedLabel}」进入拍社` : '先选一个身份' }}
        <span aria-hidden="true">→</span>
      </button>
    </footer>
  </BaseModal>
</template>

<style scoped>
.identity-head { display: grid; gap: 10px; margin-bottom: 22px; }
.identity-eyebrow { font: 9px/1 'DM Mono', ui-monospace, monospace; letter-spacing: .22em; color: #e98b6b; }
.identity-head h2 { margin: 0; font-family: 'Noto Serif SC', 'Songti SC', serif; font-size: clamp(24px, 3vw, 34px); font-weight: 600; line-height: 1.28; letter-spacing: -.02em; }
.identity-head p { margin: 0; color: #9aa8ad; font-size: 12px; line-height: 1.7; }
.identity-grid { display: grid; gap: 10px; grid-template-columns: repeat(2, minmax(0, 1fr)); }
.identity-card {
  display: grid; grid-template-columns: 38px 1fr; grid-template-rows: auto auto; gap: 4px 12px;
  align-items: center; text-align: left; padding: 14px;
  border-radius: 16px; border: 1px solid rgba(237, 241, 244, .12);
  background: rgba(237, 241, 244, .025); color: #dfe7ea; cursor: pointer;
  transition: border-color .25s ease, background .25s ease, transform .25s ease;
  animation: identity-in .45s cubic-bezier(.2, .8, .2, 1) both;
  animation-delay: calc(var(--i) * 45ms);
}
.identity-card:hover { border-color: rgba(233, 139, 107, .45); background: rgba(233, 139, 107, .06); transform: translateY(-1px); }
.identity-card.active { border-color: #e98b6b; background: rgba(233, 139, 107, .12); box-shadow: 0 12px 30px rgba(233, 139, 107, .12); }
.identity-icon { grid-row: span 2; display: grid; place-items: center; width: 38px; height: 38px; border-radius: 12px; background: rgba(233, 139, 107, .12); color: #e98b6b; }
.identity-copy { display: grid; gap: 2px; }
.identity-copy strong { font-size: 14px; font-weight: 600; }
.identity-copy small { color: #93a1a7; font-size: 11px; line-height: 1.5; }
.identity-entry { grid-column: 2; font: 9px/1.4 ui-monospace, monospace; letter-spacing: .08em; color: #7f8d93; }
.identity-card.active .identity-entry { color: #f2a080; }
.identity-extra { display: grid; gap: 8px; margin-top: 18px; }
.identity-extra-label { color: #93a1a7; font-size: 11px; }
.identity-extra small { color: #7f8d93; font-size: 10px; line-height: 1.6; }
.identity-select { display: flex; align-items: center; gap: 9px; min-height: 44px; padding: 0 12px; border-radius: 12px; border: 1px solid rgba(237, 241, 244, .13); background: rgba(237, 241, 244, .035); color: #87949a; transition: border-color .2s ease, background .2s ease; }
.identity-select:focus-within { border-color: rgba(233, 139, 107, .7); background: rgba(233, 139, 107, .06); }
.identity-select select { flex: 1; min-width: 0; background: transparent; border: 1px solid transparent; outline: none; color: #eef3f5; font-size: 13px; cursor: pointer; padding: 6px 0; }
.identity-select select option { background: #0d141a; color: #eef3f5; }

.identity-foot { display: grid; gap: 12px; margin-top: 22px; }
.identity-foot p { margin: 0; color: #7f8d93; font-size: 11px; }
.identity-confirm {
  display: inline-flex; align-items: center; justify-content: center; gap: 10px;
  min-height: 48px; border: 0; border-radius: 999px; cursor: pointer;
  background: linear-gradient(135deg, #f2a080, #e98b6b 55%, #d9734f);
  color: #1b2225; font-size: 13px; font-weight: 700; letter-spacing: .02em;
  box-shadow: 0 18px 40px rgba(233, 139, 107, .28);
  transition: transform .25s ease, box-shadow .25s ease, opacity .25s ease;
}
.identity-confirm:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 24px 52px rgba(233, 139, 107, .34); }
.identity-confirm:active:not(:disabled) { transform: translateY(0) scale(.99); }
.identity-confirm:disabled { opacity: .45; cursor: not-allowed; }
@keyframes identity-in { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
@media (max-width: 620px) { .identity-grid { grid-template-columns: 1fr; } }
@media (prefers-reduced-motion: reduce) { .identity-card { animation: none; } }
</style>
