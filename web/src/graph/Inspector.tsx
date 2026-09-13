import { useMemo, type RefObject } from 'react'
import styles from './Inspector.module.css'
import type { DagEntry, GraphData, Hypothesis, RunData } from '../data/schema'
import { COLORS, type NodeRole } from './renderer'
import { fmtInt, fmtMoney, fmtPct, fmtSigned, titleCase } from '../lib/format'

export const ROLE_COLOR: Record<NodeRole, string> = {
  origin: COLORS.origin,
  held: COLORS.held,
  ndx: COLORS.ndx,
  other: COLORS.other,
}
export const ROLE_LABEL: Record<NodeRole, string> = {
  origin: 'Hypothesis origin',
  held: 'NASDAQ-100, in portfolio',
  ndx: 'NASDAQ-100, not held',
  other: 'Other entity',
}

interface Common {
  graph: GraphData
  run: RunData
  roles: NodeRole[]
  visibleCount: { nodes: number; edges: number }
}

interface Props extends Common {
  nodeIndex: number | null
  hypothesis: Hypothesis | null
  dag: DagEntry | null
  onSelectNode: (i: number | null) => void
  onSelectHypothesis: (id: string) => void
  onReplay: () => void
  onScrub: (p: number) => void
  progressRef: RefObject<HTMLInputElement>
  stage?: boolean
}

export function Inspector(p: Props) {
  if (p.nodeIndex !== null) return <NodePanel {...p} index={p.nodeIndex} />
  if (p.hypothesis && p.dag) return <HypothesisPanel {...p} hypothesis={p.hypothesis} dag={p.dag} />
  return <Overview {...p} />
}

function Overview({ graph, run, roles, visibleCount, stage }: Props) {
  const types = useMemo(() => {
    const m = new Map<string, number>()
    graph.nodes.forEach((n) => m.set(n.type, (m.get(n.type) ?? 0) + 1))
    return [...m.entries()].sort((a, b) => b[1] - a[1]).slice(0, 7)
  }, [graph])
  const max = types[0]?.[1] ?? 1
  const originCount = roles.filter((r) => r === 'origin').length
  return (
    <div className={styles.panel}>
      <div className={styles.head}>
        <div>
          <div className={styles.kicker}>Cala entity graph</div>
          <div className={styles.name}>{fmtInt(graph.stats.nNodes)} entities, {fmtInt(graph.stats.nEdges)} relationships</div>
        </div>
      </div>
      <div className={styles.stats}>
        <div>
          <div className={styles.v}>{fmtInt(visibleCount.nodes)}</div>
          <div className={styles.k}>nodes in view</div>
        </div>
        <div>
          <div className={styles.v}>{fmtInt(visibleCount.edges)}</div>
          <div className={styles.k}>edges in view</div>
        </div>
        <div>
          <div className={styles.v}>{originCount}</div>
          <div className={styles.k}>hypothesis origins</div>
        </div>
        <div>
          <div className={styles.v}>{run.nTransactions}</div>
          <div className={styles.k}>tickers held</div>
        </div>
      </div>
      <div className={styles.legend}>
        {(['origin', 'held', 'ndx', 'other'] as NodeRole[]).map((r) => (
          <div key={r}>
            <i style={{ background: ROLE_COLOR[r] }} />
            {ROLE_LABEL[r]}
          </div>
        ))}
      </div>
      <div className={styles.groupTitle}>Entity types</div>
      <div className={styles.typeRows}>
        {types.map(([t, n]) => (
          <div key={t} className={styles.typeRow}>
            <span>{t}</span>
            <span className={styles.bar}>
              <i style={{ width: `${(n / max) * 100}%` }} />
            </span>
            <span className={styles.n}>{n}</span>
          </div>
        ))}
      </div>
      {!stage && (
        <p className={styles.hint} style={{ marginTop: 'auto' }}>
          Pick a hypothesis to watch it propagate from its origin entity to the tickers it touches. Click any node to inspect its
          relationships. Node size follows degree.
        </p>
      )}
    </div>
  )
}

function NodePanel({ graph, run, roles, index, onSelectNode, onSelectHypothesis, hypothesis }: Props & { index: number }) {
  const n = graph.nodes[index]!
  const role = roles[index]!
  const rels = useMemo(() => {
    const out: { rel: string; other: number; dir: 'out' | 'in' }[] = []
    graph.edges.forEach(([s, d, r]) => {
      if (s === index) out.push({ rel: graph.relTypes[r] ?? '', other: d, dir: 'out' })
      else if (d === index) out.push({ rel: graph.relTypes[r] ?? '', other: s, dir: 'in' })
    })
    // held tickers first, then by degree
    return out.sort((a, b) => Number(roles[b.other] === 'held') - Number(roles[a.other] === 'held') || graph.nodes[b.other]!.deg - graph.nodes[a.other]!.deg)
  }, [graph, index, roles])
  const holding = run.tickers.find((t) => t.index === index)
  const origins = run.hypotheses.filter((h) => h.originIndex === index)

  return (
    <div className={styles.panel}>
      <div className={styles.head}>
        <div>
          <div className={styles.kicker}>
            <i style={{ background: ROLE_COLOR[role] }} />
            {n.type} · {ROLE_LABEL[role]}
          </div>
          <div className={styles.name}>{titleCase(n.name)}</div>
          <div className={styles.sub}>{n.id}</div>
        </div>
        <button className={styles.back} onClick={() => onSelectNode(null)}>
          {hypothesis ? '← hypothesis' : '× close'}
        </button>
      </div>
      <div className={styles.facts}>
        <div className={styles.fact}>
          <div className={styles.k}>ticker</div>
          <div className={styles.v}>{n.tickers.join(' / ') || '—'}</div>
        </div>
        <div className={styles.fact}>
          <div className={styles.k}>degree</div>
          <div className={styles.v}>{n.deg}</div>
        </div>
        <div className={styles.fact}>
          <div className={styles.k}>{holding ? 'weight · return' : 'in portfolio'}</div>
          <div className={styles.v}>
            {holding ? (
              <>
                {fmtMoney(holding.amount)} <span className={(holding.returnPct ?? 0) >= 0 ? 'up' : 'down'}>{fmtPct(holding.returnPct)}</span>
              </>
            ) : (
              'no'
            )}
          </div>
        </div>
      </div>
      <div className={styles.scroll}>
        {origins.length > 0 && (
          <>
            <div className={styles.groupTitle}>Hypotheses generated here ({origins.length})</div>
            <div className={styles.hypoList}>
              {origins.map((h) => (
                <button key={h.id} className={styles.hypoRow} onClick={() => onSelectHypothesis(h.id)}>
                  <div className={styles.id}>
                    {h.id} · P {h.probability.toFixed(2)} · {fmtSigned(h.magnitude * 100, 0)}% · play ▶
                  </div>
                  {h.trigger}
                </button>
              ))}
            </div>
          </>
        )}
        <div className={styles.groupTitle}>
          <span>Relationships ({rels.length})</span>
        </div>
        <div className={styles.relList}>
          {rels.slice(0, 120).map((r, i) => {
            const o = graph.nodes[r.other]!
            return (
              <button key={`${r.other}-${i}`} className={styles.relRow} onClick={() => onSelectNode(r.other)}>
                <span className={styles.who}>
                  <i style={{ background: ROLE_COLOR[roles[r.other]!] }} />
                  {o.tickers[0] ? `${o.tickers[0]} · ` : ''}
                  {titleCase(o.name)}
                </span>
                <span className={styles.rel}>
                  {r.dir === 'in' ? '← ' : '→ '}
                  {r.rel}
                </span>
              </button>
            )
          })}
          {rels.length > 120 && <div className={styles.hint}>… {rels.length - 120} more</div>}
        </div>
      </div>
    </div>
  )
}

function HypothesisPanel({ graph, hypothesis: h, dag, onReplay, onScrub, progressRef, onSelectNode, stage }: Props & { hypothesis: Hypothesis; dag: DagEntry }) {
  const held = dag.affected.filter((a) => a.inPortfolio).sort((a, b) => b.weight - a.weight)
  const notHeld = dag.affected.filter((a) => !a.inPortfolio)
  const heldDollars = held.reduce((s, a) => s + a.weight, 0)
  const shift = dag.affected[0]?.shift ?? h.magnitude
  return (
    <div className={styles.panel}>
      <div className={styles.head}>
        <div>
          <div className={styles.kicker}>
            <i style={{ background: COLORS.origin }} />
            {h.id} · origin
          </div>
          <button className={styles.name} style={{ textAlign: 'left' }} onClick={() => h.originIndex >= 0 && onSelectNode(h.originIndex)}>
            {titleCase(h.originName)}
          </button>
        </div>
      </div>
      <p className={styles.trigger}>{h.trigger}</p>
      <div className={styles.facts}>
        <div className={styles.fact}>
          <div className={styles.k}>probability</div>
          <div className={styles.v}>{h.probability.toFixed(2)}</div>
        </div>
        <div className={styles.fact}>
          <div className={styles.k}>magnitude → shift</div>
          <div className={`${styles.v} ${h.magnitude >= 0 ? 'up' : 'down'}`}>
            {fmtSigned(h.magnitude * 100, 0)}% → {fmtSigned(shift * 100, 1)}%
          </div>
        </div>
        <div className={styles.fact}>
          <div className={styles.k}>reach</div>
          <div className={styles.v}>
            {dag.affected.length} <span style={{ color: 'var(--muted)', fontSize: 14 }}>tickers</span>
          </div>
        </div>
      </div>
      {!stage && (
        <div className={styles.progressRow}>
          <button className="btn small" onClick={onReplay}>
            ↻ Replay
          </button>
          <input ref={progressRef} type="range" min={0} max={1} step={0.001} defaultValue={0} onChange={(e) => onScrub(Number(e.target.value))} aria-label="Scrub propagation" />
        </div>
      )}
      <div className={styles.groupTitle}>
        <span>Held — weights land here ({held.length})</span>
        <span>{fmtMoney(heldDollars)}</span>
      </div>
      <div className={styles.scroll}>
        <div className={styles.chips}>
          {held.map((a) => (
            <span key={a.ticker} className={styles.chip} data-weight-chip={a.ticker} title={graph.nodes[a.index]?.name}>
              <b>{a.ticker}</b> {fmtMoney(a.weight)}
            </span>
          ))}
        </div>
        {notHeld.length > 0 && (
          <>
            <div className={styles.groupTitle}>
              <span>Touched, not held ({notHeld.length})</span>
            </div>
            <div className={styles.chips}>
              {notHeld.map((a) => (
                <span key={a.ticker} className={`${styles.chip} ${styles.muted}`}>
                  {a.ticker}
                </span>
              ))}
            </div>
          </>
        )}
      </div>
      <div className={styles.total}>
        <span>Shift is magnitude × 0.6 per hop, floored at 0.1 (propagation params)</span>
      </div>
    </div>
  )
}
