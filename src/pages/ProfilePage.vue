<script setup lang="ts">
import { ArrowLeft, Camera, Check, Image as ImageIcon, RotateCcw, ShieldCheck } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { makeAvatar } from '../utils/avatar'
import { fileToCompressedDataUrl } from '../utils/imageTools'
import { clearAvatar, clearWallpaper, openWallpaperPicker, personalize, setAvatar, wallpaperName, wallpaperStyle } from '../utils/personalize'
import { AGE_RANGES, AVAILABILITY, CITIES, GENDERS, MBTI_TYPES, OCCUPATIONS, STYLE_PREFS, profile, saveProfile } from '../utils/profile'
import { chooseRole, identities, session, setMbti, setName, type RoleKey } from '../utils/session'

const name = ref(session.name)
const role = ref<string>(session.role)
const mbti = ref(session.mbti)
const gender = ref(profile.gender)
const ageRange = ref(profile.ageRange)
const occupation = ref(profile.occupation)
const city = ref(profile.city)
const bio = ref(profile.bio)
const styles = ref<string[]>([...profile.styles])
const device = ref(profile.device)
const availability = ref(profile.availability)
const matchProfile = ref(profile.matchProfile)
const savedAt = ref('')

const avatar = computed(() => makeAvatar(name.value))
const avatarSrc = computed(() => personalize.avatar || avatar.value)
// 2026-11-16 用户：头像可上传。压成 512 方图后存本机，顶栏同步；失败如实提示。
const avatarInput = ref<HTMLInputElement | null>(null)
const avatarBusy = ref(false)
const avatarError = ref('')

async function onAvatarChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  avatarError.value = ''
  avatarBusy.value = true
  try {
    const dataUrl = await fileToCompressedDataUrl(file, { maxEdge: 512, square: true, quality: 0.86 })
    if (!setAvatar(dataUrl)) avatarError.value = '这张图太大，本机存不下；换一张小一点的。'
  } catch (err) {
    avatarError.value = err instanceof Error ? err.message : '这张图没有处理成功，换一张试试'
  } finally {
    avatarBusy.value = false
  }
}
const roleText = computed(() => identities.find((item) => item.key === role.value)?.label || '未选身份')
const sinceLabel = computed(() => {
  if (!session.since) return '今天'
  return new Date(session.since).toLocaleDateString('zh-CN', { year: 'numeric', month: 'long' })
})
const completeness = computed(() => {
  const checks = [
    gender.value !== '不公开',
    Boolean(ageRange.value),
    Boolean(occupation.value),
    Boolean(city.value),
    Boolean(bio.value.trim()),
    styles.value.length > 0,
    Boolean(device.value.trim())
  ]
  return Math.round((checks.filter(Boolean).length / checks.length) * 100)
})

function toggleStyle(item: string) {
  const index = styles.value.indexOf(item)
  if (index >= 0) styles.value.splice(index, 1)
  else styles.value.push(item)
}

function save() {
  setName(name.value)
  if (role.value) chooseRole(role.value as RoleKey)
  setMbti(mbti.value)
  saveProfile({
    gender: gender.value,
    ageRange: ageRange.value,
    occupation: occupation.value,
    city: city.value,
    bio: bio.value.trim(),
    styles: [...styles.value],
    device: device.value.trim(),
    availability: availability.value,
    matchProfile: matchProfile.value
  })
  savedAt.value = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function reset() {
  name.value = session.name
  role.value = session.role
  mbti.value = session.mbti
  gender.value = profile.gender
  ageRange.value = profile.ageRange
  occupation.value = profile.occupation
  city.value = profile.city
  bio.value = profile.bio
  styles.value = [...profile.styles]
  device.value = profile.device
  availability.value = profile.availability
  matchProfile.value = profile.matchProfile
  savedAt.value = ''
}
</script>

<template>
  <div class="profile-page">
    <header class="profile-head">
      <RouterLink class="profile-back" to="/discover"><ArrowLeft :size="14" />返回约拍</RouterLink>
      <span class="profile-eyebrow">PERSONAL FILE / 2026</span>
      <h1>你的拍摄档案</h1>
      <p>资料只保存在这台设备的浏览器里，不会上传。改完点「保存修改」，约拍与搭子匹配会用这份信息。</p>
    </header>

    <div class="profile-layout">
      <aside class="profile-card">
        <button class="profile-avatar-edit" type="button" :aria-label="personalize.avatar ? '更换头像' : '上传头像'" @click="avatarInput?.click()">
          <img class="profile-avatar" :src="avatarSrc" :alt="`${name || '我'}的头像`" />
          <span class="profile-avatar-hint"><Camera :size="13" aria-hidden="true" />{{ avatarBusy ? '处理中…' : '更换头像' }}</span>
        </button>
        <input ref="avatarInput" type="file" accept="image/*" hidden @change="onAvatarChange" />
        <button v-if="personalize.avatar" class="profile-avatar-reset" type="button" @click="clearAvatar()">恢复默认头像</button>
        <p v-if="avatarError" class="profile-avatar-error" role="status">{{ avatarError }}</p>
        <strong class="profile-name">{{ name || '未命名' }}</strong>
        <span class="profile-role">{{ roleText }}<i />{{ city }}</span>
        <p class="profile-bio" :class="{ 'is-empty': !bio.trim() }">{{ bio.trim() || '还没有写一句话简介。' }}</p>

        <div class="profile-completeness">
          <div><span>资料完整度</span><b>{{ completeness }}%</b></div>
          <i><span :style="{ width: `${completeness}%` }" /></i>
        </div>

        <dl class="profile-meta">
          <div><dt>加入拍社</dt><dd>{{ sinceLabel }}</dd></div>
          <div><dt>资料存放</dt><dd>本机 localStorage</dd></div>
          <div><dt>当前身份</dt><dd>{{ roleText }}</dd></div>
        </dl>

        <p class="profile-note"><ShieldCheck :size="14" /><span>换浏览器或清缓存后需要重新填写；资料不会同步到其他设备。</span></p>
      </aside>

      <div class="profile-form">
        <section class="profile-section">
          <div class="profile-section-head"><span>01</span><h2>基础资料</h2><small>会用在约拍与接拍</small></div>
          <div class="profile-fields">
            <label class="profile-field">
              <span>显示称呼</span>
              <input v-model="name" type="text" maxlength="20" placeholder="你的称呼" />
            </label>

            <fieldset class="profile-field">
              <legend>性别</legend>
              <div class="profile-chips">
                <button v-for="item in GENDERS" :key="item" type="button" :class="{ active: gender === item }" :aria-pressed="gender === item" @click="gender = item">{{ item }}</button>
              </div>
            </fieldset>

            <fieldset class="profile-field">
              <legend>年龄段</legend>
              <div class="profile-chips">
                <button v-for="item in AGE_RANGES" :key="item" type="button" :class="{ active: ageRange === item }" :aria-pressed="ageRange === item" @click="ageRange = ageRange === item ? '' : item">{{ item }}</button>
              </div>
            </fieldset>

            <div class="profile-row">
              <label class="profile-field">
                <span>职业</span>
                <select v-model="occupation">
                  <option value="">先不填</option>
                  <option v-for="item in OCCUPATIONS" :key="item" :value="item">{{ item }}</option>
                </select>
              </label>
              <label class="profile-field">
                <span>常驻城市</span>
                <select v-model="city">
                  <option v-for="item in CITIES" :key="item" :value="item">{{ item }}</option>
                </select>
              </label>
            </div>

            <label class="profile-field">
              <span>一句话简介 <small>{{ bio.length }} / 60</small></span>
              <input v-model="bio" type="text" maxlength="60" placeholder="例如：想拍一组有风的街头人像" />
            </label>
          </div>
        </section>

        <section class="profile-section">
          <div class="profile-section-head"><span>02</span><h2>拍摄偏好</h2><small>用于推荐与搭子匹配</small></div>
          <div class="profile-fields">
            <fieldset class="profile-field">
              <legend>喜欢的风格（可多选）</legend>
              <div class="profile-chips profile-chips--styles">
                <button v-for="item in STYLE_PREFS" :key="item" type="button" :class="{ active: styles.includes(item) }" :aria-pressed="styles.includes(item)" @click="toggleStyle(item)">{{ item }}</button>
              </div>
            </fieldset>

            <div class="profile-row">
              <label class="profile-field">
                <span>常用机型</span>
                <input v-model="device" type="text" maxlength="30" placeholder="例如：索尼 A7M5 / 手机" />
              </label>
              <fieldset class="profile-field">
                <legend>方便的时间</legend>
                <div class="profile-chips">
                  <button v-for="item in AVAILABILITY" :key="item" type="button" :class="{ active: availability === item }" :aria-pressed="availability === item" @click="availability = item">{{ item }}</button>
                </div>
              </fieldset>
            </div>
          </div>
        </section>

        <section class="profile-section">
          <div class="profile-section-head"><span>03</span><h2>身份与匹配</h2><small>影响入口与推荐</small></div>
          <div class="profile-row">
            <label class="profile-field">
              <span>身份</span>
              <select v-model="role">
                <option value="">先不选</option>
                <option v-for="item in identities" :key="item.key" :value="item.key">{{ item.label }}</option>
              </select>
            </label>
            <label class="profile-field">
              <span>MBTI（只用于搭子匹配）</span>
              <select v-model="mbti">
                <option value="">先不填</option>
                <option v-for="type in MBTI_TYPES" :key="type" :value="type">{{ type }}</option>
              </select>
            </label>
          </div>

          <label class="profile-switch">
            <input v-model="matchProfile" type="checkbox" />
            <span class="profile-switch-track"><i /></span>
            <span class="profile-switch-copy">
              <strong>允许在匹配中参考年龄段与职业</strong>
              <small>关闭后只按地点、时间、预算与风格匹配；资料仍然只存在本机。</small>
            </span>
          </label>
        </section>

        <section class="profile-section">
          <div class="profile-section-head"><span>04</span><h2>个性化</h2><small>只在这台设备生效</small></div>
          <div class="profile-personalize">
            <div class="personalize-wallpaper">
              <span class="personalize-thumb" :style="wallpaperStyle(personalize.wallpaper) ?? undefined">
                <ImageIcon v-if="!personalize.wallpaper" :size="18" aria-hidden="true" />
              </span>
              <div class="personalize-copy">
                <strong>页面壁纸 · {{ wallpaperName(personalize.wallpaper) }}</strong>
                <small>一张，用在个人信息、摄影工作台和我的约拍；只保存这台设备。</small>
              </div>
              <div class="personalize-actions">
                <button class="personalize-btn" type="button" @click="openWallpaperPicker()">选择壁纸</button>
                <button v-if="personalize.wallpaper" class="personalize-link" type="button" @click="clearWallpaper()">恢复默认</button>
              </div>
            </div>
            <p class="personalize-note">头像与壁纸都只存在这个浏览器里，不会上传；换设备或清缓存会回到默认。</p>
          </div>
        </section>
      </div>
    </div>

    <div class="profile-actions">
      <span v-if="savedAt" class="profile-saved"><Check :size="14" />已保存 · {{ savedAt }}</span>
      <span v-else class="profile-hint">改动只在本机生效</span>
      <button class="profile-reset" type="button" @click="reset"><RotateCcw :size="14" />还原</button>
      <button class="profile-save" type="button" @click="save"><Check :size="15" />保存修改</button>
    </div>
  </div>
</template>

<style scoped>
.profile-page {
  --p-ink: #eef2f5;
  --p-ink-2: rgba(238, 242, 245, .7);
  --p-ink-3: rgba(238, 242, 245, .46);
  --p-line: rgba(238, 242, 245, .12);
  --p-coral: #e9896b;
  --p-mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  max-width: 1180px;
  margin: 0 auto;
  padding: clamp(22px, 4vw, 48px) 0 96px;
  color: var(--p-ink);
  /* 2026-11-16：壁纸层是 App.vue 里的 fixed 节点（z-index 0），页面内容抬到它上面 */
  position: relative;
  z-index: 1;
}

.profile-back { display: inline-flex; align-items: center; gap: 6px; min-height: 34px; color: var(--p-ink-3); font-size: 11px; transition: color .2s ease; }
.profile-back:hover { color: var(--p-coral); }
.profile-eyebrow { display: block; margin-top: 14px; font: 9px/1 var(--p-mono); letter-spacing: .22em; color: var(--p-coral); }
.profile-head h1 { margin: 12px 0 12px; font-family: 'Noto Serif SC', 'Songti SC', serif; font-size: clamp(36px, 4.8vw, 58px); font-weight: 600; letter-spacing: -.06em; line-height: 1.04; }
.profile-head p { margin: 0; max-width: 600px; color: var(--p-ink-3); font-size: 12.5px; line-height: 1.85; }

.profile-layout { display: grid; grid-template-columns: minmax(0, 330px) minmax(0, 1fr); gap: clamp(26px, 4vw, 56px); align-items: start; margin-top: 34px; }

.profile-card {
  position: sticky;
  top: 100px;
  display: grid;
  gap: 0;
  padding: 22px;
  border-radius: 22px;
  border: 1px solid var(--p-line);
  background:
    radial-gradient(110% 80% at 15% 0%, rgba(233, 139, 107, .1), transparent 55%),
    linear-gradient(165deg, rgba(238, 242, 245, .045), rgba(238, 242, 245, .012));
  box-shadow: 0 30px 70px rgba(0, 0, 0, .22);
}
.profile-avatar { width: 88px; height: 88px; border-radius: 50%; border: 1px solid rgba(238, 242, 245, .2); object-fit: cover; }
.profile-name { margin-top: 14px; font-family: 'Noto Serif SC', 'Songti SC', serif; font-size: 28px; font-weight: 600; letter-spacing: -.03em; line-height: 1.15; }
.profile-role { display: inline-flex; align-items: center; gap: 7px; margin-top: 7px; color: var(--p-ink-3); font: 9.5px var(--p-mono); letter-spacing: .05em; }
.profile-role i { width: 3px; height: 3px; border-radius: 50%; background: var(--p-coral); }
.profile-bio { margin: 15px 0 0; color: var(--p-ink-2); font-size: 12px; line-height: 1.75; }
.profile-bio.is-empty { color: rgba(238, 242, 245, .3); }

.profile-completeness { margin-top: 20px; display: grid; gap: 7px; }
.profile-completeness div { display: flex; justify-content: space-between; align-items: baseline; }
.profile-completeness span { font-size: 9.5px; letter-spacing: .06em; color: var(--p-ink-3); }
.profile-completeness b { font: 500 12px var(--p-mono); color: var(--p-coral); }
.profile-completeness > i { display: block; height: 3px; border-radius: 999px; background: rgba(238, 242, 245, .1); overflow: hidden; }
.profile-completeness > i > span { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #f4a688, #e9896b); transition: width .35s ease; }

.profile-meta { display: grid; gap: 0; margin: 20px 0 0; padding: 0; border-top: 1px solid var(--p-line); }
.profile-meta div { display: flex; justify-content: space-between; gap: 12px; padding: 9px 0; border-bottom: 1px solid rgba(238, 242, 245, .07); }
.profile-meta dt { color: var(--p-ink-3); font-size: 10px; }
.profile-meta dd { margin: 0; color: var(--p-ink-2); font: 9.5px var(--p-mono); text-align: right; }
.profile-note { display: flex; gap: 7px; margin: 16px 0 0; color: rgba(238, 242, 245, .34); font-size: 9.5px; line-height: 1.65; }
.profile-note svg { flex: 0 0 auto; margin-top: 1px; color: var(--p-coral); }

.profile-form { display: grid; gap: 0; min-width: 0; }
.profile-section { padding: 22px 0; border-top: 1px solid var(--p-line); }
.profile-section:first-child { padding-top: 0; border-top: 0; }
.profile-section-head { display: flex; align-items: baseline; gap: 8px; margin-bottom: 15px; }
.profile-section-head span { font: 9.5px/1 var(--p-mono); letter-spacing: .08em; color: var(--p-coral); }
.profile-section-head h2 { margin: 0; font-size: 14px; font-weight: 500; letter-spacing: .02em; color: var(--p-ink); }
.profile-section-head small { margin-left: auto; color: var(--p-ink-3); font-size: 9.5px; }

.profile-fields { display: grid; gap: 14px; }
.profile-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.profile-field { display: grid; gap: 7px; min-width: 0; margin: 0; padding: 0; border: 0; }
.profile-field > span, .profile-field legend { padding: 0; color: var(--p-ink-3); font-size: 10.5px; letter-spacing: .02em; }
.profile-field > span small { margin-left: 4px; color: rgba(238, 242, 245, .3); font-size: 9px; }
.profile-field input,
.profile-field select {
  width: 100%;
  min-height: 42px;
  padding: 0 12px;
  border-radius: 9px;
  border: 1px solid var(--p-line);
  background: rgba(238, 242, 245, .03);
  color: var(--p-ink);
  font-size: 12px;
  outline: none;
  transition: border-color .2s ease, background .2s ease;
}
.profile-field select { padding-right: 28px; }
.profile-field input:focus, .profile-field select:focus { border-color: rgba(233, 139, 107, .65); background: rgba(233, 139, 107, .05); }
.profile-field input::placeholder { color: rgba(238, 242, 245, .3); }

.profile-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.profile-chips button {
  min-height: 34px;
  padding: 0 13px;
  border-radius: 999px;
  border: 1px solid var(--p-line);
  background: transparent;
  color: var(--p-ink-3);
  font-size: 10.5px;
  transition: border-color .18s ease, background .18s ease, color .18s ease;
}
.profile-chips button:hover { border-color: rgba(233, 139, 107, .5); color: #f3d9cd; }
.profile-chips button.active { border-color: rgba(233, 139, 107, .75); background: rgba(233, 139, 107, .14); color: #ffd9c9; }
.profile-chips--styles button { min-height: 36px; }

.profile-switch { display: flex; align-items: flex-start; gap: 11px; margin-top: 18px; padding: 12px 13px; border-radius: 12px; border: 1px solid var(--p-line); background: rgba(238, 242, 245, .02); cursor: pointer; }
.profile-switch input { position: absolute; opacity: 0; pointer-events: none; }
.profile-switch-track { position: relative; flex: 0 0 auto; width: 36px; height: 21px; margin-top: 1px; border-radius: 999px; background: rgba(238, 242, 245, .16); transition: background .25s ease; }
.profile-switch-track i { position: absolute; left: 3px; top: 3px; width: 15px; height: 15px; border-radius: 50%; background: #cfd9dd; transition: transform .25s cubic-bezier(.2, .8, .2, 1); }
.profile-switch input:checked + .profile-switch-track { background: rgba(233, 139, 107, .85); }
.profile-switch input:checked + .profile-switch-track i { transform: translateX(15px); background: #1b2225; }
.profile-switch input:focus-visible + .profile-switch-track { outline: 2px solid var(--p-coral); outline-offset: 3px; }
.profile-switch-copy { display: grid; gap: 2px; }
.profile-switch-copy strong { font-size: 11.5px; font-weight: 500; }
.profile-switch-copy small { color: var(--p-ink-3); font-size: 9.5px; line-height: 1.6; }

.profile-actions {
  position: sticky;
  bottom: 16px;
  z-index: 5;
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 28px;
  padding: 12px 14px;
  border: 1px solid var(--p-line);
  border-radius: 16px;
  background: rgba(10, 14, 18, .88);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow: 0 20px 50px rgba(0, 0, 0, .35);
}
.profile-hint { margin-right: auto; color: var(--p-ink-3); font-size: 10px; }
.profile-saved { display: inline-flex; align-items: center; gap: 6px; margin-right: auto; color: #8fc9a8; font-size: 10.5px; }
.profile-reset { display: inline-flex; align-items: center; gap: 6px; min-height: 42px; padding: 0 16px; border-radius: 999px; border: 1px solid rgba(238, 242, 245, .2); background: transparent; color: var(--p-ink-2); font-size: 11.5px; }
.profile-reset:hover { border-color: rgba(238, 242, 245, .38); color: var(--p-ink); }
.profile-save { display: inline-flex; align-items: center; gap: 7px; min-height: 42px; padding: 0 20px; border: 0; border-radius: 999px; background: linear-gradient(135deg, #f2a080, #e98b6b 60%, #d9734f); color: #1b2225; font-size: 12px; font-weight: 700; box-shadow: 0 14px 32px rgba(233, 139, 107, .24); transition: transform .2s ease; }
.profile-save:hover { transform: translateY(-2px); }

@media (max-width: 980px) {
  .profile-layout { grid-template-columns: 1fr; }
  .profile-card { position: relative; top: auto; }
}
@media (max-width: 620px) {
  .profile-row { grid-template-columns: 1fr; }
  .profile-actions { flex-wrap: wrap; }
  .profile-hint, .profile-saved { width: 100%; }
  .profile-save { flex: 1; justify-content: center; }
}
@media (prefers-reduced-motion: reduce) {
  .profile-save:hover { transform: none; }
  .profile-completeness > i > span { transition: none; }
}

/* ---- 2026-11-16 用户：头像上传 + 全局壁纸入口 ---- */
.profile-avatar-edit {
  position: relative; justify-self: start; display: inline-block;
  width: 88px; height: 88px; padding: 0; border: 0; border-radius: 50%;
  background: none; cursor: pointer;
}
.profile-avatar-edit .profile-avatar { display: block; }
.profile-avatar-edit:focus-visible { outline: 2px solid rgba(233, 139, 107, .7); outline-offset: 3px; }
.profile-avatar-hint {
  position: absolute; left: 50%; bottom: 5px; transform: translateX(-50%);
  display: inline-flex; align-items: center; gap: 4px; padding: 3px 9px;
  border-radius: 999px; background: rgba(9, 13, 17, .8); color: #ffd9c9;
  font-size: 9.5px; white-space: nowrap; opacity: 0; pointer-events: none;
  transition: opacity .2s ease;
}
.profile-avatar-edit:hover .profile-avatar-hint,
.profile-avatar-edit:focus-visible .profile-avatar-hint { opacity: 1; }
@media (hover: none) { .profile-avatar-hint { opacity: .94; } }
.profile-avatar-reset {
  justify-self: start; margin-top: 8px; padding: 0; border: 0; background: none;
  color: rgba(238, 242, 245, .46); font-size: 10.5px; text-decoration: underline;
  text-underline-offset: 3px; cursor: pointer; transition: color .2s ease;
}
.profile-avatar-reset:hover { color: #e9896b; }
.profile-avatar-error { margin: 8px 0 0; color: #f0a48f; font-size: 10.5px; line-height: 1.55; }

.personalize-wallpaper {
  display: grid; grid-template-columns: 92px minmax(0, 1fr) auto; gap: 14px; align-items: center;
  padding: 14px; border: 1px solid rgba(238, 242, 245, .1); border-radius: 16px;
  background: rgba(238, 242, 245, .03);
}
.personalize-thumb {
  display: grid; place-items: center; width: 92px; height: 58px; border-radius: 10px;
  border: 1px solid rgba(238, 242, 245, .12); background-color: #0d1218;
  background-position: center; background-size: cover; color: rgba(238, 242, 245, .4);
}
.personalize-copy { display: grid; gap: 4px; min-width: 0; }
.personalize-copy strong { font-size: 12.5px; font-weight: 500; }
.personalize-copy small { color: rgba(238, 242, 245, .46); font-size: 10.5px; line-height: 1.6; }
.personalize-actions { display: flex; align-items: center; gap: 10px; }
.personalize-btn {
  min-height: 36px; padding: 0 14px; border-radius: 999px; cursor: pointer;
  border: 1px solid rgba(233, 139, 107, .5); background: rgba(233, 139, 107, .12);
  color: #ffd9c9; font-size: 11.5px; transition: background .2s ease, border-color .2s ease;
}
.personalize-btn:hover { border-color: rgba(233, 139, 107, .9); background: rgba(233, 139, 107, .2); }
.personalize-link {
  padding: 0; border: 0; background: none; color: rgba(238, 242, 245, .46);
  font-size: 10.5px; text-decoration: underline; text-underline-offset: 3px; cursor: pointer;
}
.personalize-link:hover { color: #e9896b; }
.personalize-note { margin: 10px 0 0; color: rgba(238, 242, 245, .38); font-size: 10.5px; line-height: 1.6; }

@media (max-width: 720px) {
  .personalize-wallpaper { grid-template-columns: 72px minmax(0, 1fr); }
  .personalize-thumb { width: 72px; height: 46px; }
  .personalize-actions { grid-column: span 2; }
}

/* ===== 2026-11-16 用户：圆角 + 液态渐变玻璃（替换原来的灰面） ===== */
.profile-page {
  --lg-line: rgba(255, 255, 255, .17);
  --lg-warm: rgba(233, 139, 107, .24);
  --lg-cool: rgba(112, 146, 214, .22);
  --lg-teal: rgba(108, 188, 176, .16);
}
.profile-page .profile-card {
  padding: 24px;
  border: 1px solid var(--lg-line);
  border-radius: 26px;
  isolation: isolate;
  overflow: hidden;
  background:
    radial-gradient(125% 150% at 6% -8%, var(--lg-warm), transparent 56%),
    radial-gradient(115% 140% at 104% 110%, var(--lg-cool), transparent 62%),
    linear-gradient(158deg, rgba(255, 255, 255, .11), rgba(255, 255, 255, .038) 46%, rgba(255, 255, 255, .075));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .20), 0 36px 80px -42px rgba(0, 0, 0, 1);
  backdrop-filter: blur(18px) saturate(150%);
  -webkit-backdrop-filter: blur(18px) saturate(150%);
}
.profile-page .profile-card::before {
  content: ''; position: absolute; inset: -30% -20%; z-index: -1; pointer-events: none;
  background:
    radial-gradient(38% 44% at 26% 28%, rgba(244, 166, 136, .34), transparent 62%),
    radial-gradient(36% 42% at 76% 72%, rgba(112, 146, 214, .32), transparent 64%),
    radial-gradient(30% 36% at 60% 6%, rgba(108, 188, 176, .18), transparent 66%);
  filter: blur(42px); opacity: .92;
  animation: ps-glass-drift 20s ease-in-out infinite alternate;
}
@keyframes ps-glass-drift {
  from { transform: translate3d(-3%, -2%, 0) scale(1); }
  to { transform: translate3d(4%, 3%, 0) scale(1.1); }
}
.profile-page .profile-avatar { border-color: rgba(255, 255, 255, .35); box-shadow: 0 0 0 4px rgba(233, 139, 107, .14), 0 16px 34px -18px rgba(0, 0, 0, .9); }
.profile-page .profile-field input,
.profile-page .profile-field select,
.profile-page .profile-field textarea {
  min-height: 46px; border-radius: 14px; border: 1px solid rgba(255, 255, 255, .16);
  background:
    radial-gradient(120% 160% at 0% 0%, rgba(112, 146, 214, .13), transparent 62%),
    linear-gradient(180deg, rgba(255, 255, 255, .085), rgba(255, 255, 255, .03));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .13);
}
.profile-page .profile-field input:focus,
.profile-page .profile-field select:focus,
.profile-page .profile-field textarea:focus {
  border-color: rgba(233, 139, 107, .72);
  background: linear-gradient(180deg, rgba(233, 139, 107, .12), rgba(233, 139, 107, .04));
  box-shadow: 0 0 0 3px rgba(233, 139, 107, .14), inset 0 1px 0 rgba(255, 255, 255, .16);
}
.profile-page .profile-chips button {
  border: 1px solid rgba(255, 255, 255, .15); border-radius: 999px;
  background: linear-gradient(160deg, rgba(255, 255, 255, .08), rgba(255, 255, 255, .025));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .12);
  color: rgba(238, 242, 245, .66);
}
.profile-page .profile-chips button:hover { border-color: rgba(233, 139, 107, .5); color: #ffd9c9; background: rgba(233, 139, 107, .10); }
.profile-page .profile-chips button.active {
  color: #1b2225; border-color: transparent;
  background: linear-gradient(135deg, #f4a688 0%, #e9896b 58%, #d9734f 100%);
  box-shadow: 0 10px 24px -12px rgba(233, 139, 107, .6), inset 0 1px 0 rgba(255, 255, 255, .36);
}
.profile-page .profile-switch {
  border: 1px solid rgba(255, 255, 255, .14); border-radius: 16px;
  background: linear-gradient(160deg, rgba(255, 255, 255, .075), rgba(255, 255, 255, .028));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .12);
}
.profile-page .profile-section { border-top-color: rgba(255, 255, 255, .10); }
.profile-page .personalize-wallpaper {
  border: 1px solid rgba(255, 255, 255, .15); border-radius: 18px;
  background:
    radial-gradient(120% 140% at 0% 0%, rgba(108, 188, 176, .14), transparent 60%),
    linear-gradient(160deg, rgba(255, 255, 255, .09), rgba(255, 255, 255, .03));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .14);
}
.profile-page .profile-actions {
  border: 1px solid rgba(255, 255, 255, .16); border-radius: 20px;
  background: linear-gradient(160deg, rgba(20, 26, 34, .82), rgba(10, 14, 18, .72));
  backdrop-filter: blur(18px) saturate(150%);
  -webkit-backdrop-filter: blur(18px) saturate(150%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .14), 0 26px 60px -30px rgba(0, 0, 0, 1);
}
.profile-page .profile-save {
  background: linear-gradient(135deg, #f6b092 0%, #ee946f 52%, #d9734f 100%);
  box-shadow: 0 18px 40px -18px rgba(233, 139, 107, .65), inset 0 1px 0 rgba(255, 255, 255, .45);
}
.profile-page .profile-reset { border-radius: 999px; border-color: rgba(255, 255, 255, .18); background: rgba(255, 255, 255, .05); }
@media (max-width: 980px) {
  .profile-page .profile-card { position: relative; top: auto; }
}
@media (prefers-reduced-motion: reduce) {
  .profile-page .profile-card::before { animation: none; }
}
</style>
