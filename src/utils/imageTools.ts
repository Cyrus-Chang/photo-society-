/**
 * 本地图片处理（头像 / 壁纸）——不引依赖，纯 Canvas 2D。
 *
 * 用户 2026-11-16 选的是「本机 localStorage」存储，所以这里不调任何上传接口，
 * 只负责把用户选的图压成能塞进 localStorage 的 dataURL：
 *  - 头像：中心裁 1:1，最长边 512；
 *  - 壁纸：等比缩到最长边 1920（不裁），JPEG 质量按体积自动降档。
 * 压缩后仍超限就抛错，由界面如实提示，不静默存半张。
 */

const MAX_SOURCE_BYTES = 12 * 1024 * 1024
/** localStorage 大约 5MB / 域，单个 dataURL 留 1.8M 字符的余量 */
const MAX_DATA_CHARS = 1_800_000

export interface CompressOptions {
  /** 输出最长边（px） */
  maxEdge: number
  /** 首次编码质量，默认 0.82 */
  quality?: number
  /** 头像用：中心裁成正方形 */
  square?: boolean
}

interface LoadedImage {
  drawable: CanvasImageSource
  width: number
  height: number
  release: () => void
}

async function loadImage(file: File): Promise<LoadedImage> {
  if (typeof createImageBitmap === 'function') {
    try {
      const bitmap = await createImageBitmap(file)
      return {
        drawable: bitmap,
        width: bitmap.width,
        height: bitmap.height,
        release: () => bitmap.close()
      }
    } catch {
      /* 老浏览器 / 特殊格式回退到 <img> */
    }
  }
  const url = URL.createObjectURL(file)
  try {
    const image = await new Promise<HTMLImageElement>((resolve, reject) => {
      const node = new Image()
      node.onload = () => resolve(node)
      node.onerror = () => reject(new Error('这张图读不出来，换一张试试'))
      node.src = url
    })
    return {
      drawable: image,
      width: image.naturalWidth,
      height: image.naturalHeight,
      release: () => URL.revokeObjectURL(url)
    }
  } catch (error) {
    URL.revokeObjectURL(url)
    throw error
  }
}

export async function fileToCompressedDataUrl(file: File, options: CompressOptions): Promise<string> {
  if (!file.type.startsWith('image/')) throw new Error('这不是图片文件，换一张 jpg / png / webp 试试')
  if (file.size > MAX_SOURCE_BYTES) throw new Error('图片超过 12MB，换一张小一点的')

  const source = await loadImage(file)
  try {
    if (!source.width || !source.height) throw new Error('这张图读不出来，换一张试试')

    const square = Boolean(options.square)
    const maxEdge = Math.max(64, options.maxEdge)
    let targetWidth = 0
    let targetHeight = 0
    let sx = 0
    let sy = 0
    let sw = source.width
    let sh = source.height

    if (square) {
      const side = Math.min(source.width, source.height, maxEdge)
      sx = (source.width - side) / 2
      sy = (source.height - side) / 2
      sw = side
      sh = side
      targetWidth = Math.round(side)
      targetHeight = Math.round(side)
    } else {
      const scale = Math.min(1, maxEdge / Math.max(source.width, source.height))
      targetWidth = Math.max(1, Math.round(source.width * scale))
      targetHeight = Math.max(1, Math.round(source.height * scale))
    }

    const canvas = document.createElement('canvas')
    canvas.width = targetWidth
    canvas.height = targetHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) throw new Error('当前浏览器不支持 Canvas，换一个浏览器再试')
    // 先铺深色底：带透明通道的 png 压成 jpeg 时不会变成黑块以外的脏边
    ctx.fillStyle = '#0b0d10'
    ctx.fillRect(0, 0, targetWidth, targetHeight)
    ctx.imageSmoothingEnabled = true
    ctx.imageSmoothingQuality = 'high'
    ctx.drawImage(source.drawable, sx, sy, sw, sh, 0, 0, targetWidth, targetHeight)

    const ladder = [options.quality ?? 0.82, 0.7, 0.58, 0.45]
    let dataUrl = ''
    for (const quality of ladder) {
      dataUrl = canvas.toDataURL('image/jpeg', quality)
      if (dataUrl.length <= MAX_DATA_CHARS) return dataUrl
    }
    throw new Error('这张图压完还是太大，换一张小一点的')
  } finally {
    source.release()
  }
}
