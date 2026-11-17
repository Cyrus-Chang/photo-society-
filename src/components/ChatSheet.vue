<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { ArrowUp, Send, Sparkles } from 'lucide-vue-next'
import BaseModal from './BaseModal.vue'
import { replyChat, type ChatContext, type ChatTurn } from '../services/api'

/**
 * AI 约拍对话框（2026-11-16，第七轮 P0）
 *
 * 用户口径：这是「AI 助手帮你起个头」——用摄影师平时的口吻先回你一句，
 * 但界面必须标明这是 AI，不冒充真人（他在 2026-11-16 选的就是这个口径）。
 * 后端没接本地模型时返回 mode='fallback'，界面同样照实说，不假装是模型。
 */
const props = defineProps<{
  open: boolean
  persona: string
  name: string
  city?: string
  price?: string
  nextSlot?: string
  scene?: string
  /** 弹层标题；不给就是「和 {name} 聊两句」 */
  title?: string
  /** 打开后先自动发出去的一句（接拍页用来让 AI 直接起草回复）；不给就只取开场白 */
  opening?: string
  /** chat=正常对话；draft=接拍页的「帮我回一句」 */
  mode?: 'chat' | 'draft'
}>()

const emit = defineEmits<{ (event: 'close'): void }>()

const turns = ref<ChatTurn[]>([])
const draft = ref('')
const busy = ref(false)
const error = ref('')
const mode = ref('')
const started = ref(false)
const scroller = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)

const QUICK = ['你最近还有档期吗？', '这组大概多少钱？', '我想拍夜景，你拍得多吗？']

async function scrollToEnd() {
  await nextTick()
  const el = scroller.value
  if (el) el.scrollTop = el.scrollHeight
}

async function ask(text: string) {
  if (busy.value) return
  const message = text.trim()
  if (message) turns.value.push({ role: 'user', content: message })
  busy.value = true
  error.value = ''
  await scrollToEnd()
  try {
    const context: ChatContext = {
      name: props.name,
      city: props.city,
      price: props.price,
      nextSlot: props.nextSlot,
      scene: props.scene,
      count: '8'
    }
    const result = await replyChat({
      message,
      persona: props.persona,
      mode: props.mode || 'chat',
      context,
      history: turns.value.slice(-8)
    })
    mode.value = result.mode
    turns.value.push({ role: 'assistant', content: result.reply })
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'AI 回复失败'
  } finally {
    busy.value = false
    await scrollToEnd()
  }
}

async function submit() {
  const text = draft.value
  draft.value = ''
  await ask(text)
}

watch(() => props.open, async (open) => {
  if (!open) return
  error.value = ''
  if (!started.value) {
    started.value = true
    turns.value = []
    // 接拍页会先塞一句「我想接这条…」让 AI 直接起草；约拍页则只取一句开场白
    await ask(props.opening || '')
    inputRef.value?.focus()
  } else {
    await scrollToEnd()
  }
})
</script>

<template>
  <BaseModal :open="open" labelled-by="chat-sheet-title" @close="emit('close')">
    <section class="ps-chat" aria-label="AI 约拍对话">
      <header class="ps-chat-head">
        <div>
          <p class="ps-chat-kicker">AI 助手 · 先替你起个头</p>
          <h2 id="chat-sheet-title">{{ title || `和 ${name} 聊两句` }}</h2>
        </div>
        <span class="ps-chat-badge" :class="{ 'is-fallback': mode === 'fallback' }">
          <Sparkles :size="13" aria-hidden="true" />
          {{ mode === 'model' ? '本地小模型回复' : mode === 'fallback' ? '人设模板回复' : 'AI 代写' }}
        </span>
      </header>

      <div ref="scroller" class="ps-chat-log" role="log" aria-live="polite">
        <p v-if="!turns.length && !busy" class="ps-chat-hint">正在叫 TA……</p>
        <div
          v-for="(turn, index) in turns"
          :key="index"
          class="ps-chat-row"
          :class="turn.role === 'user' ? 'is-me' : 'is-them'"
        >
          <span v-if="turn.role === 'assistant'" class="ps-chat-avatar" aria-hidden="true">{{ name.slice(0, 1) }}</span>
          <p class="ps-chat-bubble">{{ turn.content }}</p>
        </div>
        <div v-if="busy" class="ps-chat-row is-them">
          <span class="ps-chat-avatar" aria-hidden="true">{{ name.slice(0, 1) }}</span>
          <p class="ps-chat-bubble is-typing"><i /><i /><i /></p>
        </div>
      </div>

      <p v-if="error" class="ps-chat-error">{{ error }}</p>

      <div v-if="turns.filter((t) => t.role === 'user').length === 0" class="ps-chat-quick">
        <button v-for="item in QUICK" :key="item" type="button" @click="ask(item)">{{ item }}</button>
      </div>

      <form class="ps-chat-form" @submit.prevent="submit">
        <label class="sr-only" for="ps-chat-input">说点什么</label>
        <input
          id="ps-chat-input"
          ref="inputRef"
          v-model="draft"
          type="text"
          placeholder="说一下你想怎么拍，比如时间、地点、想要的风格"
          autocomplete="off"
          :disabled="busy"
        />
        <button class="ps-chat-send" type="submit" :disabled="busy || !draft.trim()" aria-label="发送">
          <Send :size="16" aria-hidden="true" />
        </button>
      </form>

      <p class="ps-chat-foot">
        <ArrowUp :size="12" aria-hidden="true" />
        这是 AI 用 TA 平时的口吻代写的开场，不是真人实时回复；档期和价格以本人确认为准。
      </p>
    </section>
  </BaseModal>
</template>

<style scoped>
.ps-chat {
  display: grid;
  gap: 14px;
  min-height: 0;
}

.ps-chat-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(238, 242, 245, .12);
}

.ps-chat-kicker {
  margin: 0 0 6px;
  color: #e9896b;
  font: 10px/1 'DM Mono', monospace;
  letter-spacing: .18em;
  text-transform: uppercase;
}

.ps-chat-head h2 {
  margin: 0;
  font-family: 'Source Han Serif SC', serif;
  font-size: 26px;
  font-weight: 600;
  letter-spacing: -.02em;
  color: #eef2f5;
}

.ps-chat-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border: 1px solid rgba(238, 242, 245, .18);
  border-radius: 999px;
  color: rgba(238, 242, 245, .74);
  font-size: 11.5px;
  white-space: nowrap;
}

.ps-chat-badge.is-fallback {
  border-color: rgba(224, 178, 92, .42);
  color: #e0b25c;
}

.ps-chat-log {
  display: grid;
  gap: 10px;
  max-height: min(46vh, 380px);
  overflow-y: auto;
  padding: 4px 2px;
  scrollbar-width: thin;
}

.ps-chat-hint {
  margin: 0;
  color: rgba(238, 242, 245, .5);
  font-size: 12.5px;
}

.ps-chat-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}

.ps-chat-row.is-me {
  justify-content: flex-end;
}

.ps-chat-avatar {
  display: grid;
  place-items: center;
  flex: none;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: rgba(233, 137, 107, .18);
  color: #f4a688;
  font-size: 12px;
}

.ps-chat-bubble {
  max-width: 78%;
  margin: 0;
  padding: 10px 13px;
  border-radius: 14px;
  background: rgba(18, 24, 31, .92);
  border: 1px solid rgba(238, 242, 245, .1);
  color: #eef2f5;
  font-size: 14px;
  line-height: 1.62;
  white-space: pre-wrap;
}

.ps-chat-row.is-me .ps-chat-bubble {
  background: rgba(233, 137, 107, .16);
  border-color: rgba(233, 137, 107, .34);
}

.ps-chat-bubble.is-typing {
  display: inline-flex;
  gap: 5px;
  align-items: center;
  padding: 12px 14px;
}

.ps-chat-bubble.is-typing i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: rgba(238, 242, 245, .5);
  animation: ps-typing 1.1s infinite ease-in-out;
}

.ps-chat-bubble.is-typing i:nth-child(2) { animation-delay: .15s; }
.ps-chat-bubble.is-typing i:nth-child(3) { animation-delay: .3s; }

@keyframes ps-typing {
  0%, 60%, 100% { opacity: .25; transform: translateY(0); }
  30% { opacity: 1; transform: translateY(-2px); }
}

.ps-chat-error {
  margin: 0;
  color: #e0b25c;
  font-size: 12.5px;
}

.ps-chat-quick {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.ps-chat-quick button {
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid rgba(238, 242, 245, .18);
  border-radius: 999px;
  background: transparent;
  color: rgba(238, 242, 245, .78);
  font-size: 12.5px;
  cursor: pointer;
  transition: .18s ease;
}

.ps-chat-quick button:hover {
  border-color: rgba(233, 137, 107, .5);
  color: #fff;
}

.ps-chat-form {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 48px;
  padding: 0 6px 0 14px;
  border: 1px solid rgba(238, 242, 245, .18);
  border-radius: 999px;
  background: rgba(10, 13, 16, .72);
}

.ps-chat-form input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: none;
  background: transparent;
  color: #eef2f5;
  font-size: 13.5px;
}

.ps-chat-form input::placeholder {
  color: rgba(238, 242, 245, .42);
}

.ps-chat-send {
  display: grid;
  place-items: center;
  flex: none;
  width: 38px;
  height: 38px;
  border: 0;
  border-radius: 50%;
  background: #e9896b;
  color: #1b0f0b;
  cursor: pointer;
  transition: .18s ease;
}

.ps-chat-send:disabled {
  opacity: .38;
  cursor: not-allowed;
}

.ps-chat-foot {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin: 0;
  color: rgba(238, 242, 245, .46);
  font-size: 11.5px;
  line-height: 1.5;
}

.ps-chat-foot svg {
  flex: none;
  margin-top: 2px;
}

@media (prefers-reduced-motion: reduce) {
  .ps-chat-bubble.is-typing i { animation: none; opacity: .6; }
}

@media (max-width: 520px) {
  .ps-chat-head h2 { font-size: 22px; }
  .ps-chat-bubble { max-width: 86%; }
}
</style>
