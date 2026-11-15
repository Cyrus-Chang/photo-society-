/**
 * 品牌文案的唯一来源。
 *
 * 2026-11-14 用户确认：英文副标 PHOTO SOCIETY「还没定」。
 * 定稿时只改这里，全站生效（App.vue / HomePage / LoginPage / IdentityModal）。
 *
 * 注意两处例外，改品牌时要手动同步：
 * 1. index.html 的 <title> 与 <meta name="description">（HTML 无法 import）；
 * 2. styles.css 里没有品牌文案，只有颜色，不用管。
 */
export const brand = {
  /** 中文名 */
  cn: '拍社',
  /** 英文副标（待定稿） */
  en: 'PHOTO SOCIETY',
  /** 首页落字动画用的拼音 */
  pinyin: 'PĀI SHÈ'
} as const

export default brand
