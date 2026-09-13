import type { GraphView } from './data/graphViews'

export interface PresentationConfig {
  /** Run shown first and used as the headline. Must be a file name stem in data/submissions/. */
  heroRunId: string
  /** Hypothesis animated in presentation step 3. `null` = the one with the most affected tickers. */
  featuredHypothesisId: string | null
  /** Graph view for step 3. */
  graphView: GraphView
  /** Seconds each auto-playing step timeline is allowed before it is considered "settled" (screenshots). */
  stepSettleSeconds: number
}

export const presentationConfig: PresentationConfig = {
  heroRunId: 'mvp2_run_20260425_174212',
  featuredHypothesisId: null,
  graphView: 'neighborhood',
  stepSettleSeconds: 5,
}
