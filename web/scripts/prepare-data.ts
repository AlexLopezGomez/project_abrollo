/**
 * prepare-data — derives everything the web app needs from ../data/ into public/data/.
 *
 * Mirrors dashboard/components/data_loader.py:
 *   - runs come from data/submissions/{mvp,mvp2}_run_*.json
 *   - a run with data/runs/<id>/manifest.json uses that snapshot's artifacts
 *   - otherwise it falls back to the pipeline-level artifacts (data/{hypotheses,dag,portfolios}/{mvp|mvp2}.json)
 *   - the entity graph is always data/mvp2/graph.json (never the .gpickle)
 *
 * Extra derivations done here so the client does none at load time:
 *   - deterministic force layout (seeded) for the full graph
 *   - per-run subgraph views (focus / neighborhood) and propagation paths per hypothesis
 */
import { readFileSync, writeFileSync, mkdirSync, existsSync, readdirSync } from 'node:fs'
import { join, resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  forceSimulation,
  forceLink,
  forceManyBody,
  forceCenter,
  forceX,
  forceY,
  forceCollide,
  type SimulationNodeDatum,
  type SimulationLinkDatum,
} from 'd3-force'
import type {
  AffectedTicker,
  ArtifactSource,
  DagEntry,
  DataIndex,
  GraphData,
  GraphEdge,
  GraphNode,
  Hypothesis,
  MetaData,
  Pipeline,
  PortfolioMeta,
  Propagation,
  PropagationPath,
  RunData,
  RunSummary,
  TickerRow,
} from '../src/data/schema'

const HERE = dirname(fileURLToPath(import.meta.url))
const ROOT = resolve(HERE, '..', '..')
const DATA = join(ROOT, 'data')
const OUT = join(HERE, '..', 'public', 'data')
const CUTOFF = '2025-04-15'

// ---------------------------------------------------------------------------
// helpers

function readJson<T = unknown>(path: string): T {
  return JSON.parse(readFileSync(path, 'utf8')) as T
}
function tryJson<T = unknown>(path: string): T | null {
  if (!existsSync(path)) return null
  try {
    return readJson<T>(path)
  } catch {
    return null
  }
}
function assert(cond: unknown, msg: string): asserts cond {
  if (!cond) throw new Error(`prepare-data: ${msg}`)
}
function num(v: unknown): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null
}
function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

/** mulberry32 — small deterministic PRNG for the layout */
function seeded(seed: number): () => number {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

// ---------------------------------------------------------------------------
// raw schemas (as found on disk)

interface RawGraph {
  nodes: { id: string; name: string; entity_type: string; is_ndx: boolean; tickers: string[] | null }[]
  edges: { src: string; dst: string; rel_type: string }[]
  ndx_uuid_to_tickers: Record<string, string[]>
  stats: { n_nodes: number; n_edges: number; n_components: number }
  hubs: { id: string; name: string; degree: number }[]
}

interface RawSubmission {
  status?: number
  request?: {
    team_id?: string
    model_agent_name?: string
    model_agent_version?: string
    transactions?: { nasdaq_code: string; amount: number }[]
  }
  response?: {
    success?: boolean
    submission_id?: string
    total_invested?: number
    total_value?: number
    purchase_prices_apr15?: Record<string, number>
    eval_prices_today?: Record<string, number>
  }
}

interface RawManifest {
  hypotheses_count?: number
  graph_nodes?: number
  graph_edges?: number
}

interface RawPortfolio {
  alpha_level?: number
  cvar_5_pct?: number
  expected_return_pct?: number
  lambda?: number
  n_nonzero_tickers?: number
  solver?: string
  status?: string
  weights?: Record<string, number>
}

// ---------------------------------------------------------------------------
// graph

interface Graph {
  data: GraphData
  indexOf: Map<string, number>
  adj: Set<number>[]
  tickerToIndex: Map<string, string | number> // ticker -> node index
  edgeSet: Set<string>
}

function buildGraph(): Graph {
  const raw = readJson<RawGraph>(join(DATA, 'mvp2', 'graph.json'))
  assert(Array.isArray(raw.nodes) && Array.isArray(raw.edges), 'graph.json shape changed')

  const indexOf = new Map<string, number>()
  raw.nodes.forEach((n, i) => indexOf.set(n.id, i))

  const relTypes: string[] = []
  const relIndex = new Map<string, number>()
  const edges: GraphEdge[] = []
  const edgeSet = new Set<string>()
  const deg = new Array<number>(raw.nodes.length).fill(0)
  const adj: Set<number>[] = raw.nodes.map(() => new Set<number>())
  for (const e of raw.edges) {
    const s = indexOf.get(e.src)
    const d = indexOf.get(e.dst)
    if (s === undefined || d === undefined) continue
    let r = relIndex.get(e.rel_type)
    if (r === undefined) {
      r = relTypes.length
      relTypes.push(e.rel_type)
      relIndex.set(e.rel_type, r)
    }
    edges.push([s, d, r])
    edgeSet.add(`${s}-${d}`)
    deg[s]!++
    deg[d]!++
    adj[s]!.add(d)
    adj[d]!.add(s)
  }

  // --- deterministic force layout ------------------------------------------
  type N = SimulationNodeDatum & { i: number }
  const rand = seeded(20260415)
  // component ids, so small disconnected pieces can be pulled toward the centre instead of drifting away
  const comp = new Array<number>(raw.nodes.length).fill(-1)
  let nComp = 0
  for (let s = 0; s < raw.nodes.length; s++) {
    if (comp[s] !== -1) continue
    const stack = [s]
    comp[s] = nComp
    while (stack.length) {
      const u = stack.pop()!
      for (const v of adj[u]!) if (comp[v] === -1) {
        comp[v] = nComp
        stack.push(v)
      }
    }
    nComp++
  }
  const compSize = new Array<number>(nComp).fill(0)
  for (const c of comp) compSize[c]!++
  const giant = compSize.indexOf(Math.max(...compSize))

  const R = 1400
  const simNodes: N[] = raw.nodes.map((_, i) => {
    const a = rand() * Math.PI * 2
    const rr = Math.sqrt(rand()) * R
    return { i, x: Math.cos(a) * rr, y: Math.sin(a) * rr }
  })
  const links: SimulationLinkDatum<N>[] = edges.map(([s, d]) => ({ source: s, target: d }))
  const sim = forceSimulation<N>(simNodes)
    .randomSource(rand)
    .alphaDecay(0.012)
    .velocityDecay(0.35)
    .force(
      'link',
      forceLink<N, SimulationLinkDatum<N>>(links)
        .id((n) => n.i)
        .distance((l) => {
          const s = l.source as N
          const t = l.target as N
          const hub = Math.max(deg[s.i]!, deg[t.i]!)
          const both = Math.min(deg[s.i]!, deg[t.i]!)
          return 40 + Math.min(120, hub) * 0.9 + (both > 20 ? 110 : 0)
        })
        .strength((l) => {
          const s = l.source as N
          const t = l.target as N
          return 1 / Math.min(deg[s.i]!, deg[t.i]!)
        }),
    )
    .force('charge', forceManyBody<N>().strength((n) => -60 - Math.min(deg[n.i]!, 150) * 7).theta(0.9).distanceMax(1100))
    .force('center', forceCenter(0, 0))
    .force('x', forceX<N>(0).strength((n) => (comp[n.i] === giant ? 0.02 : 0.08)))
    .force('y', forceY<N>(0).strength((n) => (comp[n.i] === giant ? 0.02 : 0.08)))
    .force('collide', forceCollide<N>().radius((n) => 6 + Math.sqrt(deg[n.i]!) * 1.6).strength(0.8).iterations(2))
    .stop()
  const ticks = 500
  for (let t = 0; t < ticks; t++) sim.tick()

  let minX = Infinity,
    maxX = -Infinity,
    minY = Infinity,
    maxY = -Infinity
  const nodes: GraphNode[] = raw.nodes.map((n, i) => {
    const sn = simNodes[i]!
    const x = Math.round((sn.x ?? 0) * 10) / 10
    const y = Math.round((sn.y ?? 0) * 10) / 10
    minX = Math.min(minX, x)
    maxX = Math.max(maxX, x)
    minY = Math.min(minY, y)
    maxY = Math.max(maxY, y)
    return {
      id: n.id,
      name: n.name,
      type: n.entity_type,
      ndx: Boolean(n.is_ndx),
      tickers: n.tickers ?? raw.ndx_uuid_to_tickers[n.id] ?? [],
      deg: deg[i]!,
      x,
      y,
    }
  })

  const tickerToIndex = new Map<string, number>()
  for (const [uuid, tickers] of Object.entries(raw.ndx_uuid_to_tickers)) {
    const i = indexOf.get(uuid)
    if (i === undefined) continue
    for (const t of tickers) tickerToIndex.set(t, i)
  }
  nodes.forEach((n, i) => n.tickers.forEach((t) => tickerToIndex.set(t, i)))

  const hubs = [...nodes.keys()]
    .sort((a, b) => nodes[b]!.deg - nodes[a]!.deg)
    .slice(0, 12)
    .map((i) => ({ index: i, name: nodes[i]!.name, degree: nodes[i]!.deg, ticker: nodes[i]!.tickers[0] ?? null }))

  const data: GraphData = {
    nodes,
    edges,
    relTypes,
    stats: {
      nNodes: nodes.length,
      nEdges: edges.length,
      nComponents: raw.stats?.n_components ?? 0,
      nNdx: nodes.filter((n) => n.ndx).length,
    },
    hubs,
    bounds: { minX, maxX, minY, maxY },
  }
  return { data, indexOf, adj, tickerToIndex, edgeSet }
}

function neighbors(g: Graph, seeds: Iterable<number>): Set<number> {
  const out = new Set<number>()
  for (const s of seeds) {
    out.add(s)
    for (const n of g.adj[s]!) out.add(n)
  }
  return out
}

// ---------------------------------------------------------------------------
// runs

const SUBMISSION_RE = /^(mvp2|mvp)_run_(\d{8})_(\d{6})\.json$/

function stampToIso(date: string, time: string): string {
  return `${date.slice(0, 4)}-${date.slice(4, 6)}-${date.slice(6, 8)}T${time.slice(0, 2)}:${time.slice(2, 4)}:${time.slice(4, 6)}`
}

function listSubmissions(): { file: string; id: string; pipeline: Pipeline; timestamp: string }[] {
  const dir = join(DATA, 'submissions')
  const out: { file: string; id: string; pipeline: Pipeline; timestamp: string }[] = []
  for (const f of readdirSync(dir)) {
    const m = SUBMISSION_RE.exec(f)
    if (!m) continue
    out.push({ file: join(dir, f), id: f.replace(/\.json$/, ''), pipeline: m[1] as Pipeline, timestamp: stampToIso(m[2]!, m[3]!) })
  }
  return out.sort((a, b) => a.timestamp.localeCompare(b.timestamp))
}

function artifactPaths(id: string, pipeline: Pipeline): { hypotheses: string; dag: string; portfolio: string; source: ArtifactSource; manifest: RawManifest | null } {
  const snap = join(DATA, 'runs', id)
  const manifest = tryJson<RawManifest>(join(snap, 'manifest.json'))
  if (manifest) {
    return {
      hypotheses: join(snap, 'hypotheses.json'),
      dag: join(snap, 'dag.json'),
      portfolio: join(snap, 'portfolio.json'),
      source: { kind: 'snapshot', label: `Snapshot of ${id}`, runId: id },
      manifest,
    }
  }
  const key = pipeline === 'mvp' ? 'mvp' : 'mvp2'
  return {
    hypotheses: join(DATA, 'hypotheses', key === 'mvp' ? 'semi.json' : 'mvp2.json'),
    dag: join(DATA, 'dag', `${key}.json`),
    portfolio: join(DATA, 'portfolios', `${key}.json`),
    source: { kind: 'legacy', label: `${key.toUpperCase()} pipeline artifacts (data/*/${key}.json)`, runId: null },
    manifest: null,
  }
}

function normalizeHypotheses(raw: unknown, pipeline: Pipeline, g: Graph): Hypothesis[] {
  const list: unknown[] = Array.isArray(raw) ? raw : isRecord(raw) && Array.isArray(raw.hypotheses) ? raw.hypotheses : []
  return list.filter(isRecord).map((h, i) => {
    const effectTarget = typeof h.effect_target === 'string' ? h.effect_target : null
    let originUuid = typeof h.origin_entity_uuid === 'string' ? h.origin_entity_uuid : typeof h.origin_uuid === 'string' ? h.origin_uuid : ''
    let originIndex = originUuid ? (g.indexOf.get(originUuid) ?? -1) : -1
    if (originIndex < 0 && effectTarget) {
      const ti = g.tickerToIndex.get(effectTarget)
      if (typeof ti === 'number') {
        originIndex = ti
        originUuid = g.data.nodes[ti]!.id
      }
    }
    const sourceDates = Array.isArray(h.source_dates) ? h.source_dates.filter((d): d is string => typeof d === 'string') : []
    return {
      id: typeof h.id === 'string' ? h.id : `${pipeline.toUpperCase()}_${String(i + 1).padStart(2, '0')}`,
      trigger: typeof h.trigger === 'string' ? h.trigger : '',
      originUuid,
      originName: originIndex >= 0 ? g.data.nodes[originIndex]!.name : (effectTarget ?? '—'),
      originIndex,
      probability: num(h.probability) ?? num(h.trigger_probability) ?? 0,
      magnitude: num(h.magnitude) ?? num(h.effect_magnitude) ?? 0,
      horizonDays: num(h.horizon_days),
      sources: Array.isArray(h.sources) ? h.sources.filter((s): s is string => typeof s === 'string') : [],
      sourceDates,
      datesValid: sourceDates.length > 0 && sourceDates.every((d) => d <= CUTOFF),
      effectTarget,
      effectType: typeof h.effect_type === 'string' ? h.effect_type : null,
    }
  })
}

function normalizeDag(raw: unknown, hypotheses: Hypothesis[], g: Graph, weights: Record<string, number>): DagEntry[] {
  const affectedFrom = (arr: unknown): AffectedTicker[] =>
    (Array.isArray(arr) ? arr : []).filter(isRecord).map((a) => {
      const ticker = typeof a.ticker === 'string' ? a.ticker : ''
      let index = typeof a.ticker_uuid === 'string' ? (g.indexOf.get(a.ticker_uuid) ?? -1) : -1
      if (index < 0) {
        const ti = g.tickerToIndex.get(ticker)
        if (typeof ti === 'number') index = ti
      }
      return {
        uuid: typeof a.ticker_uuid === 'string' ? a.ticker_uuid : index >= 0 ? g.data.nodes[index]!.id : '',
        index,
        ticker,
        name: typeof a.name === 'string' ? a.name : index >= 0 ? g.data.nodes[index]!.name : ticker,
        shift: num(a.shift) ?? 0,
        inPortfolio: ticker in weights,
        weight: weights[ticker] ?? 0,
      }
    })

  if (Array.isArray(raw)) {
    return raw.filter(isRecord).map((e) => {
      const originUuid = typeof e.origin_uuid === 'string' ? e.origin_uuid : typeof e.origin_entity_uuid === 'string' ? e.origin_entity_uuid : ''
      const originIndex = g.indexOf.get(originUuid) ?? -1
      return {
        hypothesisId: typeof e.hypothesis_id === 'string' ? e.hypothesis_id : typeof e.id === 'string' ? e.id : '',
        originUuid,
        originName: typeof e.origin_name === 'string' ? e.origin_name : originIndex >= 0 ? g.data.nodes[originIndex]!.name : '',
        originIndex,
        magnitude: num(e.magnitude) ?? 0,
        probability: num(e.probability) ?? 0,
        affected: affectedFrom(e.affected_tickers),
      }
    })
  }
  // MVP-1: the DAG file is a CPD text dump; derive the propagation from effect_target (like the Python loader)
  return hypotheses.map((h) => ({
    hypothesisId: h.id,
    originUuid: h.originUuid,
    originName: h.originName,
    originIndex: h.originIndex,
    magnitude: h.magnitude,
    probability: h.probability,
    affected: h.effectTarget
      ? affectedFrom([{ ticker: h.effectTarget, ticker_uuid: h.originUuid, name: h.originName, shift: h.magnitude }])
      : [],
  }))
}

function buildPropagation(dag: DagEntry[], g: Graph): Record<string, Propagation> {
  const out: Record<string, Propagation> = {}
  for (const entry of dag) {
    if (entry.originIndex < 0) continue
    const o = entry.originIndex
    const paths: PropagationPath[] = []
    for (const a of entry.affected) {
      if (a.index < 0) continue
      if (a.index === o) {
        paths.push({ target: a.index, ticker: a.ticker, nodes: [o], virtual: false })
        continue
      }
      if (g.adj[o]!.has(a.index)) {
        paths.push({ target: a.index, ticker: a.ticker, nodes: [o, a.index], virtual: false })
        continue
      }
      // two hops: pick the lowest-degree common neighbour (most specific intermediary), deterministic
      let best = -1
      let bestDeg = Infinity
      for (const mid of g.adj[o]!) {
        if (g.adj[mid]!.has(a.index)) {
          const d = g.data.nodes[mid]!.deg
          if (d < bestDeg || (d === bestDeg && mid < best)) {
            best = mid
            bestDeg = d
          }
        }
      }
      if (best >= 0) paths.push({ target: a.index, ticker: a.ticker, nodes: [o, best, a.index], virtual: false })
      else paths.push({ target: a.index, ticker: a.ticker, nodes: [o, a.index], virtual: true })
    }
    // deterministic order: by path length then ticker
    paths.sort((p, q) => p.nodes.length - q.nodes.length || p.ticker.localeCompare(q.ticker))
    out[entry.hypothesisId] = { origin: o, paths }
  }
  return out
}

function buildRun(sub: ReturnType<typeof listSubmissions>[number], g: Graph): RunData {
  const raw = readJson<RawSubmission>(sub.file)
  const req = raw.request ?? {}
  const res = raw.response ?? {}
  const transactions = (req.transactions ?? []).filter((t) => t && typeof t.nasdaq_code === 'string')
  const purchase = res.purchase_prices_apr15 ?? {}
  const evalP = res.eval_prices_today ?? {}

  const art = artifactPaths(sub.id, sub.pipeline)
  const rawPortfolio = tryJson<RawPortfolio>(art.portfolio) ?? {}
  const weights = rawPortfolio.weights ?? {}
  const hypotheses = normalizeHypotheses(tryJson(art.hypotheses), sub.pipeline, g)
  const dag = normalizeDag(tryJson(art.dag), hypotheses, g, Object.fromEntries(transactions.map((t) => [t.nasdaq_code, t.amount])))

  const totalInvested = num(res.total_invested) ?? transactions.reduce((s, t) => s + (num(t.amount) ?? 0), 0)
  const totalValue = num(res.total_value) ?? 0
  const returnPct = totalInvested > 0 ? (totalValue / totalInvested - 1) * 100 : 0

  const tickers: TickerRow[] = transactions
    .map((t) => {
      const pp = num(purchase[t.nasdaq_code])
      const ep = num(evalP[t.nasdaq_code])
      const shares = pp ? t.amount / pp : null
      const value = shares !== null && ep !== null ? shares * ep : null
      const idx = g.tickerToIndex.get(t.nasdaq_code)
      const index = typeof idx === 'number' ? idx : -1
      return {
        ticker: t.nasdaq_code,
        name: index >= 0 ? g.data.nodes[index]!.name : t.nasdaq_code,
        index,
        amount: t.amount,
        purchasePrice: pp,
        evalPrice: ep,
        shares,
        value,
        returnPct: pp && ep ? (ep / pp - 1) * 100 : null,
        weightPct: totalInvested > 0 ? (t.amount / totalInvested) * 100 : 0,
      }
    })
    .sort((a, b) => (b.returnPct ?? -Infinity) - (a.returnPct ?? -Infinity))

  const consistent =
    Object.keys(weights).length === transactions.length &&
    transactions.every((t) => Math.abs((weights[t.nasdaq_code] ?? NaN) - t.amount) < 1)

  const portfolioIdx = new Set<number>()
  for (const t of tickers) if (t.index >= 0) portfolioIdx.add(t.index)
  const origins = new Set<number>()
  for (const h of hypotheses) if (h.originIndex >= 0) origins.add(h.originIndex)
  const focus = new Set<number>([...neighbors(g, origins), ...portfolioIdx])
  const neighborhood = new Set<number>([...focus, ...neighbors(g, portfolioIdx)])

  const propagation = buildPropagation(dag, g)
  const affectedSet = new Set<string>()
  const affectedInPortfolioSet = new Set<string>()
  let propagationEdges = 0
  for (const d of dag) {
    for (const a of d.affected) {
      affectedSet.add(a.ticker)
      if (a.inPortfolio) affectedInPortfolioSet.add(a.ticker)
    }
    propagationEdges += d.affected.length
  }
  const allDates = hypotheses.flatMap((h) => h.sourceDates)
  const featured = [...dag].sort((a, b) => b.affected.length - a.affected.length || a.hypothesisId.localeCompare(b.hypothesisId))[0]

  const portfolio: PortfolioMeta = {
    alphaLevel: num(rawPortfolio.alpha_level),
    cvar5Pct: num(rawPortfolio.cvar_5_pct),
    expectedReturnPct: num(rawPortfolio.expected_return_pct),
    lambda: num(rawPortfolio.lambda),
    nNonzero: num(rawPortfolio.n_nonzero_tickers) ?? Object.keys(weights).length,
    solver: rawPortfolio.solver ?? '—',
    status: rawPortfolio.status ?? '—',
  }

  const summary: RunSummary = {
    id: sub.id,
    pipeline: sub.pipeline,
    pipelineLabel: sub.pipeline === 'mvp' ? 'MVP-1' : 'MVP-2',
    timestamp: sub.timestamp,
    dateLabel: sub.timestamp.slice(0, 10),
    submissionId: res.submission_id ?? '',
    agent: req.model_agent_name ?? '',
    version: req.model_agent_version ?? '',
    httpStatus: num(raw.status),
    success: res.success === true,
    totalInvested,
    totalValue,
    returnPct,
    nTransactions: transactions.length,
    hypothesesCount: art.manifest?.hypotheses_count ?? hypotheses.length,
    artifactSource: art.source,
    consistent,
  }

  return {
    ...summary,
    tickers,
    hypotheses,
    dag,
    portfolio,
    views: { focus: [...focus].sort((a, b) => a - b), neighborhood: [...neighborhood].sort((a, b) => a - b) },
    propagation,
    featuredHypothesisId: featured?.hypothesisId ?? hypotheses[0]?.id ?? '',
    counts: {
      hypotheses: hypotheses.length,
      affectedTickers: affectedSet.size,
      affectedInPortfolio: affectedInPortfolioSet.size,
      propagationEdges,
      sources: hypotheses.reduce((s, h) => s + h.sources.length, 0),
      maxSourceDate: allDates.length ? allDates.reduce((a, b) => (a > b ? a : b)) : null,
    },
  }
}

function summarize(run: RunData): RunSummary {
  return {
    id: run.id,
    pipeline: run.pipeline,
    pipelineLabel: run.pipelineLabel,
    timestamp: run.timestamp,
    dateLabel: run.dateLabel,
    submissionId: run.submissionId,
    agent: run.agent,
    version: run.version,
    httpStatus: run.httpStatus,
    success: run.success,
    totalInvested: run.totalInvested,
    totalValue: run.totalValue,
    returnPct: run.returnPct,
    nTransactions: run.nTransactions,
    hypothesesCount: run.hypothesesCount,
    artifactSource: run.artifactSource,
    consistent: run.consistent,
  }
}

// ---------------------------------------------------------------------------
// meta

function buildMeta(g: Graph): MetaData {
  const allow = tryJson<{ cutoff_date?: string; dates?: string[] }>(join(DATA, 'mvp2', 'date_allowlist.json'))
  const mc = tryJson<{ n_sims?: number; n_tickers?: number }>(join(DATA, 'scenarios', 'mvp2_meta.json'))
  const cov = tryJson<{ method?: string; shrinkage_coef?: number; n_obs?: number }>(join(DATA, 'cov', 'mvp2_meta.json'))
  return {
    cutoffDate: allow?.cutoff_date ?? CUTOFF,
    allowlistDates: (allow?.dates ?? []).filter((d) => typeof d === 'string').sort(),
    mc: { nSims: mc?.n_sims ?? 0, nTickers: mc?.n_tickers ?? 0 },
    cov: { method: cov?.method ?? '—', shrinkage: num(cov?.shrinkage_coef), nObs: num(cov?.n_obs) },
    graph: g.data.stats,
    topHubs: g.data.hubs.map((h) => ({ name: h.name, degree: h.degree })),
  }
}

// ---------------------------------------------------------------------------
// main

function main() {
  const t0 = Date.now()
  mkdirSync(join(OUT, 'runs'), { recursive: true })

  const g = buildGraph()
  writeFileSync(join(OUT, 'graph.json'), JSON.stringify(g.data))
  console.log(`graph: ${g.data.stats.nNodes} nodes, ${g.data.stats.nEdges} edges, ${g.data.relTypes.length} rel types`)

  const subs = listSubmissions()
  assert(subs.length > 0, 'no submissions found')
  const summaries: RunSummary[] = []
  for (const sub of subs) {
    const run = buildRun(sub, g)
    writeFileSync(join(OUT, 'runs', `${run.id}.json`), JSON.stringify(run))
    summaries.push(summarize(run))
    console.log(
      `run ${run.id}: $${run.totalValue.toFixed(0)} (${run.returnPct.toFixed(1)}%) · ${run.hypotheses.length} hyp · ${run.dag.length} dag · focus ${run.views.focus.length} · neighborhood ${run.views.neighborhood.length} · ${run.artifactSource.kind}${run.consistent ? ' · consistent' : ''} · featured ${run.featuredHypothesisId}`,
    )
  }
  const index: DataIndex = {
    generatedAt: new Date().toISOString(),
    cutoffDate: CUTOFF,
    runs: [...summaries].sort((a, b) => b.timestamp.localeCompare(a.timestamp)),
    latestRunId: summaries[summaries.length - 1]!.id,
  }
  writeFileSync(join(OUT, 'index.json'), JSON.stringify(index, null, 2))
  writeFileSync(join(OUT, 'meta.json'), JSON.stringify(buildMeta(g), null, 2))
  console.log(`done in ${Date.now() - t0} ms → ${OUT}`)
}

main()
