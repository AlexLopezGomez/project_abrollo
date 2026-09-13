import { useEffect, useMemo, useState } from 'react'
import styles from './PresentationStage.module.css'
import { usePresentation } from './PresentationContext'
import { useAppData } from '../data/RunContext'
import { presentationConfig } from '../presentation.config'
import { Hero } from '../sections/Hero/Hero'
import { Pipeline } from '../sections/Pipeline/Pipeline'
import { GraphExplorer } from '../sections/Graph/GraphExplorer'
import { Hypotheses } from '../sections/Hypotheses/Hypotheses'
import { Portfolio } from '../sections/Portfolio/Portfolio'

const W = 1920
const H = 1080

function useStageScale(): number {
  const [scale, setScale] = useState(() => Math.min(window.innerWidth / W, window.innerHeight / H))
  useEffect(() => {
    const onResize = () => setScale(Math.min(window.innerWidth / W, window.innerHeight / H))
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])
  return scale
}

/**
 * Locked 1920×1080 stage. Each step is a fresh mount (keyed by step + playToken), so its GSAP
 * timeline plays from zero on entry and on `R`. Nothing here reflows with the window.
 */
export function PresentationStage() {
  const { step, playToken } = usePresentation()
  const { run } = useAppData()
  const scale = useStageScale()
  const featured = useMemo(() => {
    const id = presentationConfig.featuredHypothesisId
    return id && run.hypotheses.some((h) => h.id === id) ? id : run.featuredHypothesisId
  }, [run])

  const key = `${run.id}-${step}-${playToken}`
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
    <div className={styles.root} aria-label="Presentation">
      <div className={styles.stage} style={{ transform: `translate(-50%, -50%) scale(${scale})` }}>
        {content}
      </div>
    </div>
  )
}
