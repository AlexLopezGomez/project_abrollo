import { useMemo, useRef } from 'react'
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import styles from './History.module.css'
import { useAppData } from '../../data/RunContext'
import { useSectionTimeline } from '../../lib/useSectionTimeline'
import { fmtMoney, fmtPct, shortId } from '../../lib/format'
import type { RunSummary } from '../../data/schema'
import type { SectionProps } from '../Hero/Hero'

interface Point {
  i: number
  label: string
  value: number
  returnPct: number
  run: RunSummary
}

function Tip({ active, payload }: { active?: boolean; payload?: { payload: Point }[] }) {
  const d = payload?.[0]?.payload
  if (!active || !d) return null
  return (
    <div className={styles.tooltip}>
      <div>
        {d.run.pipelineLabel} · {d.run.timestamp.replace('T', ' ')}
      </div>
      <div>
        <b>{fmtMoney(d.value)}</b> · {fmtPct(d.returnPct)}
      </div>
      <div style={{ color: 'var(--muted)' }}>{shortId(d.run.submissionId)}</div>
    </div>
  )
}

export function History({ mode = 'scroll', playToken = 0 }: SectionProps) {
  const { runs, run, selectRun } = useAppData()
  const scope = useRef<HTMLElement>(null)
  const ordered = useMemo(() => [...runs].sort((a, b) => a.timestamp.localeCompare(b.timestamp)), [runs])
  const points = useMemo<Point[]>(
    () => ordered.map((r, i) => ({ i, label: `${r.pipelineLabel} ${r.dateLabel.slice(5)} ${r.timestamp.slice(11, 16)}`, value: r.totalValue, returnPct: r.returnPct, run: r })),
    [ordered],
  )
  const best = ordered.reduce((b, r) => (r.totalValue > b.totalValue ? r : b), ordered[0]!)

  useSectionTimeline(
    (tl) => {
      tl.from('[data-head]', { autoAlpha: 0, y: 12, duration: 0.6 }, 0)
      tl.from('[data-chart]', { autoAlpha: 0, duration: 0.8 }, 0.2)
      tl.from('[data-run]', { autoAlpha: 0, y: 14, duration: 0.5, stagger: 0.07 }, 0.4)
    },
    { scope, mode, playToken, deps: [runs.length] },
  )

  return (
    <section id="history" ref={scope} className="section">
      <div className="container">
        <div className="section-head" data-head data-reveal>
          <h2 className="section-title">
            History <em>— {runs.length} submissions, one pipeline</em>
          </h2>
          <p className="section-lede">
            Every run re-reads Cala, regenerates hypotheses and re-solves the portfolio. The spread between runs is the honest
            cost of LLM-generated priors. Click a run to load it everywhere.
          </p>
        </div>
        <div className={styles.chart} data-chart data-reveal>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={points}
              margin={{ top: 16, right: 24, left: 8, bottom: 0 }}
              onClick={(e) => {
                const idx = typeof e?.activeTooltipIndex === 'number' ? e.activeTooltipIndex : Number(e?.activeTooltipIndex)
                const p = Number.isFinite(idx) ? points[idx] : undefined
                if (p) selectRun(p.run.id)
              }}
            >
              <CartesianGrid stroke="var(--line)" vertical={false} />
              <XAxis dataKey="label" tick={{ fill: 'var(--muted)', fontFamily: 'var(--font-mono)', fontSize: 13 }} axisLine={{ stroke: 'var(--line)' }} tickLine={false} padding={{ left: 40, right: 40 }} interval={0} />
              <YAxis
                tick={{ fill: 'var(--muted)', fontFamily: 'var(--font-mono)', fontSize: 13 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v: number) => (v === 1_000_000 ? 'invested' : `$${(v / 1e6).toFixed(2)}M`)}
                domain={[1_000_000, 1_650_000]}
                width={72}
              />
              <ReferenceLine y={1_000_000} stroke="var(--line-strong)" strokeDasharray="4 4" />
              <Tooltip content={<Tip />} cursor={{ stroke: 'var(--line-strong)' }} />
              <Line
                type="monotone"
                dataKey="value"
                stroke="var(--cyan)"
                strokeWidth={2}
                isAnimationActive={false}
                dot={(p: { cx?: number; cy?: number; payload?: Point }) => {
                  const active = p.payload?.run.id === run.id
                  return (
                    <circle
                      key={p.payload?.i}
                      cx={p.cx}
                      cy={p.cy}
                      r={active ? 8 : 5}
                      fill={active ? 'var(--cyan)' : 'var(--bg)'}
                      stroke="var(--cyan)"
                      strokeWidth={2}
                      style={{ cursor: 'pointer' }}
                      onClick={() => p.payload && selectRun(p.payload.run.id)}
                    />
                  )
                }}
                activeDot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className={styles.runs}>
          {ordered.map((r) => (
            <button
              key={r.id}
              className={`${styles.run} ${r.id === run.id ? styles.active : ''} ${r.id === best.id ? styles.best : ''}`}
              onClick={() => selectRun(r.id)}
              data-run
              data-reveal
            >
              <div className={styles.meta}>
                <span>{r.pipelineLabel}</span>
                <span>
                  {r.dateLabel.slice(5)} {r.timestamp.slice(11, 16)}
                </span>
              </div>
              <div className={styles.value}>{fmtMoney(r.totalValue)}</div>
              <div className={`${styles.ret} ${r.returnPct >= 0 ? 'up' : 'down'}`}>{fmtPct(r.returnPct)}</div>
              <div className={styles.id} title={r.submissionId}>
                {shortId(r.submissionId, 10, 4)}
              </div>
              <div className={styles.tags}>
                <span className={`${styles.tag} ${r.success ? styles.ok : ''}`}>HTTP {r.httpStatus ?? '—'}</span>
                <span className={styles.tag}>{r.artifactSource.kind === 'snapshot' ? 'snapshot' : 'legacy artifacts'}</span>
                {r.id === best.id && <span className={`${styles.tag} ${styles.ok}`}>best</span>}
              </div>
            </button>
          ))}
        </div>
      </div>
    </section>
  )
}
