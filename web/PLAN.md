# Abrollo web app — plan

Target: a React + TypeScript + GSAP single-page app in `web/`, optimized for a 1920×1080 screen
recording of the story *knowledge graph → hypotheses → causal DAG → simulated futures → portfolio*.

**Read "Open questions" first — Q1 changes what number goes on camera.**

---

## 0. What the data actually contains (findings from inspection)

| Item | Brief says | Found |
|---|---|---|
| Submissions | 4 runs | **8** files in `data/submissions/` (1 MVP-1, 7 MVP-2). 5 of them have snapshots in `data/runs/<id>/` (manifest + hypotheses/dag/portfolio/submission/graph.gpickle). |
| Hero run `mvp2_run_20260428_090421` | $1,551,515 / +55.2% | That file is **$1,367,770 / +36.8%** (`jx72zp14…`). |
| README figure $1,551,515.14 / `jx704evq…` | the hero | **Not in `data/`** — it was the 2026-04-15 hackathon-day submission (see `docs/architecture/04-mvp-2-retro.md`); its JSON was never committed. Closest real run: `mvp2_run_20260425_174212` = **$1,554,039.86 / +55.4%** (`jx75j0f6…`), no snapshot. |
| Top-level `data/{hypotheses,dag,portfolios}/mvp2.json` | hero artifacts | They belong to the **last** run `mvp2_run_20260428_140843` ($1,385,531 / +38.6%) — identical to its snapshot; its transactions match `portfolios/mvp2.json` exactly. |
| `data/mvp2/graph.json` | ~2,400 / ~4,500 | 2,413 nodes / 4,458 edges, 98 NDX nodes, 7 components. All 10 origins present. Node: `{id,name,entity_type,is_ndx,tickers}`, edge `{src,dst,rel_type}`. |
| Run `graph.gpickle` (1,135 / 1,731) | "~1,100-node default subgraph" | The gpickle is a strict **subset** of `graph.json` (post-cutoff relationship filter). We won't read pickles; see Q2 for how the default view is sized. |
| BFS from origins | depth 1 / 2 toggle | Origins are hubs (Vanguard deg 75, BlackRock 68…). depth 1 + portfolio = **104 nodes / 338 edges**; depth 2 = **2,213 nodes / 4,151 edges** (≈ full graph). |
| `hypotheses/mvp2_100.json`, `mvp2_10.json` | list of 12 | Dicts (`{cutoff_date, requested_count, …, hypotheses: [...]}`) — not lists. Only used as alternates; the app reads them via the same normalizer. |
| `hypotheses/semi.json` (MVP-1) | list | Dict with `hypotheses` + `rejects`; items use `trigger_probability`, `effect_target`, `effect_magnitude`, no `origin_entity_uuid`. Normalize like the Python loader does. |
| `dag/mvp.json` (MVP-1) | JSON | It's a **text table of CPDs**, not JSON. MVP-1 DAG is derived from `effect_target` like `_dag_from_hypotheses`. |
| Monte Carlo size | "N scenarios" | `scenarios/mvp2_meta.json`: **500 sims × 98 tickers**. |
| Source dates | all ≤ 2025-04-15 | Verified for MVP-2 (max 2025-03-12). MVP-1 also ≤ cutoff. `mvp2/date_allowlist.json` has the 34-date allow-list → shown in the firewall gate. |
| DAG shifts | per-ticker | Uniform per hypothesis (magnitude × 0.6 decay, e.g. 0.072). Largest fan-out: **H_V2_02 Vanguard → 71 tickers (42 in portfolio)**. |

Toolchain: Node 26.7 present; **pnpm is not installed** (will `corepack enable pnpm`). `.venv` exists but the TS prep script will not depend on Python.

---

## 1. Data pipeline — `web/scripts/prepare-data.ts` (`pnpm prepare-data`, run with `tsx`)

Replicates `dashboard/components/data_loader.py`:

1. Glob `../data/submissions/{mvp,mvp2}_run_*.json`, parse `pipeline` + timestamp from filename.
2. For each run: if `../data/runs/<id>/manifest.json` exists → artifacts from that dir (`hypotheses.json`, `dag.json`, `portfolio.json`); else → `../data/{hypotheses,dag,portfolios}/{mvp|mvp2}.json` (legacy mapping, exactly like `ARTIFACTS` in Python). `graph.gpickle` is ignored; `data/mvp2/graph.json` is the entity graph for every run.
3. Normalize hypotheses (`probability|trigger_probability`, `magnitude|effect_magnitude`, `origin_entity_uuid|effect_target→NDX uuid`), normalize DAG rows, derive MVP-1 DAG from `effect_target`.
4. Compute per-ticker rows: amount, purchase price, eval price, shares, value, return; run totals; `isConsistent` flag (transactions == portfolio weights).
5. **Graph**: build adjacency, degree; compute for each run the node sets `focus` (origins d1 ∪ portfolio), `neighborhood` (origins d1 ∪ portfolio d1), `full`. Run **d3-force in Node with a seeded PRNG** and freeze `x,y` for every node of the full graph → layout is identical on every load (deterministic takes, zero simulation cost on the client). Per-hypothesis propagation paths (origin → affected ticker, direct edge or 2-hop via BFS) are precomputed so the animation never searches.
6. Write to `web/public/data/`:
   - `index.json` — runs list (id, pipeline, timestamp, submissionId, totals, return, counts, artifact source, consistency).
   - `runs/<id>.json` — hypotheses, dag, portfolio, tickers table, focus/neighborhood node-id lists, propagation paths, presentation featured hypothesis id.
   - `graph.json` — nodes with `{id,name,type,isNdx,tickers,degree,x,y}` + edges as index pairs (compact, ~300 KB).
   - `meta.json` — cutoff date, allow-list dates, MC sims/tickers, cov method, graph stats, top hubs.
7. `prepare-data` is idempotent and asserts the schemas (fails loudly if a file changes shape).

Client loads `index.json` + `graph.json` + the selected run's file; switching run swaps one JSON.

---

## 2. Stack decisions

- Vite 6 + React 18 + TS strict, pnpm, ESLint (typescript-eslint + react-hooks) + `tsc --noEmit` as `lint`/`typecheck`.
- **GSAP 3.13** + `@gsap/react` (`useGSAP({ scope })`, `contextSafe` for handlers). Plugins registered once in `src/lib/gsap.ts`: ScrollTrigger, Flip, SplitText, DrawSVGPlugin, MotionPathPlugin, ScrollToPlugin. `gsap.matchMedia()` with `(prefers-reduced-motion: reduce)` → durations 0 / timelines jump to end.
- **Graph: hand-rolled d3-force (prepare-time) + Canvas 2D + d3-zoom, with an SVG overlay for GSAP.** I considered `react-force-graph-2d` and sigma.js and recommend against both: (a) they re-simulate on mount, so the layout differs between takes unless every node is pinned, at which point the library adds nothing; (b) the GSAP overlay must stay pixel-locked to node positions through zoom/pan, which is trivial when we own the single `d3-zoom` transform and awkward through a wrapper; (c) 2.4k nodes / 4.5k edges of frozen positions draw in < 4 ms on Canvas, well under the 50 fps bar. Hover hit-testing via a `d3-quadtree`.
- Charts: **Recharts** (bar charts, timeline); the CVaR distribution illustration is hand-drawn SVG (so DrawSVG can animate the tail).
- Styling: **CSS Modules + `tokens.css`** (custom properties for the palette, type scale, spacing, 12-col grid). Fonts bundled via `@fontsource` (no runtime network): **Fraunces** (display serif) + **IBM Plex Mono** (`font-variant-numeric: tabular-nums`) + Inter for body. Minimum rendered size 14 px; numbers on camera ≥ 20 px.
- Screenshots: a `pnpm screenshots` script using **Playwright** (headless Chromium, 1920×1080) that visits each section anchor and each presentation step (`?present=1&step=n`, timelines fast-forwarded to their end) and writes `web/screenshots/*.png`. Adds a ~150 MB browser download as a dev dependency — see Q5.

---

## 3. Component tree

```
src/
  main.tsx, App.tsx
  lib/gsap.ts                 registerPlugin once; reducedMotion helper
  lib/format.ts               money / pct / uuid truncation
  data/schema.ts              TS types for every JSON
  data/loader.ts              fetch index/graph/run; RunProvider context (selected run)
  presentation.config.ts      featuredHypothesisId (default: most affected tickers), heroRunId, step timings
  App
  ├── RunProvider                       (selected run, data, switchRun)
  ├── PresentationProvider              (on/off, step, replay; keyboard: P ← → R, Esc)
  ├── Nav                               sticky; section links, run switcher, "Present" button
  ├── Grain                             fixed grain + vignette overlay (CSS only)
  ├── sections/
  │   ├── Hero                          count-up value, return, SplitText title, chips (copyable submission id)
  │   ├── Pipeline                      4 StageCards + Connector(SVG path, MotionPath dot) + FirewallGate(DrawSVG)
  │   ├── GraphExplorer
  │   │   ├── GraphCanvas               canvas draw loop, d3-zoom, quadtree hover, fit/zoom controls
  │   │   ├── GraphOverlay              SVG: highlight rings, propagation paths, ticker labels, shift badges
  │   │   ├── GraphControls             hypothesis selector, depth (Focus/Neighborhood/Full), search, fit
  │   │   ├── Inspector                 entity details, relationships (rel_type), hypotheses for origins,
  │   │   │                             weight chips (Flip target), propagation progress bar (scrub)
  │   │   └── usePropagationTimeline    builds the deterministic GSAP timeline for a hypothesis
  │   ├── Hypotheses
  │   │   ├── HypothesisFilters         min probability, direction, sort
  │   │   └── HypothesisCard            trigger, origin, P/M/H, CitationBlock, AffectedTickersBar, "Show in graph"
  │   ├── Portfolio
  │   │   ├── KpiRow                    return, value, invested, tickers
  │   │   ├── ReturnBars                sorted per-ticker returns (Recharts, green/red)
  │   │   ├── HoldingsTable             sortable
  │   │   └── CvarPanel                 alpha, CVaR5, E[r], λ, solver + DistributionSketch (SVG, labeled schematic)
  │   └── History                       8-run timeline (value + return), click = switch run
  └── presentation/
      ├── PresentationStage             fixed 16:9 stage scaled to the viewport (no reflow at any window size)
      ├── steps/ HeroStep, PipelineStep, GraphStep, HypothesisStep, PortfolioStep
      └── useStepTimeline               each step = one GSAP timeline; play on enter, R replays, ←/→ navigate
```

Sections and presentation steps share the same inner components; the step wrappers pass a `stage` prop
that fixes dimensions (1920×1080 grid) and disables hover chrome and scrollbars.

---

## 4. GSAP timeline map

| Where | Trigger | Timeline (all deterministic; durations in s) |
|---|---|---|
| Hero | on enter (ScrollTrigger once) / step 1 | SplitText title chars (0.9, stagger 0.02) → value count-up `gsap.to({v:0→total}, {duration:1.6, snap, ease:power2.out})` with tabular figures → return % fades in → chips stagger 0.06. |
| Pipeline | on enter / step 2 | stages `autoAlpha/x` stagger 0.25 left→right → dot travels the connector (MotionPath 1.4 s, 3 hops) → between stage 1 and 2 the firewall bars **DrawSVG 0→100%**, then checkmark DrawSVG + "34 dates ≤ 2025-04-15" label. Live numbers count up as each stage lands. |
| Graph propagation (money shot) | hypothesis select / "Show in graph" / step 3 | 0.0 origin ring pulses (scale 1→2.2, 2 beats) → 0.6 paths draw in sequence (DrawSVG, stagger by path length, total 1.8 s) → 2.2 affected NDX nodes scale up on the overlay, `shift` badge pops → 2.8 weight chips **Flip** from node position into the Inspector list → 3.6 end. Exposed via `tl.progress()` to a scrub bar; replay = `tl.restart()`. Canvas dims non-highlighted nodes in lockstep via a tweened `dim` value. |
| Hypotheses | on enter / step 4 | card slides up; citation rows stagger 0.08 with the date badge flipping to a green check (0.3 s each). |
| Portfolio | on enter / step 5 | KPI count-ups → return bars grow from 0 (stagger 0.01) → CVaR sketch: curve DrawSVG, then the 5 % tail shades in. |
| History | on enter | timeline dots + connector DrawSVG. |
| Sections | scroll | ScrollTrigger reveals only (`once: true`); no pinning, no parallax. |

Reduced motion: every timeline is built the same way, then `matchMedia` sets `timeScale` to ~1000 / calls `progress(1)`.

---

## 5. Presentation Mode

- Toggle: `P` key or nav button; `Esc` exits. Renders `PresentationStage` (`position: fixed; inset: 0; background: bg`), hides Nav, Grain stays, `cursor: none`, `overflow: hidden`, no hover tooltips.
- The stage is a 1920×1080 box centered and scaled with `transform: scale(min(vw/1920, vh/1080))` — no reflow, no layout shift for any window size; at a true 1920×1080 window scale = 1.
- Steps 1–5 as above; `←/→` navigate, `R` replays the current step, step index shown in the URL (`?present=1&step=3`) so a take can start at any step.
- `presentation.config.ts`: `heroRunId`, `featuredHypothesisId` (default = max `n_affected` → H_V2_02 Vanguard), `graphView` for step 3 (`neighborhood`), per-step durations.

---

## 6. Build order & commits

data prep → tokens/layout/Hero → Portfolio → Hypotheses → Graph explorer → Pipeline → History → Presentation Mode → screenshots + polish → README update. One conventional commit per step.

Definition of done as in the brief; I'll add `pnpm check` = typecheck + lint + build.

---

## Open questions

**Q1 — Which run is the hero, and what number goes on camera?** The `$1,551,515 / +55.2%` submission does not exist in `data/`. Options:
- **(A, recommended)** Hero = `mvp2_run_20260425_174212`: **$1,554,040 / +55.4%**, real, submitted (HTTP 200), same story as the README. It has no artifact snapshot, so hypotheses/DAG/CVaR figures come from the top-level `mvp2.json` files (which are run `…140843`'s), exactly as the Streamlit loader already does for legacy runs. The per-ticker returns and weights come from its own transactions, so the Portfolio section is fully truthful; the Hypotheses/Graph sections show "MVP-2 pipeline artifacts" with a small provenance label. I'd also fix the README table to these numbers.
- (B) Hero = `mvp2_run_20260428_140843`: **$1,385,531 / +38.6%** — the only run where submission, portfolio, hypotheses and DAG are all mutually consistent. Honest end-to-end, but the headline is +38.6%.
- (C) Hard-code the README's $1,551,515 with run 140843's artifacts — not backed by any file; I'd rather not.
`heroRunId` will be a config value either way, and the History section will show all 8 runs.

**Q2 — Default graph view.** Depth-1 BFS from origins is only ~104 nodes (too sparse to read as a "knowledge graph" on camera) and depth 2 is ~92 % of the full graph. I propose three views instead of a 1/2 toggle: **Focus** (origins d1 ∪ portfolio, 104 n / 338 e), **Neighborhood** (origins d1 ∪ portfolio d1, ~1,543 n / 3,329 e — default and used in presentation step 3) and **Full** (2,413 / 4,458). OK, or do you want the literal depth 1/2 toggle kept as well?

**Q3 — Pipeline "live numbers".** Stage 2's node/edge count: the manifests say 1,135 / 1,731 (the pipeline's cutoff-filtered DAG, from the gpickle we're not reading), `graph.json` says 2,413 / 4,458. I plan to show **hypotheses → affected tickers → propagation edges from `dag.json`** (e.g. 10 → 83 tickers, 197 edges) on stage 2 and the entity-graph size (2,413 / 4,458) in the graph section header. Stage 3 shows **500 scenarios × 98 tickers** (that's what `scenarios/mvp2_meta.json` says, not 1,000 or 10,000). Fine?

**Q4 — CVaR histogram: real or schematic?** `data/scenarios/mvp2.parquet` (500 × 98) can be read in the prep script with a pure-JS parquet reader (`hyparquet`) and dotted with the run's weights to plot the *actual* distribution of simulated portfolio returns for the mvp2 artifacts. Costs ~1 h. Default plan: schematic SVG labeled "illustrative"; say the word and I'll make it real.

**Q5 — Playwright as a dev dependency** for `pnpm screenshots` (downloads Chromium, ~150 MB). Alternative: I take the screenshots manually through the browser tooling and commit them. Playwright is reproducible for future takes; your call.

**Q6 — Nothing in `web/` may reach the network.** Fonts are bundled (`@fontsource`); confirm Fraunces + IBM Plex Mono + Inter is acceptable, or name the pair you prefer.
