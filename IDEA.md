Monte Carlo Cathedral — Project Brief
Context
The hackathon: Cala AI Challenge at Project Barcelona, April 15-16, 2026 (running now). Sponsored by Cala.ai. Team name: Abrollo (members: Alex, Nico, Carlos). Venue: Itnig / Norrsken House Barcelona.
The challenge in one paragraph: Each team gets $1,000,000 of virtual capital and must build an AI agent that constructs a portfolio of 50+ NASDAQ stocks. Purchase prices are locked at the April 15, 2025 close. The portfolio is evaluated against today's prices (April 15, 2026) — a one-year hindsight window. The leaderboard ranks teams by portfolio value; SPY buy-and-hold is the benchmark to beat. Critical constraint: the agent must not use any market data or news events dated after April 15, 2025 (no lookahead bias). Scoring is 50% leaderboard rank + 50% qualitative judgment of the agent's reasoning, citation discipline, and articulation of why each stock was chosen.
What Cala is (do not confuse this): Cala is a verified entity graph — a queryable knowledge substrate where companies, people, products, research papers, laws, and places are typed entities with structured fields, relationships, and numerical observations. Every fact carries a source UUID and timestamp. It exposes:

entity_search — find an entity by name
entity_introspection — discover queryable fields/relationships for an entity UUID
retrieve_entity — fetch specific properties, relationships, numerical observations for a UUID
knowledge_query — deterministic dot-notation queries (companies.sector=Technology.employee_count>5000)
knowledge_search — natural-language semantic search with synthesized + cited answers
triggers — webhooks that fire on entity changes
MCP integration (https://api.cala.ai/mcp/)

Cala is not a web search API, not a scraper, not a stock data provider. It's a substrate of verified, time-stamped, source-traceable facts that agents call as a tool.
The submission endpoint: POST https://different-cormorant-663.convex.site/api/submit with team_id, model_agent_name, model_agent_version, and a transactions array. Server fetches April 15, 2025 close prices, computes share counts, and evaluates against today's prices.
Submission rules (server-enforced, hard):

≥50 distinct NASDAQ tickers (case-insensitive)
Total = exactly $1,000,000
Min $5,000 per ticker
No duplicates
Resubmissions allowed (iterate freely)


The Approach We Chose: Monte Carlo Cathedral
The contrarian thesis
The naive approach — what ~80% of teams will build — is "swarm of LLM agents debate each stock using Cala data, then a Judge agent allocates capital." This collapses into vibes-based scoring with extra steps. LLMs are bad judges of markets (not what they train on), don't model correlations between holdings, and don't produce uncertainty distributions.
Our inversion:

LLMs do what they're good at: read unstructured text from Cala and emit structured causal hypotheses with citations.
Math does what it's good at: propagate probabilities through a causal graph, simulate thousands of futures, optimize portfolios under uncertainty.
Correlations are explicit in the graph structure, not implicit in an LLM's brain.
Output is a distribution of outcomes, not a point prediction.

The frame: we're not predicting which stocks will win. We're enumerating plausible 12-month futures and choosing the portfolio that survives well across the distribution — especially in the tail. This is RAND-style war-gaming applied to capital allocation.
Why this wins both halves of scoring

Leaderboard half: CVaR-optimized portfolios systematically avoid concentration in correlated risks. Even if expected return is unspectacular, tail-risk reduction historically adds 100-300bps over equal-weight in adversarial windows.
Qualitative half: Every weight in the final portfolio is traceable backward through (optimizer → simulated scenarios → bayesian graph edges → hypotheses → Cala UUIDs with dates). The "no post-cutoff data" constraint becomes a mechanical guarantee rather than an honor system, because every hypothesis must cite a Cala source dated ≤ April 15, 2025.


Architecture (4 stages)
Stage 1 — Agent Swarm (parallel, ~2-3 min)
~30 specialist LLM agents run in parallel, one per domain (semiconductors, biotech, consumer tech, fintech, cloud, regulatory, supply chain, talent flow, geopolitics, energy, etc.). Each agent independently:

Queries Cala for the entities relevant to its domain (NASDAQ companies in its sector, plus relevant non-company entities like regulatory bodies, suppliers, key people).
Uses entity_introspection + retrieve_entity to gather structured facts.
Receives a strict prompt asking for ~10 structured causal hypotheses as JSON, each citing the Cala source UUIDs that support it.

Output schema per hypothesis:
json{
  "id": "H_0247",
  "trigger": "TSMC reduces N3 capacity in Q3 2025",
  "trigger_probability": 0.18,
  "effect_target": "NVDA",
  "effect_magnitude": -0.08,
  "effect_type": "gross_margin_delta",
  "sources": ["uuid-tsmc-capex-2024", "uuid-nvda-supplier-disclosure-q4"],
  "source_dates": ["2024-11-12", "2025-02-08"]
}
The agents do not talk to each other and do not make portfolio decisions. They emit hypotheses and shut down. Total output: a pool of ~300 hypotheses dumped to a table.
Critical: every hypothesis must validate that its source_dates are all ≤ 2025-04-15. Reject any hypothesis that fails this check. This is the lookahead-bias firewall.
Stage 2 — Bayesian DAG Construction (single-pass, ~30 sec)
A classical script (zero LLMs) takes the ~300 hypotheses and assembles one unified Bayesian network using pgmpy or equivalent. Structure:

Root nodes (top of DAG): world events (TSMC outage, FDA ruling, Fed rate hike, election outcome, named M&A approvals). ~50 root nodes typical.
Intermediate nodes: mechanism nodes ("global chip supply -15%", "biotech sector sentiment shift").
Leaf nodes (bottom): ~100 NASDAQ companies. Each leaf carries a return distribution conditioned on its parents.

Hypotheses contribute either nodes or edges with conditional probabilities. Deduplication step: merge hypotheses that reference the same trigger/effect pair, weighting by source quality.
Why one unified graph and not one per sector: cross-sector correlations are where the real alpha lives. A rate hike hits fintech, leveraged biotechs, and consumer tech simultaneously. Sector-isolated graphs would miss this.
Stage 3 — Monte Carlo Simulation (single run, ~5-10 min)
Key insight to internalize: Monte Carlo runs once on the entire graph, not once per hypothesis or once per sector. Each iteration is a complete simulated year of the world.
For iteration i in 1..10,000:
  1. Sample every root node according to its prior probability
     (TSMC outage? Roll dice with p=0.18 → outcome)
  2. Propagate consequences through the graph using the conditional
     probabilities on each edge (standard Bayesian inference)
  3. Compute resulting return for each of the ~100 leaf companies
  4. Store the 100-vector of returns for this iteration

Output: a matrix of shape (10_000, 100) — 10K scenarios × 100 stocks
This matrix is the distribution of futures. Each row is one possible 2025-2026.
For the wedge version: 1,000 iterations and 50 hypotheses are sufficient for the distribution to stabilize visually.
Stage 4 — CVaR Portfolio Optimization (single solve, ~10 sec)
Feed the (10K × 100) matrix to a classical convex optimizer (cvxpy). No LLMs, no Cala, no agents. Pure linear programming.
Objective: maximize E[return] - λ · CVaR₅%[loss]

E[return] = mean return across all 10K scenarios
CVaR₅% = mean loss in the worst 5% of scenarios
λ = risk aversion parameter (start at 2.0, tune)

Constraints (must match submission rules exactly):

sum(weights) == 1_000_000
weights[i] == 0 OR weights[i] >= 5_000 (mixed-integer; can relax to ≥5000 with binary inclusion vars)
count(weights > 0) >= 50
All weights ≥ 0 (long-only)

Output: a vector of 50+ weights. That's the submission.

Common Confusions (Hard-Won)
Confusion 1: "Is Monte Carlo run per hypothesis?" No. Hypotheses are components of the graph. The Monte Carlo runs over the entire graph, sampling all hypotheses simultaneously per iteration.
Confusion 2: "Does each agent run its own Monte Carlo and then we average?" No — that destroys cross-sector correlations. The unified graph + single Monte Carlo is the entire point. Per-agent simulations would be no better than the naive consensus approach we're rejecting.
Confusion 3: "Where do conditional probabilities come from if we don't have historical data?" From the LLM agents' hypothesis emissions. This is the biggest weakness — priors are LLM-generated. Mitigations: (a) require every hypothesis to cite ≥2 Cala sources, (b) sanity-bound probabilities into [0.05, 0.95], (c) for high-impact root nodes, use a second-pass agent to triangulate the probability against multiple Cala-citable analog events.
Confusion 4: "Won't the optimizer just converge to SPY?" Possibly, if the graph captures only market-wide correlations. Counter: explicitly include idiosyncratic hypotheses (M&A, FDA, key-person events) which create dispersion between stocks. If the demo portfolio looks like SPY, the graph is too coarse and we need more idiosyncratic hypotheses.

Tech Stack

Language: Python 3.11
Agent framework: Direct Anthropic SDK calls with claude-sonnet-4-6. No LangGraph/CrewAI/AutoGen — they add complexity for no value here. Parallelize with asyncio.gather().
Cala access: REST API directly (X-API-KEY header). MCP only if it noticeably accelerates iteration; not required.
Bayesian network: pgmpy for the DAG and CPDs.
Monte Carlo: custom numpy loop (faster than pgmpy's built-in samplers for this volume).
Optimizer: cvxpy with ECOS or SCS solver.
Visualization (for the demo): pyvis or d3.js for the DAG, matplotlib/plotly for the histogram, all rendered to a static HTML page or simple Streamlit app.
Storage: flat JSON files for hypotheses + scenarios. No database. Hackathon scope.


Hackathon Scope: Wedge MVP (must ship)
Cut ruthlessly to ship by submission deadline:

5 agents, not 30. Sectors: semiconductors, biotech, consumer tech, fintech, cloud infrastructure.
50 hypotheses total (10 per agent).
Bayesian DAG hand-curated from the 50 hypotheses using pgmpy. Don't auto-infer structure — humans encode the parent-child relationships in ~1 hour.
1,000 Monte Carlo simulations, not 10,000. Distribution stabilizes; runtime drops to seconds.
Universe = NASDAQ-100 only. Smaller, tractable, well-covered by Cala.
CVaR optimization with hardcoded λ=2.0.
Submit early, resubmit often. First submission can be naive equal-weight NASDAQ-100 within 2 hours of starting, just to lock a leaderboard position. Iterate from there.

Stretch goals (only if MVP ships clean)

Scale to 30 agents
10K simulations
Auto-construct DAG structure from hypothesis overlap
Web demo with live DAG animation + collapsing histogram
A "transcript" page per holding (which hypotheses contributed, which Cala sources)


The Demo (60 seconds, what judges see)
Three panels side-by-side:

Left: scrolling log of agents emitting structured hypotheses with visible Cala UUID citations. Judge sees: "no opinions, only cited assertions."
Center: Bayesian DAG materializing — root event nodes at top, company leaves at bottom, edges thickening as hypotheses consolidate. Judge sees: "structure emerging from chaos."
Right: a histogram of 10K simulated portfolio values. Initially wide and flat (high uncertainty). As the optimizer converges, the distribution narrows and shifts right. Judge literally sees risk being squeezed out.

Closing line: "We didn't pick stocks. We picked a shape of uncertainty we're comfortable living with for 12 months."

Failure Modes (Be Honest)

Industrial GIGO. If LLM-generated probabilities are garbage, the entire mathematical apparatus is theater. Hypothesis priors are the weakest link. Mitigation: require multi-source citations, cap extreme probabilities, manual spot-check of 10% of hypotheses.
Engineering overrun. 30 agents + DAG + 10K sims + optimizer + demo viz in a weekend is genuinely tight. Wedge scope is non-negotiable.
Convergence to SPY. If the graph mostly captures market beta, the CVaR-optimal portfolio looks like the index. Mitigation: explicitly seed idiosyncratic-event hypotheses.
Histogram doesn't move judges. Humans feel transcripts and stories more than statistical distributions. Mitigation: also produce a "memo per holding" page that traces weight back through the pipeline to specific Cala citations — rip the artifact strategy from the abandoned "Oracle's Receipt" idea.
Lookahead leakage. A single hypothesis citing a post-cutoff source poisons the submission's qualitative score. Mitigation: hard validator on every hypothesis (assert all(d <= "2025-04-15" for d in source_dates)).