const localWorkAssets = import.meta.glob('../assets/works/*.{jpg,webp}', {
  eager: true,
  import: 'default',
  query: '?url'
}) as Record<string, string>

// 螺旋照片墙专用：单独一个目录，避免和 works 的 jpg 混在一起
const spiralAssets = import.meta.glob('../assets/spirals/*.webp', {
  eager: true,
  import: 'default',
  query: '?url'
}) as Record<string, string>

export function localWorkUrl(filename: string) {
  return localWorkAssets[`../assets/works/${filename}`] ?? `/works/${filename}`
}

export function resolveWorkImage(imageUrl: string) {
  if (!imageUrl.startsWith('/works/')) return imageUrl
  return localWorkUrl(imageUrl.slice('/works/'.length))
}

/** 螺旋照片墙图片（src/assets/spirals/*.webp） */
export function spiralUrl(filename: string) {
  return spiralAssets[`../assets/spirals/${filename}`] ?? ''
}

// 整屏背景图专用：src/assets/bg/*.webp（约拍 / 接拍），由 PageAtmosphere.vue 使用
const bgAssets = import.meta.glob('../assets/bg/*.webp', {
  eager: true,
  import: 'default',
  query: '?url'
}) as Record<string, string>

/** 页面背景图（src/assets/bg/*.webp）；文件不存在时返回空串 */
export function bgUrl(filename: string) {
  return bgAssets[`../assets/bg/${filename}`] ?? ''
}

// 空状态 / 氛围图专用：src/assets/ui/*.webp（只作氛围与空态，不充当作品图）
const uiAssets = import.meta.glob('../assets/ui/*.webp', {
  eager: true,
  import: 'default',
  query: '?url'
}) as Record<string, string>

/** UI 氛围图（src/assets/ui/*.webp）；文件不存在时返回空串，模板据此退回 CSS 构图 */
export function uiUrl(filename: string) {
  return uiAssets[`../assets/ui/${filename}`] ?? ''
}
