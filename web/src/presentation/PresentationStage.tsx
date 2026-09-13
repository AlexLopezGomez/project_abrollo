import { useEffect, useMemo, useState } from 'react'
import styles from './PresentationStage.module.css'
import { usePresentation } from './PresentationContext'
import { useAppData } from '../data/RunContext'
import { presentationConfig, STAGE_SIZES, type StageFormat } from '../presentation.config'
import { Hero } from '../sections/Hero/Hero'
import { Pipeline } from '../sections/Pipeline/Pipeline'
import { GraphExplorer } from '../sections/Graph/GraphExplorer'
import { Hypotheses } from '../sections/Hypotheses/Hypotheses'
import { Portfolio } from '../sections/Portfolio/Portfolio'

function useStageScale(format: StageFormat): number {
  const { width: W, height: H } = STAGE_SIZES[format]
  const fit = () => Math.min(window.innerWidth / W, window.innerHeight / H)
  const [scale, setScale] = useState(fit)
  useEffect(() => {
    const onResize = () => setScale(fit())
    onResize()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [W, H])
  return scale
}

/**
 * Locked stage (1920×1080 `wide` or 1080×1064 `square`, see STAGE_SIZES). Each step is a fresh mount
 * (keyed by step + playToken + format), so its GSAP timeline plays from zero on entry, on `R` and on `F`.
 * Nothing here reflows with the window; sections adapt to the format through `[data-format]`.
 */
export function PresentationStage() {
  const { step, playToken, format } = usePresentation()
  const { run } = useAppData()
  const scale = useStageScale(format)
  const { width, height } = STAGE_SIZES[format]
  const featured = useMemo(() => {
    const id = presentationConfig.featuredHypothesisId
    return id && run.hypotheses.some((h) => h.id === id) ? id : run.featuredHypothesisId
  }, [run])

  const key = `${run.id}-${step}-${playToken}-${format}`
  let content: React.ReactNode
  switch (step) {
    case 0:
      content = (
        <div className={styles.step} key={key}>
          <Hero mode="stage" playToken={playToken} />
        </div>
      )
      break
    case 1:
      content = (
        <div className={styles.step} key={key}>
          <Pipeline mode="stage" playToken={playToken} />
        </div>
      )
      break
    case 2:
      content = (
        <div className={`${styles.step} ${styles.padded}`} key={key}>
          <div className={styles.stepFill}>
            <GraphExplorer mode="stage" playToken={playToken} featuredId={featured} />
          </div>
        </div>
      )
      break
    case 3:
      content = (
        <div className={styles.step} key={key}>
          <Hypotheses mode="stage" playToken={playToken} featuredId={featured} />
        </div>
      )
      break
    default:
      content = (
        <div className={`${styles.step} ${styles.padded}`} key={key}>
          <Portfolio mode="stage" playToken={playToken} />
        </div>
      )
  }

  return (
    <div className={styles.root} aria-label="Presentation" data-format={format}>
      <div className={styles.stage} style={{ width, height, transform: `translate(-50%, -50%) scale(${scale})` }}>
        {content}
      </div>
    </div>
  )
}
