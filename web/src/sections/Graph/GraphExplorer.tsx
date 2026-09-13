import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import styles from './GraphExplorer.module.css'
import { useAppData } from '../../data/RunContext'
import { useGraphSelection } from '../../state/GraphSelection'
import { GRAPH_VIEWS, type GraphView } from '../../data/graphViews'
import { GraphCanvas, type GraphCanvasHandle } from '../../graph/GraphCanvas'
import { PropagationOverlay } from '../../graph/PropagationOverlay'
import { Inspector, ROLE_COLOR, ROLE_LABEL } from '../../graph/Inspector'
import { buildPropagationTimeline, type PropagationTimeline } from '../../graph/propagationTimeline'
import type { NodeRole } from '../../graph/renderer'
import { useGSAP, REDUCE } from '../../lib/gsap'
import { useSectionTimeline } from '../../lib/useSectionTimeline'
import { fmtInt, fmtMoney, fmtPct, fmtSigned, titleCase } from '../../lib/format'
import { presentationConfig } from '../../presentation.config'
import type { SectionProps } from '../Hero/Hero'

interface Props extends SectionProps {
  featuredId?: string
}

export function GraphExplorer({ mode = 'scroll', playToken = 0, featuredId }: Props) {
  const { graph, run } = useAppData()
  const sel = useGraphSelection()
  const stage = mode === 'stage'
  const scope = useRef<HTMLElement>(null)
  const canvasRef = useRef<GraphCanvasHandle>(null)
  const progressRef = useRef<HTMLInputElement>(null)
  const timelineRef = useRef<PropagationTimeline | null>(null)

  const [view, setView] = useState<GraphView>(stage ? presentationConfig.graphView : 'neighborhood')
  const [query, setQuery] = useState('')
  const [labelMode, setLabelMode] = useState<'auto' | 'all' | 'none'>('auto')

  // In stage mode the selection is local (featured hypothesis); on the page it is shared.
  const featuredDefault = useMemo(() => {
    const id = presentationConfig.featuredHypothesisId
    return id && run.hypotheses.some((h) => h.id === id) ? id : run.featuredHypothesisId
  }, [run])
  const hypothesisId = stage ? (featuredId ?? featuredDefault) : sel.hypothesisId === 'featured' ? featuredDefault : sel.hypothesisId
  const hypothesis = useMemo(() => run.hypotheses.find((h) => h.id === hypothesisId) ?? null, [run, hypothesisId])
  const dag = useMemo(() => run.dag.find((d) => d.hypothesisId === hypothesisId) ?? null, [run, hypothesisId])
  const propagation = hypothesisId ? (run.propagation[hypothesisId] ?? null) : null

  // node roles for the current run
  const { roles, heldWeights } = useMemo(() => {
    const roles: NodeRole[] = graph.nodes.map((n) => (n.ndx ? 'ndx' : 'other'))
    const held = new Map<string, number>()
    for (const t of run.tickers) {
      held.set(t.ticker, t.amount)
      if (t.index >= 0) roles[t.index] = 'held'
    }
    for (const h of run.hypotheses) if (h.originIndex >= 0) roles[h.originIndex] = 'origin'
    return { roles, heldWeights: held }
  }, [graph, run])

  // visible node set = view ∪ propagation nodes
  const visible = useMemo<Set<number> | null>(() => {
    if (view === 'full' && !propagation) return null
    const base = view === 'full' ? graph.nodes.map((_, i) => i) : view === 'focus' ? run.views.focus : run.views.neighborhood
    const s = new Set<number>(base)
    if (propagation) for (const p of propagation.paths) for (const n of p.nodes) s.add(n)
    return s
  }, [view, run, graph, propagation])

  const visibleCount = useMemo(() => {
    if (!visible) return { nodes: graph.stats.nNodes, edges: graph.stats.nEdges }
    let edges = 0
    for (const [s, d] of graph.edges) if (visible.has(s) && visible.has(d)) edges++
    return { nodes: visible.size, edges }
  }, [visible, graph])

  const shifts = useMemo(() => {
    const m = new Map<number, { shift: number; held: boolean }>()
    dag?.affected.forEach((a) => a.index >= 0 && m.set(a.index, { shift: a.shift, held: a.inPortfolio }))
    return m
  }, [dag])

  const [nodeIndex, setNodeIndexLocal] = useState<number | null>(null)
  const nodeSelected = stage ? nodeIndex : sel.nodeIndex
  const setNode = useCallback(
    (i: number | null) => {
      if (stage) setNodeIndexLocal(i)
      else sel.setNode(i)
    },
    [stage, sel],
  )

  // fit on run/view change
  useEffect(() => {
    canvasRef.current?.fit(undefined, { duration: 0 })
  }, [run.id, view])

  // section reveal
  useSectionTimeline(
    (tl) => {
      if (!stage) tl.from('[data-head]', { autoAlpha: 0, y: 12, duration: 0.6 }, 0)
      tl.from('[data-bench]', { autoAlpha: 0, y: 16, duration: 0.8 }, 0.15)
    },
    { scope, mode, playToken, deps: [run.id] },
  )

  // propagation: fit to the hypothesis, then build + play the timeline
  const propToken = stage ? playToken : sel.playToken
  useGSAP(
    () => {
      timelineRef.current?.dispose()
      timelineRef.current = null
      const r = canvasRef.current?.renderer()
      const wrap = canvasRef.current?.element()
      if (!propagation || !r || !wrap) return
      const reduced = window.matchMedia(REDUCE).matches
      const inspector = scope.current?.querySelector<HTMLElement>('[data-inspector]')
      const nodes = new Set<number>([propagation.origin, ...propagation.paths.map((p) => p.target)])
      let cancelled = false
      canvasRef.current?.fit(nodes, {
        duration: reduced ? 0 : 0.9,
        padding: 90,
        onComplete: () => {
          if (cancelled) return
          const built = buildPropagationTimeline({
            wrap,
            renderer: r,
            graph,
            propagation,
            held: heldWeights,
            chipFor: (ticker) => inspector?.querySelector<HTMLElement>(`[data-weight-chip="${ticker}"]`) ?? null,
            reduced,
            maxFlyingChips: 14,
          })
          timelineRef.current = built
          built.tl.eventCallback('onUpdate', () => {
            if (progressRef.current) progressRef.current.value = String(built.tl.progress())
          })
          built.tl.play(0)
        },
      })
      return () => {
        cancelled = true
      }
    },
    { scope, dependencies: [propagation, propToken, run.id] },
  )

  useEffect(() => () => timelineRef.current?.dispose(), [])

  const onScrub = (p: number) => {
    const t = timelineRef.current?.tl
    if (!t) return
    t.pause()
    t.progress(p)
  }
  const replay = () => {
    const t = timelineRef.current?.tl
    if (t) t.restart()
    else if (hypothesisId) sel.select(hypothesisId)
  }

  // search
  const results = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (q.length < 2) return []
    const out: number[] = []
    for (let i = 0; i < graph.nodes.length; i++) {
      const n = graph.nodes[i]!
      if (visible && !visible.has(i)) continue
      if (n.tickers.some((t) => t.toLowerCase().startsWith(q)) || n.name.toLowerCase().includes(q)) out.push(i)
    }
    const exact = (i: number) => (graph.nodes[i]!.tickers.some((t) => t.toLowerCase() === q) ? 1 : 0)
    return out.sort((a, b) => exact(b) - exact(a) || graph.nodes[b]!.deg - graph.nodes[a]!.deg).slice(0, 8)
  }, [query, graph, visible])

  const goToNode = (i: number) => {
    setQuery('')
    setNode(i)
    canvasRef.current?.zoomTo(i, 2.4)
  }

  const onSelectHypothesis = (id: string) => {
    setNode(null)
    sel.select(id)
  }

  return (
    <section id="graph" ref={scope} className={stage ? undefined : 'section'} style={stage ? { height: '100%' } : undefined}>
      <div className="container" style={stage ? { height: '100%', paddingBlock: 0 } : undefined}>
        {!stage && (
          <div className="section-head" data-head data-reveal>
            <h2 className="section-title">
              Knowledge graph <em>— where the hypotheses come from</em>
            </h2>
            <p className="section-lede">
              {fmtInt(graph.stats.nNodes)} Cala entities and {fmtInt(graph.stats.nEdges)} typed relationships around the NASDAQ-100. A
              hypothesis starts at one entity and propagates along real edges to the tickers it can move.
            </p>
          </div>
        )}
        <div className={`${styles.bench} ${stage ? styles.stage : ''}`} data-bench data-reveal>
          <div className={styles.left}>
            {!stage && (
              <div className={styles.controls}>
                <span className={styles.seg}>
                  {GRAPH_VIEWS.map((v) => (
                    <button key={v.id} className={view === v.id ? styles.on : ''} onClick={() => setView(v.id)} title={v.hint}>
                      {v.label}
                    </button>
                  ))}
                </span>
                <select
                  className={styles.select}
                  value={hypothesisId ?? ''}
                  onChange={(e) => (e.target.value ? onSelectHypothesis(e.target.value) : sel.clear())}
                  aria-label="Hypothesis to propagate"
                >
                  <option value="">Propagate a hypothesis…</option>
                  {run.hypotheses.map((h) => {
                    const d = run.dag.find((x) => x.hypothesisId === h.id)
                    return (
                      <option key={h.id} value={h.id}>
                        {h.id} · {titleCase(h.originName)} · {fmtSigned(h.magnitude * 100, 0)}% → {d?.affected.length ?? 0} tickers
                      </option>
                    )
                  })}
                </select>
                <div className={styles.search}>
                  <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search entity or ticker" aria-label="Search" />
                  {results.length > 0 && (
                    <div className={styles.results}>
                      {results.map((i) => (
                        <button key={i} onClick={() => goToNode(i)}>
                          {titleCase(graph.nodes[i]!.name)}
                          <span>
                            {graph.nodes[i]!.tickers[0] ?? graph.nodes[i]!.type} · {graph.nodes[i]!.deg}
                          </span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
            <div className={styles.canvasCard}>
              {!stage && (
                <div className={styles.floating}>
                  <span className={styles.seg}>
                    <button onClick={() => canvasRef.current?.zoomBy(0.7)} title="Zoom out">
                      −
                    </button>
                    <button onClick={() => canvasRef.current?.zoomBy(1.4)} title="Zoom in">
                      +
                    </button>
                    <button onClick={() => canvasRef.current?.fit(undefined, { duration: 0.6 })} title="Fit to view">
                      Fit
                    </button>
                  </span>
                  <span className={styles.seg}>
                    {(['auto', 'all', 'none'] as const).map((m) => (
                      <button key={m} className={labelMode === m ? styles.on : ''} onClick={() => setLabelMode(m)}>
                        labels: {m}
                      </button>
                    ))}
                  </span>
                </div>
              )}
              {stage && hypothesis && (
                <div className={styles.stageTitle}>
                  {hypothesis.id} · {titleCase(hypothesis.originName)} → {dag?.affected.length ?? 0} tickers · view: {view}
                </div>
              )}
              <GraphCanvas
                ref={canvasRef}
                graph={graph}
                roles={roles}
                visible={visible}
                selected={nodeSelected}
                onSelect={setNode}
                labelMode={labelMode}
                interactive={!stage}
                overlay={(t) => (propagation ? <PropagationOverlay graph={graph} propagation={propagation} shifts={shifts} t={t} /> : null)}
                tooltip={(n, i) => {
                  const holding = run.tickers.find((t) => t.index === i)
                  return (
                    <>
                      <b>{titleCase(n.name)}</b>
                      <div className="mono">
                        {n.type}
                        {n.tickers.length ? ` · ${n.tickers.join('/')}` : ''} · degree {n.deg}
                      </div>
                      {holding && (
                        <div className="mono">
                          held {fmtMoney(holding.amount)} · <span className={(holding.returnPct ?? 0) >= 0 ? 'up' : 'down'}>{fmtPct(holding.returnPct)}</span>
                        </div>
                      )}
                      <div className="mono" style={{ color: ROLE_COLOR[roles[i]!] }}>
                        {ROLE_LABEL[roles[i]!]}
                      </div>
                    </>
                  )
                }}
              />
              <div className={styles.legend}>
                {(['origin', 'held', 'ndx', 'other'] as NodeRole[]).map((r) => (
                  <span key={r}>
                    <i style={{ background: ROLE_COLOR[r] }} />
                    {ROLE_LABEL[r]}
                  </span>
                ))}
              </div>
              <div className={styles.counts}>
                {fmtInt(visibleCount.nodes)} nodes · {fmtInt(visibleCount.edges)} edges
              </div>
            </div>
          </div>
          <div className={`card ${styles.right}`} data-inspector>
            <Inspector
              graph={graph}
              run={run}
              roles={roles}
              visibleCount={visibleCount}
              nodeIndex={nodeSelected}
              hypothesis={hypothesis}
              dag={dag}
              onSelectNode={setNode}
              onSelectHypothesis={onSelectHypothesis}
              onReplay={replay}
              onScrub={onScrub}
              progressRef={progressRef}
              stage={stage}
            />
          </div>
        </div>
      </div>
    </section>
  )
}

