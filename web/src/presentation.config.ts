import type { GraphView } from './data/graphViews'

/**
 * Stage formats. `wide` is the 16:9 talk slide; `square` fits the black band under a 4:3-ish
 * webcam clip in a 9:16 (1080×1920) vertical video — the clip takes ~856 px, the stage the rest.
 */
export type StageFormat = 'wide' | 'square'
export const STAGE_SIZES: Record<StageFormat, { width: number; height: number }> = {
  wide: { width: 1920, height: 1080 },
  square: { width: 1080, height: 1064 },
}

export interface PresentationConfig {
  /** Run shown first and used as the headline. Must be a file name stem in data/submissions/. */
  heroRunId: string
  /** Hypothesis animated in presentation step 3. `null` = the one with the most affected tickers. */
  featuredHypothesisId: string | null
  /** Graph view for step 3. */
  graphView: GraphView
  /** Seconds each auto-playing step timeline is allowed before it is considered "settled" (screenshots). */
  stepSettleSeconds: number
  /** Stage format on entry. Override per session with `?stage=wide|square` or the `F` key. */
  stageFormat: StageFormat
}

export const presentationConfig: PresentationConfig = {
  heroRunId: 'mvp2_run_20260425_174212',
  featuredHypothesisId: null,
  graphView: 'neighborhood',
  stepSettleSeconds: 5,
  stageFormat: 'square',
}
