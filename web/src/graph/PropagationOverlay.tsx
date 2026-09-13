import type { GraphData, Propagation } from '../data/schema'
import type { Transform } from './renderer'
import { fmtSigned } from '../lib/format'
import { COLORS } from './renderer'

interface Props {
  graph: GraphData
  propagation: Propagation
  shifts: Map<number, { shift: number; held: boolean }>
  t: Transform
}

/**
 * SVG layer GSAP animates during a propagation. Paths live in graph units under a scaled group
 * (so DrawSVG lengths stay valid across zoom); rings and labels live in screen units so they don't scale.
 */
export function PropagationOverlay({ graph, propagation, shifts, t }: Props) {
  const o = graph.nodes[propagation.origin]!
  const sx = (x: number) => x * t.k + t.x
  const sy = (y: number) => y * t.k + t.y
  // label only held targets, greedily skipping labels that would overlap an already placed one
  const placed: [number, number, number, number][] = [[sx(o.x) + 16, sy(o.y) - 36, sx(o.x) + 16 + o.name.length * 9.6, sy(o.y) - 14]]
  const ordered = [...propagation.paths].sort((a, b) => {
    const wa = shifts.get(a.target)
    const wb = shifts.get(b.target)
    return Number(wb?.held ?? false) - Number(wa?.held ?? false) || graph.nodes[b.target]!.deg - graph.nodes[a.target]!.deg
  })
  const labeled = ordered.map((p) => {
    const held = shifts.get(p.target)?.held ?? false
    if (!held) return { p, label: false }
    const n = graph.nodes[p.target]!
    const x0 = sx(n.x) + 13
    const y0 = sy(n.y) - 24
    const rect: [number, number, number, number] = [x0, y0, x0 + (p.ticker.length + 7) * 8.6, y0 + 18]
    const hit = placed.some((r) => rect[0] < r[2] && rect[2] > r[0] && rect[1] < r[3] && rect[3] > r[1])
    if (!hit) placed.push(rect)
    return { p, label: !hit }
  })
  return (
    <g data-propagation>
      <g transform={`translate(${t.x} ${t.y}) scale(${t.k})`}>
        {propagation.paths.map((p) => {
          const pts = p.nodes.map((i) => graph.nodes[i]!)
          if (pts.length < 2) return null
          const d = pts.map((n, i) => `${i === 0 ? 'M' : 'L'}${n.x} ${n.y}`).join(' ')
          const held = shifts.get(p.target)?.held ?? false
          return (
            <path
              key={p.target}
              d={d}
              data-prop-path
              fill="none"
              stroke={held ? COLORS.held : COLORS.ndx}
              strokeOpacity={held ? 0.95 : 0.55}
              strokeWidth={held ? 2 : 1.25}
              strokeDasharray={p.virtual ? '4 4' : undefined}
              vectorEffect="non-scaling-stroke"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )
        })}
      </g>
      <g transform={`translate(${sx(o.x)} ${sy(o.y)})`}>
        <circle data-prop-origin-pulse r={14} fill="none" stroke={COLORS.origin} strokeWidth={2} />
        <circle data-prop-origin-pulse r={14} fill="none" stroke={COLORS.origin} strokeWidth={2} />
        <circle data-prop-origin-ring r={12} fill={COLORS.origin} fillOpacity={0.25} stroke={COLORS.origin} strokeWidth={2} />
        <text data-prop-origin-label x={16} y={-22} fill={COLORS.origin} fontFamily="var(--font-mono)" fontSize={16} fontWeight={500} paintOrder="stroke" stroke={COLORS.bg} strokeWidth={5} strokeLinejoin="round">
          {o.name}
        </text>
      </g>
      {labeled.map(({ p, label }) => {
        const n = graph.nodes[p.target]!
        const s = shifts.get(p.target)
        const held = s?.held ?? false
        const shift = s?.shift ?? 0
        return (
          <g key={p.target} transform={`translate(${sx(n.x)} ${sy(n.y)})`} data-prop-target-group>
            <circle data-prop-target r={held ? 9 : 5} fill={held ? COLORS.held : COLORS.bg} stroke={held ? COLORS.held : COLORS.ndx} strokeWidth={1.5} />
            {label && (
              <text data-prop-shift x={13} y={-11} fontFamily="var(--font-mono)" fontSize={14} fontWeight={500} fill={COLORS.label} paintOrder="stroke" stroke={COLORS.bg} strokeWidth={4} strokeLinejoin="round">
                {p.ticker}
                <tspan fill={shift >= 0 ? '#67e8a5' : COLORS.origin} dx={6}>
                  {fmtSigned(shift * 100, 1)}%
                </tspan>
              </text>
            )}
          </g>
        )
      })}
    </g>
  )
}
