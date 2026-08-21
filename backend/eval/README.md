# Creative evaluation lab

Internal only. This is not a user-facing feature and is never imported by campaign requests.

The production wizard stays frozen. Use this lab to compare Creative Director recommendations, style/template recipes, prompts, identity preservation, QC, cost, and the 9:16-master crop experiment.

## Layout

```
backend/eval/
  creative_cases/     fixture JSON (committed)
  experiments/        batch experiment manifests (committed)
  assets/             product photos (replace placeholders)
  creative_runs/      immutable outputs (gitignored)
  briefs/             older LLM-copy eval briefs (unchanged)
  out/                older eval_images / eval_llm output (gitignored)
```

## Two modes (do not mix the questions)

**Fixed recipe** — given a known style × template, how good is image generation?
Does **not** call the Creative Director.

**Director** — given only product + brief, does Afarin propose good directions?
Calls the real multimodal Creative Director **once**, then optionally generates images for those three recipes.

## Fixture schema

See `creative_cases/*.json`. Required:

- `case_id`
- `product_image` (path relative to the JSON file)
- `product.name`
- `objective`: `sell_product` | `new_product` | `promotion` | `brand_awareness`
- `visual_style`: `luxury` | `minimal` | `friendly` | `bold` | `persian_traditional` | `modern`

Optional: `category` (for summary filters), description, price, benefit, brand, audience, identity constraints, `fixed_recipes`.

Style and template IDs must exist in `app/content/visual_catalog.json`.

## Commands

From `backend/`:

```bash
uv run python -m scripts.run_creative_eval --case sweatshirt_01 --mode fixed --dry-run

uv run python -m scripts.run_creative_eval \
  --case sweatshirt_01 \
  --mode fixed \
  --recipes fashion_editorial:model_using,anime:illustrated_scene,cinematic:cinematic_environment \
  --candidates 3 \
  --quality-check \
  --repair none \
  --provider stub

uv run python -m scripts.run_creative_eval \
  --case sweatshirt_01 \
  --mode director \
  --candidates 3 \
  --provider openrouter \
  --paid \
  --open
```

Useful flags: `--story`, `--master-crop`, `--repair none|production`, `--label identity-v2`, `--all-styles --template hero_product`, `--all-templates --style photoreal_commercial`.

`--dry-run` makes **zero** provider calls.

## Batch experiments

Committed manifests live in `eval/experiments/`. Each case still writes a normal immutable run folder.

```bash
uv run python -m scripts.run_creative_eval \
  --experiment baseline-v1 \
  --provider stub \
  --dry-run

uv run python -m scripts.run_creative_eval \
  --experiment baseline-v1 \
  --provider openrouter \
  --paid \
  --confirm
```

Before any paid call the CLI prints TOTAL LLM calls, paid image outputs, estimated cost, cases, and recipes. Paid batches also require `--confirm`. `--provider openrouter` without `--paid` is still refused.

Director-only (no image spend):

```bash
uv run python -m scripts.run_creative_eval \
  --case sweatshirt_01 --mode director --candidates 0 --provider stub
```

## Paid-call protection

- Default provider is `stub` (fake JPEGs, $0).
- `--provider openrouter` without `--paid` is refused.
- `--all-styles` / `--all-templates` also need `--confirm`.
- Paid `--experiment` batches also need `--confirm`.
- Pytest forces stub providers. This module is not imported by `app.main`.
- Normal CI therefore cannot spend image budget.

Before a paid run the CLI prints case, mode, recipes, expected image **frames** (not HTTP requests), LLM calls, and an approximate image cost ($0.04/frame estimate). Actual OpenRouter `usage.cost_usd` is stored on the run.

## Adding a case

1. Put a product photo in `eval/assets/`.
2. Copy a JSON file in `eval/creative_cases/`.
3. Use production field names (`product.name`, `visual_style`, catalog IDs).
4. `--dry-run` to validate. No provider call is required to add a fixture.

## Where runs appear

`eval/creative_runs/YYYY-MM-DD_001_caseid_label/`

Never overwritten. Each run stores `run_meta.json`, the fixture, the reference JPEG, prompts, sanitized provider metadata (no API keys), candidates, optional Story/master-crop, QC, cost, and `ratings.json`.

## Review UI

Start the frontend, then open:

- http://localhost:3000/dev/creative-eval
- http://localhost:3000/dev/creative-eval/{runId}
- http://localhost:3000/dev/creative-eval/compare
- http://localhost:3000/dev/creative-eval/summary

`--open` tries the run URL. The pages 404 in production builds and are not in seller navigation.

Rate candidates 1–5 (overall, identity, attractiveness, style match, template match, commercial usefulness) plus flags. Director-only runs (`--candidates 0`) can still rate analysis correctness, direction diversity, and per-direction strategic fit / recipe suitability / overall. Ratings stay in that run’s `ratings.json`, not in campaign tables.

Compare two runs of the **same case** at `/dev/creative-eval/compare`. Matching recipes are shown side by side (image, human scores, AUTO QC, prompt version, model, latency/cost). There is no automatic winner.

Summary filters/groups by case, category, style, template, label/prompt version, fixed vs director, and image model. Default grouping is case + recipe so clothing scores are not averaged with food.

AUTO QC and human scores sit side by side so you can see whether QC rejects good images or accepts bad ones. Thresholds are not auto-tuned.

Each recipe row also shows the committed public preview cards (`/visual-previews/styles/{id}.jpg` and `templates/{id}.jpg`) next to real outputs. Previews are not regenerated.

## Style / template library sweeps

```bash
uv run python -m scripts.run_creative_eval \
  --case sweatshirt_01 --mode fixed \
  --all-styles --template hero_product \
  --provider openrouter --paid --confirm
```

One axis per run. Combining `--all-styles` with `--all-templates` is refused.

## Master-crop experiment

`--master-crop` adds, per recipe:

- A: dedicated 4:5 candidate
- B: dedicated 9:16 Story (same as production winner adaptation)
- C: one 9:16 master + deterministic 4:5 center crop

Crop math lives in `app/services/campaigns/master_crop.py`. Production `image_compose_strategy` is unchanged.

The older empty-scene comparison is still:

```bash
uv run python -m scripts.eval_master_crop --synthetic
```
