import type { GraphData, GraphNode } from '../data/schema'

export interface Transform {
  k: number
  x: number
  y: number
}

export const COLORS = {
  origin: '#ff6b5f',
  held: '#69d4df',
  ndx: '#9da79d',
  other: '#3d463f',
  edge: 'rgba(157, 167, 157, 0.16)',
  edgeHover: 'rgba(244, 241, 232, 0.6)',
  label: '#f4f1e8',
  labelMuted: '#9da79d',
  bg: '#050706',
} as const

export type NodeRole = 'origin' | 'held' | 'ndx' | 'other'

export function nodeRadius(n: GraphNode): number {
  return 2.2 + Math.sqrt(n.deg) * 0.75
}

/**
 * Canvas renderer for the entity graph. Positions are precomputed; this only projects and paints.
 * Draws are requested (coalesced to one rAF) rather than run in a loop.
 */
export class GraphRenderer {
  private ctx: CanvasRenderingContext2D
  private graph: GraphData | null = null
  private roles: NodeRole[] = []
  private visible = new Uint8Array(0)
  private visibleEdges: number[] = []
  private transform: Transform = { k: 1, x: 0, y: 0 }
  private hover = -1
  private hoverEdges: number[] = []
  private selected = -1
  private highlightNodes = new Set<number>()
  private highlightEdges = new Set<string>()
  private width = 0
  private height = 0
  private dpr = 1
  private raf = 0
  /** 0 → nothing dimmed, 1 → everything outside the highlight set is dimmed */
  dim = 0
  labelMode: 'auto' | 'all' | 'none' = 'auto'
  relTypeLabels = true

  constructor(private canvas: HTMLCanvasElement) {
    const ctx = canvas.getContext('2d')
    if (!ctx) throw new Error('2d context unavailable')
    this.ctx = ctx
  }

  setData(graph: GraphData, roles: NodeRole[]) {
    this.graph = graph
    this.roles = roles
    this.visible = new Uint8Array(graph.nodes.length).fill(1)
    this.visibleEdges = graph.edges.map((_, i) => i)
    this.requestDraw()
  }

  setVisible(indices: Iterable<number> | null) {
    if (!this.graph) return
    const n = this.graph.nodes.length
    if (indices === null) {
      this.visible = new Uint8Array(n).fill(1)
    } else {
      this.visible = new Uint8Array(n)
      for (const i of indices) this.visible[i] = 1
    }
    this.visibleEdges = []
    this.graph.edges.forEach(([s, d], i) => {
      if (this.visible[s] && this.visible[d]) this.visibleEdges.push(i)
    })
    this.requestDraw()
  }

  isVisible(i: number): boolean {
    return this.visible[i] === 1
  }

  setSize(width: number, height: number, dpr: number) {
    this.width = width
    this.height = height
    this.dpr = dpr
    this.canvas.width = Math.round(width * dpr)
    this.canvas.height = Math.round(height * dpr)
    this.canvas.style.width = `${width}px`
    this.canvas.style.height = `${height}px`
    this.requestDraw()
  }

  setTransform(t: Transform) {
    this.transform = t
    this.requestDraw()
  }
  getTransform(): Transform {
    return this.transform
  }

  setHover(i: number) {
    if (i === this.hover) return
    this.hover = i
    this.hoverEdges = []
    if (i >= 0 && this.graph) {
      this.graph.edges.forEach(([s, d], ei) => {
        if ((s === i || d === i) && this.visible[s] && this.visible[d]) this.hoverEdges.push(ei)
      })
    }
    this.requestDraw()
  }

  setSelected(i: number) {
    this.selected = i
    this.requestDraw()
  }

  setHighlight(nodes: Set<number>, edges: Set<string>) {
    this.highlightNodes = nodes
    this.highlightEdges = edges
    this.requestDraw()
  }

  toScreen(x: number, y: number): [number, number] {
    const { k, x: tx, y: ty } = this.transform
    return [x * k + tx, y * k + ty]
  }
  toGraph(sx: number, sy: number): [number, number] {
    const { k, x: tx, y: ty } = this.transform
    return [(sx - tx) / k, (sy - ty) / k]
  }

  screenRadius(n: GraphNode): number {
    const k = this.transform.k
    return nodeRadius(n) * Math.min(1.8, Math.max(0.55, Math.pow(k, 0.7)))
  }

  requestDraw() {
    if (this.raf) return
    this.raf = requestAnimationFrame(() => {
      this.raf = 0
      this.draw()
    })
  }

  destroy() {
    if (this.raf) cancelAnimationFrame(this.raf)
  }

  private draw() {
    const g = this.graph
    const ctx = this.ctx
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0)
    ctx.clearRect(0, 0, this.width, this.height)
    if (!g) return
    const { k, x: tx, y: ty } = this.transform
    const dim = this.dim
    const hasHighlight = this.highlightNodes.size > 0
    const nodes = g.nodes
    const edges = g.edges

    // --- edges -------------------------------------------------------------
    ctx.lineWidth = Math.max(0.5, Math.min(1.4, k * 0.9))
    ctx.strokeStyle = COLORS.edge
    ctx.globalAlpha = 1 - dim * 0.85
    ctx.beginPath()
    for (const ei of this.visibleEdges) {
      const e = edges[ei]!
      if (hasHighlight && this.highlightEdges.has(`${e[0]}-${e[1]}`)) continue
      const a = nodes[e[0]]!
      const b = nodes[e[1]]!
      ctx.moveTo(a.x * k + tx, a.y * k + ty)
      ctx.lineTo(b.x * k + tx, b.y * k + ty)
    }
    ctx.stroke()
    ctx.globalAlpha = 1

    // hovered node's edges
    if (this.hover >= 0 && this.hoverEdges.length) {
      ctx.strokeStyle = COLORS.edgeHover
      ctx.lineWidth = 1.2
      ctx.beginPath()
      for (const ei of this.hoverEdges) {
        const e = edges[ei]!
        const a = nodes[e[0]]!
        const b = nodes[e[1]]!
        ctx.moveTo(a.x * k + tx, a.y * k + ty)
        ctx.lineTo(b.x * k + tx, b.y * k + ty)
      }
      ctx.stroke()
    }

    // --- nodes -------------------------------------------------------------
    const radiusScale = Math.min(1.8, Math.max(0.55, Math.pow(k, 0.7)))
    const drawRole = (role: NodeRole, color: string) => {
      ctx.fillStyle = color
      for (let i = 0; i < nodes.length; i++) {
        if (!this.visible[i] || this.roles[i] !== role) continue
        const n = nodes[i]!
        const sx = n.x * k + tx
        const sy = n.y * k + ty
        if (sx < -20 || sy < -20 || sx > this.width + 20 || sy > this.height + 20) continue
        const inHl = hasHighlight && this.highlightNodes.has(i)
        ctx.globalAlpha = inHl ? 1 : role === 'other' ? 0.8 - dim * 0.7 : 1 - dim * 0.8
        const r = nodeRadius(n) * radiusScale
        ctx.beginPath()
        ctx.arc(sx, sy, r, 0, Math.PI * 2)
        ctx.fill()
      }
    }
    drawRole('other', COLORS.other)
    drawRole('ndx', COLORS.ndx)
    drawRole('held', COLORS.held)
    drawRole('origin', COLORS.origin)
    ctx.globalAlpha = 1

    // selected / hovered rings
    for (const i of [this.selected, this.hover]) {
      if (i < 0 || !this.visible[i]) continue
      const n = nodes[i]!
      const sx = n.x * k + tx
      const sy = n.y * k + ty
      ctx.strokeStyle = i === this.selected ? COLORS.label : COLORS.labelMuted
      ctx.lineWidth = 1.5
      ctx.beginPath()
      ctx.arc(sx, sy, nodeRadius(n) * radiusScale + 4, 0, Math.PI * 2)
      ctx.stroke()
    }

    // --- labels (with simple collision avoidance, drawn in priority order) --
    if (this.labelMode !== 'none') {
      const showAll = this.labelMode === 'all'
      ctx.font = `500 13px "IBM Plex Mono", monospace`
      ctx.textBaseline = 'middle'
      const placed: [number, number, number, number][] = []
      const candidates: { i: number; prio: number }[] = []
      for (let i = 0; i < nodes.length; i++) {
        if (!this.visible[i]) continue
        const role = this.roles[i]!
        const n = nodes[i]!
        const inHl = hasHighlight && this.highlightNodes.has(i)
        const important = role === 'origin' || role === 'held'
        let show = false
        if (i === this.hover || i === this.selected) show = false // tooltip covers it
        else if (inHl) show = false // the SVG overlay labels highlighted nodes
        else if (hasHighlight && dim > 0.5) show = false // everything else is dimmed while a propagation is shown
        else if (showAll) show = important || n.deg >= 20
        else if (role === 'origin') show = true
        else if (role === 'held') show = k >= 1.15
        else if (k >= 2.4 && n.deg >= 8) show = true
        if (!show) continue
        candidates.push({ i, prio: (role === 'origin' ? 0 : inHl ? 1 : role === 'held' ? 2 : 3) * 1000 - n.deg })
      }
      candidates.sort((a, b) => a.prio - b.prio)
      for (const { i } of candidates) {
        const n = nodes[i]!
        const role = this.roles[i]!
        const inHl = hasHighlight && this.highlightNodes.has(i)
        const sx = n.x * k + tx
        const sy = n.y * k + ty
        if (sx < -40 || sy < -20 || sx > this.width + 40 || sy > this.height + 20) continue
        const text = n.tickers[0] ?? shortName(n.name)
        const r = nodeRadius(n) * radiusScale
        const w = ctx.measureText(text).width
        const x0 = sx + r + 5
        const y0 = sy - 8
        const rect: [number, number, number, number] = [x0, y0, x0 + w, y0 + 16]
        if (placed.some((p) => rect[0] < p[2] && rect[2] > p[0] && rect[1] < p[3] && rect[3] > p[1])) continue
        placed.push(rect)
        ctx.globalAlpha = inHl || !hasHighlight ? 1 : 1 - dim * 0.85
        ctx.fillStyle = role === 'origin' ? COLORS.origin : role === 'held' ? COLORS.label : COLORS.labelMuted
        ctx.fillText(text, x0, sy)
      }
      ctx.globalAlpha = 1
    }

    // --- rel_type labels on hover ------------------------------------------
    if (this.relTypeLabels && this.hover >= 0 && this.hoverEdges.length && this.hoverEdges.length <= 40) {
      ctx.font = `400 12px "IBM Plex Mono", monospace`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      for (const ei of this.hoverEdges) {
        const e = edges[ei]!
        const a = nodes[e[0]]!
        const b = nodes[e[1]]!
        const mx = ((a.x + b.x) / 2) * k + tx
        const my = ((a.y + b.y) / 2) * k + ty
        const label = g.relTypes[e[2]] ?? ''
        const w = ctx.measureText(label).width + 10
        ctx.fillStyle = 'rgba(5, 7, 6, 0.85)'
        ctx.fillRect(mx - w / 2, my - 9, w, 18)
        ctx.fillStyle = COLORS.labelMuted
        ctx.fillText(label, mx, my)
      }
      ctx.textAlign = 'start'
    }
  }
}

export function shortName(name: string): string {
  const n = name.replace(/\b(INC|CORP|CORPORATION|LTD|LLC|PLC|CO|INCORPORATED)\b\.?/gi, '').replace(/[,.\s]+$/, '').trim()
  const t = n.length > 22 ? `${n.slice(0, 21)}…` : n
  return t.toUpperCase() === t ? t.toLowerCase().replace(/(^|[\s-])([a-z])/g, (_m, sep: string, c: string) => sep + c.toUpperCase()) : t
}
