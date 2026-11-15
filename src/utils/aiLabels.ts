/**
 * AI 标签词典（2026-11-15）
 *
 * 为什么单独一个文件：前端界面上的标签和模型输出的 code 不是一个词表，
 * 而且它们是**三层不同层级的概念**，不能混成一行：
 *
 *   风格 STYLE —— 模型 13 类锚图原型（留一法 0.706），code 是英文常量
 *   影调 TONE  —— 模型 9 条色彩规则，code 是 TONE_* 常量
 *   题材 SUBJECT —— 模型只有 3 类线性头，且人像会误判成静物美食，**默认不在界面暴露**
 *
 * 场景词（夜景 / 古风 / coser / 旅拍 …）模型没有这一层，属于作者自填，
 * 不要在这里给它们编一个"AI 识别"的来源。
 */

export type AiTagSource = 'STYLE' | 'TONE' | 'RULE' | 'SUBJECT'

export interface AiTag {
  code: string
  confidence?: number
  source?: AiTagSource | string
}

export interface AiClassifyResult {
  subject?: AiTag[]
  style?: AiTag[]
  tone?: AiTag[]
  color?: Record<string, number>
  modelVersion?: Record<string, string>
  fallback?: string
  latencyMs?: number
}

/** 模型 13 类风格 → 中文（与 ai-classifier/pipeline/anchors.py 的 STYLE_NAMES 保持一致） */
export const STYLE_LABELS: Record<string, string> = {
  JAPANESE: '日系',
  KOREAN: '韩系',
  INS: 'ins风',
  FRESH: '清新',
  FILM: '胶片',
  VINTAGE: '复古',
  CINEMATIC: '电影感',
  DARK_MOOD: '暗调',
  MONO: '黑白',
  BLUE_TONE: '蓝调',
  HK_RETRO: '港风',
  CYBER: '赛博',
  WESTERN: '欧美'
}

/** 模型 9 条影调规则 → 中文（与 serve.py 的 derive_tone 保持一致） */
export const TONE_LABELS: Record<string, string> = {
  TONE_WARM: '暖调',
  TONE_COOL: '冷调',
  TONE_HIGH_SAT: '高饱和',
  TONE_LOW_SAT: '低饱和',
  TONE_HIGH_CONTRAST: '高对比',
  TONE_LOW_CONTRAST: '低对比',
  TONE_HIGH_KEY: '高调',
  TONE_LOW_KEY: '低调',
  TONE_LIFTED_BLACK: '抬黑'
}

/** 题材 3 类：只保留词典，界面默认不展示（内测中，人像会误判） */
export const SUBJECT_LABELS: Record<string, string> = {
  ARCHITECTURE: '建筑',
  LANDSCAPE: '风景',
  STILL_FOOD: '静物美食'
}

/** 模型认不出的 code 直接显示原 code，不要瞎猜中文 */
export function labelOf(dict: Record<string, string>, code: unknown): string {
  if (typeof code !== 'string' || !code) return ''
  return dict[code] ?? code
}

export function styleLabel(code: string): string {
  return labelOf(STYLE_LABELS, code)
}

export function toneLabel(code: string): string {
  return labelOf(TONE_LABELS, code)
}

/**
 * 取前 N 个风格标签。confidence 是锚图原型按留一法间隔分档校准过的概率，
 * 可以直接当百分比显示；低于 MIN_CONF 的模型侧已经不给，这里不再二次过滤。
 */
export function topStyles(result: AiClassifyResult | null, count = 2): AiTag[] {
  const list = Array.isArray(result?.style) ? result.style : []
  return list.slice(0, count)
}

export function toneTags(result: AiClassifyResult | null): AiTag[] {
  return Array.isArray(result?.tone) ? result.tone : []
}

/** 界面上一律用「AI 识别」这个来源标签，避免读者以为场景词也是模型给的 */
export const AI_SOURCE_LABEL = 'AI 识别'
