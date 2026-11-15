export type PostKind = 'requirement' | 'availability' | 'companion'
export type CompanionMode = 'paid-companion' | 'pure-companion'
export type OrderStatus = 'pending' | 'confirmed' | 'shooting-done' | 'settled' | 'cancelled'

export interface WorkCard {
  id: string
  imageUrl: string
  title: string
  photographerId: string
  photographerName: string
  photographerAvatar: string
  location: string
  city: string
  styles: string[]
  types?: string[]
  device?: string
  shootDate: string
  canBook: boolean
  matchReason?: string
  accent?: string
  /** 作者自己写的详细介绍；没写时页面用统一占位文案，不代为编造 */
  story?: string
}

export interface Photographer {
  id: string
  name: string
  avatar: string
  city: string
  bio: string
  tags: string[]
  devices: string[]
  role?: 'photographer' | 'enthusiast'
  responseTime: string
  nextSlot: string
  works: string[]
  verified: boolean
}

export interface MarketPost {
  id: string
  kind: PostKind
  title: string
  city: string
  location: string
  date: string
  time: string
  author: string
  avatar: string
  description: string
  budget?: string
  spots?: string
  mode?: CompanionMode
  status: string
}

export interface BookingOrder {
  id: string
  workId: string
  photographerId: string
  photographerName: string
  photographerAvatar: string
  title: string
  location: string
  date: string
  time: string
  price: string
  status: OrderStatus
  statusLabel: string
  updatedAt: string
}

export interface DiscoverQuery {
  location: string
  scene: string
  shootAt: string
}

export interface FilterPayload {
  date: string
  city: string
  address: string
  budget: number
  type: string
  styles: string[]
  ai: boolean
}
