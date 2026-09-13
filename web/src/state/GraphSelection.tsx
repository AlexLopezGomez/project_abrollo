import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

export interface GraphSelection {
  /** Hypothesis whose propagation is shown/animated in the graph. */
  hypothesisId: string | null
  /** Increments every time a (re)play is requested, even for the same hypothesis. */
  playToken: number
  /** Node index selected in the inspector (click). */
  nodeIndex: number | null
  select: (hypothesisId: string | null, opts?: { scroll?: boolean }) => void
  setNode: (index: number | null) => void
  clear: () => void
}

const Ctx = createContext<GraphSelection | null>(null)

export function useGraphSelection(): GraphSelection {
  const v = useContext(Ctx)
  if (!v) throw new Error('useGraphSelection outside GraphSelectionProvider')
  return v
}

export function GraphSelectionProvider({ children }: { children: ReactNode }) {
  const [hypothesisId, setHypothesisId] = useState<string | null>(null)
  const [playToken, setPlayToken] = useState(0)
  const [nodeIndex, setNodeIndex] = useState<number | null>(null)

  const select = useCallback((id: string | null, opts?: { scroll?: boolean }) => {
    setHypothesisId(id)
    setPlayToken((t) => t + 1)
    if (opts?.scroll) {
      document.getElementById('graph')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [])
  const setNode = useCallback((i: number | null) => setNodeIndex(i), [])
  const clear = useCallback(() => {
    setHypothesisId(null)
    setNodeIndex(null)
  }, [])

  const value = useMemo(() => ({ hypothesisId, playToken, nodeIndex, select, setNode, clear }), [hypothesisId, playToken, nodeIndex, select, setNode, clear])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}
