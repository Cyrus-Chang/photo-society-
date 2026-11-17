<script setup lang="ts">
import { ArrowLeft, ArrowRight, Eye, EyeOff, KeyRound, LoaderCircle, LockKeyhole, ShieldCheck, Smartphone } from 'lucide-vue-next'
import { computed, onBeforeUnmount, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { brand } from '../utils/brand'
import { accountName, registerAccount, verifyAccount } from '../utils/account'
import { signIn } from '../utils/session'
import loginScene from '../assets/works/shanghai-night.jpg'

const route = useRoute()
const router = useRouter()
const mode = ref<'login' | 'register'>('login')
/** 登录方式：验证码 / 密码。注册固定走验证码 + 设置密码 */
const method = ref<'code' | 'password'>('code')
const form = reactive({ name: '', phone: '', code: '', password: '', agree: false })
const showPassword = ref(false)
const error = ref('')
const loading = ref(false)
const countdown = ref(0)
let timer: number | undefined

const title = computed(() => (mode.value === 'login' ? '回到拍社' : '第一次来拍社'))
const subtitle = computed(() => {
  if (mode.value === 'register') return '注册需要手机号和密码，资料之后可以再补。'
  return method.value === 'password' ? '用手机号和密码登录，下次不用再收验证码。' : '登录后继续看作品、约人、发需求。'
})

/** 验证码输入框是否出现：注册必用；登录看是否选了验证码方式 */
const needCode = computed(() => mode.value === 'register' || method.value === 'code')
const needPassword = computed(() => mode.value === 'register' || method.value === 'password')

const canSubmit = computed(() => {
  if (form.phone.length !== 11 || !form.agree) return false
  if (mode.value === 'register') return form.name.trim().length > 0 && form.code.length === 6 && form.password.length >= 6
  if (method.value === 'password') return form.password.length >= 6
  return form.code.length === 6
})

function switchMode(next: 'login' | 'register') {
  mode.value = next
  error.value = ''
}

function switchMethod(next: 'code' | 'password') {
  method.value = next
  error.value = ''
}

function sendCode() {
  if (!/^1\d{10}$/.test(form.phone)) { error.value = '先填一个 11 位的手机号。'; return }
  error.value = ''
  countdown.value = 60
  window.clearInterval(timer)
  timer = window.setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0) window.clearInterval(timer)
  }, 1000)
}

async function submit() {
  if (loading.value) return
  if (!/^1\d{10}$/.test(form.phone)) { error.value = '手机号要 11 位、以 1 开头。'; return }
  if (mode.value === 'register' && form.password.length < 6) { error.value = '密码需要 6–20 位。'; return }
  if (mode.value === 'login' && method.value === 'password' && form.password.length < 6) { error.value = '密码至少 6 位。'; return }
  if (!form.agree) { error.value = '需要先同意用户协议与隐私说明。'; return }
  if (!canSubmit.value) { error.value = '手机号或验证码还不完整。'; return }

  error.value = ''
  loading.value = true
  try {
    if (mode.value === 'register') {
      const result = await registerAccount(form.phone, form.name, form.password)
      if (!result.ok) { error.value = result.reason; return }
      finish(result.name)
      return
    }
    if (method.value === 'password') {
      const result = await verifyAccount(form.phone, form.password)
      if (!result.ok) { error.value = result.reason; return }
      finish(result.name)
      return
    }
    finish(accountName(form.phone) || '拍社用户')
  } finally {
    loading.value = false
  }
}

function finish(name: string) {
  signIn(name)
  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
  // 登录后先落到 /discover（不带 filter），让「选身份」先出现；
  // 筛选弹窗由身份完成后的「要不要开始约拍」确认再打开，避免两个弹窗同时出现。
  if (redirect && !redirect.startsWith('/discover')) router.replace(redirect)
  else router.replace({ name: 'discover' })
}

onBeforeUnmount(() => window.clearInterval(timer))
</script>

<template>
  <div class="login-page">
    <div class="login-visual" aria-hidden="true">
      <img :src="loginScene" alt="" />
      <div class="login-visual-shade" />
      <div class="login-visual-copy">
        <span class="login-eyebrow">{{ brand.en }} / 2026</span>
        <h1>把每一次想拍照，<br /><em>都交给刚好能到场的人。</em></h1>
        <p>先看作品，再决定见谁。地点、时间、预算说清楚，剩下的交给现场。</p>
        <div class="login-meta"><span>28 位摄影师在线</span><i /><span>西安 · 成都 · 青岛</span></div>
      </div>
    </div>

    <section class="login-panel" aria-labelledby="login-title">
      <RouterLink class="login-back" to="/"><ArrowLeft :size="15" />回到首页</RouterLink>

      <div class="login-brand"><span class="login-brand-mark">拍</span><span><strong>{{ brand.cn }}</strong><small>{{ brand.en }}</small></span></div>

      <div class="login-tabs" role="tablist" aria-label="登录或注册">
        <button type="button" role="tab" :aria-selected="mode === 'login'" :class="{ active: mode === 'login' }" @click="switchMode('login')">登录</button>
        <button type="button" role="tab" :aria-selected="mode === 'register'" :class="{ active: mode === 'register' }" @click="switchMode('register')">注册</button>
      </div>

      <header class="login-head">
        <h2 id="login-title">{{ title }}</h2>
        <p>{{ subtitle }}</p>
      </header>

      <div v-if="mode === 'login'" class="login-method" role="tablist" aria-label="登录方式">
        <button type="button" role="tab" :aria-selected="method === 'code'" :class="{ active: method === 'code' }" @click="switchMethod('code')">验证码登录</button>
        <button type="button" role="tab" :aria-selected="method === 'password'" :class="{ active: method === 'password' }" @click="switchMethod('password')">密码登录</button>
      </div>

      <form class="login-form" @submit.prevent="submit">
        <label v-if="mode === 'register'" class="login-field">
          <span>怎么称呼你</span>
          <div><Smartphone :size="15" /><input v-model="form.name" type="text" autocomplete="nickname" placeholder="例如：小满" /></div>
        </label>

        <label class="login-field">
          <span>手机号</span>
          <div><Smartphone :size="15" /><input v-model="form.phone" type="tel" inputmode="numeric" maxlength="11" autocomplete="tel" placeholder="11 位手机号" /></div>
        </label>

        <label v-if="needCode" class="login-field">
          <span>验证码</span>
          <div>
            <LockKeyhole :size="15" />
            <input v-model="form.code" type="text" inputmode="numeric" maxlength="6" autocomplete="one-time-code" placeholder="6 位验证码" />
            <button class="login-send" type="button" :disabled="countdown > 0" @click="sendCode">{{ countdown > 0 ? `${countdown}s` : '获取验证码' }}</button>
          </div>
        </label>

        <label v-if="needPassword" class="login-field">
          <span>{{ mode === 'register' ? '设置登录密码' : '登录密码' }}</span>
          <div>
            <KeyRound :size="15" />
            <input
              v-model="form.password"
              :type="showPassword ? 'text' : 'password'"
              :autocomplete="mode === 'register' ? 'new-password' : 'current-password'"
              maxlength="20"
              :placeholder="mode === 'register' ? '6–20 位，之后可以用它登录' : '6–20 位登录密码'"
            />
            <button
              class="login-eye"
              type="button"
              :aria-label="showPassword ? '隐藏密码' : '显示密码'"
              :aria-pressed="showPassword"
              :title="showPassword ? '隐藏密码' : '显示密码'"
              @click="showPassword = !showPassword"
            >
              <EyeOff v-if="showPassword" :size="15" />
              <Eye v-else :size="15" />
            </button>
          </div>
        </label>

        <label class="login-agree">
          <input v-model="form.agree" type="checkbox" />
          <span>我已阅读并同意<span class="login-agree-link">《用户协议》</span>与<span class="login-agree-link">《隐私说明》</span></span>
        </label>

        <p v-if="error" class="login-error" role="alert">{{ error }}</p>

        <button class="login-submit" type="submit" :disabled="loading">
          <LoaderCircle v-if="loading" class="spin" :size="17" />
          <template v-else>{{ mode === 'login' ? '登录' : '注册并进入' }}<ArrowRight :size="17" /></template>
        </button>

        <p class="login-note"><ShieldCheck :size="13" />演示环境：验证码任意 6 位即可；密码登录需要先在当前浏览器注册过。</p>
      </form>
    </section>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100svh; display: grid; grid-template-columns: minmax(0, 1.12fr) minmax(360px, .88fr);
  background: #070b10; color: #edf1f4; overflow: hidden;
}
.login-visual { position: relative; min-height: 100svh; overflow: hidden; }
.login-visual > img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; object-position: center 42%; filter: saturate(.92) brightness(.82); animation: login-zoom 18s ease-out both; }
.login-visual-shade { position: absolute; inset: 0; background: linear-gradient(90deg, rgba(4, 8, 12, .55), rgba(4, 8, 12, .18) 46%, rgba(7, 11, 16, .92) 100%), linear-gradient(180deg, rgba(4, 8, 12, .35), transparent 40%, rgba(4, 8, 12, .72)); }
.login-visual-copy { position: absolute; left: clamp(28px, 5vw, 76px); bottom: clamp(34px, 8vh, 92px); max-width: 560px; z-index: 2; display: grid; gap: 18px; animation: login-rise .9s cubic-bezier(.2, .8, .2, 1) both .1s; }
.login-eyebrow { font: 9px/1 ui-monospace, monospace; letter-spacing: .26em; color: #e98b6b; }
.login-visual-copy h1 { margin: 0; font-family: 'Noto Serif SC', 'Songti SC', serif; font-size: clamp(30px, 3.4vw, 52px); font-weight: 600; line-height: 1.24; letter-spacing: -.02em; text-shadow: 0 18px 50px rgba(0, 0, 0, .45); }
.login-visual-copy h1 em { color: #f0a184; font-style: normal; }
.login-visual-copy p { margin: 0; max-width: 420px; color: rgba(237, 241, 244, .66); font-size: 13px; line-height: 1.9; }
.login-meta { display: flex; align-items: center; gap: 12px; color: rgba(237, 241, 244, .48); font-size: 10px; letter-spacing: .08em; }
.login-meta i { width: 26px; height: 1px; background: rgba(237, 241, 244, .3); }

.login-panel { position: relative; display: flex; flex-direction: column; justify-content: center; gap: 18px; padding: clamp(28px, 5vw, 68px); background: radial-gradient(120% 80% at 100% 0%, rgba(233, 139, 107, .07), transparent 50%), #080d12; }
.login-back { position: absolute; top: 28px; right: clamp(24px, 4vw, 56px); display: inline-flex; align-items: center; gap: 7px; color: #a9b5ba; font-size: 11px; text-decoration: none; padding: 8px 13px; border-radius: 999px; border: 1px solid rgba(237, 241, 244, .12); transition: .25s ease; }
.login-back:hover { color: #fff; border-color: rgba(233, 139, 107, .5); background: rgba(233, 139, 107, .08); }
.login-brand { display: flex; align-items: center; gap: 11px; }
.login-brand-mark { display: grid; place-items: center; width: 38px; height: 38px; border: 1.5px solid #e98b6b; border-radius: 11px; color: #e98b6b; font-family: 'Noto Serif SC', serif; font-size: 20px; }
.login-brand span:last-child { display: grid; line-height: 1.1; }
.login-brand strong { font-family: 'Noto Serif SC', 'Songti SC', serif; font-size: 20px; letter-spacing: .1em; }
.login-brand small { font: 8px/1 ui-monospace, monospace; letter-spacing: .2em; color: rgba(237, 241, 244, .44); margin-top: 4px; }
.login-tabs { display: inline-flex; gap: 4px; padding: 4px; border-radius: 999px; border: 1px solid rgba(237, 241, 244, .1); width: fit-content; background: rgba(237, 241, 244, .03); }
.login-tabs button { min-width: 84px; min-height: 34px; border: 0; border-radius: 999px; background: transparent; color: #8c9aa0; font-size: 12px; cursor: pointer; transition: all .25s ease; }
.login-tabs button.active { background: rgba(233, 139, 107, .16); color: #ffd9c9; box-shadow: inset 0 0 0 1px rgba(233, 139, 107, .36); }
.login-method { display: inline-flex; gap: 6px; width: fit-content; }
.login-method button { border: 0; background: transparent; color: #7d8b91; font-size: 11px; padding: 5px 12px; border-radius: 999px; cursor: pointer; transition: color .2s ease, background .2s ease; }
.login-method button:hover { color: #d8c3b8; }
.login-method button.active { color: #ffd9c9; background: rgba(233, 139, 107, .12); box-shadow: inset 0 0 0 1px rgba(233, 139, 107, .3); }
.login-head h2 { margin: 0 0 8px; font-family: 'Noto Serif SC', 'Songti SC', serif; font-size: clamp(26px, 2.6vw, 34px); font-weight: 600; letter-spacing: -.02em; }
.login-head p { margin: 0; color: #8c9aa0; font-size: 12px; }
.login-form { display: grid; gap: 13px; }
.login-field { display: grid; gap: 7px; }
.login-field > span { color: #8c9aa0; font-size: 11px; }
.login-field > div { display: flex; align-items: center; gap: 9px; min-height: 46px; padding: 0 12px; border-radius: 12px; border: 1px solid rgba(237, 241, 244, .13); background: rgba(237, 241, 244, .035); color: #87949a; transition: border-color .2s ease, background .2s ease; }
.login-field > div:focus-within { border-color: rgba(233, 139, 107, .7); background: rgba(233, 139, 107, .06); }
.login-field input { flex: 1; min-width: 0; background: transparent; border: 0; outline: none; color: #eef3f5; font-size: 13px; }
.login-field input::placeholder { color: #626f75; }
.login-send { flex: 0 0 auto; border: 0; background: transparent; color: #e98b6b; font-size: 11px; cursor: pointer; padding: 6px 2px; }
.login-send:disabled { color: #6d7a80; cursor: default; }
/* 密码可见性开关：贴在输入框最右侧（标准做法，不额外占一行） */
.login-eye { flex: 0 0 auto; display: grid; place-items: center; width: 26px; height: 26px; margin-right: -4px; border: 0; border-radius: 8px; background: transparent; color: #7d8b91; cursor: pointer; transition: color .2s ease, background .2s ease; }
.login-eye:hover { color: #ffd9c9; background: rgba(233, 139, 107, .12); }
.login-eye:focus-visible { outline: 2px solid rgba(233, 139, 107, .6); outline-offset: 1px; }
/* 协议行：全局 input{width:100%} 会把复选框拉成白条，这里必须显式收回宽度 */
.login-agree { display: flex; align-items: flex-start; gap: 9px; color: #8c9aa0; font-size: 11px; line-height: 1.6; cursor: pointer; }
.login-agree input { flex: 0 0 auto; width: 15px; height: 15px; min-width: 15px; margin: 2px 0 0; padding: 0; accent-color: #e98b6b; }
.login-agree span { flex: 1; min-width: 0; }
.login-agree-link { color: #f0a184; text-decoration: none; }
.login-agree-link:hover { color: #ffd9c9; text-decoration: underline; }
.login-error { margin: 0; color: #f3a184; background: rgba(233, 139, 107, .1); border: 1px solid rgba(233, 139, 107, .24); border-radius: 10px; padding: 9px 11px; font-size: 11px; }
.login-submit { display: inline-flex; align-items: center; justify-content: center; gap: 9px; min-height: 48px; border: 0; border-radius: 999px; cursor: pointer; background: linear-gradient(135deg, #f2a080, #e98b6b 58%, #d9734f); color: #1b2225; font-size: 13px; font-weight: 700; letter-spacing: .02em; box-shadow: 0 18px 42px rgba(233, 139, 107, .26); transition: transform .22s ease, box-shadow .22s ease, opacity .22s ease; }
.login-submit:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 24px 54px rgba(233, 139, 107, .32); }
.login-submit:active:not(:disabled) { transform: translateY(0) scale(.995); }
.login-submit:disabled { opacity: .72; cursor: wait; }
.login-note { display: flex; align-items: flex-start; gap: 6px; margin: 2px 0 0; color: #6f7d83; font-size: 10px; line-height: 1.6; }
@keyframes login-rise { from { opacity: 0; transform: translateY(18px); } to { opacity: 1; transform: none; } }
@keyframes login-zoom { from { transform: scale(1.06); } to { transform: scale(1); } }
@media (max-height: 880px) {
  .login-panel { gap: 14px; padding-top: 34px; padding-bottom: 34px; }
  .login-form { gap: 11px; }
  .login-field > div { min-height: 42px; }
}
@media (max-width: 980px) {
  .login-page { grid-template-columns: 1fr; }
  .login-visual { min-height: 42svh; }
  .login-visual-copy { bottom: 22px; left: 22px; right: 22px; }
  .login-visual-copy h1 { font-size: clamp(24px, 7vw, 34px); }
  .login-panel { padding: 26px 22px 40px; }
  .login-back { top: 16px; right: 16px; }
}
@media (prefers-reduced-motion: reduce) {
  .login-visual > img, .login-visual-copy { animation: none; }
}
</style>
