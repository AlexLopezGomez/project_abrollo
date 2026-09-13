import { useRef, useState } from 'react'
import styles from './Hero.module.css'
import { useAppData } from '../../data/RunContext'
import { useSectionTimeline } from '../../lib/useSectionTimeline'
import { addCountUp } from '../../lib/useCountUp'
import { SplitText } from '../../lib/gsap'
import { fmtMoney, fmtPct, shortId } from '../../lib/format'

export interface SectionProps {
  mode?: 'scroll' | 'stage'
  playToken?: number
}

export function Hero({ mode = 'scroll', playToken = 0 }: SectionProps) {
  const { run, meta } = useAppData()
  const scope = useRef<HTMLElement>(null)
  const valueRef = useRef<HTMLSpanElement>(null)
  const retRef = useRef<HTMLSpanElement>(null)
  const [copied, setCopied] = useState(false)

  useSectionTimeline(
    (tl) => {
      const title = scope.current?.querySelector<HTMLElement>('[data-title]')
      if (title) {
        const split = new SplitText(title, { type: 'chars,words' })
        tl.set(title, { autoAlpha: 1 }).from(split.chars, { yPercent: 60, autoAlpha: 0, stagger: 0.018, duration: 0.7, ease: 'power4.out' }, 0)
      }
      tl.from('[data-eyebrow]', { autoAlpha: 0, y: 8, duration: 0.5 }, 0.1)
      tl.set('[data-value]', { autoAlpha: 1 }, 0.45)
      addCountUp(tl, valueRef.current, run.totalValue, fmtMoney, { duration: 1.7, position: 0.45 })
      tl.set('[data-ret]', { autoAlpha: 1 }, 1.05)
      addCountUp(tl, retRef.current, run.returnPct * 10, (v) => fmtPct(v / 10), { duration: 1.1, position: 1.05 })
      tl.from('[data-basis]', { autoAlpha: 0, y: 6, duration: 0.5 }, 1.3)
      tl.from('[data-thesis]', { autoAlpha: 0, y: 14, duration: 0.8 }, 1.5)
      tl.from('[data-chip]', { autoAlpha: 0, y: 10, duration: 0.5, stagger: 0.07 }, 1.8)
      tl.from('[data-prov]', { autoAlpha: 0, duration: 0.5 }, 2.2)
    },
    { scope, mode, playToken, deps: [run.id], start: 'top 80%' },
  )

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(run.submissionId)
      setCopied(true)
      setTimeout(() => setCopied(false), 1400)
    } catch {
      /* clipboard unavailable */
    }
  }

  const down = run.returnPct < 0
  return (
    <section id="hero" ref={scope} className={`${styles.hero} ${mode === 'stage' ? styles.stage : ''}`}>
      <div className={`container ${styles.inner}`}>
        <div className={styles.eyebrowRow} data-eyebrow data-reveal>
          <span className={styles.dot} />
          <span className="eyebrow">Abrollo · Cala AI Challenge · {run.pipelineLabel} · Submission accepted (HTTP {run.httpStatus ?? 200})</span>
        </div>
        <h1 className={styles.title} data-title data-reveal>
          Monte Carlo <em>Cathedral</em>
        </h1>
        <div className={styles.numbers}>
          <span ref={valueRef} className={styles.value} data-value data-reveal>
            {fmtMoney(run.totalValue)}
          </span>
          <span ref={retRef} className={`${styles.ret} ${down ? styles.down : ''}`} data-ret data-reveal>
            {fmtPct(run.returnPct)}
          </span>
        </div>
        <p className={styles.basis} data-basis data-reveal>
          on {fmtMoney(run.totalInvested)} · bought at the {meta.cutoffDate} close · valued 2026-04-15 · benchmark: SPY buy-and-hold
        </p>
        <p className={styles.thesis} data-thesis data-reveal>
          We don't pick stocks. We pick a <strong>shape of uncertainty</strong> we're comfortable living with for 12 months.
        </p>
        <div className={styles.chips}>
          <span className="chip" data-chip data-reveal>
            <span className="k">run</span> {run.dateLabel}
          </span>
          <span className="chip" data-chip data-reveal>
            <span className="k">tickers</span> {run.nTransactions}
          </span>
          <span className="chip" data-chip data-reveal>
            <span className="k">hypotheses</span> {run.hypothesesCount}
          </span>
          <span className="chip" data-chip data-reveal>
            <span className="k">solver</span> {run.portfolio.solver} · λ {run.portfolio.lambda ?? '—'}
          </span>
          <span className="chip" data-chip data-reveal title={run.submissionId}>
            <span className="k">submission</span> {shortId(run.submissionId)}
            <button className={styles.copyBtn} onClick={copy} aria-label="Copy submission id">
              {copied ? 'copied' : 'copy'}
            </button>
          </span>
        </div>
        {run.artifactSource.kind === 'legacy' && (
          <p className={styles.provenance} data-prov data-reveal>
            Hypotheses, DAG and CVaR figures for this run come from the {run.pipelineLabel} pipeline artifacts; per-ticker prices and weights are this submission's own.
          </p>
        )}
      </div>
    </section>
  )
}
