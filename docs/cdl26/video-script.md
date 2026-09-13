# CDL26 — guión del vídeo de 3 min (speaker preview, 9:16)

**Formato.** Vertical, móvil a la altura de los ojos, los tres en el mismo sitio (una mesa, un pasillo) y os vais
pasando el turno, no tres clips pegados. Subtítulos quemados (mucha gente lo verá sin sonido). Nadie lee: cada
bloque es una idea, decidla con vuestras palabras si os sale mejor.

**La app.** El CFP pide speaker preview, NO demo. La web app entra solo como cortes de 3–5 s (Presentation Mode
recortado a vertical): la tarjeta de hipótesis con la fecha en verde, y el grafo propagando desde Vanguard. En total
< 25 s de pantalla en todo el vídeo. Si dudáis, menos pantalla y más cara.

**Duración.** ~450 palabras habladas = 3:00 justos a ritmo normal. Si os pasáis, cortad las frases marcadas ✂.

---

## [0:00–0:18] ALEX — gancho
*(a cámara, sin "hola soy…", directo)*

> Last April the three of us were handed a million dollars. Virtual, sadly.
> The brief: build an AI agent that builds a NASDAQ portfolio — and here's the catch — it gets evaluated one year
> later, with prices the agent was never allowed to see.
> I'm Alex, that's Nico, that's Carlos. We're team Abrollo.

## [0:18–0:55] NICO — el problema
> Here's what almost every team did — and honestly, what we'd have done on day one: throw a swarm of LLMs at the
> stocks, let them argue, and have a "judge" model split the money.
> Sounds smart. It's vibes with extra steps. ✂
> Language models are bad judges of markets. They don't model correlations. And they will happily quote a news
> article from after the cutoff without noticing.
> So we asked a different question. Not "which stocks win?" — "which futures are plausible, and what survives most
> of them?"

## [0:55–1:45] CARLOS — lo que construimos
> We split the job by what each tool is actually good at.
> The LLMs only read. They query Cala — a verified entity graph: companies, people, regulators, every fact with a
> source ID and a date — and they emit hypotheses. Not opinions. Structured claims: trigger, probability, magnitude,
> citations.

*(corte 4 s: tarjeta de hipótesis, badges de fecha pasando a verde)*

> Then the graph takes over. Each hypothesis lands on an entity and propagates through its connections to the
> companies it actually touches. One claim about Vanguard's fee war fans out to seventy-one tickers.
> That's the part an LLM can't do in its head. ✂

*(corte 5 s: propagación del grafo en el modo presentación)*

> Then plain maths. Monte Carlo over the whole graph — five hundred simulated years — and a CVaR optimiser that
> picks the portfolio that holds up in the ugly tail.

## [1:45–2:15] ALEX — el grafo como firewall
> And the bit I actually want to talk about in London: the graph is our firewall against lookahead.
> Every hypothesis has to cite entities whose source dates are before April 15th, 2025. If it can't, it's rejected.
> Mechanically. No honour system.
> Every dollar in the final portfolio traces back: optimiser, scenario, edge, hypothesis, UUID, date. You can audit
> it.

## [2:15–2:40] NICO — resultado, con honestidad
> Result: plus fifty-five percent on the million, against an S&P benchmark of [X]. *(← rellenar)*
> Now — it's a hackathon. Virtual money, one window. We're not selling alpha.
> What we're showing is a pattern: LLMs as readers, graphs as the reasoning substrate, maths as the judge.
> And where it broke — because it did break — the priors are still LLM-generated. That's the honest weak spot, and
> we'll show you what we did about it.

## [2:40–3:00] CARLOS → ALEX → NICO — cierre
*(los tres en plano)*

> **CARLOS:** That's the talk. Edges track: enough graph to be useful, enough story to follow. We didn't pick
> stocks —
> **ALEX:** — we picked a shape of uncertainty we could live with for twelve months.
> **NICO:** See you in London.

---

## Antes de grabar
- [ ] Rellenar `[X]` con el retorno de SPY en la ventana 2025-04-15 → 2026-04-15 (y el puesto en el leaderboard si lo tenéis).
- [ ] Capturar en vertical los dos cortes (`pnpm dev` → `P` → paso 3 y paso 4) o recortar los PNG de `pnpm screenshots`.
- [ ] Una toma por bloque, no del tirón: se monta después y se nota menos el nervio.
- [ ] Subir a YouTube (no listado) o Vimeo y comprobar el enlace en incógnito.
