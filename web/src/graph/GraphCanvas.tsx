import { forwardRef, useEffect, useImperativeHandle, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { select } from 'd3-selection'
import { zoom, zoomIdentity, type ZoomBehavior, type ZoomTransform } from 'd3-zoom'
import { quadtree, type Quadtree } from 'd3-quadtree'
import { gsap } from '../lib/gsap'
import type { GraphData, GraphNode } from '../data/schema'
import { GraphRenderer, nodeRadius, type NodeRole, type Transform } from './renderer'
import styles from './GraphCanvas.module.css'

export interface GraphCanvasHandle {
  fit: (indices?: Iterable<number>, opts?: { duration?: number; padding?: number; onComplete?: () => void }) => void
  zoomTo: (index: number, scale?: number, duration?: number) => void
  zoomBy: (factor: number) => void
  renderer: () => GraphRenderer | null
  element: () => HTMLDivElement | null
}

interface Props {
  graph: GraphData
  roles: NodeRole[]
  visible: Set<number> | null
  selected: number | null
  onSelect: (index: number | null) => void
  onTransform?: (t: Transform) => void
  onHover?: (index: number | null) => void
  labelMode?: 'auto' | 'all' | 'none'
  interactive?: boolean
  /** Overlay rendered on top of the canvas (SVG); receives the live transform. */
  overlay?: (t: Transform, size: { width: number; height: number }) => ReactNode
  tooltip?: (node: GraphNode, index: number) => ReactNode
}

export const GraphCanvas = forwardRef<GraphCanvasHandle, Props>(function GraphCanvas(
  { graph, roles, visible, selected, onSelect, onTransform, onHover, labelMode = 'auto', interactive = true, overlay, tooltip },
  ref,
) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const rendererRef = useRef<GraphRenderer | null>(null)
  const zoomRef = useRef<ZoomBehavior<HTMLCanvasElement, unknown> | null>(null)
  const [transform, setTransform] = useState<Transform>({ k: 1, x: 0, y: 0 })
  const [size, setSize] = useState({ width: 0, height: 0 })
  const [hover, setHover] = useState<{ index: number; x: number; y: number } | null>(null)
  const visibleRef = useRef(visible)
  visibleRef.current = visible

  const tree = useMemo<Quadtree<number>>(() => {
    const q = quadtree<number>()
      .x((i) => graph.nodes[i]!.x)
      .y((i) => graph.nodes[i]!.y)
    q.addAll(graph.nodes.map((_, i) => i))
    return q
  }, [graph])

  // renderer lifecycle (layout effect: parents' useGSAP layout effects expect it to exist)
  useLayoutEffect(() => {
    const canvas = canvasRef.current
    const wrap = wrapRef.current
    if (!canvas || !wrap) return
    const r = new GraphRenderer(canvas)
    rendererRef.current = r
    r.setData(graph, roles)
    r.labelMode = labelMode
    const measure = () => {
      // offset* = layout size; getBoundingClientRect would include the presentation stage's CSS scale
      const width = wrap.offsetWidth
      const height = wrap.offsetHeight
      r.setSize(width, height, Math.min(2, window.devicePixelRatio || 1))
      setSize({ width, height })
    }
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(wrap)
    return () => {
      ro.disconnect()
      r.destroy()
      rendererRef.current = null
    }
  }, [graph, roles, labelMode])

  useEffect(() => {
    rendererRef.current?.setVisible(visible)
  }, [visible, graph])

  useEffect(() => {
    rendererRef.current?.setSelected(selected ?? -1)
  }, [selected])

  // zoom / pan (layout effect: must exist before parents' useGSAP layout effects call fit())
  useLayoutEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const z = zoom<HTMLCanvasElement, unknown>()
      .scaleExtent([0.12, 10])
      .filter((e: Event) => interactive && !(e as MouseEvent).ctrlKey && (e.type !== 'mousedown' || (e as MouseEvent).button === 0))
      .on('zoom', (e: { transform: ZoomTransform }) => {
        const t = { k: e.transform.k, x: e.transform.x, y: e.transform.y }
        rendererRef.current?.setTransform(t)
        setTransform(t)
        onTransform?.(t)
      })
    zoomRef.current = z
    select(canvas).call(z)
    return () => {
      select(canvas).on('.zoom', null)
    }
  }, [interactive, onTransform])

  const animateTo = (target: Transform, duration: number, onComplete?: () => void) => {
    const canvas = canvasRef.current
    const z = zoomRef.current
    if (!canvas || !z) return
    const from = { ...(rendererRef.current?.getTransform() ?? { k: 1, x: 0, y: 0 }) }
    gsap.killTweensOf(from)
    if (duration <= 0) {
      select(canvas).call(z.transform, zoomIdentity.translate(target.x, target.y).scale(target.k))
      onComplete?.()
      return
    }
    gsap.to(from, {
      k: target.k,
      x: target.x,
      y: target.y,
      duration,
      ease: 'power2.inOut',
      onUpdate: () => select(canvas).call(z.transform, zoomIdentity.translate(from.x, from.y).scale(from.k)),
      onComplete,
    })
  }

  const fitTo = (indices?: Iterable<number>, opts: { duration?: number; padding?: number; onComplete?: () => void } = {}) => {
    const wrap = wrapRef.current
    if (!wrap) return
    const width = wrap.offsetWidth
    const height = wrap.offsetHeight
    const list = [...(indices ?? (visibleRef.current ? visibleRef.current : graph.nodes.map((_, i) => i)))]
    if (!list.length) return
    // ignore far outliers (small disconnected components) when there are many nodes
    const xs = list.map((i) => graph.nodes[i]!.x).sort((a, b) => a - b)
    const ys = list.map((i) => graph.nodes[i]!.y).sort((a, b) => a - b)
    const trim = list.length > 200 ? 0.015 : 0
    const lo = Math.floor(xs.length * trim)
    const hi = Math.max(lo, Math.ceil(xs.length * (1 - trim)) - 1)
    const minX = xs[lo]!
    const maxX = xs[hi]!
    const minY = ys[lo]!
    const maxY = ys[hi]!
    const pad = opts.padding ?? 60
    const bw = Math.max(1, maxX - minX)
    const bh = Math.max(1, maxY - minY)
    const k = Math.min(10, Math.max(0.12, Math.min((width - pad * 2) / bw, (height - pad * 2) / bh)))
    const cx = (minX + maxX) / 2
    const cy = (minY + maxY) / 2
    animateTo({ k, x: width / 2 - cx * k, y: height / 2 - cy * k }, opts.duration ?? 0.8, opts.onComplete)
  }

  useImperativeHandle(
    ref,
    () => ({
      fit: fitTo,
      zoomTo: (index, scale = 2.2, duration = 0.8) => {
        const wrap = wrapRef.current
        if (!wrap) return
        const width = wrap.offsetWidth
        const height = wrap.offsetHeight
        const n = graph.nodes[index]!
        animateTo({ k: scale, x: width / 2 - n.x * scale, y: height / 2 - n.y * scale }, duration)
      },
      zoomBy: (factor) => {
        const wrap = wrapRef.current
        const t = rendererRef.current?.getTransform()
        if (!wrap || !t) return
        const width = wrap.offsetWidth
        const height = wrap.offsetHeight
        const k = Math.min(10, Math.max(0.12, t.k * factor))
        // zoom around the centre
        const cx = width / 2
        const cy = height / 2
        animateTo({ k, x: cx - ((cx - t.x) / t.k) * k, y: cy - ((cy - t.y) / t.k) * k }, 0.4)
      },
      renderer: () => rendererRef.current,
      element: () => wrapRef.current,
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [graph],
  )

  const pick = (sx: number, sy: number): number => {
    const r = rendererRef.current
    if (!r) return -1
    const [gx, gy] = r.toGraph(sx, sy)
    const t = r.getTransform()
    const radiusGraph = 14 / t.k
    let best = -1
    let bestD = Infinity
    tree.visit((node, x0, y0, x1, y1) => {
      if (x0 > gx + radiusGraph || x1 < gx - radiusGraph || y0 > gy + radiusGraph || y1 < gy - radiusGraph) return true
      if (!('length' in node)) {
        let leaf: typeof node | undefined = node
        while (leaf) {
          const i = leaf.data
          if (r.isVisible(i)) {
            const n = graph.nodes[i]!
            const d = Math.hypot(n.x - gx, n.y - gy) - nodeRadius(n) / Math.max(1, t.k)
            if (d < bestD && d < radiusGraph) {
              bestD = d
              best = i
            }
          }
          leaf = leaf.next
        }
      }
      return false
    })
    return best
  }

  const onMove = (e: React.MouseEvent) => {
    if (!interactive) return
    const rect = wrapRef.current!.getBoundingClientRect()
    const sx = e.clientX - rect.left
    const sy = e.clientY - rect.top
    const i = pick(sx, sy)
    rendererRef.current?.setHover(i)
    if (i >= 0) {
      const [nx, ny] = rendererRef.current!.toScreen(graph.nodes[i]!.x, graph.nodes[i]!.y)
      setHover({ index: i, x: nx, y: ny })
    } else setHover(null)
    onHover?.(i >= 0 ? i : null)
  }
  const onLeave = () => {
    rendererRef.current?.setHover(-1)
    setHover(null)
    onHover?.(null)
  }
  const downPos = useRef<[number, number] | null>(null)
  const onDown = (e: React.MouseEvent) => {
    downPos.current = [e.clientX, e.clientY]
  }
  const onUp = (e: React.MouseEvent) => {
    if (!interactive) return
    const d = downPos.current
    downPos.current = null
    if (!d || Math.hypot(e.clientX - d[0], e.clientY - d[1]) > 4) return
    const rect = wrapRef.current!.getBoundingClientRect()
    const i = pick(e.clientX - rect.left, e.clientY - rect.top)
    onSelect(i >= 0 ? i : null)
  }

  const hoverNode = hover ? graph.nodes[hover.index] : null
  return (
    <div ref={wrapRef} className={`${styles.wrap} ${interactive ? '' : styles.static}`}>
      <canvas ref={canvasRef} className={styles.canvas} onMouseMove={onMove} onMouseLeave={onLeave} onMouseDown={onDown} onMouseUp={onUp} />
      <svg className={styles.overlay} width={size.width} height={size.height} viewBox={`0 0 ${size.width} ${size.height}`}>
        {overlay?.(transform, size)}
      </svg>
      {hoverNode && hover && tooltip && (
        <div
          className={styles.tooltip}
          style={{
            left: Math.min(size.width - 300, hover.x + 16),
            top: hover.y + 16 > size.height - 120 ? hover.y - 110 : hover.y + 16,
          }}
        >
          {tooltip(hoverNode, hover.index)}
        </div>
      )}
    </div>
  )
})
