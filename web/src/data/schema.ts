/** Shared JSON schemas: produced by scripts/prepare-data.ts, consumed by the app. */

export type Pipeline = 'mvp' | 'mvp2'

export interface GraphNode {
  id: string
  name: string
  type: string
  ndx: boolean
  tickers: string[]
  deg: number
  x: number
  y: number
}

/** [srcIndex, dstIndex, relTypeIndex] */
export type GraphEdge = [number, number, number]

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
  relTypes: string[]
  stats: { nNodes: number; nEdges: number; nComponents: number; nNdx: number }
  hubs: { index: number; name: string; degree: number; ticker: string | null }[]
  bounds: { minX: number; maxX: number; minY: number; maxY: number }
}

export interface Hypothesis {
  id: string
  trigger: string
  originUuid: string
  originName: string
  originIndex: number
  probability: number
  magnitude: number
  horizonDays: number | null
  sources: string[]
  sourceDates: string[]
  datesValid: boolean
  effectTarget: string | null
  effectType: string | null
}

export interface AffectedTicker {
  uuid: string
  index: number
  ticker: string
  name: string
  shift: number
  inPortfolio: boolean
  weight: number
}

export interface DagEntry {
  hypothesisId: string
  originUuid: string
  originName: string
  originIndex: number
  magnitude: number
  probability: number
  affected: AffectedTicker[]
}

export interface PropagationPath {
  target: number
  ticker: string
  /** node indices from origin to target (inclusive); length 1 when origin == target */
  nodes: number[]
  virtual: boolean
}

export interface Propagation {
  origin: number
  paths: PropagationPath[]
}

export interface TickerRow {
  ticker: string
  name: string
  index: number
  amount: number
  purchasePrice: number | null
  evalPrice: number | null
  shares: number | null
  value: number | null
  returnPct: number | null
  weightPct: number
}

export interface PortfolioMeta {
  alphaLevel: number | null
  cvar5Pct: number | null
  expectedReturnPct: number | null
  lambda: number | null
  nNonzero: number
  solver: string
  status: string
}

export interface ArtifactSource {
  kind: 'snapshot' | 'legacy'
  label: string
  runId: string | null
}

export interface RunSummary {
  id: string
  pipeline: Pipeline
  pipelineLabel: 'MVP-1' | 'MVP-2'
  timestamp: string
  dateLabel: string
  submissionId: string
  agent: string
  version: string
  httpStatus: number | null
  success: boolean
  totalInvested: number
  totalValue: number
  returnPct: number
  nTransactions: number
  hypothesesCount: number
  artifactSource: ArtifactSource
  consistent: boolean
}

export interface RunData extends RunSummary {
  tickers: TickerRow[]
  hypotheses: Hypothesis[]
  dag: DagEntry[]
  portfolio: PortfolioMeta
  views: { focus: number[]; neighborhood: number[] }
  propagation: Record<string, Propagation>
  featuredHypothesisId: string
  counts: {
    hypotheses: number
    affectedTickers: number
    affectedInPortfolio: number
    propagationEdges: number
    sources: number
    maxSourceDate: string | null
  }
}

export interface DataIndex {
  generatedAt: string
  cutoffDate: string
  runs: RunSummary[]
  latestRunId: string
}

export interface MetaData {
  cutoffDate: string
  allowlistDates: string[]
  mc: { nSims: number; nTickers: number }
  cov: { method: string; shrinkage: number | null; nObs: number | null }
  graph: GraphData['stats']
  topHubs: { name: string; degree: number }[]
}
