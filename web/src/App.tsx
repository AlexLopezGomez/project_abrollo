import { RunProvider } from './data/RunContext'
import { PresentationProvider, usePresentation } from './presentation/PresentationContext'
import { PresentationStage } from './presentation/PresentationStage'
import { Nav } from './components/Nav'
import { Hero } from './sections/Hero/Hero'
import { Portfolio } from './sections/Portfolio/Portfolio'
import { Hypotheses } from './sections/Hypotheses/Hypotheses'
import { GraphExplorer } from './sections/Graph/GraphExplorer'
import { Pipeline } from './sections/Pipeline/Pipeline'
import { History } from './sections/History/History'
import { GraphSelectionProvider } from './state/GraphSelection'

function Loading() {
  return (
    <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', fontFamily: 'var(--font-mono)', color: 'var(--muted)' }}>
      loading artifacts…
    </div>
  )
}

function Page() {
  const { active } = usePresentation()
  if (active) return <PresentationStage />
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <Pipeline />
        <GraphExplorer />
        <Hypotheses />
        <Portfolio />
        <History />
      </main>
    </>
  )
}

export default function App() {
  return (
    <RunProvider fallback={<Loading />}>
      <PresentationProvider>
        <GraphSelectionProvider>
          <Page />
        </GraphSelectionProvider>
        <div className="vignette" />
        <div className="grain" />
      </PresentationProvider>
    </RunProvider>
  )
}
