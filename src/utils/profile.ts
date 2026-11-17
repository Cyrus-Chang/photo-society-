/**
 * 本机个人资料（2026-11-15）
 *
 * 只存在 localStorage，不接后端、不上传。字段范围是用户在对话里确认过的：
 * 性别 / 年龄段 / 职业 / 常驻城市 / 一句话简介；拍摄偏好与联系方式放在资料页里。
 *
 * 登录态（称呼、身份、MBTI）仍然在 utils/session.ts，这里不复制那一层，
 * 否则同一份资料会出现两个真源。
 */

import { reactive } from 'vue'

export const GENDERS = ['不公开', '女', '男', '其他']
export const AGE_RANGES = ['18–24', '25–30', '31–40', '40+']
export const OCCUPATIONS = ['学生', '上班族', '自由职业', '摄影师', '其他']
export const CITIES = ['西安', '成都', '青岛', '北京', '上海', '杭州', '广州', '深圳', '重庆', '南京', '武汉', '厦门']
export const STYLE_PREFS = ['日系', '韩系', 'ins风', '清新', '胶片', '复古', '电影感', '暗调', '黑白', '蓝调', '港风', '赛博', '欧美', '高饱和']
export const AVAILABILITY = ['工作日', '周末', '都行']
export const MBTI_TYPES = ['INTJ', 'INTP', 'ENTJ', 'ENTP', 'INFJ', 'INFP', 'ENFJ', 'ENFP', 'ISTJ', 'ISFJ', 'ESTJ', 'ESFJ', 'ISTP', 'ISFP', 'ESTP', 'ESFP']

export interface ProfileState {
  gender: string
  ageRange: string
  occupation: string
  city: string
  bio: string
  /** 喜欢的风格，可多选 */
  styles: string[]
  device: string
  availability: string
  /** 是否允许匹配时参考年龄段与职业（默认开） */
  matchProfile: boolean
  updatedAt: number
}

const STORAGE_KEY = 'paishe.profile.v1'

const defaults: ProfileState = {
  gender: '不公开',
  ageRange: '',
  occupation: '',
  city: '西安',
  bio: '',
  styles: [],
  device: '',
  availability: '都行',
  matchProfile: true,
  updatedAt: 0
}

function read(): ProfileState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { ...defaults }
    const parsed = JSON.parse(raw) as Partial<ProfileState>
    return {
      ...defaults,
      ...parsed,
      styles: Array.isArray(parsed.styles) ? parsed.styles.filter((item): item is string => typeof item === 'string') : [],
      updatedAt: Number(parsed.updatedAt) || 0
    }
  } catch {
    return { ...defaults }
  }
}

export const profile = reactive<ProfileState>(read())

function persist() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(profile))
  } catch {
    /* 隐私模式写不进去，不影响本次会话 */
  }
}

export function saveProfile(patch: Partial<ProfileState>) {
  Object.assign(profile, patch, { updatedAt: Date.now() })
  persist()
}

/** 资料完整度（资料页顶部的进度用，0–100） */
export function profileCompleteness(state: ProfileState = profile) {
  const checks = [Boolean(state.gender && state.gender !== '不公开'), Boolean(state.ageRange), Boolean(state.occupation), Boolean(state.city), Boolean(state.bio.trim()), state.styles.length > 0, Boolean(state.device.trim())]
  return Math.round((checks.filter(Boolean).length / checks.length) * 100)
}
