/**
 * screenshots — captures every page section at 1920×1080 and every presentation step in both stage formats
 * (wide 1920×1080, square 1080×1064) into web/screenshots/.
 *
 * Usage: pnpm build && pnpm screenshots        (serves dist/ with vite preview on a free port)
 *        BASE_URL=http://localhost:5173 pnpm screenshots   (use an already running server, e.g. pnpm dev)
 *
 * Requires Playwright's Chromium: pnpm exec playwright install chromium
 */
import { spawn, type ChildProcess } from 'node:child_process'
import { existsSync, mkdirSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, type Page } from 'playwright'
import { STAGE_SIZES, type StageFormat } from '../src/presentation.config'

const HERE = dirname(fileURLToPath(import.meta.url))
const WEB = resolve(HERE, '..')
const OUT = join(WEB, 'screenshots')
const PORT = 4179

const SECTIONS = ['hero', 'pipeline', 'graph', 'hypotheses', 'portfolio', 'history'] as const
const STEP_NAMES = ['1-hero', '2-pipeline', '3-graph-propagation', '4-hypothesis', '5-portfolio'] as const

async function waitFor(url: string, ms: number): Promise<boolean> {
  const t0 = Date.now()
  while (Date.now() - t0 < ms) {
    try {
      const res = await fetch(url)
      if (res.ok) return true
    } catch {
      /* not up yet */
    }
    await new Promise((r) => setTimeout(r, 250))
  }
  return false
}

function startPreview(): ChildProcess {
  if (!existsSync(join(WEB, 'dist', 'index.html'))) {
    throw new Error('dist/ not found — run `pnpm build` first (or set BASE_URL to a running dev server)')
  }
  const child = spawn('pnpm', ['exec', 'vite', 'preview', '--port', String(PORT), '--strictPort'], { cwd: WEB, stdio: 'ignore' })
  return child
}

async function settle(page: Page, ms: number) {
  await page.waitForTimeout(ms)
}

async function main() {
  let base = process.env.BASE_URL
  let child: ChildProcess | null = null
  if (!base) {
    child = startPreview()
    base = `http://localhost:${PORT}`
    if (!(await waitFor(base, 15_000))) throw new Error('preview server did not start')
  }
  mkdirSync(OUT, { recursive: true })

  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 })
  const errors: string[] = []
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push(m.text())
  })
  page.on('pageerror', (e) => errors.push(e.message))

  // --- page sections --------------------------------------------------------
  await page.goto(`${base}/`, { waitUntil: 'networkidle' })
  await settle(page, 800)
  for (const id of SECTIONS) {
    await page.evaluate((sel) => {
      document.documentElement.classList.add('no-smooth')
      document.getElementById(sel)?.scrollIntoView({ block: 'start' })
    }, id)
    await settle(page, 4500)
    await page.screenshot({ path: join(OUT, `section-${id}.png`) })
    console.log(`section-${id}.png`)
  }

  // graph with the featured propagation played to the end (`?hyp=featured` resolves to presentation.config / most affected)
  await page.goto(`${base}/?hyp=featured`, { waitUntil: 'networkidle' })
  await page.evaluate(() => {
    document.documentElement.classList.add('no-smooth')
    document.getElementById('graph')?.scrollIntoView({ block: 'start' })
  })
  await settle(page, 7500)
  await page.screenshot({ path: join(OUT, 'section-graph-propagation.png') })
  console.log('section-graph-propagation.png')

  // --- presentation steps, one viewport per stage format ------------------
  for (const format of Object.keys(STAGE_SIZES) as StageFormat[]) {
    await page.setViewportSize(STAGE_SIZES[format])
    const prefix = format === 'wide' ? 'presentation' : `presentation-${format}`
    for (let i = 0; i < STEP_NAMES.length; i++) {
      await page.goto(`${base}/?present=1&step=${i + 1}&stage=${format}`, { waitUntil: 'networkidle' })
      await settle(page, i === 2 ? 7500 : 5500)
      await page.screenshot({ path: join(OUT, `${prefix}-${STEP_NAMES[i]}.png`) })
      console.log(`${prefix}-${STEP_NAMES[i]}.png`)
    }
  }

  await browser.close()
  child?.kill()
  if (errors.length) {
    console.error(`\n${errors.length} console error(s):\n${errors.join('\n')}`)
    process.exitCode = 1
  } else {
    console.log('\nno console errors')
  }
}

main().catch((e: unknown) => {
  console.error(e)
  process.exit(1)
})
