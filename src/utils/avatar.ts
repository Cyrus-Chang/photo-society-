/**
 * 头像占位（2026-11-14，用户确认方案 A）。
 *
 * 背景：mock 里 46 个头像原来是 https://i.pravatar.cc 外链，国内直连不可达，
 * 加载失败就是一个白方块。这里改成「姓名首字母 + 根据名字哈希取色的圆块」，
 * 内联成 data:image/svg+xml 直接塞进 <img src>，模板一行都不用改（改模板会牵动 8 个页面）。
 *
 * 换回真实头像时：把 mock 里的 photographerAvatar / avatar 指向本地图或接口返回的真实 URL 即可，
 * 这个函数只处理 http(s) 开头的外链，本地资源不会被它碰。
 */

/** 深色页上压得住、彼此可分辨的一组底色（都偏暗，配深色字 8:1 以上） */
const palette = ['#e98b6b', '#d8a26a', '#9dbba4', '#93a7c9', '#c79aa6', '#a9ab86']

function hashOf(text: string) {
  let hash = 0
  for (const char of text) {
    hash = (hash * 31 + (char.codePointAt(0) ?? 0)) >>> 0
  }
  return hash
}

function escapeXml(text: string) {
  return text.replace(/[&<>"']/g, (char) => {
    switch (char) {
      case '&': return '&amp;'
      case '<': return '&lt;'
      case '>': return '&gt;'
      case '"': return '&quot;'
      default: return '&apos;'
    }
  })
}

/**
 * 生成一个头像 data URI。
 * @param name 用来取首字和配色的名字（中文取第一个字，英文取第一个字母）
 */
export function makeAvatar(name?: string | null) {
  const label = String(name ?? '').trim()
  const initial = Array.from(label)[0] ?? '拍'
  const bg = palette[hashOf(label || 'paishe') % palette.length]
  const svg = [
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" role="img">',
    `<rect width="96" height="96" rx="48" fill="${bg}"/>`,
    `<text x="48" y="50" text-anchor="middle" dominant-baseline="central" font-family="'Noto Serif SC','Songti SC',serif" font-size="40" font-weight="600" fill="#141a1f">${escapeXml(initial)}</text>`,
    '</svg>'
  ].join('')
  return `data:image/svg+xml,${encodeURIComponent(svg)}`
}

const remote = /^https?:\/\//i

/** 这条地址是不是外链（外链在国内基本拿不到，用它判断要不要换成本地占位） */
export function isRemoteImage(url?: string | null) {
  return remote.test(String(url ?? ''))
}

export default makeAvatar
