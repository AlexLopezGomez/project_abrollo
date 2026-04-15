# Scenario Cathedral — Project Brief

## Context

Hackathon: Cala AI Challenge, Project Barcelona, April 15-16, 2026.
Team: Abrollo (Alex, Nico, Carlos). Venue: Itnig / Norrsken House Barcelona.

**The challenge:** $1,000,000 virtual capital → build an AI agent that constructs a portfolio of 50+ NASDAQ stocks. Purchase prices locked at April 15, 2025 close. Evaluated against today's prices (April 15, 2026). 50% leaderboard rank + 50% qualitative judgment (reasoning, citations, no lookahead bias).

**Submission rules (hard):** ≥50 tickers, total = exactly $1,000,000, min $5,000 per ticker, no duplicates, resubmissions allowed.

**Submission endpoint:** POST https://different-cormorant-663.convex.site/api/submit

---

## The Idea in One Sentence

We don't pick stocks. We generate plausible futures of the world and let a mathematical optimizer pick the portfolio that survives well across all of them.

---

## Why This Beats the Naive Approach

| What most teams will build | What we build |
|---|---|
| LLMs debate which stocks to buy | LLMs generate world hypotheses and evaluate scenarios |
| A "judge" LLM decides weights | A math optimizer decides weights |
| No cross-sector correlations | Scenarios capture how events interact across sectors |
| Output: an opinion | Output: a distribution of 1,000 evaluated futures |
| "Buy NVIDIA because AI is hot" | "NVIDIA has weight X because it survives well across 1,000 world scenarios" |

The key insight: LLMs are bad at picking stocks but good at reasoning about what might happen in the world and how events affect companies. Math is good at optimizing under uncertainty. We use each for what it's good at.

---

## Architecture: 4 Layers

```
Cala API (verified company data + macro context)
       ↓
LAYER 1 — Hypothesis Generation (LLM + Cala)
  150 binary macro-hypotheses about the world
       ↓
LAYER 1.5 — Scenario Construction (LLM)
  1,000 world-scenarios (combinations of hypotheses)
       ↓
LAYER 2 — Holistic Impact Evaluation (LLM)
  For each scenario: how does it affect each of 100 stocks?
  (not additive — the LLM reasons about interactions)
       ↓
OPTIMIZER (cvxpy, zero LLMs)
  CVaR optimization → portfolio weights → submit
```

LLMs appear in layers 1, 1.5, and 2. After that, pure math. No Monte Carlo, no Bayesian DAG — the LLM handles the cross-hypothesis interactions directly through holistic scenario evaluation.

---

## Layer 1: Hypothesis Generation

### Goal
Produce 150 structured, binary, macro-level hypotheses about events that could happen between April 2025 and April 2026. Every hypothesis cites Cala sources dated ≤ 2025-04-15.

### Step 1.1 — Gather company data from Cala (parallel)

```
# Get the NASDAQ universe
POST https://api.cala.ai/v1/knowledge/search
{"input": "List all NASDAQ-100 companies"}

# For each company UUID (all in parallel, ~100 calls):
GET  https://api.cala.ai/v1/entities/{uuid}/introspection
POST https://api.cala.ai/v1/entities/{uuid}
{
  "properties": ["name", "sector", "employee_count", "registered_address"],
  "relationships": {
    "incoming": {"IS_CEO_OF": {}, "IS_BOARD_MEMBER_OF": {"limit": 5}},
    "outgoing": {"IS_REGISTERED_IN": {}, "OPERATES_IN": {}}
  }
}
```

Output: structured JSON with data on ~100 NASDAQ companies.

### Step 1.2 — Gather macro context from Cala (parallel, runs simultaneously with 1.1)

```
POST https://api.cala.ai/v1/knowledge/search

Queries (all in parallel, ~12 calls):
{"input": "Major geopolitical risks affecting global markets in early 2025"}
{"input": "US Federal Reserve monetary policy outlook 2025"}
{"input": "Semiconductor supply chain risks and developments 2025"}
{"input": "AI regulation developments worldwide 2025"}
{"input": "Biotech FDA pipeline major drug approvals expected 2025"}
{"input": "Global energy market outlook and risks 2025"}
{"input": "US-China trade tensions and technology export controls 2025"}
{"input": "Major M&A activity and antitrust developments in tech 2025"}
{"input": "Consumer spending trends and inflation outlook 2025"}
{"input": "Cloud infrastructure and enterprise software market 2025"}
{"input": "Fintech regulation and digital payments landscape 2025"}
{"input": "Climate policy and ESG regulatory changes affecting public companies 2025"}
```

Output: rich text with cited sources about the state of the world as of April 2025.

### Step 1.3 — Generate hypotheses with LLM (parallel, 10 calls)

Each call covers a domain. All run in parallel. The LLM receives the Cala data from steps 1.1 and 1.2 as context.

**Domains (10 calls, ~15 hypotheses each = 150 total):**
1. Geopolitics & conflict
2. Monetary policy & central banks
3. Semiconductor & hardware supply chain
4. AI & software regulation
5. Biotech & pharma
6. Energy & commodities
7. Trade policy & tariffs
8. M&A & antitrust
9. Consumer & macro economy
10. Fintech & crypto regulation

### Prompt for Layer 1.3

```
You are a macro risk analyst. Based EXCLUSIVELY on the data provided below
(all sourced from before April 15, 2025), generate exactly 15 hypotheses
about events that could plausibly occur between April 2025 and April 2026.

DOMAIN: {domain_name}

RULES:
- Each hypothesis must be a BINARY event (it happens or it doesn't)
- Each hypothesis must be MACRO-LEVEL (affects multiple companies, not just one)
- Probability must be between 0.05 and 0.95
- Each hypothesis must cite at least 2 Cala source UUIDs that support it
- All source_dates must be ≤ 2025-04-15
- Hypotheses should range from likely (p>0.6) to unlikely but impactful (p<0.15)
- Include at least 2 "black swan" hypotheses (p<0.10, extreme consequences)
- Be SPECIFIC. Not "economy gets worse" but "US enters technical recession
  with 2 consecutive quarters of negative GDP growth"

COMPANY DATA:
{json_empresas}

MACRO CONTEXT FOR THIS DOMAIN:
{cala_macro_context}

OUTPUT FORMAT (JSON array):
[
  {
    "id": "H001",
    "hypothesis": "Federal Reserve cuts rates by 100+ basis points before Q1 2026",
    "probability": 0.30,
    "category": "{domain_name}",
    "rationale": "Fed minutes from January 2025 signal dovish pivot, inflation
                  trending toward 2.3% target, labor market showing signs of cooling",
    "sources": ["uuid-fed-minutes-jan2025", "uuid-inflation-report-q1"],
    "source_dates": ["2025-01-29", "2025-03-12"]
  },
  ...15 hypotheses
]
```

### Output of Layer 1
150 structured hypotheses in JSON, each with probability, rationale, category, and Cala source citations.

### Validation (automated, zero LLMs)
- Reject any hypothesis with source_dates > 2025-04-15 (lookahead firewall)
- Reject any with probability outside [0.05, 0.95]
- Reject any with fewer than 2 sources
- Deduplicate by semantic similarity (simple embedding comparison)

---

## Layer 1.5: Scenario Construction

### Goal
Combine the 150 hypotheses into 1,000 world-scenarios. Each scenario is a specific combination of hypotheses that are simultaneously active — a "version of the world."

### Prompt for Layer 1.5

Run 5 calls in parallel, each generating 200 scenarios of a specific type.

```
You are a scenario planner. Given the 150 hypotheses below, construct
exactly 200 plausible world-scenarios. Each scenario is a combination
of hypotheses that could realistically co-occur.

SCENARIO TYPE FOR THIS BATCH: {type}
  - "base_case": mostly high-probability hypotheses, stable world
  - "optimistic": growth-friendly combinations
  - "pessimistic": recession/crisis combinations
  - "black_swan": low-probability but high-impact combinations
  - "mixed": surprising combinations that cross categories

RULES:
- Each scenario activates between 5 and 40 hypotheses
- Consider LOGICAL COHERENCE: if "Fed cuts rates aggressively" is active,
  "Fed raises rates" should NOT be active in the same scenario
- Calculate scenario probability as: product of p(active) × product of (1-p(inactive))
- Ensure DIVERSITY: every hypothesis must appear active in at least 15 scenarios
- Include scenarios where contradictory macro forces collide
  (e.g., geopolitical crisis + monetary easing + tech boom)

ALL HYPOTHESES:
{json_150_hypotheses}

OUTPUT FORMAT (JSON array):
[
  {
    "scenario_id": "S0001",
    "name": "Tech winter meets monetary easing",
    "description": "AI regulation hits hard across US and EU, semiconductor
                    crisis deepens, but Fed cuts aggressively to prevent recession.
                    Biotech thrives on cheap capital despite broader tech weakness.",
    "active_hypotheses": ["H003", "H012", "H015", "H027", "H041", "H058", ...],
    "probability": 0.00234,
    "type": "{type}"
  },
  ...200 scenarios
]
```

### Output of Layer 1.5
1,000 world-scenarios with their active hypotheses and probabilities.

---

## Layer 2: Holistic Impact Evaluation

### Goal
For each of the 1,000 scenarios, evaluate how the COMBINATION of active hypotheses affects each of the ~100 NASDAQ stocks. This is NOT additive — the LLM reasons about interactions between hypotheses holistically.

This is the most expensive layer: 1,000 LLM calls, run 50 concurrently.

### Prompt for Layer 2

```
You are a senior financial analyst. You are presented with a world-scenario
(a combination of events that all happen simultaneously) and a list of
~100 NASDAQ companies with their profiles.

Your job: estimate the 12-month return impact on each company, considering
ALL active hypotheses TOGETHER — not in isolation.

CRITICAL INSTRUCTIONS:
- Reason about INTERACTIONS between hypotheses before assigning numbers.
  Example: "semiconductor crisis" alone hits NVDA -18%, but if "Fed cuts
  rates" is also active, cheap capital partially offsets the damage → net -10%.
- Consider second-order effects: a chip shortage raises AAPL production
  costs, but if consumer spending is also weak, AAPL can't pass costs to
  consumers → double negative.
- Consider relative winners: in a crisis scenario, companies with strong
  balance sheets and no exposure to the crisis BENEFIT relatively.
- Returns should reflect the COMBINED world, not the sum of individual effects.
- Be precise. Use the company data to ground your estimates (sector, size,
  dependencies, geographic exposure, leadership).

SCENARIO:
{scenario}

ACTIVE HYPOTHESES IN THIS SCENARIO:
{details_of_each_active_hypothesis_with_cala_sources}

COMPANY PROFILES:
{json_company_data_from_cala}

OUTPUT FORMAT (JSON):
{
  "scenario_id": "S0001",
  "reasoning": "In this world, AI regulation and semiconductor crisis create
    a dual headwind for pure-play tech. However, aggressive Fed easing floods
    the market with cheap capital, which disproportionately benefits: (1) biotech
    with late-stage pipelines (cheap funding for trials), (2) fintech with
    lending exposure (rate-sensitive revenue), (3) defensive tech with strong
    cash positions (can acquire distressed competitors). The losers are
    capital-light tech companies that relied on AI hype for multiples —
    regulation deflates those premiums regardless of rates...",
  "impacts": [
    {
      "ticker": "NVDA",
      "return": -0.10,
      "reasoning": "Chip crisis hurts supply, AI regulation reduces datacenter
                    demand growth, but rate cuts support capex spending. Net negative
                    but less severe than chip crisis alone would suggest."
    },
    {
      "ticker": "AMGN",
      "return": 0.22,
      "reasoning": "Zero exposure to AI regulation or chip crisis. Rate cuts
                    make debt-funded acquisitions cheaper. Late-stage pipeline
                    benefits from cheaper trial financing."
    },
    ...~100 companies
  ]
}
```

### Output of Layer 2

A matrix of 1,000 scenarios × ~100 stocks, where each cell contains:
- A return estimate (float)
- A reasoning string (for the qualitative evaluation / demo)

Plus the probability of each scenario (from Layer 1.5).

```
              NVDA    AAPL    AMGN    XOM     PYPL    ... (100 cols)
S0001 (p=.002) -10%    -5%     +22%    +3%     +8%
S0002 (p=.011) +32%    +15%    +4%     -3%     +12%
S0003 (p=.000) -45%    -28%    +2%     +35%    -18%
...
S1000 (p=.008) +8%     +10%    +6%     +1%     +5%
```

---

## Optimizer: CVaR Portfolio Optimization

### Goal
Find the allocation of $1,000,000 across 50+ stocks that maximizes expected return while minimizing losses in the worst scenarios.

### Input
- Matrix: 1,000 scenarios × 100 stocks (return estimates)
- Vector: 1,000 scenario probabilities
- Constraints: ≥50 tickers, min $5,000 each, total = $1,000,000

### Method
Minimize: -E[return] + λ × CVaR₅%

Where:
- E[return] = probability-weighted mean return across all scenarios
- CVaR₅% = expected loss in the worst 5% of scenarios (by probability mass)
- λ = risk aversion parameter (start at 2.0, tune across iterations)

### Tech
cvxpy with ECOS or SCS solver. Runs in <1 second.

### Output
A vector of weights: which stocks get how many dollars. That's the submission.

---

## Execution: Parallelism & Timing

```
Layer 1.1 + 1.2 (Cala, all parallel):     ~30 sec
  150 introspections + 150 retrieves + 12 searches

Layer 1.3 (LLM × 10, all parallel):        ~8 sec
  10 domain calls generating 15 hypotheses each

Layer 1.5 (LLM × 5, all parallel):        ~10 sec
  5 scenario-type calls generating 200 scenarios each

Layer 2 (LLM × 1000, 50 concurrent):     ~100 sec
  1,000 scenario evaluations

Optimizer (cvxpy):                          ~1 sec
────────────────────────────────────────────────
Total per iteration:                      ~3 min
```

### Cost per iteration
~5M tokens → ~$20-25 (Sonnet pricing)

### Iteration loop
Each full pipeline run = 3 minutes. In a hackathon day we can run 20-30 iterations, each time improving:
- Hypothesis prompts (more specific, better grounded)
- Scenario diversity (different combinations)
- Impact evaluation quality (richer prompts)
- Optimizer lambda (more/less risk aversion)
- Cala data depth (more fields per company)

---

## Optimal Configuration

| Parameter | Value | Why |
|---|---|---|
| Hypotheses | 150 | Beyond ~200, LLM generates noise. 150 well-diversified across 10 domains covers the space. |
| Scenarios | 1,000 | Optimizer output stabilizes at ~800-1,000 scenarios. 200 is too few, 10,000 doesn't improve meaningfully. |
| Stocks | ~100 (NASDAQ-100) | Well-covered by Cala. Enough for 50+ final picks. |
| Concurrency | 50 | Practical API rate limit. |
| Optimizer λ | 2.0 (tune) | Start conservative, increase for more risk-seeking if leaderboard demands it. |

---

## Why This Wins Both Halves

**Leaderboard (50%):** The optimizer picks portfolios that are robust across 1,000 different futures. It doesn't bet on one prediction — it hedges across the distribution. Historically, CVaR-optimized portfolios add 100-300bps over naive approaches in uncertain periods.

**Qualitative (50%):** Every dollar in the portfolio traces back:
- Weight → optimizer chose it because it performed well across scenarios
- Scenarios → generated from combinations of hypotheses
- Hypotheses → each one cites Cala UUIDs with dates ≤ 2025-04-15
- The "no lookahead" constraint is mechanically enforced, not honor-system

The reasoning field in Layer 2 output gives judges a narrative for every stock in every scenario. No vibes. No "AI is the future." Just cited, structured, scenario-grounded reasoning.

---

## Failure Modes

1. **LLM impact estimates are garbage.** If the LLM can't reason well about how combined world events affect specific companies, the whole matrix is noise and the optimizer produces a random portfolio. Mitigation: invest in prompt quality for Layer 2, run multiple iterations with different prompts, compare outputs.

2. **Cala coverage gaps.** If Cala doesn't have rich data on certain NASDAQ companies, the hypotheses and evaluations for those companies will be shallow. Mitigation: check Cala coverage early, focus on well-covered companies.

3. **Convergence to SPY.** If scenarios are too generic (all capturing market beta, no idiosyncratic events), the optimizer produces index-like weights. Mitigation: ensure hypotheses include company-specific and sector-specific events, not just macro.

4. **Lookahead leakage.** A single hypothesis citing post-cutoff data poisons the qualitative score. Mitigation: automated validator rejects any source_date > 2025-04-15.

5. **Rate limits.** 1,000 concurrent LLM calls could hit Anthropic rate limits. Mitigation: throttle to 50 concurrent, total time still under 2 minutes for Layer 2.

---

## Tech Stack

- **Language:** Python 3.11
- **LLM:** Anthropic API (claude-sonnet-4-6), direct SDK calls
- **Parallelism:** asyncio.gather() with semaphore for concurrency control
- **Cala:** REST API (X-API-KEY header)
- **Optimizer:** cvxpy with ECOS solver
- **Storage:** flat JSON files (hypotheses.json, scenarios.json, impacts.json)
- **No:** pgmpy, numpy Monte Carlo, LangGraph, CrewAI, or any agent framework
