/**
 * 本机个性化：头像 + 页面壁纸（2026-11-16 用户拍板）
 *
 * 用户选的是「全局一张壁纸 + 本机 localStorage」：
 *  - 头像：个人资料页上传，顶栏同步；
 *  - 壁纸：一张，用在个人信息、摄影工作台、我的约拍（三个页面共用）；
 *  - 只存这台设备的浏览器，不接后端、不上传（资料页那句「不会上传」继续成立）。
 *
 * 拆成独立文件而不是塞进 utils/profile.ts：profile 是「资料字段」，
 * 这里是「外观」，换后端时两者的迁移节奏不一样。
 */

import { reactive, ref } from 'vue'
import { bgUrl, localWorkUrl } from './media'

export interface WallpaperPreset {
  id: string
  name: string
  note: string
  kind: 'image' | 'gradient'
  value: string
}

/** 内置图库：两张页面背景 + 五张平台作品 + 两张 CSS 渐变 */
export const WALLPAPER_PRESETS: WallpaperPreset[] = [
  { id: 'star-trail', name: '雪原星轨', note: '约拍页背景', kind: 'image', value: bgUrl('discover-star-trail.webp') },
  { id: 'nebula', name: '星云', note: '接拍页背景', kind: 'image', value: bgUrl('market-nebula.webp') },
  { id: 'lake', name: '湖面长廊', note: '作品 · 颐和园', kind: 'image', value: localWorkUrl('9e891167f97b19510a05cccde75dab8d.jpg') },
  { id: 'mountain', name: '华山石壁', note: '作品 · 山岳', kind: 'image', value: localWorkUrl('20cd7d65c810bd3c1049832daf043ef6.jpg') },
  { id: 'night-market', name: '夜市红伞', note: '作品 · 夜景', kind: 'image', value: localWorkUrl('7477a4d06549c6111e68b189b755bf6d.jpg') },
  { id: 'prayer-flags', name: '经幡色阶', note: '作品 · 色彩', kind: 'image', value: localWorkUrl('2d877e352b8d4982db812575933c8f59.jpg') },
  { id: 'door', name: '门与远山', note: '作品 · 建筑', kind: 'image', value: localWorkUrl('6383584ebff23e0a46860c6483194e6a.jpg') },
  { id: 'snow-temple', name: '雪中古寺', note: '作品 · 雪景', kind: 'image', value: localWorkUrl('6741fc86c8912535c59258de05236f46.jpg') },
  { id: 'grad-night', name: '夜色渐变', note: '纯 CSS', kind: 'gradient', value: 'linear-gradient(158deg, #070b10 0%, #101a24 46%, #241a19 100%)' },
  { id: 'grad-dusk', name: '暮色渐变', note: '纯 CSS', kind: 'gradient', value: 'linear-gradient(158deg, #120d18 0%, #2a1c22 48%, #3a2a1d 100%)' }
]

export type WallpaperChoice =
  | { kind: 'preset'; id: string }
  | { kind: 'custom'; dataUrl: string }
  | null

export interface PersonalizeState {
  /** 上传头像的 dataURL；空串 = 用姓名首字母生成的默认头像 */
  avatar: string
  wallpaper: WallpaperChoice
  updatedAt: number
}

const STORAGE_KEY = 'paishe.personalize.v1'
const defaults: PersonalizeState = { avatar: '', wallpaper: null, updatedAt: 0 }

function normalizeWallpaper(input: unknown): WallpaperChoice {
  if (!input || typeof input !== 'object') return null
  const value = input as { kind?: unknown; id?: unknown; dataUrl?: unknown }
  if (value.kind === 'preset' && typeof value.id === 'string' && WALLPAPER_PRESETS.some((item) => item.id === value.id)) {
    return { kind: 'preset', id: value.id }
  }
  if (value.kind === 'custom' && typeof value.dataUrl === 'string' && value.dataUrl.startsWith('data:image/')) {
    return { kind: 'custom', dataUrl: value.dataUrl }
  }
  return null
}

function read(): PersonalizeState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { ...defaults }
    const parsed = JSON.parse(raw) as Partial<PersonalizeState>
    return {
      avatar: typeof parsed.avatar === 'string' && parsed.avatar.startsWith('data:image/') ? parsed.avatar : '',
      wallpaper: normalizeWallpaper(parsed.wallpaper),
      updatedAt: Number(parsed.updatedAt) || 0
    }
  } catch {
    return { ...defaults }
  }
}

export const personalize = reactive<PersonalizeState>(read())

function persist(): boolean {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(personalize))
    return true
  } catch {
    /* 隐私模式或超出配额：如实返回 false，由调用方提示，不假装成功 */
    return false
  }
}

export function setAvatar(dataUrl: string): boolean {
  const previous = personalize.avatar
  personalize.avatar = dataUrl
  personalize.updatedAt = Date.now()
  if (persist()) return true
  personalize.avatar = previous
  return false
}

export function clearAvatar() {
  personalize.avatar = ''
  personalize.updatedAt = Date.now()
  persist()
}

export function setWallpaper(choice: WallpaperChoice): boolean {
  const previous = personalize.wallpaper
  personalize.wallpaper = choice
  personalize.updatedAt = Date.now()
  if (persist()) return true
  personalize.wallpaper = previous
  return false
}

export function clearWallpaper() {
  setWallpaper(null)
}

export function wallpaperPresetOf(choice: WallpaperChoice): WallpaperPreset | null {
  return choice?.kind === 'preset' ? WALLPAPER_PRESETS.find((item) => item.id === choice.id) ?? null : null
}

export function wallpaperName(choice: WallpaperChoice = personalize.wallpaper): string {
  if (!choice) return '未设置'
  if (choice.kind === 'custom') return '我上传的图'
  return wallpaperPresetOf(choice)?.name ?? '未设置'
}

/** 直接给模板用的 background-image 样式；没设壁纸返回 null */
export function wallpaperStyle(choice: WallpaperChoice = personalize.wallpaper): Record<string, string> | null {
  if (!choice) return null
  if (choice.kind === 'custom') return { backgroundImage: `url("${choice.dataUrl}")` }
  const preset = wallpaperPresetOf(choice)
  if (!preset || !preset.value) return null
  return { backgroundImage: preset.kind === 'gradient' ? preset.value : `url("${preset.value}")` }
}

/* 壁纸选择器是全局唯一的弹窗（App.vue 挂一次），三个页面只负责打开它 */
export const wallpaperPickerOpen = ref(false)
export function openWallpaperPicker() { wallpaperPickerOpen.value = true }
export function closeWallpaperPicker() { wallpaperPickerOpen.value = false }
