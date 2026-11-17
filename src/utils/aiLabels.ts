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
  aboveThreshold?: boolean
  confidenceSource?: string
  needsReview?: boolean
  source?: AiTagSource | string
}

export interface AiConfidenceCalibration {
  method?: string
  binCenters?: number[]
  binAccuracies?: number[]
  looAccuracy?: number
  reviewThreshold?: number
  gateConfidence?: number
  maxPortraitProbability?: number
}

export interface AiClassifyResult {
  subject?: AiTag[]
  subjectRaw?: AiTag[]
  subjectVisible?: AiTag[]
  style?: AiTag[]
  tone?: AiTag[]
  color?: Record<string, number>
  modelVersion?: Record<string, string>
  fallback?: string
  latencyMs?: number
  /** 置信度来自锚图留一法间隔分档的实测正确率映射。 */
  confidenceSource?: string | Record<string, string>
  confidenceCalibration?: {
    style?: AiConfidenceCalibration
    subject?: AiConfidenceCalibration
  }
  /** 低于业务阈值时要求用户确认，不把数值伪装成确定结论。 */
  needsReview?: boolean
  confidenceThreshold?: number
  reviewReasons?: string[]
  subjectGate?: {
    passed?: boolean
    reason?: string
    needsReview?: boolean
    personProbability?: number | null
    nonPersonProbability?: number | null
  }
}

export interface AiLabelDefinition {
  name: string
  aliases: string[]
  description: string
}

/**
 * 模型 13 类风格、9 条影调、3 类题材的展示词典。
 * name/aliases/description 与 ai-classifier/labels/dictionary.json 对齐；
 * 这里保留一份前端只读副本，保证模型 code 不会散落在组件里。
 */
export const AI_LABEL_DICTIONARY = {
  STYLE: {
    JAPANESE: { name: '日系', aliases: ['日系空气感', '日系清透'], description: '低饱和、高明度、柔光、轻微高光溢出、带青绿倾向、空气感与通透感' },
    KOREAN: { name: '韩系', aliases: ['奶油感', '韩系清透'], description: '奶油感：皮肤通透白皙偏粉、浅色调、低对比、黑位轻微抬升、画面干净、锐度中高。多用于棚拍与咖啡馆外景' },
    INS: { name: 'ins风', aliases: ['Instagram风', '极简留白'], description: '高亮、低对比、黑位抬升（暗部不死黑）、画面干净留白、轻暖白平衡、构图规整、有几何秩序' },
    FRESH: { name: '清新', aliases: ['明亮清透', '清透'], description: '高明度、低饱和、通透、浅色、阳光感、干净。明度比日系更高、更白亮' },
    FILM: { name: '胶片', aliases: ['胶片感', '颗粒感'], description: '颗粒感明显、黑位抬升、青影暖高光的色彩偏移（交叉冲洗感）、对比柔和、高光有轻微溢出' },
    VINTAGE: { name: '复古', aliases: ['怀旧', '褪色感'], description: '褪色感：整体低饱和、黄褐偏移、对比柔和、色彩记忆感陈旧。常见于老照片放大与胶片扫描仿真' },
    CINEMATIC: { name: '电影感', aliases: ['青橙调', '电影调色'], description: '青橙调色（teal & orange）：暗部偏青、高光偏橙、S 形对比曲线、两端不裁切（保留高光与暗部细节）、常有宽画幅构图' },
    DARK_MOOD: { name: '暗调', aliases: ['低调情绪', '低明度'], description: '低调摄影：大面积暗部、单一光源、情绪压抑、明度均值低、阴影占比高' },
    MONO: { name: '黑白', aliases: ['单色', '灰阶'], description: '完全去色，饱和度接近 0，仅灰阶' },
    BLUE_TONE: { name: '蓝调', aliases: ['冷蓝', '青蓝'], description: '整体偏蓝或青蓝：LAB 的 b* 均值为负、暗部明显偏冷、白平衡偏冷。可以是亮的也可以是暗的' },
    HK_RETRO: { name: '港风', aliases: ['港式复古', '港片风'], description: '偏绿青的中间调、暖肤色、硬光、年代颗粒、港片式构图与人物姿态' },
    CYBER: { name: '赛博', aliases: ['赛博朋克', '霓虹'], description: '霓虹高饱和、青品对冲、硬光、暗部保留高饱和光斑、夜景/室内霓虹环境' },
    WESTERN: { name: '欧美', aliases: ['欧美杂志', '时尚杂志'], description: '欧美杂志/时尚 editorial 感：高反差、硬光、强轮廓阴影、暖中性色或冷蓝背景、妆造强烈、姿态张扬' }
  },
  TONE: {
    TONE_WARM: { name: '暖调', aliases: ['偏暖'], description: '整体偏暖（R 通道均值高于 B）' },
    TONE_COOL: { name: '冷调', aliases: ['偏冷'], description: '整体偏冷' },
    TONE_HIGH_SAT: { name: '高饱和', aliases: ['浓烈色彩'], description: '色彩浓烈' },
    TONE_LOW_SAT: { name: '低饱和', aliases: ['低彩度', '克制色彩'], description: '灰调、克制' },
    TONE_HIGH_CONTRAST: { name: '高对比', aliases: ['硬朗'], description: '明暗跨度大，硬朗' },
    TONE_LOW_CONTRAST: { name: '柔和', aliases: ['低对比', '柔和'], description: '明暗跨度小，柔' },
    TONE_HIGH_KEY: { name: '高调', aliases: ['明亮'], description: '整体明亮' },
    TONE_LOW_KEY: { name: '低调', aliases: ['暗部多'], description: '整体暗' },
    TONE_LIFTED_BLACK: { name: '黑位抬升', aliases: ['抬黑', '灰黑'], description: '暗部不死黑，胶片/ins 的典型特征' }
  },
  SUBJECT: {
    ARCHITECTURE: { name: '建筑', aliases: ['建筑摄影', '建筑空间'], description: '非人像，主体为建筑立面、结构、几何线条、室内空间结构。可以有极小的人物作为尺度参照' },
    LANDSCAPE: { name: '风光', aliases: ['风景', '自然景观'], description: '非人像，自然景观为主体：山川、湖海、天空、云、植被、雪景、星空' },
    STILL_FOOD: { name: '静物美食', aliases: ['静物', '美食', '产品静物'], description: '非人像，单个/少量主体可控布景：产品、桌面小物、花艺、食物与饮品（探店、菜品、咖啡）' }
  }
} as const

/** 模型 13 类风格 → 中文（与 Python 词典保持一致） */
export const STYLE_LABELS: Record<string, string> = {
  ...Object.fromEntries(Object.entries(AI_LABEL_DICTIONARY.STYLE).map(([code, item]) => [code, item.name]))
}

/** 模型 9 条影调规则 → 中文（与 serve.py 的 derive_tone 保持一致） */
export const TONE_LABELS: Record<string, string> = {
  ...Object.fromEntries(Object.entries(AI_LABEL_DICTIONARY.TONE).map(([code, item]) => [code, item.name]))
}

/** 题材 3 类：只保留词典，界面默认不展示（内测中，人像会误判） */
export const SUBJECT_LABELS: Record<string, string> = {
  ...Object.fromEntries(Object.entries(AI_LABEL_DICTIONARY.SUBJECT).map(([code, item]) => [code, item.name]))
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

export function subjectLabel(code: string): string {
  return labelOf(SUBJECT_LABELS, code)
}

export function labelDefinition(kind: 'STYLE' | 'TONE' | 'SUBJECT', code: string): AiLabelDefinition | undefined {
  return AI_LABEL_DICTIONARY[kind][code as keyof typeof AI_LABEL_DICTIONARY[typeof kind]]
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
