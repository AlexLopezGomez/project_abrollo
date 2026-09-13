import { useMemo } from 'react'
import styles from './Portfolio.module.css'

/**
 * Schematic "distribution of simulated 12-month outcomes" with the 5 % tail shaded.
 * It is a fixed, hand-shaped curve (left-skewed) — explicitly labeled as illustrative in the UI.
 */
export function DistributionSketch({ alpha = 0.05 }: { alpha?: number }) {
  const W = 640
  const H = 260
  const padX = 24
  const { curve, area, tailArea, tailX, meanX, cvarX, baseY } = useMemo(() => {
    const baseY = H - 44
    const pts: [number, number][] = []
    const n = 160
    const f = (t: number) => {
      // left-skewed bump on t ∈ [0,1]
      const mu = 0.58
      const sL = 0.2
      const sR = 0.13
      const s = t < mu ? sL : sR
      return Math.exp(-0.5 * ((t - mu) / s) ** 2)
    }
    let total = 0
    const vals: number[] = []
    for (let i = 0; i <= n; i++) {
      const v = f(i / n)
      vals.push(v)
      total += v
    }
    let acc = 0
    let tailIdx = 0
    for (let i = 0; i <= n; i++) {
      acc += vals[i]!
      if (acc / total >= alpha) {
        tailIdx = i
        break
      }
    }
    const x = (i: number) => padX + (i / n) * (W - padX * 2)
    const y = (v: number) => baseY - v * (baseY - 30)
    for (let i = 0; i <= n; i++) pts.push([x(i), y(vals[i]!)])
    const d = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ')
    const areaD = `${d} L${x(n).toFixed(1)},${baseY} L${x(0).toFixed(1)},${baseY} Z`
    const tail = pts.slice(0, tailIdx + 1)
    const tailD = `${tail.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ')} L${x(tailIdx).toFixed(1)},${baseY} L${x(0).toFixed(1)},${baseY} Z`
    // mean of the tail (CVaR marker) ≈ weighted centre of the tail mass
    let tw = 0
    let tx = 0
    for (let i = 0; i <= tailIdx; i++) {
      tw += vals[i]!
      tx += vals[i]! * i
    }
    return { curve: d, area: areaD, tailArea: tailD, tailX: x(tailIdx), meanX: x(n * 0.6), cvarX: x(tx / tw), baseY }
  }, [alpha])

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className={styles.sketch} data-sketch aria-label="Illustrative distribution of simulated outcomes with the worst 5% shaded">
      <defs>
        <linearGradient id="dist-fill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor="var(--cyan)" stopOpacity="0.22" />
          <stop offset="1" stopColor="var(--cyan)" stopOpacity="0.02" />
        </linearGradient>
      </defs>
      <line x1={padX} x2={W - padX} y1={baseY} y2={baseY} stroke="var(--line-strong)" />
      <path d={area} fill="url(#dist-fill)" data-dist-area />
      <path d={tailArea} fill="var(--red)" fillOpacity="0.35" data-dist-tail />
      <path d={curve} fill="none" stroke="var(--cyan)" strokeWidth="2.5" data-dist-curve />
      <g data-dist-marker>
        <line x1={tailX} x2={tailX} y1={36} y2={baseY} stroke="var(--red)" strokeDasharray="4 4" />
        <text x={tailX + 8} y={30} fill="var(--red)" fontFamily="var(--font-mono)" fontSize="14">
          worst {Math.round(alpha * 100)}% of simulated years
        </text>
        <line x1={cvarX} x2={cvarX} y1={baseY - 60} y2={baseY} stroke="var(--red)" />
        <text x={cvarX} y={baseY + 22} fill="var(--red)" fontFamily="var(--font-mono)" fontSize="14" textAnchor="middle">
          CVaR₅
        </text>
        <line x1={meanX} x2={meanX} y1={30} y2={baseY} stroke="var(--text)" strokeOpacity="0.5" strokeDasharray="2 6" />
        <text x={meanX} y={baseY + 22} fill="var(--muted)" fontFamily="var(--font-mono)" fontSize="14" textAnchor="middle">
          E[r]
        </text>
      </g>
      <text x={padX} y={baseY + 36} fill="var(--muted-2)" fontFamily="var(--font-mono)" fontSize="13">
        loss ◀
      </text>
      <text x={W - padX} y={baseY + 36} fill="var(--muted-2)" fontFamily="var(--font-mono)" fontSize="13" textAnchor="end">
        ▶ gain
      </text>
    </svg>
  )
}
