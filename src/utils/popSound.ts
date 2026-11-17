/**
 * 泡泡音效（2026-11-15）
 *
 * 为什么不用音频文件：新增音频要走素材目录 + media.ts，而且 mp3 解码还有首帧延迟。
 * 这里用 Web Audio 现场合成一个 0.17s 的「啵」：正弦从低往高快速滑一下，
 * 再叠 30ms 带通噪声当破泡的纸张感。不加依赖、不占首屏体积。
 *
 * 浏览器要求 AudioContext 必须在用户手势里创建/恢复；本文件只在点击回调里调用，
 * 所以第一次点击时创建即可。失败一律静默（静音标签页 / 不支持 Web Audio 都不影响筛选）。
 */

let context: AudioContext | null = null

/** 宫商角徵羽五声音阶：每个泡泡按索引落在一个音上，连续点不会像警报 */
const PENTATONIC = [1, 9 / 8, 5 / 4, 3 / 2, 5 / 3]

function audioContext(): AudioContext | null {
  if (typeof window === 'undefined') return null
  const Ctor = window.AudioContext ?? (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
  if (!Ctor) return null
  if (!context) context = new Ctor()
  return context
}

/**
 * 播放一声泡泡。
 * @param enabled 用户是否开启了音效
 * @param seed    泡泡索引，决定音高（五声音阶循环）
 * @param dismiss true = 取消选择，音高降一点，和「选中」区分
 */
export function playPop(enabled: boolean, seed = 0, dismiss = false) {
  if (!enabled) return
  const ctx = audioContext()
  if (!ctx) return
  if (ctx.state === 'suspended') void ctx.resume()

  const now = ctx.currentTime
  const ratio = PENTATONIC[Math.abs(seed) % PENTATONIC.length]
  const base = 430 * ratio * (dismiss ? 0.74 : 1)

  const gain = ctx.createGain()
  gain.gain.setValueAtTime(0.0001, now)
  gain.gain.exponentialRampToValueAtTime(0.085, now + 0.008)
  gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.16)
  gain.connect(ctx.destination)

  const osc = ctx.createOscillator()
  osc.type = 'sine'
  osc.frequency.setValueAtTime(base * 0.62, now)
  osc.frequency.exponentialRampToValueAtTime(base * 1.42, now + 0.05)
  osc.frequency.exponentialRampToValueAtTime(base * 0.9, now + 0.16)
  osc.connect(gain)
  osc.start(now)
  osc.stop(now + 0.17)

  // 破泡的一下：极短噪声过带通，音量很低，只负责「啵」的齿音
  const length = Math.max(1, Math.floor(ctx.sampleRate * 0.03))
  const buffer = ctx.createBuffer(1, length, ctx.sampleRate)
  const data = buffer.getChannelData(0)
  for (let i = 0; i < length; i += 1) {
    const decay = (1 - i / length) ** 2
    data[i] = (Math.random() * 2 - 1) * decay
  }
  const noise = ctx.createBufferSource()
  noise.buffer = buffer
  const filter = ctx.createBiquadFilter()
  filter.type = 'bandpass'
  filter.frequency.value = 1800
  filter.Q.value = 1.1
  const noiseGain = ctx.createGain()
  noiseGain.gain.value = 0.03
  noise.connect(filter)
  filter.connect(noiseGain)
  noiseGain.connect(ctx.destination)
  noise.start(now)
}
