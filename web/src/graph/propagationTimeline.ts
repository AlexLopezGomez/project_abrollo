import { gsap, Flip } from '../lib/gsap'
import type { GraphData, Propagation } from '../data/schema'
import type { GraphRenderer } from './renderer'

export interface PropagationTimelineArgs {
  wrap: HTMLElement
  renderer: GraphRenderer
  graph: GraphData
  propagation: Propagation
  /** tickers held in the portfolio, with their dollar weight */
  held: Map<string, number>
  /** element in the inspector a weight chip should land on, by ticker */
  chipFor: (ticker: string) => HTMLElement | null
  reduced: boolean
  maxFlyingChips?: number
}

export interface PropagationTimeline {
  tl: gsap.core.Timeline
  dispose: () => void
}

/**
 * The "money shot": origin pulses → paths draw → affected tickers pop with their shift →
 * weight chips fly (Flip) into the inspector. Deterministic: built only from data + current layout.
 */
export function buildPropagationTimeline(a: PropagationTimelineArgs): PropagationTimeline {
  const q = gsap.utils.selector(a.wrap)
  const tl = gsap.timeline({ paused: true, defaults: { ease: 'power3.out' } })
  const paths = q<SVGPathElement>('[data-prop-path]')
  const targets = q<SVGGElement>('[data-prop-target-group]')
  const originRing = q('[data-prop-origin-ring]')
  const originPulse = q('[data-prop-origin-pulse]')
  const originLabel = q('[data-prop-origin-label]')

  const highlightNodes = new Set<number>([a.propagation.origin])
  const highlightEdges = new Set<string>()
  for (const p of a.propagation.paths) {
    p.nodes.forEach((n, i) => {
      highlightNodes.add(n)
      if (i > 0) {
        highlightEdges.add(`${p.nodes[i - 1]}-${n}`)
        highlightEdges.add(`${n}-${p.nodes[i - 1]}`)
      }
    })
  }
  a.renderer.setHighlight(highlightNodes, highlightEdges)

  // ghosts for the Flip flight
  const ghosts: HTMLElement[] = []
  const flights: { ghost: HTMLElement; chip: HTMLElement }[] = []
  const heldPaths = a.propagation.paths.filter((p) => a.held.has(p.ticker))
  const flying = heldPaths.slice(0, a.maxFlyingChips ?? 14)
  for (const p of flying) {
    const chip = a.chipFor(p.ticker)
    if (!chip) continue
    const n = a.graph.nodes[p.target]!
    const [sx, sy] = a.renderer.toScreen(n.x, n.y)
    const ghost = document.createElement('span')
    ghost.className = chip.className
    ghost.textContent = chip.textContent
    ghost.setAttribute('data-ghost', '')
    Object.assign(ghost.style, {
      position: 'absolute',
      left: `${sx}px`,
      top: `${sy}px`,
      transform: 'translate(-50%, -50%) scale(0.6)',
      opacity: '0',
      pointerEvents: 'none',
      zIndex: '5',
      whiteSpace: 'nowrap',
    })
    a.wrap.appendChild(ghost)
    ghosts.push(ghost)
    flights.push({ ghost, chip })
  }
  const allChips = heldPaths.map((p) => a.chipFor(p.ticker)).filter((c): c is HTMLElement => Boolean(c))

  // ---- initial state (also what restart() resets to) -----------------------
  tl.set(a.renderer, { dim: 0 }, 0)
  tl.set(originRing, { scale: 0, transformOrigin: 'center', autoAlpha: 0 }, 0)
  tl.set(originPulse, { scale: 1, transformOrigin: 'center', autoAlpha: 0 }, 0)
  tl.set(originLabel, { autoAlpha: 0 }, 0)
  tl.set(paths, { drawSVG: '0%' }, 0)
  tl.set(targets, { autoAlpha: 0, scale: 0.3, transformOrigin: 'center' }, 0)
  tl.set(allChips, { autoAlpha: 0, y: 6 }, 0)
  tl.set(ghosts, { autoAlpha: 0, scale: 0.6 }, 0)

  // ---- 1. origin -----------------------------------------------------------
  tl.to(originRing, { scale: 1, autoAlpha: 1, duration: 0.45, ease: 'back.out(2)' }, 0.05)
  tl.to(originLabel, { autoAlpha: 1, duration: 0.4 }, 0.25)
  originPulse.forEach((el, i) => {
    tl.fromTo(el, { scale: 1, autoAlpha: 0.9 }, { scale: 3.2, autoAlpha: 0, duration: 0.9, ease: 'power2.out' }, 0.3 + i * 0.35)
  })
  tl.to(a.renderer, { dim: 1, duration: 0.7, ease: 'power2.inOut', onUpdate: () => a.renderer.requestDraw() }, 0.25)

  // ---- 2. paths draw in sequence -------------------------------------------
  const n = Math.max(1, paths.length)
  const window = Math.min(1.9, 0.6 + n * 0.03)
  const each = n > 1 ? (window - 0.55) / (n - 1) : 0
  const pathStart = 0.75
  paths.forEach((p, i) => {
    tl.to(p, { drawSVG: '0% 100%', duration: 0.55, ease: 'power2.inOut' }, pathStart + i * each)
  })

  // ---- 3. targets pop with their shift -------------------------------------
  targets.forEach((g, i) => {
    tl.to(g, { autoAlpha: 1, scale: 1, duration: 0.4, ease: 'back.out(2.5)' }, pathStart + i * each + 0.42)
  })

  // ---- 4. weight chips fly into the inspector (Flip) -----------------------
  const flyStart = pathStart + window + 0.25
  flights.forEach(({ ghost, chip }, i) => {
    const at = flyStart + i * 0.06
    tl.to(ghost, { autoAlpha: 1, scale: 1, duration: 0.2 }, at)
    tl.add(Flip.fit(ghost, chip, { duration: 0.7, ease: 'power2.inOut', absolute: true }) as gsap.core.Tween, at + 0.15)
    tl.to(ghost, { autoAlpha: 0, duration: 0.15 }, at + 0.8)
    tl.to(chip, { autoAlpha: 1, y: 0, duration: 0.3 }, at + 0.78)
  })
  const rest = allChips.slice(flying.length)
  if (rest.length) tl.to(rest, { autoAlpha: 1, y: 0, duration: 0.35, stagger: 0.02 }, flyStart + flights.length * 0.06 + 0.7)

  if (a.reduced) tl.progress(1)

  return {
    tl,
    dispose: () => {
      tl.kill()
      ghosts.forEach((g) => g.remove())
      gsap.set(allChips, { clearProps: 'all' })
      a.renderer.dim = 0
      a.renderer.setHighlight(new Set(), new Set())
    },
  }
}
