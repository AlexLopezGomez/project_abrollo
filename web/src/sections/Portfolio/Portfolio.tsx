import { useRef } from 'react'
import styles from './Portfolio.module.css'
import { useAppData } from '../../data/RunContext'
import { useSectionTimeline } from '../../lib/useSectionTimeline'
import { addCountUp } from '../../lib/useCountUp'
import { fmtInt, fmtMoney, fmtPct, fmtRatio } from '../../lib/format'
import { HoldingsTable } from './HoldingsTable'
import { DistributionSketch } from './DistributionSketch'
import type { SectionProps } from '../Hero/Hero'

export function Portfolio({ mode = 'scroll', playToken = 0 }: SectionProps) {
  const { run, meta } = useAppData()
  const scope = useRef<HTMLElement>(null)
  const kpiRefs = useRef<(HTMLSpanElement | null)[]>([])
  const p = run.portfolio

  const maxSqrt = Math.sqrt(Math.max(1, ...run.tickers.map((t) => Math.abs(t.returnPct ?? 0))))
  const winners = run.tickers.filter((t) => (t.returnPct ?? 0) > 0).length
  const stage = mode === 'stage'
  const nCols = stage ? 3 : 2
  const per = Math.ceil(run.tickers.length / nCols)
  const columns = Array.from({ length: nCols }, (_, c) => run.tickers.slice(c * per, (c + 1) * per))

  useSectionTimeline(
    (tl) => {
      tl.from('[data-head]', { autoAlpha: 0, y: 12, duration: 0.6 }, 0)
      tl.set('[data-kpi]', { autoAlpha: 1 }, 0.1)
      addCountUp(tl, kpiRefs.current[0], run.returnPct * 10, (v) => fmtPct(v / 10), { duration: 1.2, position: 0.1 })
      addCountUp(tl, kpiRefs.current[1], run.totalValue, fmtMoney, { duration: 1.4, position: 0.15 })
      addCountUp(tl, kpiRefs.current[2], run.totalInvested, fmtMoney, { duration: 1.0, position: 0.2 })
      addCountUp(tl, kpiRefs.current[3], run.nTransactions, fmtInt, { duration: 0.8, position: 0.25 })
      tl.from('[data-bars-head]', { autoAlpha: 0, duration: 0.5 }, 0.5)
      tl.set('[data-bar-row]', { autoAlpha: 1 }, 0.5)
      tl.from('[data-bar]', { scaleX: 0, duration: 0.7, ease: 'power2.out', stagger: { each: 0.012, from: 'start' } }, 0.6)
      if (!stage) tl.from('[data-table]', { autoAlpha: 0, y: 16, duration: 0.7 }, 1.2)
      tl.from('[data-cvar]', { autoAlpha: 0, y: 16, duration: 0.7 }, 1.3)
      tl.from('[data-dist-curve]', { drawSVG: '0%', duration: 1.4, ease: 'power2.inOut' }, 1.6)
      tl.from('[data-dist-area]', { autoAlpha: 0, duration: 0.8 }, 2.2)
      tl.from('[data-dist-tail]', { autoAlpha: 0, scaleY: 0, transformOrigin: 'bottom', duration: 0.6 }, 2.9)
      tl.from('[data-dist-marker]', { autoAlpha: 0, duration: 0.5 }, 3.2)
    },
    { scope, mode, playToken, deps: [run.id] },
  )

  const barsHead = (
    <div className={styles.barsHead} data-bars-head data-reveal>
      <h3 className={styles.barsTitle}>Return per ticker, Apr 2025 → Apr 2026</h3>
      <div className={styles.legend}>
        <span>
          <i style={{ background: 'var(--green)' }} />
          gain
        </span>
        <span>
          <i style={{ background: 'var(--red)' }} />
          loss
        </span>
        <span>sorted by return · bar length on a √ scale</span>
      </div>
    </div>
  )
  const bars = (
    <div className={`${styles.bars} ${stage ? styles.barsStage : ''}`}>
      {columns.map((col, ci) => (
        <div key={ci}>
          {col.map((t) => {
            const r = t.returnPct ?? 0
            const neg = r < 0
            return (
              <div key={t.ticker} className={`${styles.barRow} ${neg ? styles.neg : ''}`} data-bar-row data-reveal>
                <span className={styles.barTicker}>{t.ticker}</span>
                <div className={styles.barTrack}>
                  <div className={`${styles.barFill} ${neg ? styles.down : styles.up}`} data-bar style={{ left: 0, width: `${(Math.sqrt(Math.abs(r)) / maxSqrt) * 100}%` }} />
                </div>
                <span className={styles.barVal}>{fmtPct(r)}</span>
              </div>
            )
          })}
        </div>
      ))}
    </div>
  )

  return (
    <section id="portfolio" ref={scope} className={stage ? styles.stageSection : 'section'}>
      <div className="container">
        <div className="section-head" data-head data-reveal>
          <h2 className="section-title">
            Portfolio <em>— the shape we chose</em>
          </h2>
          <p className="section-lede">
            {run.nTransactions} NASDAQ tickers, {fmtMoney(run.totalInvested)}, bought at the {meta.cutoffDate} close and
            valued one year later. Weights come from a convex optimizer, not from a vote.
          </p>
        </div>

        <div className={styles.kpis}>
          {[
            { label: 'Total return', value: fmtPct(run.returnPct), sub: `vs. ${fmtMoney(run.totalInvested)} invested`, cls: run.returnPct >= 0 ? 'up' : 'down' },
            { label: 'Final value', value: fmtMoney(run.totalValue), sub: 'evaluated 2026-04-15', cls: '' },
            { label: 'Invested', value: fmtMoney(run.totalInvested), sub: `min $5,000 per ticker`, cls: '' },
            { label: 'Tickers', value: fmtInt(run.nTransactions), sub: `${winners} up · ${run.nTransactions - winners} down`, cls: '' },
          ].map((k, i) => (
            <div key={k.label} className={styles.kpi} data-kpi data-reveal>
              <div className={`eyebrow ${styles.kpiLabel}`}>{k.label}</div>
              <span
                ref={(el) => {
                  kpiRefs.current[i] = el
                }}
                className={`${styles.kpiValue} ${k.cls}`}
              >
                {k.value}
              </span>
              <div className={styles.kpiSub}>{k.sub}</div>
            </div>
          ))}
        </div>

        {!stage && barsHead}
        {!stage && bars}

        <div className={`${styles.lower} ${stage ? styles.lowerStage : ''}`}>
          {stage ? (
            <div>
              {barsHead}
              {bars}
            </div>
          ) : (
            <HoldingsTable rows={run.tickers} />
          )}
          <div className={`card ${styles.cvar}`} data-cvar data-reveal>
            <h3 className={styles.cvarTitle}>Optimized for the tail, not the mean</h3>
            <div className={styles.objective}>maximize E[r] − λ · CVaR₅%</div>
            <div className={styles.stats}>
              <div className={styles.stat}>
                <div className={styles.k}>CVaR at α = {fmtRatio(p.alphaLevel, 2)}</div>
                <div className={styles.v}>{p.cvar5Pct === null ? '—' : fmtPct(p.cvar5Pct * 100, 1, false)}</div>
              </div>
              <div className={styles.stat}>
                <div className={styles.k}>Expected return E[r]</div>
                <div className={styles.v}>{p.expectedReturnPct === null ? '—' : fmtPct(p.expectedReturnPct * 100)}</div>
              </div>
              <div className={styles.stat}>
                <div className={styles.k}>Risk aversion λ</div>
                <div className={styles.v}>{fmtRatio(p.lambda, 1)}</div>
              </div>
              <div className={styles.stat}>
                <div className={styles.k}>Solver</div>
                <div className={styles.v}>
                  {p.solver}
                  <small>{p.status}</small>
                </div>
              </div>
            </div>
            <DistributionSketch alpha={p.alphaLevel ?? 0.05} />
            <div className={styles.sketchNote}>
              Illustrative shape — not the simulated distribution. Scenarios: {fmtInt(meta.mc.nSims)} × {meta.mc.nTickers} tickers.
            </div>
            <p className={styles.caption}>
              Every simulated year is one row of a {fmtInt(meta.mc.nSims)} × {meta.mc.nTickers} matrix. The optimizer does not
              chase the best average: it is charged λ times the mean loss of the worst {Math.round((p.alphaLevel ?? 0.05) * 100)}% of those years. The
              output is a <strong>distribution we can live with</strong>, not a point prediction.
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}
