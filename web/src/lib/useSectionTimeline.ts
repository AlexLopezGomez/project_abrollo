import { useRef, type RefObject } from 'react'
import { gsap, useGSAP, REDUCE, MOTION, ScrollTrigger } from './gsap'

export interface SectionTimelineOptions {
  scope: RefObject<HTMLElement>
  /** `scroll`: play once when the section enters the viewport. `stage`: play immediately (presentation). */
  mode: 'scroll' | 'stage'
  /** Bump to replay (stage mode). */
  playToken?: number
  /** Extra dependencies that should rebuild the timeline. */
  deps?: unknown[]
  /** Viewport start for the scroll trigger. */
  start?: string
}

/**
 * Builds one deterministic GSAP timeline per section. The same builder is used on the page
 * (played by ScrollTrigger) and in presentation mode (played on mount / on replay).
 * Reduced-motion users get the finished state immediately via gsap.matchMedia().
 */
export function useSectionTimeline(
  build: (tl: gsap.core.Timeline, ctx: { reduced: boolean }) => void,
  { scope, mode, playToken = 0, deps = [], start = 'top 70%' }: SectionTimelineOptions,
): RefObject<gsap.core.Timeline | null> {
  const tlRef = useRef<gsap.core.Timeline | null>(null)

  useGSAP(
    () => {
      const mm = gsap.matchMedia()
      mm.add({ reduce: REDUCE, motion: MOTION }, (context) => {
        const reduced = Boolean(context.conditions?.reduce)
        const tl = gsap.timeline({ paused: true, defaults: { ease: 'power3.out' } })
        build(tl, { reduced })
        tlRef.current = tl
        if (reduced) {
          tl.progress(1)
          return
        }
        if (mode === 'stage') {
          tl.play(0)
          return
        }
        const st = ScrollTrigger.create({
          trigger: scope.current,
          start,
          once: true,
          onEnter: () => tl.play(0),
        })
        return () => st.kill()
      })
      return () => mm.revert()
    },
    { scope, dependencies: [mode, playToken, ...deps], revertOnUpdate: true },
  )

  return tlRef
}
