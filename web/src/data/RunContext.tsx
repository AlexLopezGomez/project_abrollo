import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import type { DataIndex, GraphData, MetaData, RunData, RunSummary } from './schema'
import { loadGraph, loadIndex, loadMeta, loadRun } from './loader'
import { presentationConfig } from '../presentation.config'

export interface AppData {
  index: DataIndex
  meta: MetaData
  graph: GraphData
  run: RunData
  runs: RunSummary[]
  selectRun: (id: string) => void
  switching: boolean
}

const Ctx = createContext<AppData | null>(null)

export function useAppData(): AppData {
  const v = useContext(Ctx)
  if (!v) throw new Error('useAppData outside RunProvider')
  return v
}

function initialRunId(index: DataIndex): string {
  const params = new URLSearchParams(window.location.search)
  const fromUrl = params.get('run')
  if (fromUrl && index.runs.some((r) => r.id === fromUrl)) return fromUrl
  if (index.runs.some((r) => r.id === presentationConfig.heroRunId)) return presentationConfig.heroRunId
  return index.latestRunId
}

export function RunProvider({ children, fallback }: { children: ReactNode; fallback: ReactNode }) {
  const [base, setBase] = useState<{ index: DataIndex; meta: MetaData; graph: GraphData } | null>(null)
  const [run, setRun] = useState<RunData | null>(null)
  const [switching, setSwitching] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const cache = useRef(new Map<string, RunData>())

  useEffect(() => {
    let alive = true
    Promise.all([loadIndex(), loadMeta(), loadGraph()])
      .then(async ([index, meta, graph]) => {
        const first = await loadRun(initialRunId(index))
        if (!alive) return
        cache.current.set(first.id, first)
        setBase({ index, meta, graph })
        setRun(first)
      })
      .catch((e: unknown) => alive && setError(e instanceof Error ? e.message : String(e)))
    return () => {
      alive = false
    }
  }, [])

  const selectRun = useCallback((id: string) => {
    const cached = cache.current.get(id)
    if (cached) {
      setRun(cached)
      return
    }
    setSwitching(true)
    loadRun(id)
      .then((r) => {
        cache.current.set(id, r)
        setRun(r)
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setSwitching(false))
  }, [])

  useEffect(() => {
    if (!run) return
    const url = new URL(window.location.href)
    url.searchParams.set('run', run.id)
    window.history.replaceState(null, '', url)
  }, [run])

  const data = useMemo<AppData | null>(
    () => (base && run ? { ...base, run, runs: base.index.runs, selectRun, switching } : null),
    [base, run, selectRun, switching],
  )

  if (error) {
    return (
      <div style={{ padding: 80, fontFamily: 'var(--font-mono)' }}>
        <p>Could not load data: {error}</p>
        <p style={{ color: 'var(--muted)' }}>Run `pnpm prepare-data` first.</p>
      </div>
    )
  }
  if (!base || !run) return <>{fallback}</>
  return <Ctx.Provider value={data}>{children}</Ctx.Provider>
}
