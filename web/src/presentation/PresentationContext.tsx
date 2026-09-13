import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

export const STEP_COUNT = 5
export const STEP_NAMES = ['Hero', 'Pipeline', 'Knowledge graph', 'Hypothesis', 'Portfolio'] as const

export interface PresentationState {
  active: boolean
  step: number
  playToken: number
  enter: (step?: number) => void
  exit: () => void
  next: () => void
  prev: () => void
  goTo: (step: number) => void
  replay: () => void
}

const Ctx = createContext<PresentationState | null>(null)

export function usePresentation(): PresentationState {
  const v = useContext(Ctx)
  if (!v) throw new Error('usePresentation outside PresentationProvider')
  return v
}

function readUrl(): { active: boolean; step: number } {
  const p = new URLSearchParams(window.location.search)
  const step = Math.min(STEP_COUNT - 1, Math.max(0, Number(p.get('step') ?? 1) - 1 || 0))
  return { active: p.get('present') === '1', step }
}

function writeUrl(active: boolean, step: number) {
  const url = new URL(window.location.href)
  if (active) {
    url.searchParams.set('present', '1')
    url.searchParams.set('step', String(step + 1))
  } else {
    url.searchParams.delete('present')
    url.searchParams.delete('step')
  }
  window.history.replaceState(null, '', url)
}

export function PresentationProvider({ children }: { children: ReactNode }) {
  const [{ active, step }, setState] = useState(readUrl)
  const [playToken, setPlayToken] = useState(0)

  const enter = useCallback((s = 0) => setState({ active: true, step: s }), [])
  const exit = useCallback(() => setState((st) => ({ ...st, active: false })), [])
  const goTo = useCallback((s: number) => setState((st) => ({ ...st, step: Math.min(STEP_COUNT - 1, Math.max(0, s)) })), [])
  const next = useCallback(() => setState((st) => ({ ...st, step: Math.min(STEP_COUNT - 1, st.step + 1) })), [])
  const prev = useCallback(() => setState((st) => ({ ...st, step: Math.max(0, st.step - 1) })), [])
  const replay = useCallback(() => setPlayToken((t) => t + 1), [])

  useEffect(() => {
    writeUrl(active, step)
    document.documentElement.classList.toggle('presenting', active)
  }, [active, step])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable)) return
      if (e.key === 'p' || e.key === 'P') {
        e.preventDefault()
        setState((st) => ({ ...st, active: !st.active }))
        return
      }
      if (!active) return
      switch (e.key) {
        case 'ArrowRight':
        case ' ':
        case 'PageDown':
          e.preventDefault()
          next()
          break
        case 'ArrowLeft':
        case 'PageUp':
          e.preventDefault()
          prev()
          break
        case 'r':
        case 'R':
          e.preventDefault()
          replay()
          break
        case 'Escape':
          exit()
          break
        case 'Home':
          goTo(0)
          break
        case 'End':
          goTo(STEP_COUNT - 1)
          break
        default: {
          const n = Number(e.key)
          if (n >= 1 && n <= STEP_COUNT) goTo(n - 1)
        }
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [active, next, prev, replay, exit, goTo])

  const value = useMemo<PresentationState>(
    () => ({ active, step, playToken, enter, exit, next, prev, goTo, replay }),
    [active, step, playToken, enter, exit, next, prev, goTo, replay],
  )
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}
