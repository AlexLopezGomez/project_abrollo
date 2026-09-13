import { RunProvider } from './data/RunContext'
import { PresentationProvider } from './presentation/PresentationContext'
import { Nav } from './components/Nav'
import { Hero } from './sections/Hero/Hero'

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
        <Nav />
        <main>
          <Hero />
        </main>
        <div className="vignette" />
        <div className="grain" />
      </PresentationProvider>
    </RunProvider>
  )
}
