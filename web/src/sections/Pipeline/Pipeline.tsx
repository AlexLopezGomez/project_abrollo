import { useRef } from 'react'
import styles from './Pipeline.module.css'
import { useAppData } from '../../data/RunContext'
import { useSectionTimeline } from '../../lib/useSectionTimeline'
import { addCountUp } from '../../lib/useCountUp'
import { fmtInt, fmtMoney, fmtPct, fmtRatio } from '../../lib/format'
import type { SectionProps } from '../Hero/Hero'

function Connector({ gate, index }: { gate?: boolean; index: number }) {
  // 132 × 200 box; path runs left→right through the middle
  return (
    <div className={styles.conn}>
      <svg viewBox="0 0 132 200" data-conn={index} aria-hidden="true">
        <path d="M0 100 L132 100" stroke="var(--line-strong)" strokeWidth="1.5" fill="none" data-conn-path />
        {gate && (
          <g data-gate>
            <line x1="66" y1="60" x2="66" y2="92" stroke="var(--green)" strokeWidth="3" strokeLinecap="round" data-gate-bar />
            <line x1="66" y1="140" x2="66" y2="108" stroke="var(--green)" strokeWidth="3" strokeLinecap="round" data-gate-bar />
            <circle cx="66" cy="100" r="15" fill="var(--bg)" stroke="var(--green)" strokeWidth="2" data-gate-ring />
            <path d="M58 100 L64 106 L75 94" stroke="var(--green)" strokeWidth="2.5" fill="none" strokeLinecap="round" strokeLinejoin="round" data-gate-check />
          </g>
        )}
        <circle r="5" fill="var(--cyan)" data-conn-dot cx="0" cy="100" />
      </svg>
    </div>
  )
}

export function Pipeline({ mode = 'scroll', playToken = 0 }: SectionProps) {
  const { run, meta, graph } = useAppData()
  const scope = useRef<HTMLElement>(null)
  const nums = useRef<(HTMLSpanElement | null)[]>([])

  const stages = [
    {
      n: '01',
      title: 'Agents read Cala',
      tech: 'Claude',
      desc: 'Specialist agents query the entity graph and emit structured causal hypotheses. No opinions — every claim cites entity UUIDs with dates.',
      big: run.counts.hypotheses,
      unit: 'hypotheses',
      sub: `${run.counts.sources} cited sources · ${new Set(run.hypotheses.map((h) => h.originUuid)).size} distinct origin entities · latest source ${run.counts.maxSourceDate ?? '—'}`,
      fmt: fmtInt,
    },
    {
      n: '02',
      title: 'Causal graph',
      tech: 'networkx',
      desc: 'Each hypothesis starts at its origin entity and propagates along real relationships, decaying per hop, until it reaches NASDAQ-100 tickers.',
      big: run.counts.affectedTickers,
      unit: 'tickers',
      sub: `${run.counts.propagationEdges} propagation edges · ${fmtInt(graph.stats.nNodes)} entities / ${fmtInt(graph.stats.nEdges)} relationships`,
      fmt: fmtInt,
    },
    {
      n: '03',
      title: 'Monte Carlo',
      tech: 'numpy',
      desc: 'Every iteration samples all hypotheses at once and simulates one complete year of the world — correlations included.',
      big: meta.mc.nSims,
      unit: 'scenarios',
      sub: `× ${meta.mc.nTickers} tickers · covariance: ${meta.cov.method.replace(/_/g, ' ')} · shrinkage ${fmtRatio(meta.cov.shrinkage, 2)}`,
      fmt: fmtInt,
    },
    {
      n: '04',
      title: 'CVaR optimization',
      tech: 'cvxpy',
      desc: 'A convex program maximizes E[r] − λ·CVaR₅% over the scenario matrix, subject to the submission rules.',
      big: run.nTransactions,
      unit: 'weights',
      sub: `${fmtMoney(run.totalInvested)} · λ ${fmtRatio(run.portfolio.lambda, 1)} · CVaR₅ ${run.portfolio.cvar5Pct === null ? '—' : fmtPct(run.portfolio.cvar5Pct * 100, 1, false)} · ${run.portfolio.solver}`,
      fmt: fmtInt,
    },
  ]

  useSectionTimeline(
    (tl) => {
      tl.from('[data-head]', { autoAlpha: 0, y: 12, duration: 0.6 }, 0)
      const stageEls = scope.current?.querySelectorAll('[data-stage]') ?? []
      const step = 0.95
      stageEls.forEach((el, i) => {
        const at = 0.2 + i * step
        tl.from(el, { autoAlpha: 0, x: -24, duration: 0.6 }, at)
        const s = stages[i]!
        addCountUp(tl, nums.current[i], s.big, s.fmt, { duration: 0.8, position: at + 0.2 })
        if (i < stageEls.length - 1) {
          const conn = `[data-conn="${i}"]`
          tl.from(`${conn} [data-conn-path]`, { drawSVG: '0%', duration: 0.45, ease: 'power2.inOut' }, at + 0.35)
          if (i === 0) {
            // the firewall gate closes (bars draw in), then the check appears, then the dot is allowed through
            tl.from(`${conn} [data-gate-bar]`, { drawSVG: '0%', duration: 0.35, ease: 'power2.out', stagger: 0.05 }, at + 0.45)
            tl.from(`${conn} [data-gate-ring]`, { scale: 0, transformOrigin: 'center', autoAlpha: 0, duration: 0.3, ease: 'back.out(2)' }, at + 0.6)
            tl.from(`${conn} [data-gate-check]`, { drawSVG: '0%', duration: 0.3 }, at + 0.75)
            tl.from('[data-gate-label]', { autoAlpha: 0, y: 6, duration: 0.4 }, at + 0.8)
          }
          tl.fromTo(
            `${conn} [data-conn-dot]`,
            { autoAlpha: 0 },
            {
              autoAlpha: 1,
              duration: 0.55,
              ease: 'power1.inOut',
              motionPath: { path: `${conn} [data-conn-path]`, align: `${conn} [data-conn-path]`, alignOrigin: [0.5, 0.5] },
            },
            at + (i === 0 ? 0.85 : 0.5),
          )
          tl.to(`${conn} [data-conn-dot]`, { autoAlpha: 0, duration: 0.15 }, at + (i === 0 ? 1.35 : 1.0))
        }
      })
      tl.from('[data-foot]', { autoAlpha: 0, duration: 0.5 }, 0.2 + stageEls.length * step)
    },
    { scope, mode, playToken, deps: [run.id] },
  )

  return (
    <section id="pipeline" ref={scope} className={mode === 'stage' ? undefined : 'section'} style={mode === 'stage' ? { height: '100%' } : undefined}>
      <div className={`container ${styles.wrap} ${mode === 'stage' ? styles.stage : ''}`}>
        <div className="section-head" data-head data-reveal>
          <h2 className="section-title">
            Pipeline <em>— let each tool do what it is good at</em>
          </h2>
          <p className="section-lede">
            LLMs read and cite. Graphs carry structure. Simulation enumerates futures. A convex solver chooses. No
            LLM ever picks a stock.
          </p>
        </div>
        <div className={styles.row}>
          {stages.map((s, i) => (
            <div key={s.n} style={{ display: 'contents' }}>
              <div className={`card ${styles.stage_}`} data-stage data-reveal>
                <div className={styles.stageTop}>
                  <span className={styles.num}>STAGE {s.n}</span>
                  <span className={styles.tech}>{s.tech}</span>
                </div>
                <h3 className={styles.stageTitle}>{s.title}</h3>
                <p className={styles.stageDesc}>{s.desc}</p>
                <div className={styles.big}>
                  <span
                    ref={(el) => {
                      nums.current[i] = el
                    }}
                  >
                    {s.fmt(s.big)}
                  </span>
                  <small>{s.unit}</small>
                </div>
                <div className={styles.bigSub}>{s.sub}</div>
              </div>
              {i < stages.length - 1 && <Connector index={i} gate={i === 0} />}
            </div>
          ))}
        </div>
        <div className={styles.gateRow}>
          <div className={styles.gateLabel} data-gate-label data-reveal>
            <b>anti-lookahead firewall</b>
            every source dated ≤ {meta.cutoffDate} · {meta.allowlistDates.length} allowed dates · latest used {run.counts.maxSourceDate ?? '—'}
          </div>
        </div>
        <div className={styles.foot} data-foot data-reveal>
          <span>
            Submission rules: <b>≥ 50 tickers</b> · <b>exactly {fmtMoney(1_000_000)}</b> · <b>≥ $5,000 per ticker</b> · long only
          </span>
          <span>
            Objective: <b>max E[r] − λ · CVaR₅%</b>, λ = {fmtRatio(run.portfolio.lambda, 1)}
          </span>
        </div>
      </div>
    </section>
  )
}
