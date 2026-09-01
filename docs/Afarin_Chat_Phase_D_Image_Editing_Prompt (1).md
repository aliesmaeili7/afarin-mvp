@AGENTS.md
@docs/MVP_SPEC.md
@docs/CHAT_ARCHITECTURE.md

# Afarin Chat — Phase D: Conversational Image Editing + Stronger Reference Handling

Phase A, B, and C are complete.

Current architecture:

```text
Chat UI
   ↓
ChatApi
   ↓
/api/chat
   ↓
persist user turn
   ↓
Orchestrator (0 or 1 call)
   ↓
Skill registry
   ├── Advertising
   ├── Education
   ├── General Image
   └── General Chat
   ↓
assistant messages + artifacts
```

Phase C dynamic activity states are also implemented:

```text
thinking
→ preparing_*
→ generating_image
→ optional finalizing
→ ready / failed
```

No extra model calls were added for activity states.

Before Phase D implementation, run the Phase C mock browser verification once with:

```bash
NEXT_PUBLIC_API_MODE=mock
npm run verify:chat
```

If that passes, proceed.

This task is **Phase D only**.

The goal is:

> A user should be able to continue working with a generated image naturally in chat
> by referring to it conversationally and asking for edits, revisions, or another
> version without re-uploading it or starting a new wizard.

Examples:

> روشن‌ترش کن

> صندوق گنج رو حذف کن

> تیتر رو عوض کن به «تمرین اعشار»

> همین رو با تم آبی بساز

> از همین عکس استفاده کن

> یکی دیگه شبیه همین بساز

> همین رو برای استوری عمودی کن

The user should not need to know artifact IDs, image-edit APIs, skill names, model names,
or domain-record IDs.

---

# 1. PHASE D SCOPE

Implement:

1. reliable reference-image resolution inside the current conversation
2. functional “Use as reference” behavior end-to-end
3. conversational references such as:
   - همین
   - همون
   - عکس قبلی
   - تصویر قبلی
   - آخری
   - this one
   - the previous image
4. a dedicated internal `image_edit` route / skill
5. direct image editing using the existing provider abstraction
6. revisions of generated images without duplicating user messages
7. optional target aspect-ratio changes when the provider supports them cleanly
8. preservation of artifact lineage
9. correct activity states for editing
10. safe fallback/clarification when a reference is ambiguous

Do NOT implement:

- voice
- music
- video
- subtitles
- long-term memory
- vector search
- cross-conversation asset library
- public sharing
- projects
- carousel planning
- educational multi-slide approval
- global brand system redesign
- deletion of `/create` or `/create/education`
- a new agent swarm
- a second prompt architect

---

# 2. PRODUCT PRINCIPLE

Afarin should feel conversational.

After generating an image, the user can say:

> بک‌گراندش رو روشن‌تر کن

and Afarin should understand that the user means the most relevant image in the
current conversation.

The user should not need to click “Edit” first.

Explicit “Use as reference” remains available when the user wants certainty.

---

# 3. REFERENCE PRIORITY

Resolve image references in this order:

```text
1. explicit reference_artifact_ids from the current outgoing turn
2. explicit attachment uploaded in the current turn
3. direct artifact reference supplied by a UI action
4. clearly referenced most-recent image in recent conversation context
5. most recent image artifact only when the language is unambiguous
6. otherwise ask a clarification
```

Do not randomly choose among several old images.

---

# 4. EXPLICIT REFERENCE CHIP

The existing “Use as reference” action must be fully functional.

When selected, show a removable composer chip:

```text
🖼 مرجع: آخرین تصویر ×
```

or a small thumbnail if already supported cleanly.

Outgoing message metadata:

```json
{
  "reference_artifact_ids": ["..."]
}
```

After successful send:
- clear the reference chip

On failed send before persistence:
- preserve/restore it

The server must re-check ownership.

Never trust client-supplied artifact IDs.

---

# 5. CURRENT-CONVERSATION ONLY

Phase D references are limited to the current conversation.

Do not implement:
- global media library
- searching other chats
- arbitrary cross-chat artifact reuse

If a user wants an image from another conversation, they can re-upload it for now.

---

# 6. REFERENCE RESOLUTION HELPER

Create a single backend reference resolver.

Conceptually:

```python
resolve_reference_artifacts(
    conversation_id,
    user_message,
    explicit_reference_ids,
    recent_messages,
    recent_artifacts,
) -> ReferenceResolution
```

It should return:
- resolved artifacts
- resolution source
- ambiguous yes/no
- clarification needed yes/no

Do not scatter “latest image” logic across skills.

---

# 7. OWNERSHIP

Every resolved artifact must satisfy:

- same authenticated user
- allowed conversation scope
- artifact exists
- artifact status is `ready`
- image type when an image edit is requested
- storage path can be resolved securely

Foreign references:
- return the existing generic not-found/clarify behavior
- never expose whether another user's artifact exists

No signed URL is a capability by itself.

---

# 8. ORCHESTRATOR ROUTE

Extend internal routes with:

```text
image_edit
```

Initial route set becomes:

```text
advertising
education
general_image
image_edit
general_chat
clarify
unsupported
```

This is internal only.

Do not display “image_edit skill” to users.

---

# 9. WHEN TO ROUTE TO IMAGE_EDIT

Examples:

```text
روشن‌ترش کن
پس‌زمینه رو آبی کن
اون ستاره رو حذف کن
تیترش رو عوض کن
این تصویر رو مینیمال‌تر کن
make this brighter
remove the text
change the background to blue
```

when there is a resolvable image reference.

→ `image_edit`

---

# 10. WHEN NOT TO ROUTE TO IMAGE_EDIT

User generated an ad, then says:

> یه نسخه دیگه با حال‌وهوای لوکس‌تر بساز

This may be better treated as another Advertising generation using prior
context/reference rather than a direct image edit.

User generated an educational poster, then says:

> یه نسخه دیگه برای فصل چهارم بساز

→ likely Education generation, not edit.

The Orchestrator should distinguish:

```text
modify this existing image
```

from:

```text
make another/new version based on prior context
```

Do not force all follow-ups through image editing.

---

# 11. EDIT VS REGENERATE

Use these conceptual rules:

## Edit

The user asks to modify a specific existing image:

- brighter
- darker
- remove object
- change text
- change color
- move/resize subject
- clean background
- replace element
- crop/reframe
- make portrait/square

→ `image_edit`

## Regenerate / another version

The user asks for a new creative result:

- another version
- one more ad
- try a different style
- make another educational poster
- give me 3 alternatives

→ originating creation skill where context is clear.

Do not over-engineer with a separate regenerate agent.

---

# 12. IMAGE EDIT MODEL

Use a dedicated config:

```text
CHAT_IMAGE_EDIT_MODEL
```

Recommended default:

```text
openai/gpt-image-2
```

Reason:
- already integrated
- strong Persian text behavior
- suitable for image generation/editing workflows
- keeps Phase D implementation simple

Do NOT change:
- Advertising image model
- Educational image model
- General image model

---

# 13. NO EXTRA PROMPT AGENT

Do NOT create:

```text
ImageEditPromptAgent
EditPlanner
PromptArchitect
Critic
```

Preferred flow:

```text
user edit request
+ reference image
+ optional active theme
+ requested output language/aspect ratio
→ ImageEditSkill
→ image provider edit/generate interface
```

If the current image provider abstraction needs a concise instruction, use the user's
natural text directly or the Orchestrator's existing structured output.

Do not add another LLM call.

---

# 14. ORCHESTRATOR STRUCTURED OUTPUT

Extend the Phase C structured schema minimally.

Potential fields:

```json
{
  "route": "image_edit",
  "reply_language": "fa",
  "artifact_language": "fa",
  "assistant_preamble": "باشه، روشن‌ترش می‌کنم.",
  "reference_artifact_ids": ["..."],
  "edit_instruction": "پس‌زمینه را روشن‌تر کن",
  "target_aspect_ratio": null
}
```

Do not include hidden reasoning or long edit plans.

`edit_instruction` should be concise and operational.

If the user explicitly selected a reference artifact, preserve that ID rather than
letting the Orchestrator replace it.

---

# 15. EXPLICIT REFERENCE + NO ORCHESTRATOR SHORTCUT

Do NOT automatically bypass the Orchestrator just because a reference image exists.

Example:

Reference image selected + user says:

> یه کپشن براش بده

This is `general_chat`, not `image_edit`.

Reference image selected + user says:

> روشن‌ترش کن

→ `image_edit`.

The reference is context, not route identity.

Explicit creation chips may still bypass routing as in Phase C.

---

# 16. IMAGE_EDIT SKILL

Add:

```text
ImageEditSkill
```

Input:
- owned reference image
- user edit request
- reply language
- artifact language
- optional active theme
- optional target aspect ratio

Output:
- new image artifact
- assistant message
- lineage metadata

Never mutate/overwrite the original image object.

Every edit creates a new artifact.

---

# 17. ARTIFACT LINEAGE

Persist lineage in `chat_artifacts.metadata_json`.

Example:

```json
{
  "skill": "image_edit",
  "source_artifact_ids": ["..."],
  "edit_instruction": "background brighter",
  "generation": 2
}
```

Keep it minimal.

Do not store hidden reasoning.

Do not overwrite the source artifact.

---

# 18. SOURCE DOMAIN METADATA

If the source image originally came from Advertising or Education, preserve useful
origin metadata on the new edited artifact.

Example:

```json
{
  "skill": "image_edit",
  "source_artifact_ids": ["..."],
  "source_domain": "education",
  "source_domain_id": "..."
}
```

The edited image itself is chat-owned unless there is a strong existing domain reason
otherwise.

Do NOT silently mutate:
- Campaign
- EducationalPost

---

# 19. STORAGE

Edited image output should normally be stored under:

```text
chat/{conversation_id}/artifacts/{token}.{ext}
```

Reason:
- edit is a Chat-owned derivative
- deleting chat can safely remove it
- original domain object remains untouched
- lineage points back to original artifact

Do not overwrite domain storage.

---

# 20. ACTIVE THEME DURING EDIT

The active conversation theme may influence an edit only when it makes sense.

Example:

> همین رو با تم خمیری من بساز

→ use active theme

But:

> فقط روشن‌ترش کن

should not unexpectedly restyle the entire image because a theme is active.

Rule:
- explicit edit instruction has priority
- active theme is secondary context
- do not inject theme aggressively into small corrective edits

---

# 21. TEXT EDITING INSIDE IMAGES

Support requests like:

> تیتر رو عوض کن به «تمرین اعشار»

The image edit model should receive:
- reference image
- exact replacement text
- artifact language
- instruction to preserve other visual structure where appropriate

For Persian:
- preserve exact Persian string
- do not transliterate
- do not rewrite title unnecessarily

Do not add frontend text overlays.

---

# 22. PERSIAN TEXT QUALITY

For image edits involving Persian text:
- preserve exact quoted Persian strings
- do not paraphrase
- do not translate unless asked

Do not route Persian typography edits to a model known to garble Persian.

---

# 23. ASPECT-RATIO CHANGES

Support conversational ratio changes only if the provider abstraction supports them
cleanly.

Examples:

> همین رو استوری کن
→ `9:16`

> مربعش کن
→ `1:1`

> برای فید 4:5 کن
→ `4:5`

Implement a small deterministic parser for obvious cases.

Do not use an extra LLM solely for ratios.

If the provider cannot safely reframe to the requested ratio:
- report that in PLAN
- do not fake support

---

# 24. “SAME STYLE” / “ANOTHER ONE”

Follow-ups such as:

> یکی دیگه شبیه همین بساز

should preferably use the originating generation skill when recent metadata clearly
identifies it:

```text
source route=education → Education
source route=advertising → Advertising
source route=general_image → GeneralImage
```

Use prior artifact/reference as context if supported.

Do not treat “another one” as a direct image edit by default.

---

# 25. FOLLOW-UP CONTEXT

The bounded Orchestrator context should include for recent artifacts:

```text
artifact id
artifact type
origin route
source domain metadata
created_at
aspect ratio
whether explicitly referenced this turn
```

Do not send:
- storage credentials
- signed URLs
- raw provider responses

---

# 26. AMBIGUOUS REFERENCES

If several images exist and the user's wording does not determine one reliably,
ask naturally rather than choosing randomly.

Example:

> کدوم تصویر رو می‌گی؟ اگه روی همون عکس «استفاده به‌عنوان مرجع» بزنی، دقیقاً همونو تغییر می‌دم.

---

# 27. NO-REFERENCE EDIT REQUEST

User:

> روشن‌ترش کن

but there is no image in conversation.

Reply naturally:

> کدوم تصویر رو می‌خوای تغییر بدم؟ یه عکس بفرست یا یکی از تصاویر گفتگو رو به‌عنوان مرجع انتخاب کن.

No image model call.

---

# 28. MULTIPLE REFERENCES

Phase D should support one primary image reference.

If multiple references are selected:
- allow only if the provider supports it cleanly
- otherwise ask the user to choose one

Do not build multi-image compositing in this phase.

---

# 29. USER-UPLOADED IMAGE EDITING

A current-turn uploaded image can be edited directly.

Example:

User uploads photo:

> پس‌زمینه رو سفید کن

→ `image_edit`

No need to first create a General Image artifact.

Ensure uploaded attachment is securely resolved server-side.

---

# 30. ADVERTISING PRODUCT BEHAVIOR

When editing an Advertising artifact:

> همین تبلیغ رو روشن‌تر کن
→ ImageEditSkill

> یکی دیگه تبلیغ بساز
→ AdvertisingSkill

The direct edit result is a new Chat artifact and must not rewrite the existing
Campaign record.

---

# 31. EDUCATION EDITS

Example:

> صندوق گنج رو حذف کن
→ ImageEditSkill

Then:

> یه پوستر دیگه درباره فصل چهارم بساز
→ EducationSkill

Do not mutate the original EducationalPost for direct image edits.

---

# 32. GENERAL IMAGE EDITS

General Image → edit:

```text
GeneralImage artifact
→ ImageEditSkill
→ new Chat artifact
```

Preserve the source artifact ID.

---

# 33. ACTIVITY STATES

Extend Phase C activity states minimally.

Add:

```text
preparing_edit
```

Persian:

```text
دارم تغییرات رو آماده می‌کنم…
```

English:

```text
Preparing your changes…
```

Then:

```text
preparing_edit
→ generating_image
→ ready
```

Do not invent fake sub-stages.

---

# 34. EDIT RESULT UI

The edited image appears as a normal `ImageArtifact`.

Do not show:
- source artifact IDs
- model names
- technical edit metadata

The original image remains visible in conversation.

---

# 35. RESULT ACTIONS

Edited artifacts support the same actions:

- Download
- Use as reference
- overflow

This enables iterative editing:

```text
original
→ edit 1
→ edit 2
→ edit 3
```

without a separate image editor.

---

# 36. RETRY

If image editing fails:

- original remains
- failed assistant/artifact state appears
- Retry uses the same source artifact
- no duplicate user message
- no duplicate reference selection required

Retry should preserve:
- source artifact
- edit instruction
- target aspect ratio
- artifact language

---

# 37. IDEMPOTENCY

Prevent duplicate paid edits from:
- double Send
- retry race
- browser resend

Reuse Phase C busy/turn protections.

---

# 38. TRANSACTION BOUNDARIES

Same Phase C pattern:

```text
persist user message
commit
↓
route/reference resolution
↓
persist generating assistant/artifact
commit
↓
background task with fresh DB session
↓
provider edit
↓
persist ready/failed
commit
```

Do not keep HTTP request DB sessions alive across provider calls.

---

# 39. PROVIDER INTERFACE

Inspect the current image-provider abstraction.

Prefer a generic reference-image request if it already supports one.

Do not special-case OpenRouter calls inside `ImageEditSkill`.

Before implementation confirm:
1. how GPT Image 2 editing/reference input is represented
2. whether one image reference is supported
3. whether output aspect ratio can be requested
4. whether exact text replacement can be passed
5. whether current cost telemetry works for edit calls

If needed, extend the provider abstraction minimally and generically.

---

# 40. NO MULTIMODAL ORCHESTRATOR UNLESS REQUIRED

The Orchestrator does not need image pixels for edit routing.

It receives:
- a ready image reference exists
- source route
- artifact metadata
- user text

The ImageEditSkill/provider receives the actual image.

Do not make the Orchestrator multimodal solely for Phase D.

---

# 41. GENERAL CHAT WITH IMAGE REFERENCE

Reference image +:

> یه کپشن براش بده

should remain `general_chat`.

Do not assume a reference implies image editing.

If actual visual understanding is required and the Orchestrator is text-only, do not
pretend it saw the pixels. Use known domain metadata where sufficient; otherwise leave
visual Q&A/caption-from-arbitrary-photo for a later capability.

---

# 42. USER LANGUAGE

Keep Phase C behavior:

- Persian default
- primarily English → English
- mixed Persian/English → Persian
- explicit reply-language override
- artifact language independent

Example:

> تیترش رو انگلیسی کن

Conversation reply: Persian  
Edited image text: English

---

# 43. EDIT INSTRUCTION PRESERVATION

The requested change must not be diluted.

Example:

> فقط پس‌زمینه رو روشن‌تر کن، به هیچ چیز دیگه دست نزن

Preserve:
- only background
- brighter
- keep everything else unchanged

Do not over-stylize because an active theme exists.

---

# 44. EXACT TEXT PRESERVATION

When the user provides quoted text:

> تیتر رو بکن «ماموریت کسرها»

preserve exactly:

```text
ماموریت کسرها
```

Do not:
- correct spelling unless asked
- translate it
- paraphrase it
- add punctuation

---

# 45. COST

Track image edit usage separately where existing telemetry allows:

```text
route=image_edit
model
latency
image usage/cost
conversation_id
user_message_id
assistant_message_id
source_artifact_id
```

No new analytics system.

---

# 46. FAILURE UX

Persian:

> نتونستم تغییرات رو روی تصویر اعمال کنم. دوباره امتحان کنم؟

English:

> I couldn't apply those changes to the image. Want me to try again?

Do not expose provider errors or model names.

---

# 47. FRONTEND

Keep frontend changes small.

Expected:
- reference chip state
- correct reference metadata
- generic `preparing_edit` activity
- lineage-compatible `ImageArtifact`
- retry
- optional small reference thumbnail

Do not build a separate image editor canvas.

The edit UI is the conversation.

---

# 48. NO FORM

Do NOT introduce brightness/background/object/ratio form fields.

Natural language remains the primary interface.

---

# 49. OPTIONAL ARTIFACT ACTION

If useful, add:

```text
ویرایش این تصویر
Edit this image
```

to the artifact overflow.

Behavior:
- set image as reference
- focus composer
- do not navigate away

Optional if existing “Use as reference” already covers it well.

---

# 50. MOCK MODE

Extend `mockChatApi` to support deterministic image-edit behavior.

Example:

```text
source artifact
→ “روشن‌ترش کن”
→ preparing_edit
→ generating_image
→ ready edited artifact
```

No paid calls.

---

# 51. ROUTER EVAL

Extend router eval with image-edit cases.

Persian:
- روشن‌ترش کن
- پس‌زمینه رو حذف کن
- تیترش رو عوض کن
- همین رو استوری کن
- یکی دیگه شبیه همین بساز

English:
- make this brighter
- remove the background
- change the title
- make this vertical
- make another one like this

Expected distinction:
- direct change → image_edit
- another version → originating skill when context supports it

Also test:
- no reference
- ambiguous reference
- explicit reference
- reference + caption request → general_chat

---

# 52. BACKEND TESTS

Add deterministic tests for:

Reference resolution:
- explicit current-conversation artifact
- latest unambiguous artifact
- foreign artifact rejected
- failed artifact rejected
- no image → clarify
- ambiguous images → clarify where necessary

Image edit:
- Persian direct edit
- English direct edit
- mixed Persian edit
- artifact language separate
- exact quoted replacement text preserved

Provider boundary:
- `preparing_edit`
- `generating_image` immediately before provider call
- ready artifact

Lineage:
- source remains unchanged
- new artifact created
- source IDs stored
- edit stored under `chat/`

Retry:
- no duplicate user message
- same source reused
- same instruction preserved

Security:
- cannot edit foreign artifact
- cannot resolve foreign storage object

Regression:
- Education
- Advertising
- General Image
- General Chat
- Phase C activity tests

No paid calls in CI.

---

# 53. FRONTEND TESTS

Test:
- Use as reference creates correct chip
- remove chip
- outgoing message includes artifact id
- chip clears after success
- chip restores on send failure
- `preparing_edit` copy fa/en
- polling transitions to generating image
- ready renders new image
- retry preserves reference context
- original artifact remains visible
- no raw artifact IDs shown
- mobile chip layout

---

# 54. PLAYWRIGHT

Extend mock `verify:chat` with:

Desktop:
1. select source image
2. Use as reference
3. send Persian edit
4. preparing_edit
5. generating_image
6. edited artifact ready
7. original still visible
8. edit result selectable as new reference
9. retry failed edit

Mobile:
1. reference chip
2. send edit
3. activity state
4. edited result

No live credits required.

---

# 55. LIVE SMOKE TEST

After stub/CI tests pass, run a minimal real-provider check:

1. create or use one existing image
2. select as reference
3. send:
   > پس‌زمینه رو کمی روشن‌تر کن
4. verify:
   - route=image_edit
   - correct reference
   - generating activity
   - new image ready
   - refresh preserves original + edit
5. second edit:
   > تیتر رو بکن «تمرین اعشار»
6. verify Persian text quality

Do not run many expensive generations.

---

# 56. DELETE BEHAVIOR

Deleting the conversation:
- deletes chat-owned edited artifacts
- deletes chat-owned uploads
- does not delete original Advertising/Education domain objects
- does not delete domain-owned storage

---

# 57. DB MIGRATION

Try to use:
- `chat_messages.metadata_json`
- `chat_artifacts.metadata_json`
- artifact status
- storage path

No migration should be necessary.

Only propose one if there is a concrete correctness need.

---

# 58. DOCUMENTATION

After implementation update:
- `docs/CHAT_ARCHITECTURE.md`
- `docs/MVP_SPEC.md`
- `AGENTS.md`

Mark:

```text
Phase A — Chat UX: done
Phase B — Persistence: done
Phase C — Orchestrator + initial skills: done
Phase D — Conversational image editing/reference handling: done
```

Keep memory, voice, music, video, subtitles, projects, cross-chat assets, and
multi-slide education as future work.

---

# 59. SUCCESS CRITERIA

Phase D is complete when:

1. “Use as reference” works end-to-end.
2. Server validates ownership of every referenced artifact.
3. “روشن‌ترش کن” edits the intended image.
4. English edit requests behave in English.
5. No reference → clarification, no paid call.
6. Ambiguous reference → clarification, not random selection.
7. Direct changes route to `image_edit`.
8. “Another version” can route back to the originating skill.
9. One primary image reference works cleanly.
10. Original artifacts remain untouched.
11. Every edit produces a new artifact.
12. Artifact lineage persists.
13. Edited images are chat-owned.
14. Advertising/Education domain records are not mutated by direct edits.
15. Persian replacement text is preserved exactly.
16. Reply language and artifact language remain separate.
17. `preparing_edit → generating_image → ready` reflects real execution.
18. Retry does not duplicate user messages.
19. Retry preserves source reference and instruction.
20. Existing Phase A/B/C flows remain green.
21. No new prompt agent exists.
22. No extra Orchestrator call beyond Phase C rules.
23. React still knows only `ChatApi`.
24. `/create` and `/create/education` remain unchanged.
25. CI has no paid provider calls.
26. One controlled live image-edit smoke test passes.

---

# 60. FIRST RESPONSE — PLAN ONLY

Before implementation, inspect the actual current repository and return a concrete
Phase D plan covering:

1. current `reference_artifact_ids` flow from UI to backend
2. current artifact metadata and storage ownership
3. current Orchestrator schema and how to add `image_edit`
4. current image-provider API and whether GPT Image 2 reference-image editing is already supported
5. proposed `CHAT_IMAGE_EDIT_MODEL`
6. exact edit vs regenerate routing rules
7. exact reference-resolution rules
8. explicit-reference behavior
9. latest-artifact behavior
10. ambiguity handling
11. user-uploaded image editing
12. artifact-language handling
13. exact quoted text preservation
14. target aspect-ratio parsing/support
15. active-theme behavior during small edits
16. ImageEditSkill design
17. edited-artifact storage path
18. artifact lineage metadata
19. Advertising/Education source-domain behavior
20. delete semantics
21. retry semantics
22. concurrency/idempotency
23. activity-state integration
24. mock-mode behavior
25. backend tests
26. frontend tests
27. router eval additions
28. Playwright additions
29. live smoke test
30. exact files to add/change
31. whether any migration is required
32. any provider limitation that prevents a requested Phase D behavior
33. any blocking question

Do NOT implement until I approve the plan.

Keep Phase D narrow:

> conversational reference resolution + one clean image-edit capability.

Do not expand it into memory, video, music, voice, subtitles, projects, or a visual
image editor.
