import { RunProvider } from './data/RunContext'
import { PresentationProvider } from './presentation/PresentationContext'
import { Nav } from './components/Nav'
import { Hero } from './sections/Hero/Hero'
import { Portfolio } from './sections/Portfolio/Portfolio'
import { Hypotheses } from './sections/Hypotheses/Hypotheses'
import { GraphExplorer } from './sections/Graph/GraphExplorer'
import { GraphSelectionProvider } from './state/GraphSelection'

function Loading() {
  return (
    <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', fontFamily: 'var(--font-mono)', color: 'var(--muted)' }}>
      loading artifacts…
    </div>
  )
}

export default function App() {
  return (
    <RunProvider fallback={<Loading />}>
      <PresentationProvider>
        <GraphSelectionProvider>
          <Nav />
          <main>
            <Hero />
            <GraphExplorer />
            <Hypotheses />
            <Portfolio />
          </main>
        </GraphSelectionProvider>
        <div className="vignette" />
        <div className="grain" />
      </PresentationProvider>
    </RunProvider>
  )
}
