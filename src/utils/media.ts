const localWorkAssets = import.meta.glob('../assets/works/*.jpg', {
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
