# CDL26 — formulario de envío (Oxford Abstracts)

Límites del formulario en **palabras**: Title 20 · Outline 500 · Bio 250. Los `[corchetes]` son huecos que tenéis que rellenar.

---

## Title (≤ 20 palabras)

Monte Carlo Cathedral: LLMs read, graphs reason, math decides — a citable, lookahead-proof portfolio agent

---

## Outline (≤ 500 palabras)

**The problem.** Ask an LLM to build a portfolio and it will do it with confidence and no accountability. It cannot model correlations between holdings, it produces a point answer instead of a distribution, and it will happily lean on a news article dated after your cutoff without noticing. That last failure is the one that matters: if you cannot prove which facts a decision rested on, and when those facts were known, the decision is not defensible.

**What we built.** For the Cala AI Challenge (April 2026) we were given $1M of virtual capital, a NASDAQ universe, and a hard rule: build an agent that allocates the money, then evaluate it a year later on prices the agent never saw. Most teams built LLM swarms debating stocks. We inverted the roles.

- **LLMs only read.** Claude agents query Cala, a verified entity graph (companies, people, regulators, filings — every fact with a source UUID and a date) and emit structured causal hypotheses: trigger, probability, magnitude, and the entity sources they rest on. No opinions, no allocation.
- **The graph carries structure.** Each hypothesis lands on its origin entity and propagates along real relationships to the NASDAQ-100 companies it touches, decaying per hop. One claim about Vanguard's fee war fans out to 71 tickers. Cross-sector correlation lives in the edges, not in a model's head.
- **Math decides.** A Monte Carlo over the whole graph simulates hundreds of complete years of the world; a convex CVaR optimizer picks the portfolio that holds up in the worst 5% of them.

**The part we most want to discuss at CDL:** the knowledge graph is the anti-lookahead firewall. Every hypothesis must cite entities whose source dates fall before the cutoff, or it is mechanically rejected. Every dollar in the final portfolio traces back — weight, scenario, edge, hypothesis, UUID, date. You can audit it.

**Impact and honesty.** The submission returned +55.4% on the $1M over the evaluation year [vs. X% for the S&P benchmark]. It is a hackathon result: virtual money, one window, and priors that are still LLM-generated — that is the weak spot and we will show what we did about it (multi-source citations, bounded probabilities, an allow-list of dates pulled from the graph itself). What we claim is the pattern, not the alpha: LLMs as readers, graphs as the reasoning and provenance substrate, classical math as the judge. It applies to any decision that must be explained after the fact — credit, procurement, risk, policy.

**Audience.** Edges track: business and technical, intermediate. Background: knowledge graphs and LLM agents, conceptually. No finance required; the finance is the excuse, the graph is the point.

**What attendees take away.** A concrete architecture for LLM + graph systems where the graph enforces provenance instead of just storing it; a working example of temporal cutoffs as a graph constraint; a candid account of what broke; and the open-source pipeline to take home.

**Video (speaker preview, 9:16, < 3 min):** [ENLACE PÚBLICO]

---

## Speakers and affiliations

| | First | Last | Presenting | Email | Institution | City | Country |
|---|---|---|---|---|---|---|---|
| 1 | Alex | [apellido] | **Yes** | alex@optimizalo.es | [Optimizalo / Abrollo] | Barcelona | Spain |
| 2 | Nico | [apellido] | No | [email] | [institución] | [ciudad] | Spain |
| 3 | Carlos | [apellido] | No | [email] | [institución] | [ciudad] | Spain |

Headshot obligatorio para cada uno.

---

## Speaker Bio & Additional Information (≤ 250 palabras)

**Alex [apellido]** — [rol, p. ej. founder at Optimizalo, where he builds …]. On Abrollo he owned the pipeline architecture, the CVaR optimizer and the interactive presentation. [1 línea de background: años, sector, algo concreto que hayas construido.]

**Nico [apellido]** — [rol]. On Abrollo he owned [las hipótesis / los agentes Claude / la integración con Cala]. [1 línea de background.]

**Carlos [apellido]** — [rol]. On Abrollo he owned [el grafo causal y la propagación / el Monte Carlo]. [1 línea de background.]

**Speaking experience.** [Enlaces a charlas previas, meetups, podcasts. Si no hay ninguna grabada, decidlo tal cual: "No recorded conference talks yet; the 3-minute video is our sample."]

**Why CDL26.** We built this because the LLM-only approach to decisions felt wrong and the graph was the piece that made it defensible. CDL is the one room where people will care more about the provenance edges than about the return number, and we want that conversation — including the parts that did not work.

**Links.** [LinkedIn Alex] · [LinkedIn Nico] · [LinkedIn Carlos] · GitHub: https://github.com/AlexLopezGomez/project_abrollo · [web app desplegada, si la publicáis]

---

## Resto del formulario

- **Permission & Approval:** marcar (los tres tenéis que estar de acuerdo en asistir).
- **Submission Type:** Presentation
- **Categories:** Knowledge Graphs
- **Presentation Track:** Edges track
- **Masterclass description:** vacío
