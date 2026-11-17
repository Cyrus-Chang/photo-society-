/**
 * 很小的跨组件信号：身份确认后先弹「要不要开始约拍」，
 * 用户点「开始」才通知约拍页打开筛选弹窗。
 *
 * 为什么不用路由 query：改 query 会让 App.vue 里按 fullPath 做 key 的 RouterView
 * 整页重挂载，弹窗和页面会一起闪一下；这里只递增一个 ref，页面不动。
 */
import { ref } from 'vue'

export const bookingFilterRequest = ref(0)

export function requestBookingFilter() {
  bookingFilterRequest.value += 1
}
