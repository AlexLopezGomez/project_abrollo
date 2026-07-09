# Abrollo — Monte Carlo Cathedral

Agente de construcción de carteras para el **Cala AI Challenge** (Project Barcelona, abril 2026).
Equipo Abrollo: Alex, Nico, Carlos.

> **No elegimos acciones. Elegimos una forma de incertidumbre con la que estar cómodos 12 meses.**

## Resultados

$1M de capital virtual, compra a cierre del 15-abr-2025, evaluado a precios del 15-abr-2026. Benchmark a batir: SPY buy-and-hold.

| Versión | Valor final | Retorno | Cartera | Submission ID |
|--------|-------------|---------|---------|---------------|
| **MVP-2** | **$1,551,515.14** | **+55.2%** | 60 tickers | `jx704evqag7xry244jxqwcg5qh84x0p4` |
| MVP-1 | $1,473,435.33 | +47.3% | 60 tickers | `jx7czbecp7106ezabxq50f79b984w0kb` |

Ambos envíos aceptados por el endpoint (HTTP 200). Números verificados en `docs/architecture/02-mvp-retro.md` y `04-mvp-2-retro.md`.

## La idea en 60 segundos

El enfoque naíf (que hará ~80% de los equipos): un enjambre de LLMs debate cada acción y un LLM "juez" reparte capital. Eso colapsa en scoring por intuición. Los LLMs son malos jueces de mercado, no modelan correlaciones y no producen distribuciones de incertidumbre.

**Nuestra inversión:** que cada herramienta haga lo que sabe hacer.

- **Los LLMs** leen texto de Cala y emiten **hipótesis causales estructuradas con citas** (nada de opiniones, solo afirmaciones con fuente).
- **Las matemáticas** propagan probabilidades por un grafo causal, simulan miles de futuros y optimizan la cartera bajo incertidumbre.
- Las **correlaciones** son explícitas en el grafo, no implícitas en la "cabeza" del modelo.
- La salida es una **distribución de resultados**, no una predicción puntual.

No predecimos qué acciones ganarán: enumeramos futuros a 12 meses plausibles y elegimos la cartera que sobrevive bien en toda la distribución, sobre todo en la cola (war-gaming estilo RAND aplicado a asignación de capital).

### El pipeline (4 etapas)

```
  ┌─────────────────────┐   ┌──────────────────┐   ┌──────────────────┐   ┌────────────────────┐
  │ 1. Agentes (Claude) │──▶│ 2. Grafo causal  │──▶│ 3. Monte Carlo   │──▶│ 4. Optimización    │
  │                     │   │    (DAG)         │   │                  │   │    CVaR (cvxpy)    │
  │ Leen Cala y emiten  │   │ Hipótesis → nodos│   │ N escenarios ×   │   │                    │
  │ hipótesis con citas │   │ y aristas con    │   │ M tickers.       │   │ max E[r] − λ·CVaR  │
  │ (UUID + fecha).     │   │ probabilidades.  │   │ Cada fila = un   │   │ → 50+ pesos = la   │
  │ Firewall: toda      │   │ Propagación      │   │ año simulado del │   │ cartera final.    │
  │ fuente ≤ 2025-04-15 │   │ causal.          │   │ mundo entero.    │   │                    │
  └─────────────────────┘   └──────────────────┘   └──────────────────┘   └────────────────────┘
        sin lookahead              networkx / pgmpy        numpy                  cvxpy / SCS
```

**Cala** es un grafo de entidades verificadas (empresas, personas, leyes, papers…), cada hecho con UUID y timestamp. No es un buscador ni un proveedor de datos de bolsa: es un sustrato de hechos citables que el agente consulta como herramienta. El *firewall anti-lookahead* es mecánico: toda hipótesis debe citar fuentes con fecha ≤ 15-abr-2025.

El brief completo del concepto está en **[`IDEA.md`](IDEA.md)**.

## Ver la data — Dashboard Streamlit

La forma más rápida de entender qué hicimos es **levantar el dashboard**. Los artefactos reales del pipeline (submissions, grafos, hipótesis, carteras) están versionados en `data/`, así que funciona sin ejecutar el pipeline.

```bash
python -m venv .venv
.venv/bin/pip install -e .                       # en Windows: .venv\Scripts\pip
.venv/bin/pip install -r dashboard/requirements.txt

.venv/bin/streamlit run dashboard/app.py --server.port 8501
```

Abre http://localhost:8501. Selecciona cualquier run histórico en la barra lateral y explora las pestañas:

- **Returns** — cartera final, valor y retorno del run seleccionado.
- **Historial** — todos los envíos y su evolución.
- **Knowledge Graph** — el DAG causal navegable (nodos evento → mecanismos → tickers).
- **Hipótesis de Claude** — las hipótesis generadas con sus citas a Cala (UUID + fecha).

![Dashboard Abrollo](dashboard_home.png)

## Mapa del repo

```
abrollo/            Código del pipeline (paquete instalable)
├── cala/           Cliente Cala, resolución del NASDAQ-100, cutoff temporal
├── agents/         Generación y validación de hipótesis (Claude)
├── dag/            Construcción del grafo causal y propagación
├── mc/             Covarianza y simulación Monte Carlo
├── opt/            Optimización CVaR
└── submit/         Validación y envío al endpoint Convex

scripts/            Pipelines ejecutables paso a paso
├── step1..step11             MVP-1 (flujo inicial end-to-end)
└── mvp2_step1..mvp2_step10   MVP-2 (grafo de entidades + MC correlacionado)
    + mvp2_run_all.py         corre MVP-2 completo de una vez

dashboard/          App Streamlit para visualizar los artefactos
data/               Artefactos versionados (submissions, grafos, hipótesis…)
docs/architecture/  Diseño, planes y retros (ver "Por dónde seguir")
IDEA.md             Brief completo del concepto
```

## Ejecutar el pipeline (opcional)

El dashboard ya trae la data. Solo necesitas esto si quieres **regenerar** los artefactos.

Requisitos: Python `>=3.11` y un `.env` en la raíz:

```env
CALA_API_KEY=tu_api_key
ANTHROPIC_API_KEY=tu_api_key
```

**MVP-1** (primera ejecución, en orden):

```bash
python -m scripts.step1_smoke_test
python -m scripts.step2_resolve_ndx
python -m scripts.step3_introspect
python -m scripts.step4_semi_profiles
python -m scripts.step5_cutoff_test
python -m scripts.step6_semi_hypotheses
python -m scripts.step7_build_dag
python -m scripts.step8_mc
python -m scripts.step9_cvar
python -m scripts.step10_validate
python -m scripts.step11_submit --dry-run
```

Modos de envío (`step11_submit.py`): `--dry-run` (imprime, no hace POST) · `--safe` (POST equal-weight 50×$20k) · `--real` (POST con `data/portfolios/mvp.json`).

**MVP-2** (necesita `data/nasdaq100_uuids.json` con 99 hits del `step2` previo):

```bash
python scripts/mvp2_run_all.py          # todo de una vez
# o paso a paso: mvp2_step1_preflight.py … mvp2_step10_submit.py
```

## Por dónde seguir leyendo

En orden, para entender el proyecto en profundidad:

1. **[`IDEA.md`](IDEA.md)** — el brief y la tesis contraria.
2. **[`docs/architecture/00-cto-design.md`](docs/architecture/00-cto-design.md)** — diseño técnico.
3. **[`docs/architecture/01-mvp-plan.md`](docs/architecture/01-mvp-plan.md)** y **[`02-mvp-retro.md`](docs/architecture/02-mvp-retro.md)** — plan y retro de MVP-1.
4. **[`docs/architecture/03-mvp-2-plan.md`](docs/architecture/03-mvp-2-plan.md)** y **[`04-mvp-2-retro.md`](docs/architecture/04-mvp-2-retro.md)** — plan y retro de MVP-2 (incluye limitaciones conocidas y próximos pasos).
