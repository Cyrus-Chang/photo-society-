<script setup lang="ts">
import { Aperture, Camera, Check, Eye, Sparkles, Users } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import BaseModal from './BaseModal.vue'
import { brand } from '../utils/brand'
import { chooseRole, identities, session, setMbti, type RoleKey } from '../utils/session'
import { AGE_RANGES, CITIES, GENDERS, MBTI_TYPES, OCCUPATIONS, profile, saveProfile } from '../utils/profile'

defineProps<{ open: boolean }>()
const emit = defineEmits<{ (event: 'done'): void }>()

const picked = ref<RoleKey | ''>(session.role || '')
const mbti = ref(session.mbti || '')
const gender = ref(profile.gender)
const ageRange = ref(profile.ageRange)
const occupation = ref(profile.occupation)
const city = ref(profile.city)
const bio = ref(profile.bio)

const icons = { visitor: Eye, enthusiast: Camera, photographer: Aperture, creator: Sparkles, partner: Users }
const pickedLabel = computed(() => identities.find((item) => item.key === picked.value)?.label ?? '')

function confirm() {
  if (!picked.value) return
  chooseRole(picked.value)
  setMbti(mbti.value)
  saveProfile({
    gender: gender.value,
    ageRange: ageRange.value,
    occupation: occupation.value,
    city: city.value,
    bio: bio.value.trim()
  })
  emit('done')
}
</script>

<template>
  <BaseModal :open="open" labelled-by="identity-title" :close-on-backdrop="false" size="xl">
    <header class="identity-head">
      <span class="identity-eyebrow">WELCOME TO {{ brand.en }}</span>
      <h2 id="identity-title">先选一个身份，<br />我们好把首页交给你。</h2>
      <p>这一步只决定你进来先看到什么。资料只保存在本机，之后随时能在「个人信息」里改。</p>
    </header>

    <div class="identity-body">
      <div class="identity-list" role="radiogroup" aria-labelledby="identity-title">
        <button
          v-for="(item, index) in identities"
          :key="item.key"
          type="button"
          class="identity-row"
          :class="{ active: picked === item.key }"
          :style="{ '--i': index }"
          role="radio"
          :aria-checked="picked === item.key"
          @click="picked = item.key"
        >
          <span class="identity-icon"><component :is="icons[item.key]" :size="18" /></span>
          <span class="identity-copy">
            <strong>{{ item.label }}</strong>
            <small>{{ item.hint }}</small>
            <em>{{ item.entry }}</em>
          </span>
          <span class="identity-radio" aria-hidden="true"><i><Check :size="11" /></i></span>
        </button>
      </div>

      <div class="identity-profile">
        <div class="identity-profile-head"><span>PROFILE / 可选填</span><small>只用于推荐与搭子匹配</small></div>

        <fieldset class="identity-field">
          <legend>性别</legend>
          <div class="identity-chips">
            <button v-for="item in GENDERS" :key="item" type="button" :class="{ active: gender === item }" :aria-pressed="gender === item" @click="gender = item">{{ item }}</button>
          </div>
        </fieldset>

        <fieldset class="identity-field">
          <legend>年龄段</legend>
          <div class="identity-chips">
            <button v-for="item in AGE_RANGES" :key="item" type="button" :class="{ active: ageRange === item }" :aria-pressed="ageRange === item" @click="ageRange = ageRange === item ? '' : item">{{ item }}</button>
          </div>
        </fieldset>

        <div class="identity-field-row">
          <label class="identity-field">
            <span>职业</span>
            <select v-model="occupation">
              <option value="">先不填</option>
              <option v-for="item in OCCUPATIONS" :key="item" :value="item">{{ item }}</option>
            </select>
          </label>
          <label class="identity-field">
            <span>常驻城市</span>
            <select v-model="city">
              <option v-for="item in CITIES" :key="item" :value="item">{{ item }}</option>
            </select>
          </label>
        </div>

        <label class="identity-field">
          <span>一句话简介 <small>{{ bio.length }} / 60</small></span>
          <input v-model="bio" type="text" maxlength="60" placeholder="例如：想拍一组有风的街头人像" />
        </label>

        <label class="identity-field">
          <span>MBTI（可选 · 只用于搭子匹配）</span>
          <select v-model="mbti">
            <option value="">先不填</option>
            <option v-for="type in MBTI_TYPES" :key="type" :value="type">{{ type }}</option>
          </select>
        </label>
      </div>
    </div>

    <footer class="identity-foot">
      <p>身份只影响推荐与入口，不会限制你能做什么。</p>
      <button class="identity-confirm" type="button" :disabled="!picked" @click="confirm">
        {{ picked ? `以「${pickedLabel}」继续` : '先选一个身份' }}
        <span aria-hidden="true">→</span>
      </button>
    </footer>
  </BaseModal>
</template>

<style scoped>
.identity-head { display: grid; gap: 10px; margin-bottom: 18px; }
.identity-eyebrow { font: 9px/1 ui-monospace, SFMono-Regular, Menlo, monospace; letter-spacing: .22em; color: #e98b6b; }
.identity-head h2 { margin: 0; font-family: 'Noto Serif SC', 'Songti SC', serif; font-size: clamp(24px, 2.6vw, 32px); font-weight: 600; line-height: 1.24; letter-spacing: -.03em; color: #eef2f5; }
.identity-head p { margin: 0; color: rgba(238, 242, 245, .56); font-size: 12px; line-height: 1.7; }

.identity-body { display: grid; grid-template-columns: minmax(0, 300px) minmax(0, 1fr); gap: 26px; align-items: start; }

.identity-list { display: grid; gap: 7px; }
.identity-row {
  display: grid;
  grid-template-columns: 34px 1fr 18px;
  align-items: center;
  gap: 10px;
  padding: 10px 11px;
  border-radius: 12px;
  border: 1px solid rgba(238, 242, 245, .11);
  background: rgba(238, 242, 245, .022);
  color: #dfe7ea;
  text-align: left;
  cursor: pointer;
  transition: border-color .22s ease, background .22s ease, transform .22s ease;
  animation: identity-in .42s cubic-bezier(.2, .8, .2, 1) both;
  animation-delay: calc(var(--i) * 40ms);
}
.identity-row:hover { border-color: rgba(233, 139, 107, .45); background: rgba(233, 139, 107, .05); transform: translateX(2px); }
.identity-row.active { border-color: rgba(233, 139, 107, .8); background: rgba(233, 139, 107, .11); box-shadow: 0 10px 26px rgba(0, 0, 0, .18); }
.identity-icon { display: grid; place-items: center; width: 34px; height: 34px; border-radius: 10px; background: rgba(233, 139, 107, .11); color: #e98b6b; }
.identity-copy { display: grid; gap: 1px; min-width: 0; }
.identity-copy strong { font-size: 13px; font-weight: 600; }
.identity-copy small { color: rgba(238, 242, 245, .46); font-size: 10.5px; line-height: 1.4; }
.identity-copy em { color: rgba(238, 242, 245, .3); font: 9px/1.4 ui-monospace, SFMono-Regular, Menlo, monospace; letter-spacing: .04em; font-style: normal; }
.identity-row.active .identity-copy em { color: rgba(244, 166, 136, .78); }
.identity-radio { display: grid; place-items: center; width: 16px; height: 16px; border-radius: 50%; border: 1px solid rgba(238, 242, 245, .24); color: transparent; transition: border-color .2s ease, background .2s ease; }
.identity-radio i { display: grid; place-items: center; width: 11px; height: 11px; }
.identity-row.active .identity-radio { border-color: #e98b6b; background: #e98b6b; color: #1b2225; }

.identity-profile { display: grid; gap: 12px; min-width: 0; }
.identity-profile-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; padding-bottom: 9px; border-bottom: 1px solid rgba(238, 242, 245, .1); }
.identity-profile-head span { font: 9px/1 ui-monospace, SFMono-Regular, Menlo, monospace; letter-spacing: .14em; color: #e98b6b; }
.identity-profile-head small { color: rgba(238, 242, 245, .38); font-size: 9.5px; }

.identity-field { display: grid; gap: 6px; min-width: 0; margin: 0; padding: 0; border: 0; }
.identity-field > span, .identity-field legend { padding: 0; color: rgba(238, 242, 245, .56); font-size: 10.5px; letter-spacing: .02em; }
.identity-field > span small { margin-left: 4px; color: rgba(238, 242, 245, .3); font-size: 9px; }
.identity-field select,
.identity-field input {
  width: 100%;
  min-height: 38px;
  padding: 0 10px;
  border-radius: 9px;
  border: 1px solid rgba(238, 242, 245, .13);
  background: rgba(238, 242, 245, .03);
  color: #eef2f5;
  font-size: 12px;
  outline: none;
  transition: border-color .2s ease, background .2s ease;
}
.identity-field select { padding-right: 24px; }
.identity-field select:focus, .identity-field input:focus { border-color: rgba(233, 139, 107, .65); background: rgba(233, 139, 107, .05); }
.identity-field input::placeholder { color: rgba(238, 242, 245, .3); }

.identity-chips { display: flex; flex-wrap: wrap; gap: 5px; }
.identity-chips button {
  min-height: 32px;
  padding: 0 11px;
  border-radius: 999px;
  border: 1px solid rgba(238, 242, 245, .13);
  background: transparent;
  color: rgba(238, 242, 245, .52);
  font-size: 10.5px;
  transition: border-color .18s ease, background .18s ease, color .18s ease;
}
.identity-chips button:hover { border-color: rgba(233, 139, 107, .45); color: #f3d9cd; }
.identity-chips button.active { border-color: rgba(233, 139, 107, .7); background: rgba(233, 139, 107, .14); color: #ffd9c9; }
.identity-field-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }

.identity-foot { display: flex; align-items: center; justify-content: space-between; gap: 18px; margin-top: 20px; padding-top: 16px; border-top: 1px solid rgba(238, 242, 245, .1); }
.identity-foot p { margin: 0; color: rgba(238, 242, 245, .38); font-size: 10px; }
.identity-confirm {
  display: inline-flex; align-items: center; justify-content: center; gap: 10px;
  min-height: 46px; padding: 0 22px; border: 0; border-radius: 999px; cursor: pointer;
  background: linear-gradient(135deg, #f2a080, #e98b6b 55%, #d9734f);
  color: #1b2225; font-size: 12.5px; font-weight: 700; letter-spacing: .02em;
  box-shadow: 0 18px 40px rgba(233, 139, 107, .26);
  transition: transform .25s ease, box-shadow .25s ease, opacity .25s ease;
}
.identity-confirm:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 24px 52px rgba(233, 139, 107, .32); }
.identity-confirm:disabled { opacity: .42; cursor: not-allowed; }

@keyframes identity-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
@media (max-width: 860px) {
  .identity-body { grid-template-columns: 1fr; gap: 18px; }
  .identity-foot { align-items: stretch; flex-direction: column; }
  .identity-confirm { width: 100%; }
}
@media (prefers-reduced-motion: reduce) { .identity-row { animation: none; } .identity-row:hover { transform: none; } }
</style>
