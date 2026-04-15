# Abrollo — Monte Carlo Cathedral

**Hackathon:** Cala AI Challenge · Project Barcelona · 15–16 abril 2026
**Equipo:** Abrollo (Alex, Nico, Carlos)
**Estado actual:** MVP end-to-end funcionando, submission real aceptada por Convex, valor de cartera **+47.3 %** en la ventana 2025-04-15 → 2026-04-15.

Este README es el mapa de navegación del repo tal y como está ahora (commit `9f27a00`). Lee esto primero, luego ve al documento que necesites.

---

## 1. Qué hace este proyecto

Construimos una cartera de 50+ acciones del NASDAQ-100 a partir de **hipótesis causales con citas trazables a Cala**, no de "vibes" de un LLM.

El flujo completo (12 pasos) está en [`docs/architecture/01-mvp-plan.md`](docs/architecture/01-mvp-plan.md).

```
Cala (entidades + docs)
    ↓
Agente Sonnet 4.6 → 10 hipótesis causales en JSON estricto (con UUIDs y fechas ≤ 2025-04-15)
    ↓
DAG bayesiano hand-wired (pgmpy)
    ↓
Monte Carlo 1.000 iteraciones (numpy) → matriz (1000, 99) de retornos
    ↓
Optimizador CVaR (cvxpy, SCS)
    ↓
Validador de reglas → POST a Convex → leaderboard
```

**Tesis:** los LLM hacen lo que saben (leer texto y emitir estructura con citas). La matemática hace lo que sabe (propagar probabilidades, optimizar bajo incertidumbre). Las correlaciones entre empresas son **explícitas** en el grafo, no implícitas en el cerebro del LLM.

Detalles largos en [`IDEA.md`](IDEA.md) y [`docs/architecture/00-cto-design.md`](docs/architecture/00-cto-design.md).

---

## 2. Resultado del MVP (lee esto antes de cambiar nada)

12 de 12 gates verdes en el primer pase end-to-end. Submission real aceptada.

| Métrica | Valor |
|---|---|
| Cobertura NDX → UUID de Cala | 99 / 101 (fallos: AEP, CHTR) |
| Ratio de fuentes post-cutoff en perfiles | 116 / 123 (94 %) |
| Hipótesis generadas | 10 / 10 válidas, 0 rechazadas |
| Matriz Monte Carlo | (1000, 99) |
| Cartera final | 60 tickers, $1.000.000 exactos |
| Expected return del optimizador | +5.1 % |
| CVaR 5 % | −0.5 % |
| **Valor real a 2026-04-15** | **$1.473.435,33 (+47.3 %)** |
| `submission_id` | `jx7czbecp7106ezabxq50f79b984w0kb` |
| Coste Anthropic (1 llamada Sonnet 4.6) | ≈ $0.05 |

El **post-mortem completo** está en [`docs/architecture/02-mvp-retro.md`](docs/architecture/02-mvp-retro.md). Ahí están los 3 hallazgos críticos que hay que arreglar antes de escalar al Wedge.

---

## 3. Estructura del repo

```
project_abrollo/
├── IDEA.md                           # brief original del proyecto
├── README.md                         # este archivo
├── pyproject.toml                    # dependencias pinadas
├── .env                              # CALA_API_KEY + ANTHROPIC_API_KEY (gitignored)
├── .gitignore                        # oculta .env, .venv, .claude, data/
│
├── docs/architecture/
│   ├── 00-cto-design.md              # diseño macro (Wedge y Platform tiers)
│   ├── 01-mvp-plan.md                # plan de los 12 pasos del MVP
│   └── 02-mvp-retro.md               # retro post-ejecución
│
├── abrollo/                          # código de la aplicación
│   ├── config.py                     # constantes, carga de .env, rutas a /data
│   ├── cala/
│   │   ├── client.py                 # wrapper REST de Cala, 429 con backoff
│   │   ├── cutoff.py                 # filtro de lookahead ≤ 2025-04-15
│   │   └── ndx.py                    # fetch NASDAQ-100 desde Wikipedia + matcher
│   ├── agents/
│   │   ├── hypothesis.py             # schema pydantic + validador
│   │   └── semi_agent.py             # agente Sonnet 4.6 (sector semiconductores)
│   ├── dag/
│   │   └── mvp_dag.py                # 5 nodos: TSMC/EC → supply_delta → NVDA/AMD
│   ├── mc/
│   │   └── sim.py                    # 1.000 iteraciones de muestreo ancestral
│   ├── opt/
│   │   └── cvar.py                   # optimizador CVaR dos-fases
│   └── submit/
│       ├── validator.py              # 7 reglas de submission
│       └── client.py                 # POST a Convex
│
├── scripts/                          # un runner por paso del plan
│   ├── step1_smoke_test.py
│   ├── step2_resolve_ndx.py
│   ├── step3_introspect.py
│   ├── step4_semi_profiles.py
│   ├── step5_cutoff_test.py
│   ├── step6_semi_hypotheses.py
│   ├── step7_build_dag.py
│   ├── step8_mc.py
│   ├── step9_cvar.py
│   ├── step10_validate.py
│   └── step11_submit.py
│
└── data/                             # gitignored — todo se regenera
    ├── openapi.pinned.json
    ├── nasdaq100_uuids.json          # 99 hits, 2 misses
    ├── introspection_samples.json    # AAPL + NVDA
    ├── semi_profiles/*.json          # NVDA, AMD, INTC, QCOM, AVGO + _audit
    ├── hypotheses/semi.json          # 10 hipótesis validadas
    ├── dag/{mvp.pkl, mvp.json}
    ├── scenarios/{mvp.parquet, mvp_meta.json}
    ├── portfolios/mvp.json           # 60 tickers, $1M
    └── submissions/mvp_run_*.json    # historial de POSTs
```

---

## 4. Instalación (Windows + bash, Python 3.12)

### 4.1 Clonar y crear entorno

```bash
git clone https://github.com/AlexLopezGomez/project_abrollo.git
cd project_abrollo

# Crear venv y resolver dependencias con uv (recomendado)
uv venv --python 3.12
VIRTUAL_ENV="$PWD/.venv" uv pip install -e .

# Alternativa sin uv:
# python -m venv .venv
# .venv/Scripts/pip install -e .
```

### 4.2 Variables de entorno

Crea `.env` en la raíz con:

```
CALA_API_KEY=<tu-key-de-cala>
ANTHROPIC_API_KEY=<tu-key-de-anthropic>
```

`.env` está gitignored. No lo subas nunca.

### 4.3 Verificar instalación

```bash
.venv/Scripts/python.exe -m scripts.step1_smoke_test
```

Si ves `Step 1 complete.` al final, todo funciona.

---

## 5. Cómo ejecutar el pipeline completo

Cada paso deposita sus artefactos en `data/`. Los pasos dependen unos de otros: ejecuta en orden la primera vez.

| Paso | Comando | Duración | Qué produce |
|------|---------|----------|-------------|
| 1 | `python -m scripts.step1_smoke_test` | ~30 s | `data/openapi.pinned.json`, validación de auth y 429 |
| 2 | `python -m scripts.step2_resolve_ndx` | ~2 min | `data/nasdaq100_uuids.json` (~55 req/min, throttled) |
| 3 | `python -m scripts.step3_introspect` | ~5 s | `data/introspection_samples.json` |
| 4 | `python -m scripts.step4_semi_profiles` | ~10 s | `data/semi_profiles/*.json` |
| 5 | `python -m scripts.step5_cutoff_test` | <1 s | Tests del filtro de cutoff |
| 6 | `python -m scripts.step6_semi_hypotheses` | ~40 s | `data/hypotheses/semi.json` (≈ $0.05 en Anthropic) |
| 7 | `python -m scripts.step7_build_dag` | <1 s | `data/dag/mvp.{pkl,json}` |
| 8 | `python -m scripts.step8_mc` | <1 s | `data/scenarios/mvp.parquet` |
| 9 | `python -m scripts.step9_cvar` | ~80 s | `data/portfolios/mvp.json` (60 tickers) |
| 10 | `python -m scripts.step10_validate` | <1 s | Tests del validador de submission |
| 11 | `python -m scripts.step11_submit --dry-run` | <1 s | Preview del body sin hacer POST |
| 11 | `python -m scripts.step11_submit --safe` | ~2 s | POST equal-weight 50×$20K (test del endpoint) |
| 11 | `python -m scripts.step11_submit --real` | ~2 s | POST de la cartera real del paso 9 |

**Sobre el paso 11 — ojo:**

- `--dry-run` es seguro: imprime el body y no llama a la red.
- `--safe` envía una cartera equal-weight de 50 tickers × $20.000 para confirmar que el schema del body sigue aceptándose.
- `--real` envía la cartera real. Cada POST queda archivado en `data/submissions/mvp_run_<timestamp>.json`.
- El servidor acepta reenvíos, pero por higiene el plan limita a una submission real por iteración de código.

Windows (bash): usa siempre `.venv/Scripts/python.exe` o activa el venv antes (`source .venv/Scripts/activate`).

---

## 6. Qué hay que saber para seguir trabajando

Esto es lo que aprendimos durante el MVP y que no está obvio leyendo el código (más detalle en la retro):

### 6.1 Límites de Cala

- **Rate limit ≈ 60 req/min.** El cliente (`abrollo/cala/client.py`) throttle por defecto a 150 ms entre llamadas, pero cualquier trabajo en bulk debe forzar ≥ 1,1 s/call o acabará en 429.
- **`entity_search` prioriza subsidiarias.** `name=Intel` devuelve "INTEL MSC SDN. BHD." antes que "INTEL CORP". En `abrollo/cala/ndx.py` hay un `SEARCH_OVERRIDES` para parchear casos concretos y un matcher que prefiere el candidato con menos tokens extra.
- **`retrieve_entity` con body vacío no devuelve `numerical_observations`.** Hay que pedirlos explícitamente. Para el MVP no los usamos y delegamos en `knowledge_search`.
- **`knowledge_search.context` no trae fecha.** Ni en el item, ni en `origins`. El filtro de cutoff estricto vaciaría el contexto, así que lo aplicamos solo sobre `source_dates` de la hipótesis y confiamos en que la query de Cala ya está temporalmente acotada. Esto es el **riesgo de lookahead #1 que hay que cerrar antes del Wedge**.
- **`knowledge_query` devuelve entidades con `entity_type=Organization` y UUIDs distintos** a los que devuelve `entity_search(entity_types=["Company"])`. Los dos endpoints comparten nombre pero no índice. Para el peer set de semiconductores hardcodeamos la lista desde nuestra resolución del NDX.

### 6.2 Cómo está construido el grafo causal

El DAG del MVP es minúsculo a propósito: 2 raíces + 1 mecanismo + 2 hojas. Los pesos de las CPD salen de las `trigger_probability` de dos hipótesis concretas:

- `TSMC_event` (p=0.12) → de `H_SEMI_03` (escalada Taiwán)
- `export_control` (p=0.65) → de `H_SEMI_01` (expansión de export controls USA)

**Solo 2 de 99 tickers (NVDA, AMD) llevan señal derivada del DAG.** El resto se muestrea desde una N(0.05, 0.20) placeholder. Por eso el optimizador reparte peso uniformemente fuera de los dos anchors. Para que las hipótesis de verdad muevan la cartera hace falta el Wedge: 5 agentes × 10 hipótesis y un DAG con ≥ 30 nodos.

### 6.3 Disciplina de citas

El agente cita UUIDs de:

1. El universo NDX (los 99 que resolvimos).
2. Los perfiles de las 5 empresas semi ancla.
3. `knowledge_search.entities`, `knowledge_search.context`, `knowledge_search.explainability.references`.

El validador exige que cada `sources[i]` esté en ese allow-list y que cada `source_dates[i]` sea ≤ 2025-04-15. **Atención**: el agente a veces usa `2018-01-01` como fecha de relleno cuando no tiene una fecha real. Cumple el gate mecánicamente pero baja la calidad de la cita. Arreglarlo en el prompt del Wedge.

### 6.4 El schema del endpoint Convex

Descubierto a golpe de POST:

- Campo ticker: `nasdaq_code` (no `ticker`).
- Campo importe: `amount` (no `amount_usd`).
- El servidor devuelve `purchase_prices_apr15` y `eval_prices_today`: son la evidencia trazable para el scoring cualitativo.
- `IDEA.md` y `01-mvp-plan.md` todavía traen el schema antiguo — actualizar antes del Wedge.

---

## 7. Cómo está el código para extenderlo

### 7.1 Añadir un agente de dominio nuevo (Wedge step 1)

Copia `abrollo/agents/semi_agent.py` a `{biotech,fintech,consumer,cloud}_agent.py`. Tres cosas a cambiar por agente:

1. `SEMI_PEER_TICKERS` → lista de NDX del nuevo sector.
2. `KNOWLEDGE_QUERY` → pregunta acotada al sector.
3. `SEMI_ANCHOR_TICKERS` en `config.py` → anchors del sector (4–5 nombres).

Todas las hipótesis se validan con `abrollo/agents/hypothesis.py` (el schema es agnóstico de sector).

Ejecución en paralelo: envolver cada agente en una corutina y usar `asyncio.gather()` (el SDK de Anthropic tiene `AsyncAnthropic`). El cliente de Cala ahora mismo es síncrono; para ir a 30 agentes habrá que portarlo a `httpx.AsyncClient`.

### 7.2 Crecer el DAG

`abrollo/dag/mvp_dag.py` está hand-wired. Para el Wedge:

1. Parsea todas las hipótesis válidas.
2. Dedup por `(trigger, effect_target)`.
3. Los `trigger` únicos se vuelven nodos raíz; los `effect_target` (tickers) se vuelven hojas; añade nodos intermedios de mecanismo donde varias hipótesis compartan raíz.
4. CPDs desde `trigger_probability` × `effect_magnitude`.
5. Asegúrate de validar con `model.check_model()` y medir que el grafo sigue siendo aciclico y con CPDs que suman 1.

### 7.3 Escalar Monte Carlo

`abrollo/mc/sim.py` hace sampling ancestral vectorizado en numpy. Cambiar `N_SIMS` de 1.000 a 10.000 no requiere ningún cambio estructural — la matriz cabe de sobra en RAM (10k × 99 × 8 bytes ≈ 8 MB). Solo asegúrate de regenerar el parquet antes de correr el paso 9.

### 7.4 Afinar el optimizador

`abrollo/opt/cvar.py` tiene dos fases. `LAMBDA = 2.0` es el `λ` de aversión al riesgo (tune). `MAX_TICKERS = 60` es el tamaño del support en fase 2 (subirlo da más dispersión). Si `SCS` devuelve `optimal_inaccurate` demasiado a menudo, `pip install ecos` para usar ECOS (más preciso) o `clarabel`.

---

## 8. Dependencias

Pinadas en `pyproject.toml`. Las importantes:

| Paquete | Uso |
|---|---|
| `anthropic >= 0.40` | SDK de Anthropic, Sonnet 4.6 con tool-use |
| `requests >= 2.32` | Llamadas REST a Cala y Convex |
| `pydantic >= 2.7` | Validación de hipótesis |
| `pgmpy >= 0.1.25` | DAG bayesiano |
| `numpy >= 2.0` | Monte Carlo loop |
| `pandas >= 2.2` + `pyarrow >= 16` | Parquet de escenarios |
| `cvxpy >= 1.5` | Optimizador convexo (usamos SCS) |
| `python-dotenv >= 1.0` | Carga de `.env` |
| `tenacity >= 8.3` | Backoff (reservado para usos futuros) |
| `beautifulsoup4 >= 4.12` + `lxml >= 5.0` | Scraping de la tabla NDX de Wikipedia |

Rechazadas a propósito: LangGraph, CrewAI, AutoGen, LangChain, httpx, litellm, vector DB. Ver [`01-mvp-plan.md` §5](docs/architecture/01-mvp-plan.md).

---

## 9. Limitaciones conocidas (no fixes antes del Wedge)

1. **2 misses en la resolución NDX** (AEP, CHTR). El plan dice explícitamente que no los arreglamos en el MVP.
2. **Aproximación post-subsidiaria:** HON, COST, LIN, CCEP, MELI resuelven a subsidiarias extranjeras. Funcionalmente OK para el gate pero los perfiles son menos ricos.
3. **Solo 1 agente activo** (semiconductores). 4 sectores más están mapeados en `01-mvp-plan.md §8` pero sin implementar.
4. **DAG hand-wired.** La construcción automática desde hipótesis es trabajo del Wedge.
5. **Sin UI.** Todos los outputs son `print()` + JSON/Parquet en `data/`.
6. **ECOS no instalado.** Usamos SCS. Resultado `optimal_inaccurate` en vez de `optimal`; las constraints se cumplen igual.

---

## 10. Dónde seguir

Si quieres **entender el diseño**: lee `IDEA.md` y `docs/architecture/00-cto-design.md`.
Si quieres **entender el plan de ejecución**: lee `docs/architecture/01-mvp-plan.md`.
Si quieres **saber qué salió bien y qué salió mal**: lee `docs/architecture/02-mvp-retro.md`.
Si quieres **tocar código**: lee §6 y §7 de este README, luego mira `abrollo/cala/client.py` (todo empieza ahí).
Si quieres **reproducir la submission**: sigue §5 de arriba, paso 1 al 11 en orden.

Siguiente hito grande: escalar a 5 agentes en paralelo y DAG de 50 nodos. El `Wedge` en el CTO design es la referencia.
