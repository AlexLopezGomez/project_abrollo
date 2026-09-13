export type GraphView = 'focus' | 'neighborhood' | 'full'

export const GRAPH_VIEWS: { id: GraphView; label: string; hint: string }[] = [
  { id: 'focus', label: 'Focus', hint: 'Hypothesis origins, their direct neighbours, and the portfolio' },
  { id: 'neighborhood', label: 'Neighborhood', hint: 'Focus plus the direct neighbours of every holding' },
  { id: 'full', label: 'Full graph', hint: 'Every entity Cala returned' },
]
