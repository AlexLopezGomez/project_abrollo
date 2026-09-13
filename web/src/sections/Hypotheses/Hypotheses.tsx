import { useMemo, useRef, useState } from 'react'
import styles from './Hypotheses.module.css'
import { useAppData } from '../../data/RunContext'
import { useGraphSelection } from '../../state/GraphSelection'
import { useSectionTimeline } from '../../lib/useSectionTimeline'
import { HypothesisCard } from './HypothesisCard'
import type { SectionProps } from '../Hero/Hero'
import { fmtInt } from '../../lib/format'

type Direction = 'all' | 'positive' | 'negative'
type Sort = 'affected' | 'probability' | 'magnitude' | 'id'

export function Hypotheses({ mode = 'scroll', playToken = 0, featuredId }: SectionProps & { featuredId?: string }) {
  const { run, index } = useAppData()
  const { select } = useGraphSelection()
  const scope = useRef<HTMLElement>(null)
  const [minP, setMinP] = useState(0)
  const [dir, setDir] = useState<Direction>('all')
  const [sort, setSort] = useState<Sort>('affected')

  const dagById = useMemo(() => new Map(run.dag.map((d) => [d.hypothesisId, d])), [run.dag])
  const list = useMemo(() => {
    if (mode === 'stage') {
      const id = featuredId ?? run.featuredHypothesisId
      return run.hypotheses.filter((h) => h.id === id)
    }
    const filtered = run.hypotheses.filter(
      (h) => h.probability >= minP && (dir === 'all' || (dir === 'positive' ? h.magnitude >= 0 : h.magnitude < 0)),
    )
    const affectedOf = (id: string) => dagById.get(id)?.affected.length ?? 0
    return filtered.sort((a, b) => {
      switch (sort) {
        case 'probability':
          return b.probability - a.probability
        case 'magnitude':
          return Math.abs(b.magnitude) - Math.abs(a.magnitude)
        case 'id':
          return a.id.localeCompare(b.id)
        default:
          return affectedOf(b.id) - affectedOf(a.id) || a.id.localeCompare(b.id)
      }
    })
  }, [run, mode, featuredId, minP, dir, sort, dagById])

  const allValid = run.hypotheses.every((h) => h.datesValid)

  useSectionTimeline(
    (tl) => {
      tl.from('[data-head]', { autoAlpha: 0, y: 12, duration: 0.6 }, 0)
      if (mode !== 'stage') tl.from('[data-toolbar]', { autoAlpha: 0, y: 8, duration: 0.5 }, 0.15)
      tl.from('[data-card]', { autoAlpha: 0, y: 24, duration: 0.8, stagger: 0.12 }, 0.25)
      tl.from('[data-cite]', { autoAlpha: 0, x: -8, duration: 0.4, stagger: 0.05 }, 0.6)
      tl.from('[data-cite-check]', { scale: 0.6, autoAlpha: 0, duration: 0.35, ease: 'back.out(2)', stagger: 0.05 }, 0.9)
    },
    { scope, mode, playToken, deps: [run.id, list.length] },
  )

  return (
    <section id="hypotheses" ref={scope} className={mode === 'stage' ? undefined : 'section'}>
      <div className="container">
        <div className="section-head" data-head data-reveal>
          <h2 className="section-title">
            Hypotheses <em>— claims with receipts</em>
          </h2>
          <p className="section-lede">
            Claude reads Cala and emits causal hypotheses, never opinions. Each one cites the entity UUIDs it rests on, and
            every citation must be dated on or before {index.cutoffDate}. That gate is mechanical, not an honor system.
          </p>
        </div>

        {mode !== 'stage' && (
          <div className={styles.toolbar} data-toolbar data-reveal>
            <label>
              Min probability
              <input type="range" min={0} max={1} step={0.05} value={minP} onChange={(e) => setMinP(Number(e.target.value))} />
              <span className={styles.val}>{minP.toFixed(2)}</span>
            </label>
            <label>
              Direction
              <span className={styles.seg}>
                {(['all', 'positive', 'negative'] as Direction[]).map((d) => (
                  <button key={d} className={dir === d ? styles.on : ''} onClick={() => setDir(d)}>
                    {d}
                  </button>
                ))}
              </span>
            </label>
            <label>
              Sort
              <span className={styles.seg}>
                {(
                  [
                    ['affected', 'affected tickers'],
                    ['probability', 'probability'],
                    ['magnitude', '|magnitude|'],
                    ['id', 'id'],
                  ] as [Sort, string][]
                ).map(([k, label]) => (
                  <button key={k} className={sort === k ? styles.on : ''} onClick={() => setSort(k)}>
                    {label}
                  </button>
                ))}
              </span>
            </label>
            <span className={styles.count}>
              {list.length} / {run.hypotheses.length} shown · {fmtInt(run.counts.sources)} sources
            </span>
            <span className={`${styles.firewall} ${allValid ? '' : styles.bad}`}>
              {allValid ? '✓' : '✗'} anti-lookahead firewall · latest source {run.counts.maxSourceDate ?? '—'} ≤ {index.cutoffDate}
            </span>
          </div>
        )}

        <div className={`${styles.grid} ${mode === 'stage' ? styles.single : ''}`}>
          {list.map((h) => (
            <HypothesisCard
              key={h.id}
              h={h}
              dag={dagById.get(h.id)}
              cutoff={index.cutoffDate}
              size={mode === 'stage' ? 'stage' : 'normal'}
              onShowInGraph={mode === 'stage' ? undefined : (id) => select(id, { scroll: true })}
            />
          ))}
        </div>
      </div>
    </section>
  )
}
