import { useMemo } from 'react'
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import styles from './Hypotheses.module.css'
import type { DagEntry, Hypothesis } from '../../data/schema'
import { fmtMoney, fmtSigned, titleCase } from '../../lib/format'

interface Props {
  h: Hypothesis
  dag: DagEntry | undefined
  cutoff: string
  size?: 'normal' | 'stage'
  onShowInGraph?: (id: string) => void
}

interface BarDatum {
  ticker: string
  weight: number
  shift: number
  inPortfolio: boolean
}

function Tip({ active, payload }: { active?: boolean; payload?: { payload: BarDatum }[] }) {
  const d = payload?.[0]?.payload
  if (!active || !d) return null
  return (
    <div className={styles.tooltip}>
      <div>
        <b>{d.ticker}</b> · shift {fmtSigned(d.shift * 100, 1)}%
      </div>
      <div style={{ color: 'var(--muted)' }}>{d.inPortfolio ? `in portfolio · ${fmtMoney(d.weight)}` : 'not held'}</div>
    </div>
  )
}

export function HypothesisCard({ h, dag, cutoff, size = 'normal', onShowInGraph }: Props) {
  const affected = useMemo(() => dag?.affected ?? [], [dag])
  const data = useMemo<BarDatum[]>(
    () =>
      [...affected]
        .sort((a, b) => Number(b.inPortfolio) - Number(a.inPortfolio) || b.weight - a.weight || a.ticker.localeCompare(b.ticker))
        .map((a) => ({ ticker: a.ticker, weight: a.inPortfolio ? a.weight : 0, shift: a.shift, inPortfolio: a.inPortfolio })),
    [affected],
  )
  const held = affected.filter((a) => a.inPortfolio).length
  const heldDollars = affected.reduce((s, a) => s + (a.inPortfolio ? a.weight : 0), 0)
  const positive = h.magnitude >= 0
  const stubHeight = Math.max(1200, ...data.map((d) => d.weight)) * 0.06

  return (
    <article className={`card ${styles.card} ${size === 'stage' ? styles.stage : ''}`} data-card data-reveal>
      <header className={styles.cardHead}>
        <div>
          <div className={styles.idRow}>
            <span className={styles.hid}>{h.id}</span>
            <span className={styles.hid}>· {h.effectType ?? 'causal hypothesis'}</span>
          </div>
          <div className={styles.origin} style={{ marginTop: 8 }}>
            <i />
            {titleCase(h.originName)}
            <small>origin entity</small>
          </div>
        </div>
        <div className={styles.metrics}>
          <div className={styles.metric}>
            <div className={styles.k}>Probability</div>
            <div className={styles.v}>{h.probability.toFixed(2)}</div>
          </div>
          <div className={styles.metric}>
            <div className={styles.k}>Magnitude</div>
            <div className={`${styles.v} ${positive ? 'up' : 'down'}`}>{fmtSigned(h.magnitude * 100, 0)}%</div>
          </div>
          <div className={styles.metric}>
            <div className={styles.k}>Horizon</div>
            <div className={styles.v}>{h.horizonDays === null ? '—' : `${h.horizonDays}d`}</div>
          </div>
        </div>
      </header>

      <p className={styles.trigger}>{h.trigger}</p>

      <div>
        <div className={styles.blockLabel}>
          <span>Sources — Cala entity UUIDs</span>
          <span className={`${styles.check} ${h.datesValid ? '' : styles.bad}`}>
            {h.datesValid ? `✓ all ${h.sources.length} sources ≤ ${cutoff}` : `✗ a source is dated after ${cutoff}`}
          </span>
        </div>
        <div className={styles.cite}>
          {h.sources.map((s, i) => {
            const d = h.sourceDates[i] ?? '—'
            const ok = d !== '—' && d <= cutoff
            return (
              <div key={`${s}-${i}`} className={styles.citeRow} data-cite>
                <span className={styles.uuid}>
                  <b>{s.slice(0, 8)}</b>
                  {s.slice(8)}
                </span>
                <span className={styles.date}>{d}</span>
                <span className={`${styles.check} ${ok ? '' : styles.bad}`} data-cite-check>
                  {ok ? '✓ ≤ cutoff' : '✗ after cutoff'}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      <div>
        <div className={styles.blockLabel}>
          <span>
            Affected — {affected.length} tickers via propagation · {held} held · {fmtMoney(heldDollars)}
          </span>
          <span className={styles.chartLegend}>
            <span>
              <i style={{ background: 'var(--cyan)' }} />
              held · bar = $ weight
            </span>
            <span>
              <i style={{ background: 'var(--muted-2)' }} />
              not held
            </span>
          </span>
        </div>
        <div className={styles.chart}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 4, right: 8, left: 12, bottom: 0 }} barCategoryGap={data.length > 30 ? 1 : 3}>
              <XAxis
                dataKey="ticker"
                tick={{ fill: 'var(--muted)', fontFamily: 'var(--font-mono)', fontSize: 14 }}
                interval={data.length > 13 ? Math.ceil(data.length / 13) - 1 : 0}
                axisLine={{ stroke: 'var(--line)' }}
                tickLine={false}
                height={22}
              />
              <YAxis hide domain={[0, 'dataMax']} />
              <Tooltip content={<Tip />} cursor={{ fill: 'rgba(244,241,232,0.05)' }} />
              <Bar dataKey={(d: BarDatum) => (d.inPortfolio ? d.weight : stubHeight)} isAnimationActive={false} radius={[2, 2, 0, 0]}>
                {data.map((d) => (
                  <Cell key={d.ticker} fill={d.inPortfolio ? 'var(--cyan)' : 'var(--muted-2)'} fillOpacity={d.inPortfolio ? 1 : 0.5} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <footer className={styles.foot}>
        <span className={styles.footNote}>
          shift per affected ticker: {fmtSigned((affected[0]?.shift ?? h.magnitude) * 100, 1)}% · origin {h.originUuid.slice(0, 8)}…
        </span>
        {onShowInGraph && (
          <button className="btn" onClick={() => onShowInGraph(h.id)}>
            Show in graph →
          </button>
        )}
      </footer>
    </article>
  )
}
