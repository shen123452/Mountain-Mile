import { ref, type CSSProperties } from 'vue'
import { useIntersectionObserver } from '@vueuse/core'

export interface RevealOptions {
  /** 过渡时长（秒） */
  duration?: number
  /** 延迟（秒） */
  delay?: number
  /** 移动轴 */
  axis?: 'x' | 'y'
  /** 初始偏移距离（px） */
  distance?: number
}

/**
 * 落地页滚动显现助手：替代 framer-motion 的 whileInView。
 * 元素初始为 opacity:0 + 偏移，进入视口后过渡到可见状态（once，等效 framer 的 { once: true, margin: '-100px' }）。
 */
export function useReveal(margin = '-100px') {
  const target = ref<HTMLElement | null>(null)
  const inView = ref(false)
  useIntersectionObserver(
    target,
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          inView.value = true
          break
        }
      }
    },
    { rootMargin: margin },
  )

  function style(opts: RevealOptions = {}): CSSProperties {
    const { duration = 0.8, delay = 0, axis = 'y', distance = 40 } = opts
    const shown = inView.value
    const offset = shown ? 0 : distance
    const transform =
      axis === 'y'
        ? `translateY(${offset}px)`
        : offset > 0
          ? `translateX(${offset}px)`
          : `translateX(${-offset}px)`
    return {
      opacity: shown ? 1 : 0,
      transform,
      transition: shown
        ? `opacity ${duration}s ease ${delay}s, transform ${duration}s ease ${delay}s`
        : 'none',
    }
  }

  return { target, inView, style }
}
