# Cursor Prompt — Phase 4B Creative Visual System

@AGENTS.md
@docs/MVP_SPEC.md

Phases 1–3 are stable. Phase 4 currently has a safe/composite visual mode where Afarin generates a scene and preserves the seller's original product pixels.

We now want to extend Phase 4 before considering it complete.

Do not write code yet.

Read the current implementation carefully, especially:

* image generation provider abstraction
* OpenRouter image integration
* uploaded image preprocessing/crop/cutout flow
* AdCanvas / AssetRenderSpec
* campaign concepts
* current style system
* generation_jobs
* Supabase Storage
* regeneration logic
* the existing GPT-5-mini ContentProvider/planner architecture

## Product direction

Afarin should not only put products onto nicer backgrounds.

It should behave more like an AI creative director and create visually interesting advertising concepts using modern image-generation capabilities.

Keep the current product-preserving composite mode as the safe option, but add a creative image-generation branch.

---

## 1. Two visual creation modes

Plan two user-facing modes:

### دقیق / واقعی

* preserve the actual product pixels
* current crop + cutout + generated scene architecture
* appropriate for ecommerce / factual product representation

### خلاقانه

* use the uploaded image as a reference input to the image model
* allow the whole visual to be creatively redesigned
* product should remain recognizable, but exact details may change depending on style
* suitable for editorial, anime, illustration, surreal, 3D, cinematic, etc.

Keep the architecture flexible for a possible future third "experimental/artistic" level, but do not implement it unless necessary.

---

## 2. Multimodal Visual Planner

The planner should SEE the actual uploaded image, not only the text brief.

Plan a multimodal planner step that receives:

* uploaded product image
* product name and description
* brand
* price / promotion if provided
* target audience
* campaign objective
* selected campaign concept
* current visual style information

The planner should analyze useful visual properties such as:

* product category
* important visible identity
* dominant colors
* shape / silhouette
* logos or graphics that matter
* whether a person/mannequin is present
* overall visual character
* whether the source image is clean or messy
* whether particular creative recipes are unsuitable

It should return strict structured JSON.

Example conceptual output:

product_type: sweatshirt

visual_identity:

* navy and cream palette
* collegiate California graphic
* oversized silhouette

recommended_recipes:

1. 90s street editorial
2. anime campus scene
3. giant-product miniature-city concept

The planner must NOT invent factual product/business claims.

---

## 3. Visual Recipe system

Separate:

### STYLE = how the final image looks

Initial candidate library could include approximately:

* photoreal commercial
* fashion editorial
* anime
* manga / illustrated
* 3D render
* clay
* collage
* surreal
* cinematic
* retro
* watercolor / illustration
* neon
* modern Persian miniature-inspired
* vintage Iranian-poster-inspired

Do not use exact copyrighted artist/studio/movie imitation as the underlying taxonomy.

### TEMPLATE = what happens in the composition

Initial candidate library could include:

* hero product
* model / person using or wearing product
* product pedestal
* magazine cover / editorial
* giant product in miniature world
* cinematic environment
* floating product
* flat lay
* character poster
* illustrated scene
* product surrounded by relevant visual props
* surreal scale / environment

A VisualRecipe should combine:

style + template + transformation mode + product-preservation requirements + scene direction.

Design this as structured data rather than scattered prompt strings.

---

## 4. Smart mode and Custom mode

Plan two ways for users to choose.

### Smart mode — «آفرین پیشنهاد بده»

The multimodal planner examines the image and campaign and proposes exactly THREE materially different visual recipes.

The three proposals should intentionally differ in creative strategy.

For example:

1. realistic/editorial
2. stylized/illustrated
3. conceptual/surreal

Do not call an image-generation model yet.

These are cheap LLM/planner proposals only.

### Custom mode — «خودم انتخاب می‌کنم»

Let the user browse the full style and template libraries and combine them manually.

The planner may filter or warn about obviously unsuitable combinations, but advanced users should retain meaningful control.

Avoid exposing raw prompts or model parameters.

---

## 5. Permanent visual preview library

Users need to SEE what styles/templates mean.

Design a permanent Afarin preview-asset library.

These previews are generated once and committed/stored as product assets — never regenerated per user.

Plan:

* use the same small set of generic demo products for consistency
* style previews should hold composition mostly constant and vary style
* template previews should hold style mostly constant and vary composition
* store metadata linking each preview to its style/template ID
* frontend displays these as visual selection cards

Also design a small one-time developer script/tool that can generate these assets efficiently.

Consider:

* generating one preview per style/template initially
* optionally using contact-sheet generation and cropping if it proves reliable
* never requiring these preview generations during normal user requests

Do not manually search the internet for copyrighted reference images.

---

## 6. Actual creative generation flow

After the user selects ONE visual recipe:

Generate THREE real candidate images.

All three should share:

* same style
* same template
* same campaign concept
* same product/reference

But vary:

* composition
* camera angle
* pose where relevant
* lighting
* scene details

The purpose is to give the user three executions of the same chosen direction.

The user then selects their favorite.

Do not generate Story variants yet.

---

## 7. Winner adaptation

Once the user chooses one of the three candidates:

* use that candidate as the campaign key visual
* create ONE 9:16 Story adaptation/outpaint based on the chosen image
* Feed uses the chosen 4:5 key visual
* Carousel should reuse the key visual through crop/layout variations where possible
* do not generate three new carousel images

Normal expected image-call budget:

3 candidate images
+ 1 Story adaptation
= 4 paid image calls

Any automatic correction attempt must remain within a strict additional-call budget.

---

## 8. Cost guardrails

Design hard backend-enforced limits.

For example:

Normal campaign:

* planner: LLM only
* 3 candidate image calls
* 1 Story adaptation

Automatic failure correction:

* maximum ONE extra paid image call unless explicitly approved by the user

Never implement an open-ended regeneration loop.

Every additional user-requested generation must be explicit and traceable through generation_jobs.

Estimate expected cost using the configured image model.

---

## 9. Input-quality guardrail

Before paid image generation, evaluate whether the uploaded reference is usable.

Examples of problems:

* screenshot UI covering product
* product too small
* very low resolution
* multiple ambiguous products
* crop not confirmed
* important object partly outside crop

If quality is insufficient, stop BEFORE spending an image call and ask the user to fix/confirm the crop/reference.

Reuse the product extraction/cropping work already implemented where appropriate.

---

## 10. Product-preservation rules

The planner should generate category-specific identity constraints.

Examples:

Clothing:

* major colors
* garment silhouette
* graphic/logo identity

Cosmetics:

* packaging shape
* brand identity
* product colors

Food:

* dish identity
* visible major components

Creative mode may reinterpret the visual presentation, but must not knowingly add unsupported product claims or extra variants.

---

## 11. Image-generation prompt construction

Create a dedicated VisualPromptBuilder from the VisualRecipe.

Prompts should contain:

* campaign concept
* selected style
* template/composition
* relevant reference-image observations
* camera / lighting / mood
* preservation instructions
* explicit text-safe area when needed

Forbid:

* invented ad copy
* random readable text
* additional logos
* unsupported products/variants
* random watermarks

Persian campaign typography must continue to be rendered by Afarin / AdCanvas, not generated into the image.

---

## 12. Post-generation quality guard

Plan an automatic quality check after each generated candidate.

Prefer a cheap multimodal/vision model if technically appropriate.

Check things such as:

* product/reference still recognizable
* no obvious random text/logos
* no severe anatomy/artifact problems
* no duplicate products unless recipe calls for it
* composition suitable for an ad
* usable space for Afarin typography

Return structured scores/reasons.

Important:

Do NOT automatically regenerate every imperfect image.

A candidate may simply be rejected from the three if badly broken.

If too few usable candidates remain, allow at most ONE automatic repair image call within the campaign budget.

No unbounded loops.

---

## 13. Candidate-selection UX

Plan a screen after generation:

«کدوم رو بیشتر دوست داری؟»

Show all three images large enough to compare.

User chooses one.

Possible actions:

* انتخاب این تصویر
* ساخت سه نسخه جدید

If “سه نسخه جدید” is used, clearly treat it as three new paid image calls in the architecture, even though credits are not implemented yet.

---

## 14. Storage / persistence

Persist:

* planner result / VisualRecipe
* candidate images
* quality-check results
* selected candidate
* Story adaptation
* model/provider/cost/latency
* generation attempt number

Do not overwrite previous candidates when regenerating.

Campaign should maintain one selected/current key visual while preserving previous versions for traceability.

---

## 15. Provider architecture

Keep:
ImageProvider abstraction.

Initially continue using OpenRouter.

Evaluate whether the current Seedream model is suitable for reference-image creative transformations.

If another OpenRouter-supported image model is materially better for reference-image editing / creative transformations, compare and recommend it.

Do not hard-code provider/model assumptions into business logic.

Model remains environment-configurable.

---

## 16. Tests/evaluation

Create an evaluation set using our real examples:

* cosmetics
* sweatshirt
* restaurant/food

For each, test:

* smart-mode planner recommendations
* custom style/template selection
* three generated candidates
* identity preservation
* visual diversity
* quality guard
* winner selection
* Story adaptation
* regeneration cost semantics

Normal tests must use fake providers.

Paid live tests must only run explicitly.

---

## Explicitly out of scope

Do NOT add:

* video generation
* credits/payments
* subscriptions
* public marketplace
* social posting
* model selector UI
* raw prompt controls
* Phase 5 work

Do not change GPT-5-mini campaign-copy generation unless technically required.

---

Before finalizing the plan, identify genuine choices that require my input.

In particular, ask me before deciding:

* initial style library
* initial template library
* which multimodal planner model to use
* which image model to use for creative reference transformations
* exact auto-quality-check threshold / retry policy
* any change that increases the normal 4-image-call campaign budget

Show me the complete Phase 4B plan before implementing anything.
