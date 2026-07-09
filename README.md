# Abrollo — Monte Carlo Cathedral

Proyecto del equipo Abrollo para el Cala AI Challenge (Project Barcelona, abril de 2026).

Este README está actualizado contra el código actual de `main` a fecha **2026-04-16** y separa:

- hechos verificables en el repo;
- resultados históricos documentados en retros.

## 1) Qué hay en `main` (verificado)

El repo contiene dos pipelines ejecutables:

- **MVP-1** (scripts `step1` a `step11`): flujo inicial end-to-end.
- **MVP-2** (scripts `mvp2_step1` a `mvp2_step10` + `mvp2_run_all.py`): versión con grafo de entidades, propagación y Monte Carlo correlacionado.

Código principal:

- `abrollo/cala`: cliente Cala + resolución de NDX + cutoff temporal.
- `abrollo/agents`: generación/validación de hipótesis (`hypothesis.py`, `hypothesis_v2.py`).
- `abrollo/dag`: construcción de grafo y propagación causal.
- `abrollo/mc`: covarianza y simulación Monte Carlo.
- `abrollo/opt`: optimización CVaR.
- `abrollo/submit`: validación y envío al endpoint Convex.

Documentación de arquitectura:

- `docs/architecture/00-cto-design.md`
- `docs/architecture/01-mvp-plan.md`
- `docs/architecture/02-mvp-retro.md`
- `docs/architecture/03-mvp-2-plan.md`
- `docs/architecture/04-mvp-2-retro.md`

## 2) Requisitos (verificado en código)

- Python: `>=3.11` (`pyproject.toml`)
- Variables de entorno (`abrollo/config.py`):
  - `CALA_API_KEY`
  - `ANTHROPIC_API_KEY`
- `data/`, `.env`, `.venv/` están en `.gitignore` (los artefactos se generan localmente).

## 3) Instalación

```bash
git clone https://github.com/AlexLopezGomez/project_abrollo.git
cd project_abrollo

python -m venv .venv
.venv/Scripts/pip install -e .
```

Crea un `.env` en la raíz:

```env
CALA_API_KEY=tu_api_key
ANTHROPIC_API_KEY=tu_api_key
```

## 4) Ejecutar MVP-1

Orden recomendado (primera ejecución):

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

Modos de envío MVP-1 (`scripts/step11_submit.py`):

- `--dry-run`: imprime body y no hace POST.
- `--safe`: POST real con cartera equal-weight 50x$20k.
- `--real`: POST real con `data/portfolios/mvp.json`.

## 5) Ejecutar MVP-2

Opciones:

```bash
python scripts/mvp2_run_all.py
```

o por pasos:

```bash
python scripts/mvp2_step1_preflight.py
python scripts/mvp2_step2_bulk_retrieve.py
python scripts/mvp2_step3_covariance.py
python scripts/mvp2_step4_graph.py
python scripts/mvp2_step5_hypotheses.py
python scripts/mvp2_step6_propagation.py
python scripts/mvp2_step7_mc.py
python scripts/mvp2_step8_optimize.py
python scripts/mvp2_step9_validate.py
python scripts/mvp2_step10_submit.py
```

Nota importante: el preflight de MVP-2 exige `data/nasdaq100_uuids.json` con 99 hits, por lo que necesitas haber corrido antes `scripts.step2_resolve_ndx`.

## 6) Artefactos generados en `data/`

Rutas relevantes que escribe el código actual:

- `data/openapi.pinned.json`
- `data/nasdaq100_uuids.json`
- `data/introspection_samples.json`
- `data/semi_profiles/*.json`
- `data/cala_entities/*.json`
- `data/hypotheses/{semi.json,mvp2.json}`
- `data/graph/{mvp2.gpickle,mvp2_summary.json}`
- `data/dag/{mvp.pkl,mvp.json,mvp2.pkl,mvp2.json}`
- `data/cov/mvp2.npz`
- `data/scenarios/{mvp.parquet,mvp_meta.json,mvp2.parquet,mvp2_meta.json}`
- `data/portfolios/{mvp.json,mvp2.json}`
- `data/submissions/{mvp_run_*.json,mvp2_run_*.json}`

## 7) Resultados históricos (documentados)

Estos datos vienen de retros versionadas en el repo:

- **MVP-1**: `docs/architecture/02-mvp-retro.md` (run date `2026-04-15`), con `submission_id` documentado `jx7czbecp7106ezabxq50f79b984w0kb`.
- **MVP-2**: `docs/architecture/04-mvp-2-retro.md` (run date `2026-04-15`), con `submission_id` documentado `jx704evqag7xry244jxqwcg5qh84x0p4`.

Se consideran resultados históricos del proyecto; no son una verificación en tiempo real desde este README.


streamlit run dashboard/app.py --server.port 8501 