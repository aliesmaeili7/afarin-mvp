# Afarin Creative Evaluation — Systematic Test Plan

## 1. What this lab is for

This is a **creative-quality laboratory**, not a normal pass/fail test suite. It should answer four questions separately:

1. **Image execution:** given a known style × template, can Afarin generate a strong ad while preserving the real product?
2. **Catalog quality:** do the 14 styles and 12 templates behave distinctly and match their preview cards?
3. **Creative Director quality:** does Afarin choose good, diverse recipes for the product + brief?
4. **QC quality:** does AUTO QC agree with human judgment about what should be shown to the seller?

Do not mix these questions in the first experiments. Test them separately, then combine them.

---

## 2. What is stored

`--dry-run` stores nothing.

Every real stub or paid run creates an immutable folder under:

```text
backend/eval/creative_runs/YYYY-MM-DD_001_caseid_label/
```

Typical contents:

```text
run_meta.json
input_fixture.json
effective_brief.json
reference_product.jpg
director_output.json        # Director mode only
cost.json
ratings.json                # your human ratings
recipes/<style>__<template>/
  candidate-1.jpg
  candidate-2.jpg
  candidate-3.jpg
  prompt.*
  quality.json
  metrics.json
  story.jpg                 # only if requested
  master-9x16.jpg           # only for crop experiment
  crop-4x5.jpg
```

Review runs at:

```text
http://localhost:3000/dev/creative-eval
```

Aggregate ratings:

```text
http://localhost:3000/dev/creative-eval/summary
```

**Rule:** keep the first paid runs. They become the baseline for later prompt/model/QC changes.

---

## 3. Canonical five-case regression set

Use these five cases as your fixed initial benchmark:

| Case | Image |
|---|---|
| `sweatshirt_01` | `sweatshirt.jpeg` |
| `cosmetics_01` | `cosmetics.jpeg` |
| `restaurant_food_01` | `restaurant_food.jpeg` |
| `accessory_01` | `accessory.jpeg` |
| `shoes_01` | `shoes.png` |

Before any paid run, inspect every fixture once:

- crop is product-forward;
- product fills most of the frame;
- no screenshot/UI chrome;
- min edge ≥ 256 px;
- product name/description matches the visible product;
- no invented claims;
- objective/audience/حس تبلیغ are realistic;
- unknown price/brand is omitted rather than invented.

Do not casually change these five baseline fixtures. Add new fixtures for special cases instead.

---

## 4. Human scoring rubric

Score every real candidate consistently.

### Product identity — 1 to 5

- **5** — unmistakably the same product; important shape/colors/graphics/packaging preserved.
- **4** — clearly same product; only minor harmless drift.
- **3** — recognizable, but meaningful details changed.
- **2** — substantially altered.
- **1** — effectively a different product.

### Commercial usefulness — 1 to 5

- **5** — strong enough to show a real seller as ready-to-post.
- **4** — usable with small typography/layout edits.
- **3** — plausible but mediocre / needs meaningful improvement.
- **2** — weak ad.
- **1** — unusable.

### Visual attractiveness — 1 to 5

- **5** striking/professional
- **4** clearly attractive
- **3** acceptable/generic
- **2** weak
- **1** bad/broken

### Style match — 1 to 5

Does it genuinely look like the selected style?

### Template match — 1 to 5

Does the composition actually follow the selected template?

### Overall — 1 to 5

Final holistic judgment after the other fields.

### Practical definitions

A candidate is **seller-usable** if:

- identity ≥ 4;
- commercial usefulness ≥ 3;
- no severe artifact;
- no destructive random text/logo;
- no major unintended duplication.

A candidate is **strong** if:

- identity ≥ 4;
- commercial usefulness ≥ 4;
- attractiveness ≥ 4;
- overall ≥ 4.

For a normal three-candidate generation, the eventual target should be:

- at least **2/3 seller-usable most of the time**;
- at least **1/3 strong regularly**.

---

## 5. Failure flags and diagnosis

Use flags aggressively:

| Flag | Usually points to |
|---|---|
| random text/logo | image prompt/model/QC |
| product changed too much | identity-preservation prompt/model |
| anatomy/object artifact | model reliability |
| duplicated product | template/prompt |
| bad composition | template/prompt |
| boring/generic | creative direction/prompt |
| style mismatch | style prompt/catalog |
| template mismatch | template prompt/catalog |

Repeated failures matter more than one bad generation.

---

## 6. AUTO QC vs human judgment

For recipe testing, use:

```bash
--quality-check --repair none
```

This lets QC score the raw output without repair hiding the failure rate.

Track two disagreement types:

### QC miss
AUTO QC = PASS, but human says **not seller-usable**.

### QC over-rejection
AUTO QC = HARD FAIL, but human says **seller-usable**.

Do not tune QC from one example. Wait for repeated patterns.

---

## 7. Experiment discipline

For every paid run:

- always use `--label`;
- change only **one experimental variable** at a time;
- keep fixture + recipe identical when comparing prompt versions;
- keep `--repair none` for raw recipe quality;
- skip Story/master-crop unless they are the experiment;
- use 1 candidate by default; use 3 only after a recipe looks worth deeper testing.

Good labels:

```text
baseline-anchor
style-sweep-baseline
template-sweep-baseline
identity-v2
director-v2
qc-v2
master-crop-baseline
```

---

# TEST SEQUENCE

## Stage 0 — free sanity check

Run dry-run for all five fixtures:

```bash
cd backend

uv run python -m scripts.run_creative_eval \
  --case sweatshirt_01 \
  --mode fixed \
  --dry-run
```

Repeat for the other four cases.

Check image path, brief, recipes, expected image outputs, LLM calls, and cost.

Do one stub run only to learn the UI if needed:

```bash
uv run python -m scripts.run_creative_eval \
  --case sweatshirt_01 \
  --mode fixed \
  --candidates 1 \
  --provider stub \
  --open
```

Do not score stub image quality.

---

## Stage 1 — five-image anchor baseline

### Question
Can the current production image system produce one sensible result for each category?

Use Fixed mode, 1 sensible recipe per case, 1 candidate, QC on, no repair.

Suggested anchors:

| Case | Recipe |
|---|---|
| sweatshirt | `fashion_editorial:model_using` |
| cosmetics | `photoreal_commercial:product_pedestal` |
| restaurant food | `photoreal_commercial:product_with_props` |
| accessory | `fashion_editorial:hero_product` |
| shoes | `cinematic:cinematic_environment` |

Example:

```bash
uv run python -m scripts.run_creative_eval \
  --case sweatshirt_01 \
  --mode fixed \
  --recipes fashion_editorial:model_using \
  --candidates 1 \
  --quality-check \
  --repair none \
  --provider openrouter \
  --paid \
  --label baseline-anchor \
  --open
```

Run once per case.

**5 image outputs total ≈ $0.20** at the current ~$0.04/output working estimate, plus small QC LLM cost.

### Stop and analyze
Do **not** change prompts yet. Record:

- identity failures;
- generic/boring outputs;
- style/template mismatches;
- QC disagreements;
- which categories already look promising.

---

## Stage 2 — style catalog sweep

### Question
Do the 14 styles produce genuinely different, representative looks?

Use one clean versatile product. Default: `shoes_01` if it is the cleanest image.

Keep template fixed at `hero_product`:

```bash
uv run python -m scripts.run_creative_eval \
  --case shoes_01 \
  --mode fixed \
  --all-styles \
  --template hero_product \
  --candidates 1 \
  --quality-check \
  --repair none \
  --provider openrouter \
  --paid \
  --confirm \
  --label style-sweep-baseline \
  --open
```

Evaluate every style for:

- distinctness;
- name/style match;
- public-preview match;
- identity preservation;
- commercial usefulness.

Classify each style:

- **Green** — works and is meaningfully distinct
- **Yellow** — promising but needs tuning
- **Red** — unreliable/redundant/misleading

**14 images ≈ $0.56.**

Do not remove a Red style after one product; confirm on another category first.

---

## Stage 3 — template catalog sweep

### Question
Do the 12 templates produce genuinely different compositions?

Use a versatile object product; `cosmetics_01` is a good default.

Keep style fixed at `photoreal_commercial`:

```bash
uv run python -m scripts.run_creative_eval \
  --case cosmetics_01 \
  --mode fixed \
  --all-templates \
  --style photoreal_commercial \
  --candidates 1 \
  --quality-check \
  --repair none \
  --provider openrouter \
  --paid \
  --confirm \
  --label template-sweep-baseline \
  --open
```

Evaluate:

- composition is obvious;
- template differs from neighboring templates;
- product fits the composition;
- unwanted duplicates;
- text-safe area;
- public preview accurately teaches the template.

**12 images ≈ $0.48.**

If `hero_product`, `product_pedestal`, and `floating_product` all look almost the same, treat that as a catalog/prompt problem rather than generating many more samples.

---

## First major checkpoint

At this point you have:

- 5 anchor images
- 14 style images
- 12 template images

**31 paid image outputs ≈ $1.24**, plus QC LLM cost.

Stop here and inspect patterns before spending more.

This is the right moment for the first prompt/catalog improvements if repeated weaknesses are visible.

---

## Stage 4 — category-specific recipe shortlist

### Question
Which recipe families actually work for each product category?

For each of the five cases choose 3 recipes, ideally:

1. one realistic/editorial;
2. one stylized/illustrated;
3. one conceptual/surreal.

Run 1 candidate per recipe, QC on, repair none.

Example:

```bash
uv run python -m scripts.run_creative_eval \
  --case sweatshirt_01 \
  --mode fixed \
  --candidates 1 \
  --quality-check \
  --repair none \
  --provider openrouter \
  --paid \
  --label category-shortlist-v1 \
  --open
```

Use fixture recipes or explicit `--recipes`.

**5 cases × 3 recipes = 15 images ≈ $0.60.**

The goal is to discover category patterns such as:

- editorial/model works well for clothing;
- surreal scale works well for packaged products;
- some illustrated modes destroy packaging identity;
- some templates should be discouraged for food.

These findings can later become Director suitability rules.

---

## Stage 5 — consistency / best-of-three

### Question
For a recipe that looks good, how reliable is it? Is 3 candidates worth the cost?

Do **not** run 3 candidates for everything.

Choose only 2–3 promising or strategically important recipes:

```bash
uv run python -m scripts.run_creative_eval \
  --case <case> \
  --mode fixed \
  --recipes <style>:<template> \
  --candidates 3 \
  --quality-check \
  --repair none \
  --provider openrouter \
  --paid \
  --label consistency-baseline \
  --open
```

Measure:

- raw usable rate;
- strong-image rate;
- chance at least one of 3 is strong;
- identity variance;
- candidate diversity vs near-duplicates.

If a recipe needs repeated regeneration just to get one usable image, it is not production-ready.

---

## Stage 6 — Director-only evaluation, zero images

### Question
Does Afarin understand the product and choose sensible/diverse directions?

Run the real Director with no image generation:

```bash
uv run python -m scripts.run_creative_eval \
  --case sweatshirt_01 \
  --mode director \
  --candidates 0 \
  --provider openrouter \
  --paid \
  --label director-baseline \
  --open
```

Repeat for all five cases.

Judge:

- correctness of product visual analysis;
- strategic fit to objective/audience/حس تبلیغ;
- recipe suitability;
- diversity of the three directions;
- whether the Director avoids recipe/category combinations that fixed tests showed are weak.

Do not pay for images when the recommendation itself is bad.

---

## Stage 7 — Director execution

Once Director recommendations are sensible, generate **1 image per direction**:

```bash
uv run python -m scripts.run_creative_eval \
  --case sweatshirt_01 \
  --mode director \
  --candidates 1 \
  --quality-check \
  --repair none \
  --provider openrouter \
  --paid \
  --label director-execution-baseline \
  --open
```

Five cases = 3 directions × 5 = **15 images ≈ $0.60.**

Diagnose failures correctly:

- **good direction + bad image** → prompt/model/recipe execution
- **bad direction + good technical image** → Director
- **good direction + good image + QC fail** → QC
- **bad direction + bad image** → fix upstream first, not QC

---

## Stage 8 — QC calibration

Only after enough human ratings exist.

Compare AUTO QC with human usability.

Tune one rule/threshold at a time, then rerun the exact same baseline case/recipe under a new label.

Keep `--repair none` when evaluating QC itself.

---

## Stage 9 — 9:16 master → 4:5 crop experiment

Do this only after base image quality is stable.

Test at least:

- sweatshirt/clothing;
- cosmetics;
- restaurant food.

Compare:

A. dedicated 4:5
B. dedicated Story
C. 9:16 master → deterministic 4:5 crop

Judge Feed composition, Story composition, product crop, safe area, commercial usefulness, and cost.

Do not switch production strategy because one product works.

---

## Stage 10 — Story adaptation

Skip Story during early style/template testing.

Test Story only after candidate quality and winner selection are stable. Use strong winners from the five cases and evaluate 9:16 composition + identity preservation.

---

# 11. When to change prompts

Do not react to one ugly generation.

Change a prompt when:

- the same failure repeats across ~3 or more relevant outputs;
- a style/template repeatedly misses its definition;
- identity repeatedly fails in a category;
- Director repeatedly chooses a recipe known to perform badly.

For every change:

1. state one hypothesis;
2. change one thing;
3. label the run;
4. rerun the smallest relevant baseline;
5. compare;
6. keep or revert based on evidence.

Example hypothesis:

> `model_using` changes clothing graphics because clothing identity constraints are too weak.

Change only that behavior and rerun the exact sweatshirt recipe.

---

# 12. When to test another image model

Do not model-hop early.

First make prompts/recipes reasonably mature. Then run a model bakeoff only on 3–5 hard representative cases with identical reference, recipe, prompt, and candidate count.

Compare quality, identity, latency, and cost.

---

# 13. Recommended spend order

Using the current approximate ~$0.04/image figure:

| Stage | Image outputs | Approx. image spend |
|---|---:|---:|
| Anchor baseline | 5 | $0.20 |
| Full style sweep | 14 | $0.56 |
| Full template sweep | 12 | $0.48 |
| **First checkpoint** | **31** | **$1.24** |
| Category shortlist | 15 | $0.60 |
| Director execution | 15 | $0.60 |
| Consistency | selected recipes only | variable |
| Story/master crop | later | variable |

This is much more informative than using 3 candidates everywhere immediately.

---

# 14. Go/no-go quality gate before moving on

You do **not** need all 168 style×template combinations to work.

Move forward when the normal Creative experience roughly reaches:

### Director
- 3 directions are usually meaningfully different;
- at least 2 directions generally make strategic sense;
- recommended recipes usually fit the product/category.

### Images
- product identity is usually ≥4;
- strong recipes often produce at least 2/3 seller-usable candidates;
- at least 1/3 is regularly strong;
- random text/severe artifacts are uncommon.

### Catalog
- major styles visibly mean different things;
- major templates visibly mean different things;
- previews reasonably represent production outputs;
- known bad category/recipe combinations are discouraged.

### QC
- obvious failures are usually caught;
- good images are rarely hidden.

### Cost
- normal generation spend is predictable enough to design credits later.

---

# 15. Efficient iteration loop

Use this loop repeatedly:

```text
1. Inspect summary + weak runs
2. Pick ONE hypothesis
3. Change ONE thing
4. Re-run one case
5. Rate it
6. If promising, re-run three cases
7. If still better, re-run all five
8. Keep or revert
```

Do not rerun all five products after every tiny change.

---

# 16. Keep an experiment log

Create a lightweight human-readable file such as:

```text
backend/eval/EXPERIMENT_LOG.md
```

Example:

```markdown
## 2026-08-21 — baseline-anchor
Change: none
Question: current image quality across 5 categories
Cases: all 5
Result:
Decision:

## 2026-08-22 — identity-v2
Hypothesis: stronger must-preserve instructions reduce clothing/packaging drift
Changed: identity instruction only
Cases: sweatshirt_01, cosmetics_01
Compared against: baseline-anchor
Result:
Decision: keep / revert
```

Immutable run folders are the evidence; the log records your reasoning.

---

# 17. Lab improvements worth adding

The current lab already has the important core. These additions would make systematic testing significantly better.

## A. Batch experiment manifests

Right now runs are case-by-case. Add an experiment manifest so the five-case regression set can be rerun with one command while still showing total expected spend and requiring explicit confirmation.

Example concept:

```json
{
  "experiment_id": "baseline-v1",
  "quality_check": true,
  "repair": "none",
  "cases": [
    {
      "case": "sweatshirt_01",
      "mode": "fixed",
      "recipes": ["fashion_editorial:model_using"],
      "candidates": 1
    },
    {
      "case": "cosmetics_01",
      "mode": "fixed",
      "recipes": ["photoreal_commercial:product_pedestal"],
      "candidates": 1
    }
  ]
}
```

## B. Baseline-vs-challenger comparison page

The existing style×template summary is useful, but prompt iteration needs direct paired comparison:

```text
same case + same recipe

BASELINE              CHALLENGER
[image]               [image]
ratings               ratings
AUTO QC               AUTO QC
prompt version        prompt version
cost/latency          cost/latency
```

## C. Better reproducibility metadata

If not already stored, add to `run_meta.json`:

- Git commit SHA;
- working-tree dirty flag;
- image model ID;
- Director/QC model IDs;
- relevant provider parameters;
- creative-prompt/catalog hash/version;
- fixture hash.

Never store secrets.

## D. Director-only human ratings

If `--mode director --candidates 0` cannot currently be rated, add:

- product-analysis correctness 1–5;
- strategic fit 1–5 per direction;
- recipe suitability 1–5 per direction;
- overall direction quality 1–5;
- run-level diversity 1–5;
- optional notes.

This lets you test Director quality without paying for images.

## E. Summary filters

Allow aggregate results to filter by:

- product case/category;
- label/prompt version;
- mode;
- model.

Otherwise a recipe that is excellent for clothing and poor for food can misleadingly average to “okay”.

---

# 18. Immediate next action

Do **not** change prompts yet.

1. Dry-run all five fixtures.
2. Run the five-image anchor baseline.
3. Rate all five.
4. Run the 14-style sweep.
5. Run the 12-template sweep.
6. Stop and analyze the first **31 paid images** before making the first creative prompt/catalog changes.

That first checkpoint should reveal far more than another round of feature development.
