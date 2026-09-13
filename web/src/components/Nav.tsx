import { useEffect, useState } from 'react'
import styles from './Nav.module.css'
import { useAppData } from '../data/RunContext'
import { usePresentation } from '../presentation/PresentationContext'
import { fmtPct } from '../lib/format'

export const SECTIONS = [
  { id: 'hero', label: 'Result' },
  { id: 'pipeline', label: 'Pipeline' },
  { id: 'graph', label: 'Knowledge graph' },
  { id: 'hypotheses', label: 'Hypotheses' },
  { id: 'portfolio', label: 'Portfolio' },
  { id: 'history', label: 'History' },
] as const

export function Nav() {
  const { runs, run, selectRun } = useAppData()
  const { enter } = usePresentation()
  const [active, setActive] = useState('hero')

  useEffect(() => {
    const els = SECTIONS.map((s) => document.getElementById(s.id)).filter((e): e is HTMLElement => Boolean(e))
    const io = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0]
        if (visible) setActive(visible.target.id)
      },
      { rootMargin: '-40% 0px -50% 0px', threshold: [0, 0.2, 0.5] },
    )
    els.forEach((el) => io.observe(el))
    return () => io.disconnect()
  }, [])

  return (
    <nav className={styles.nav}>
      <div className={`container ${styles.inner}`}>
        <a className={styles.brand} href="#hero">
          Monte Carlo Cathedral <span>Abrollo</span>
        </a>
        <div className={styles.links}>
          {SECTIONS.map((s) => (
            <a key={s.id} href={`#${s.id}`} className={`${styles.link} ${active === s.id ? styles.active : ''}`}>
              {s.label}
            </a>
          ))}
        </div>
        <div className={styles.right}>
          <select
            className={styles.runSelect}
            value={run.id}
            onChange={(e) => selectRun(e.target.value)}
            aria-label="Select run"
          >
            {runs.map((r) => (
              <option key={r.id} value={r.id}>
                {r.pipelineLabel} · {r.dateLabel} · {fmtPct(r.returnPct)}
              </option>
            ))}
          </select>
          <button className="btn" onClick={() => enter(0)} title="Presentation mode (P)">
            Present <kbd className={styles.kbd}>P</kbd>
          </button>
        </div>
      </div>
    </nav>
  )
}
