@AGENTS.md
@docs/MVP_SPEC.md
@docs/CHAT_ARCHITECTURE.md

# Afarin Chat — Phase C: Persian-Native Orchestrator + Initial Skills

Phase A and Phase B are complete and approved.

Phase A established the conversational workspace.

Phase B established persistent, authenticated, user-owned conversations:

```text
Chat UI
   ↓
ChatApi
   ↓
/api/chat
   ↓
chat_conversations
chat_messages
chat_artifacts
storage
```

The persistent HTTP path has been manually verified with real signed-in accounts,
including:

- lazy conversation creation
- Persian messages
- refresh persistence
- active theme persistence
- attachments + signed URLs
- rename
- pin
- archive / restore
- delete
- logout / login
- cross-account ownership protection
- generic 404 for foreign conversations
- fresh-database Alembic migration

Advertising generation at `/create` and Educational generation at
`/create/education` are currently separate working systems.

DO NOT replace or break those existing flows.

This task is **Phase C**:

> Make the chat actually intelligent by adding one Persian-native conversational
> Orchestrator that routes each user turn to the appropriate Afarin capability.

Initial capabilities:

```text
Afarin Chat
     ↓
Orchestrator
     ├── Advertising skill
     ├── Educational skill
     ├── General Image skill
     └── General conversation
```

The user still interacts with one thing:

> Afarin.

The user should not need to know that agents, skills, models, campaigns, or
educational posts exist internally.

---

# 1. NON-NEGOTIABLE ARCHITECTURE

The frontend must continue to know only:

```text
Chat UI → ChatApi
```

It must NOT call:

- advertising endpoints directly
- educational endpoints directly
- image providers directly
- OpenRouter directly
- Supabase directly
- internal agents directly

Backend:

```text
/api/chat
   ↓
Chat turn service
   ↓
Orchestrator / explicit routing
   ↓
Skill registry
   ├── AdvertisingSkill
   ├── EducationSkill
   └── GeneralImageSkill
```

For ordinary conversation, the Orchestrator itself may return the response without
calling another LLM.

Do NOT create an agent swarm.

Do NOT create:

```text
Orchestrator
→ advertising agent
→ prompt architect
→ copy agent
→ critic
→ image prompt improver
→ image model
```

Existing Advertising and Educational specialist agents should remain the only
specialist LLM calls inside those existing skills.

---

# 2. MAIN PRODUCT PRINCIPLE

The composer is the product.

A user can write:

> برای این کفش یه تبلیغ شیک بساز

or:

> برای کلاس ششم یه پست درباره کسرها درست کن

or:

> یه تصویر از تهران آینده بساز

or:

> برای این عکس یه کپشن دوستانه بنویس

and Afarin figures out what to do.

Explicit `+` actions still exist for users who want more control:

- Advertising
- Educational post
- Generate image

Those action chips are hints, not separate applications.

---

# 3. LANGUAGE BEHAVIOR — CRITICAL

Afarin is **Persian-native by default**.

The conversational Orchestrator must sound like a native modern Persian-speaking
creative assistant.

This is not merely UI RTL.

It is a product behavior.

## Core rule

If the user's latest message is primarily Persian:

→ reply in Persian.

If the user's message is Persian with embedded English terms:

→ reply in Persian.

Examples:

> برای این محصول یه luxury ad با vibe مینیمال بساز

Reply in Persian.

Terms such as:

- Instagram
- luxury
- minimal
- GPT
- Seedream
- caption
- Story
- Clay
- Reel
- 3D

must NOT cause the assistant to switch to English.

Only reply in English when:

1. the user's latest message is primarily written in English, OR
2. the user explicitly asks Afarin to answer in English.

Example:

User:

> Make a playful educational post about fractions.

Afarin replies in English.

---

# 4. CONVERSATION LANGUAGE != ARTIFACT LANGUAGE

Keep these separate:

```text
conversation_reply_language
requested_artifact_language
```

Example:

User:

> برای این عکس یه کپشن انگلیسی بنویس

Afarin's conversational response should still be Persian:

> حتما، یه کپشن انگلیسی برات می‌نویسم.

But the caption itself should be English.

Likewise:

> انگلیسی جواب بده و یه پست فارسی بساز

may mean:

```text
conversation_reply_language = en
artifact_language = fa
```

Do not conflate these.

---

# 5. LANGUAGE DETECTION

Implement a small backend helper.

Do not spend an LLM call solely determining whether a message is Persian or English.

Recommended behavior:

```text
latest user text
   ↓
explicit reply-language request?
   ├── yes → obey
   └── no
        ↓
clearly primarily English?
   ├── yes → en
   └── no → fa
```

The key product rule is intentionally:

> If it is not clearly English, default to Persian.

This is a Persian-first product.

A mixed Persian/English message defaults to Persian.

Use the frontend Phase A direction logic as inspiration, but language detection and
text direction are not exactly the same concern.

Backend should produce:

```json
{
  "reply_language": "fa"
}
```

where useful.

---

# 6. ORCHESTRATOR PERSONALITY

The Orchestrator should sound:

- natural
- concise
- helpful
- conversational
- creative
- confident without being verbose

Avoid stiff Persian such as:

> درخواست شما دریافت گردید.

Prefer:

> حتما، یه نسخه تمیز و مینیمال برات می‌سازم.

Avoid:

> جهت انجام درخواست لطفاً تصویر محصول را بارگذاری نمایید.

Prefer:

> عکس محصول رو هم بفرست تا بتونم تبلیغش رو درست بسازم.

Do not overuse emoji.

Do not sound like customer support.

Do not expose architecture.

Never tell a normal user:

- "I selected the education skill"
- "The orchestrator routed the request"
- "I am calling GPT Image 2"
- "The Creative Agent returned..."

unless the user explicitly asks about technical implementation.

---

# 7. ORCHESTRATOR RESPONSIBILITY

The Orchestrator should do only:

1. understand the user's current intent
2. use recent conversation context
3. select an appropriate capability
4. determine whether a clarification is genuinely required
5. extract only lightweight routing/output information
6. produce a short natural conversational response when appropriate

It should NOT:

- rewrite the Educational Agent's final image prompt
- rewrite Advertising's final image prompt
- create another image prompt architecture
- critique specialist outputs
- call another planning agent
- summarize the whole conversation every turn

---

# 8. ORCHESTRATOR CALL BUDGET

At most:

> **ONE Orchestrator LLM call per user turn.**

That does not include specialist calls already required by Advertising/Education.

Examples:

```text
No explicit action:
User
→ 1 Orchestrator call
→ EducationSkill
→ existing EducationalAgent
→ GPT Image 2
```

```text
Explicit education chip:
User
→ EducationSkill directly
→ existing EducationalAgent
→ GPT Image 2
```

The explicit action chip makes routing deterministic.

Do NOT spend a routing LLM call merely to rediscover:

```json
{
  "explicit_skill_hint": "education"
}
```

---

# 9. INITIAL ROUTES

The intelligent router should conceptually support:

```text
advertising
education
general_image
general_chat
clarify
unsupported
```

These are internal values only.

Do not expose them as product terminology.

---

# 10. ROUTING EXAMPLES

## Advertising

User uploads a product image:

> برای این یه تبلیغ لوکس اینستاگرامی بساز

→ Advertising

## Education

> یه پست آموزشی درباره درصد برای کلاس ششم بساز

→ Education

## General image

> یه تصویر سه‌بعدی از یه شهر آینده بساز

→ General image

## General chat

> یه کپشن دوستانه برای عکس کافه بهم بده

→ General chat

No image model needed.

## General creative question

> چه فرقی بین کپشن رسمی و صمیمی هست؟

→ General chat

## English

> Make an educational post about decimal numbers.

→ Education

Assistant conversational language: English.

## Mixed Persian

> برای این محصول یه minimal Instagram ad بساز

→ Advertising

Assistant conversational language: Persian.

## Ambiguous

> یه چیزی برام بساز

→ clarification

Natural Persian:

> حتما. می‌خوای تبلیغ باشه، پست آموزشی یا یه تصویر معمولی؟

Do not guess when the missing information fundamentally changes the task.

## Unsupported future feature

> برام یه آهنگ بساز

Voice/music/video are NOT Phase C capabilities.

Do not pretend they exist.

Return a natural response explaining that this capability is not connected yet.

---

# 11. EXPLICIT ACTION HINTS

Phase B already stores:

```json
{
  "explicit_skill_hint": "education"
}
```

Possible Phase C hints:

```text
advertising
education
general_image
```

When one exists:

- trust it as the primary route
- do not call routing LLM
- still perform deterministic input validation
- still respect language behavior
- still inspect required attachments/context

Do NOT permanently mark the conversation as belonging to that skill.

A conversation may use different capabilities over time.

---

# 12. EXPLICIT ROUTE PREFLIGHT

Each skill should have deterministic preflight rules before spending money.

## Advertising

If the existing advertising workflow requires a product/reference image and none is
available:

Do NOT call the Advertising Creative Agent.

Reply naturally:

> عکس محصول رو هم بفرست تا تبلیغ رو بر اساس خودش بسازم.

## Education

If there is enough subject/content to work from:

Proceed.

Do not ask:
- grade
- mood
- color
- theme

unless genuinely required.

The Educational Agent should infer reasonable choices.

## General image

If the request contains enough visual subject information:

Proceed.

If user only says:

> یه تصویر بساز

ask what they want.

---

# 13. ORCHESTRATOR INPUT

Do not send the entire user's lifetime conversation every turn.

Build a bounded context.

Recommended conceptual input:

```text
latest user message
recent messages
current active theme
current turn attachments
explicit skill hint
selected/reference artifact metadata
recent artifacts
available capabilities
reply language
```

Start with something like:

- latest user message
- previous ~10–12 messages
- recent ~5 artifacts

Make the limits configurable if appropriate.

Do not introduce a conversation-summary LLM in Phase C.

Long-history summarization/retrieval can come later.

---

# 14. ORCHESTRATOR SHOULD BE TEXT-ONLY

Routing does not need multimodal image understanding.

The Orchestrator should receive attachment metadata such as:

```json
{
  "type": "image",
  "name": "shoe.jpg",
  "available": true
}
```

It does not need to analyze the pixels merely to decide:

> this is probably an advertising request.

The downstream Advertising skill is already multimodal.

Avoid paying for multimodal routing.

---

# 15. ORCHESTRATOR STRUCTURED OUTPUT

Use strict structured output.

Do NOT parse arbitrary prose.

Conceptually:

```json
{
  "route": "education",
  "reply_language": "fa",
  "artifact_language": "fa",
  "assistant_preamble": "باشه، یه پست آموزشی تمیز و جذاب برات می‌سازم.",
  "needs_clarification": false,
  "clarification_question": null,
  "reference_artifact_ids": []
}
```

For normal conversation:

```json
{
  "route": "general_chat",
  "reply_language": "fa",
  "artifact_language": null,
  "assistant_message": "...",
  "needs_clarification": false,
  "clarification_question": null
}
```

For clarification:

```json
{
  "route": "clarify",
  "reply_language": "fa",
  "assistant_message": "...",
  "needs_clarification": true
}
```

Do not include:

- reasoning
- chain-of-thought
- confidence essays
- internal deliberation

Design the exact schema according to current backend conventions.

---

# 16. ORCHESTRATOR SYSTEM PROMPT

The actual Orchestrator prompt should itself be strongly Persian-first.

Use something close to this as the behavioral core:

```text
تو آفرین هستی؛ دستیار خلاق و محاوره‌ای فارسی‌زبان.

وظیفه تو این است که بفهمی کاربر چه می‌خواهد و درخواست او را به قابلیت مناسب آفرین
هدایت کنی.

زبان پیش‌فرض تو فارسی طبیعی و محاوره‌ای است.

اگر پیام اخیر کاربر عمدتاً فارسی است، فارسی جواب بده.
وجود کلمات و اصطلاحات انگلیسی داخل یک جمله فارسی باعث نمی‌شود زبان پاسخ را
انگلیسی کنی.

فقط وقتی انگلیسی جواب بده که:
۱. پیام اخیر کاربر عمدتاً انگلیسی باشد؛ یا
۲. کاربر صریحاً بخواهد که به انگلیسی جواب بدهی.

بین زبان گفتگو و زبان محتوایی که کاربر می‌خواهد ساخته شود فرق بگذار.
مثلاً اگر کاربر به فارسی یک کپشن انگلیسی بخواهد، پاسخ مکالمه‌ای تو فارسی است ولی
زبان کپشن انگلیسی است.

فارسی تو باید طبیعی، کوتاه، دوستانه و امروزی باشد.
از فارسی رسمی، اداری یا ترجمه‌ای پرهیز کن.

نام مدل‌ها، agentها، skillها، routing و جزئیات فنی داخلی را به کاربر نگو مگر اینکه
خودش درباره پیاده‌سازی فنی سؤال کند.

اگر اطلاعات موجود برای انجام کار کافی است، سؤال اضافه نپرس.
فقط وقتی سؤال بپرس که نبود اطلاعات واقعاً جلوی انجام درست درخواست را می‌گیرد.

از پیام‌های اخیر، تم فعال، فایل‌های پیوست و آثار اخیر برای فهم عبارت‌هایی مثل
«همین»، «قبلی»، «با همون تم» و موارد مشابه استفاده کن.

قابلیت‌های فعلی آفرین:
- ساخت تبلیغ
- ساخت پست آموزشی
- ساخت تصویر عمومی
- گفتگو و کمک متنی

قابلیت‌هایی مثل ویدیو، موسیقی، صدا و زیرنویس هنوز در این مرحله فعال نیستند.

فقط خروجی ساختاریافته مطابق schema برگردان.
هیچ chain-of-thought یا استدلال داخلی را برنگردان.
```

Adapt wording if necessary, but preserve this behavior.

---

# 17. MODEL CONFIGURATION

The Orchestrator must have its own config entry.

Conceptually:

```text
CHAT_ORCHESTRATOR_MODEL
```

Do NOT hardcode a model in route/service code.

Before implementation, inspect the current text-model/provider infrastructure and
recommend the most appropriate already-supported, low-latency, low-cost text model.

Do not introduce another provider stack merely for the Orchestrator.

Prefer the provider abstraction already used by Afarin.

In your PLAN response, state:

- exact proposed model
- why
- expected call count
- how token/cost usage will be tracked

Do NOT change the existing Advertising or Educational model configuration.

---

# 18. SKILL REGISTRY

Create a small explicit registry.

Conceptually:

```python
SKILLS = {
    "advertising": AdvertisingSkill(...),
    "education": EducationSkill(...),
    "general_image": GeneralImageSkill(...),
}
```

Do not implement routing as giant conditionals spread across API/service files.

Potential structure:

```text
backend/app/services/chat/
├── service.py
├── ownership.py
├── language.py
├── orchestrator.py
├── orchestrator_prompt.py
├── skills/
│   ├── __init__.py
│   ├── base.py
│   ├── registry.py
│   ├── advertising.py
│   ├── education.py
│   └── general_image.py
```

Adapt to existing conventions.

---

# 19. SKILL CONTRACT

Use a lightweight internal interface.

Conceptually:

```python
class ChatSkill(Protocol):
    name: str

    async def execute(
        self,
        context: SkillContext,
    ) -> SkillResult:
        ...
```

`SkillContext` should provide only what the skill needs:

```text
conversation
current user message
recent conversation context
active theme
current attachments
selected reference artifacts
reply language
requested artifact language
user / principal
```

Result conceptually:

```text
assistant text
artifacts
domain metadata
```

---

# 20. ADVERTISING SKILL — REUSE EXISTING PIPELINE

Do NOT rebuild advertising.

The Advertising skill is an adapter around the currently working advertising
Creative Agent/service.

Current advertising architecture must remain:

```text
photo + natural brief
   ↓
one multimodal Creative Agent
   ↓
1 or 3 complete advertising concepts
   ↓
Seedream
```

Do NOT reintroduce:

- Creative Director
- three-direction picker
- Prompt Architect
- separate copy agent
- Accurate mode
- preserved_product_composite
- extra Story image generation

The existing Creative Agent owns creative interpretation.

Seedream continues receiving its final prompt unchanged.

---

# 21. ADVERTISING CHAT INPUT

The user should not be forced back into the advertising form.

Chat may provide:

```text
user message
product image attachment/reference
active theme/context
```

The skill adapter should translate this into the minimum input required by the
existing advertising service.

Do NOT add an LLM merely to fill form fields.

If current services require fields such as:

- objective
- audience
- mood
- product information

use existing reasonable defaults where possible and pass the user's natural-language
brief as the main instruction.

The existing multimodal Creative Agent can inspect the product.

If a truly required value is missing, ask one concise clarification.

---

# 22. ADVERTISING IMAGE COUNT

Preserve current behavior:

- default = 1 image
- user may request 3
- 3 means 3 independent finished advertisements
- NOT candidate directions
- NOT carousel slides

Detect a clearly stated count deterministically where practical.

Examples:

> سه تا تبلیغ بساز

→ `3`

> سه نسخه متفاوت بساز

→ `3`

Otherwise default to `1`.

Do not ask about image count if the user did not mention it.

---

# 23. ADVERTISING RESULTS IN CHAT

Advertising results should become chat artifacts.

The skill may continue creating the existing advertising/campaign domain records
internally.

Do NOT migrate advertising data into `chat_*`.

Instead link the chat artifact/message to the existing domain record via metadata.

Example:

```json
{
  "skill": "advertising",
  "campaign_id": "...",
  "visual_attempt_id": "..."
}
```

Persist generated image(s) into `chat_artifacts` with storage paths or references
that the chat ownership layer can safely resolve.

If the existing advertising output already lives in storage, do not unnecessarily
copy bytes if a secure reference strategy can be used.

But the chat artifact must remain resolvable later even after refresh.

---

# 24. ADVERTISING COPY IN CHAT

Advertising currently generates:

- on-image Persian text
- feed caption
- Story text
- CTA/hashtags
- visual metadata

Do not dump every field as a giant technical response.

Chat should present the finished image first.

A concise assistant message may include relevant copy such as caption/CTA if that is
useful, but do not expose internal JSON.

Keep raw/domain data in metadata for later UI actions.

---

# 25. EDUCATION SKILL — REUSE CURRENT EDUCATIONAL PIPELINE

Do NOT rebuild education.

Current educational behavior:

```text
natural prompt
+ optional style/theme
   ↓
EducationalAgent
   ↓
final_prompt
   ↓
GPT Image 2
   ↓
finished educational poster
```

Important existing decisions that MUST remain:

- one image in Phase C unless current education behavior already supports otherwise
- image model paints the finished poster including Persian text
- no AdCanvas overlay
- no CTA/badge overlay
- no advertising text layers
- no educational copy editor
- final image prompt goes to the image model unchanged
- 1:1 current educational aspect ratio unless the user clearly requests another
  supported size and current infrastructure safely supports it

Do not reintroduce the previous overlay architecture.

---

# 26. EDUCATION CHAT INPUT

Input should remain natural-language first.

Example:

> برای کلاس ششم یه پست سه‌بعدی درباره عددهای اعشاری درست کن

The user should NOT need separate form fields for:

- grade
- title
- subtitle
- mood
- palette

The EducationalAgent should infer reasonable details.

The active conversation theme should become style context when relevant.

---

# 27. EDUCATIONAL THEME HANDOFF

Phase B stores a generic semantic theme snapshot:

```json
{
  "id": "...",
  "source": "...",
  "name": "...",
  "style_json": { ... }
}
```

EducationSkill should translate this into the existing EducationalAgent theme/style
input.

Do not make chat depend directly on the educational theme database.

If `style_json` is empty for a Phase A theme fixture, use the theme name/source as
light style guidance rather than inventing a complex schema.

Existing educational saved themes may be bridged where cleanly possible, but do not
couple the generic `chat_conversations.active_theme_json` to an educational FK.

---

# 28. EDUCATION RESULTS IN CHAT

The existing EducationalPost may remain the domain execution record.

Persist linkage in message/artifact metadata:

```json
{
  "skill": "education",
  "educational_post_id": "..."
}
```

The finished poster should be a `chat_artifact`.

Chat should render it with the existing generic `ImageArtifact` component.

Do not render advertising-specific result sections.

---

# 29. GENERAL IMAGE SKILL

Phase C should add a minimal general image capability because the `+` menu already
contains "Generate image".

This should NOT use Advertising or Education merely as a workaround.

Create `GeneralImageSkill`.

Input:

```text
user visual request
optional active theme
optional image reference if existing provider supports it cleanly
requested artifact language
```

For first implementation, use an existing image-generation provider abstraction.

Before coding, inspect current providers and recommend whether GeneralImage should
use:

- GPT Image 2, or
- another already-integrated image model

Do NOT change Advertising's model.

Do NOT change Education's model.

The model choice for GeneralImage must be a dedicated config:

```text
GENERAL_IMAGE_MODEL
```

---

# 30. GENERAL IMAGE PROMPTING

Keep the first implementation simple.

Do not create another multi-agent prompt pipeline.

Preferred:

```text
natural user request
+ semantic active theme if relevant
+ explicit language/text requirements
→ one concise prompt preparation step ONLY if necessary
→ image model
```

If the image model can follow the natural request directly, avoid an extra LLM call.

If prompt preparation is genuinely needed, consider whether the already-made
Orchestrator structured result can provide a small `generation_instruction` field
without another call.

Do NOT create a GeneralImage Prompt Architect.

---

# 31. GENERAL IMAGE PERSIAN TEXT

If the user explicitly asks for readable Persian text inside an image, prefer the
image model/provider already demonstrated to handle Persian text well.

Do not route Persian typography requests to a model known to garble Persian merely
because it is cheaper.

This is a product-quality requirement.

---

# 32. GENERAL CHAT

General conversation should cover text-only creative help such as:

- captions
- hashtags
- rewriting
- brainstorming
- explanations
- content ideas
- simple social-media strategy questions

Do NOT create a separate GeneralChatAgent if the Orchestrator model can answer the
request in the same call.

Preferred:

```text
User
→ Orchestrator
→ route=general_chat + assistant_message
```

Total text-model calls: 1.

---

# 33. GENERAL CHAT LANGUAGE

Same Persian-first rules apply.

Examples:

User:

> برای یه کافه یه کپشن صمیمی بده

→ Persian caption unless another artifact language is requested.

User:

> Give me three caption options for a coffee shop.

→ English.

User:

> سه تا caption انگلیسی بده

→ conversational framing may be Persian, generated captions English.

---

# 34. DO NOT FORCE IMAGE GENERATION

The Orchestrator must distinguish:

> درباره پست آموزشی چه ایده‌ای داری؟

from:

> یه پست آموزشی بساز

The first is conversation/brainstorming.

The second requests generation.

Likewise:

> برای این محصول چه سبک تبلیغی خوبه؟

should not automatically spend money generating an ad unless the user actually asks
to make one.

Bias toward avoiding paid generation when intent is advisory.

---

# 35. COST-GATED EXECUTION

Every paid skill call should happen only after:

1. the user clearly requested generation
2. required inputs exist
3. authentication/business rules permit generation

Reuse current free-campaign/credit/business rules where applicable.

Do not invent a separate chat billing system.

If Advertising/Education currently enforce generation limits in service/API layers,
reuse the underlying enforcement rather than bypassing it.

Chat must not become a backdoor around limits.

---

# 36. AUTH / GENERATION GATING

Phase B persistent HTTP chat is authenticated.

Keep that architecture.

If an anonymous user's draft returns after login:

- persist it normally on Send
- route via Phase C

Do not create anonymous model-generation ownership.

Do not duplicate signup/login UI inside the backend.

---

# 37. CHAT TURN TRANSACTION BOUNDARIES

Do not hold a single DB transaction open across long external model calls.

Recommended flow:

```text
persist user message
commit
   ↓
route/preflight
   ↓
persist assistant generation placeholder/status if needed
commit
   ↓
external specialist/image calls
   ↓
persist final assistant message/artifacts/domain links
commit
```

Use the repo's existing generation/job patterns where appropriate.

Do not pretend DB + provider + object storage are atomic.

Failures must leave a recoverable, understandable chat state.

---

# 38. ASSISTANT MESSAGE STATES

Phase B has user/assistant roles only.

For Phase C, assistant generation may need status metadata.

Prefer `metadata_json`, e.g.:

```json
{
  "status": "generating",
  "route": "education"
}
```

then:

```json
{
  "status": "ready",
  "route": "education"
}
```

or:

```json
{
  "status": "failed",
  "route": "education",
  "retryable": true
}
```

Do not add a new message role solely for loading.

---

# 39. ARTIFACT STATES

Phase B already supports:

```text
generating
ready
failed
```

Use these.

For generation:

1. create artifact placeholder when useful
2. render existing `GenerationPlaceholder`
3. on success update artifact to `ready`
4. persist storage path + dimensions
5. on failure update to `failed`

Do not fabricate progress percentages.

---

# 40. SYNC VS ASYNC EXECUTION

Inspect how Advertising/Education currently handle generation.

Do not introduce a new queue architecture solely for Phase C if current generation is
request/response and works reliably.

However, the chat UI should support the existing loading state cleanly.

If generation calls can exceed normal request limits, report that in PLAN and reuse
existing job/polling infrastructure if present.

Do not build a new distributed job system without evidence it is necessary.

---

# 41. CHAT API TURN SEAM

The frontend should keep one main method:

```ts
sendMessage(conversationId, input)
```

In HTTP mode Phase C, that becomes a real conversational turn.

Conceptual response:

```ts
type ChatTurnResult = {
  conversation: Conversation
  userMessage: ChatMessage
  assistantMessage?: ChatMessage | null
  artifacts?: ConversationArtifact[]
}
```

Adapt to actual Phase B types instead of creating needless parallel types.

React should not care which skill ran.

---

# 42. API ENDPOINT STRATEGY

Prefer extending:

```text
POST /api/chat/conversations/{id}/messages
```

into the real turn endpoint.

And for first send:

```text
POST /api/chat/conversations
```

can:
- create conversation
- persist first message
- execute the same turn service

Avoid requiring frontend:

```text
create chat
→ call orchestrator endpoint
→ call skill endpoint
```

The backend should own the turn.

If current API design benefits from an internal shared `handle_chat_turn()` service,
use it from both first-send and existing-conversation routes.

---

# 43. FIRST-SEND BEHAVIOR

Current Phase B:

```text
POST /conversations
→ conversation + first user message
```

Phase C:

```text
POST /conversations
→ create conversation + first user message
→ handle turn
→ assistant response/artifact
→ return complete ChatTurnResult
```

Do not create the conversation twice.

If the skill/provider fails after the user message has persisted:

- conversation remains
- user message remains
- failed assistant/artifact state should be represented naturally
- retry should not duplicate the user message

Design explicit retry semantics.

---

# 44. RETRY

A failed generation should offer:

> دوباره امتحان کن

Retry should reference the original user message/turn.

Do NOT create a duplicate visible user message.

Backend may expose conceptually:

```text
POST /api/chat/messages/{message_id}/retry
```

or another clean chat-scoped retry mechanism.

Do not overbuild arbitrary replay of every message type.

Phase C only needs retry for failed generation/tool execution.

PLAN the exact route based on current API conventions.

---

# 45. CONVERSATIONAL ACKNOWLEDGEMENT

For paid generation, show a short acknowledgement before/with loading:

Education:

> باشه، یه پست آموزشی جذاب برات می‌سازم.

Advertising:

> حتما، یه تبلیغ تمیز و حرفه‌ای بر اساس همین محصول می‌سازم.

General image:

> باشه، تصویرش رو می‌سازم.

Keep it short.

Do not write two paragraphs before starting generation.

---

# 46. CONTEXTUAL REFERENCES

Phase C should support basic references to recent context without a full memory
system.

Examples:

> با همون تم بساز

→ use active theme.

> برای همین عکس تبلیغ بساز

→ use current turn attachment or a selected "Use as reference" artifact.

> تصویر قبلی رو استفاده کن

→ resolve the most recent relevant image artifact if unambiguous.

> همونو دوباره بساز

→ may use recent route + request metadata if clear.

If ambiguous because several images exist, ask which one.

Do not silently pick a random old artifact.

---

# 47. "USE AS REFERENCE" CHIP

Phase A already has artifact action/context concept.

Make it functional.

When user chooses:

> Use as reference

the next outgoing message metadata should include:

```json
{
  "reference_artifact_ids": ["..."]
}
```

The orchestrator/skill context receives those IDs.

Ownership must be rechecked server-side.

Never trust a client-provided artifact ID without verifying it belongs to the same
user/conversation as allowed by product behavior.

After send, clear next-turn reference chips unless current UX intentionally keeps
them.

---

# 48. CROSS-CONVERSATION ARTIFACT REFERENCES

For Phase C, keep this conservative.

Default:
- current conversation artifacts only.

Do not implement a global asset library or arbitrary cross-chat references yet.

If the user uploads the file again, that is fine.

Cross-conversation reuse can be Phase D/E.

---

# 49. PERSIST DOMAIN LINKS

Skill results may link to existing domain records.

Use `metadata_json`.

Examples:

Advertising:

```json
{
  "skill": "advertising",
  "campaign_id": "...",
  "visual_attempt_ids": ["..."]
}
```

Education:

```json
{
  "skill": "education",
  "educational_post_id": "..."
}
```

General image:

```json
{
  "skill": "general_image"
}
```

Do not create nullable `campaign_id`, `education_post_id`, etc. columns on
`chat_messages`.

---

# 50. CHAT ARTIFACT STORAGE

Use the Phase B secure chat storage path for chat-owned artifacts when copying is
needed:

```text
chat/{conversation_id}/artifacts/{token}.{ext}
```

But first inspect whether existing domain-generated image paths can safely be
referenced without byte duplication.

Prefer:
- one physical object
- secure ownership-aware reference

over duplicating every generated image.

However:

- chat refresh must still work
- user ownership must remain enforceable
- deleting a chat must not accidentally delete an image still owned by a campaign or
  educational post

Design ownership semantics carefully.

In PLAN response, explicitly state whether skill artifacts are:
1. referenced from existing domain storage, or
2. copied into chat storage

and why.

---

# 51. DELETION SEMANTICS

Because chat may reference campaign/education outputs:

Deleting a conversation should delete:
- chat_messages
- chat_artifact rows
- chat-owned uploaded attachments
- chat-owned generated objects

It should NOT automatically delete:
- an existing Campaign
- an existing EducationalPost
- domain-owned image storage

unless the current product already defines that ownership relationship.

Metadata links are references, not cascade ownership.

---

# 52. GENERAL CHAT PERSISTENCE

General-chat assistant responses must be persisted as normal assistant messages.

Example:

```text
user message
assistant message
```

No artifact required.

Store language.

Metadata may simply be:

```json
{
  "route": "general_chat"
}
```

Do not store the raw Orchestrator prompt or hidden reasoning.

---

# 53. CLARIFICATION PERSISTENCE

Clarification is a normal assistant message.

Example:

User:

> یه چیزی برام بساز

Assistant:

> دوست داری تبلیغ باشه، پست آموزشی یا یه تصویر معمولی؟

Persist both.

Next turn uses recent context normally.

Do not introduce a wizard state machine for clarification.

---

# 54. UNSUPPORTED CAPABILITY RESPONSE

Unsupported requests should remain useful and concise.

Example:

User:

> برام موزیک بساز

Persian response:

> فعلاً ساخت موسیقی به آفرین وصل نشده. می‌تونم ایده، متن یا کانسپت موسیقی رو برات آماده کنم.

If user then asks for concept/text:

→ general chat.

Do not show a dead-end error.

---

# 55. SAFETY / PROVIDER ERRORS

Reuse existing safety/provider error mappings where appropriate.

Normal user sees:

> نتونستم این تصویر رو بسازم. می‌خوای با یه توصیف کمی متفاوت دوباره امتحان کنیم؟

Not:

```text
OpenRouter 400
provider moderation failure
JSON schema parse error
```

Log internal detail server-side.

Do not expose provider keys/models in error messages.

---

# 56. STRUCTURED OUTPUT FAILURE

Orchestrator output parsing must be robust.

Use provider-supported structured output / schema if existing abstraction supports it.

If invalid structured output occurs:

- one bounded repair/retry may be acceptable only if current provider abstraction
  already supports it cheaply
- do not create an unbounded retry loop
- otherwise fail gracefully with safe fallback

Do not route randomly after a parse failure.

In PLAN, explain exact failure behavior.

---

# 57. ROUTER EVALUATION DATASET

Create a small deterministic routing eval fixture.

Examples should include at least:

## Persian
- advertising
- education
- general image
- general chat
- clarification
- unsupported

## English
same categories

## Mixed
examples with:
- Instagram
- luxury
- caption
- Clay
- 3D
- GPT

## Explicit action hints
verify zero orchestrator routing call.

## Artifact language
- Persian conversation asking for English caption
- English conversation asking for Persian poster

Keep expected fields explicit.

This is not a giant benchmark.

Start around 30–50 carefully chosen cases.

---

# 58. ORCHESTRATOR TESTING

Unit tests should NOT require live model calls.

Mock the text-model provider and test:

- prompt/context construction
- schema parsing
- language fallback
- explicit hint bypass
- clarification
- unsupported response
- route dispatch
- bounded context
- no hidden reasoning persistence

Optionally provide a developer-only eval CLI for live model evaluation.

Do not make CI depend on OpenRouter.

---

# 59. LIVE ORCHESTRATOR EVAL CLI

If the repository already has eval CLI patterns, add:

```text
python -m ... chat-router-eval
```

or equivalent.

It should report:

- case
- expected route
- actual route
- reply language
- artifact language
- latency
- token usage
- estimated/actual cost
- pass/fail

No automatic image generation in router eval.

The eval should exercise only the Orchestrator.

Keep live eval opt-in.

---

# 60. COST TRACKING

Track Orchestrator usage separately from specialist generation.

At minimum capture:

```text
model
input tokens
output tokens
estimated/actual cost
latency
route
conversation_id
message_id
```

Do not expose this in normal UI.

If existing `generation_jobs` or cost telemetry can cleanly represent chat
orchestration, reuse it.

If not, add the smallest telemetry abstraction necessary.

Do NOT invent a full analytics platform.

In PLAN response, identify the existing cost-tracking mechanism and exact reuse.

---

# 61. LATENCY TRACKING

Measure wall-clock segments independently:

```text
orchestrator_ms
skill_ms
image_generation_ms
total_turn_ms
```

Do not sum provider-reported values and call that user wait time if execution overlaps
or includes storage/network overhead.

This is developer telemetry only.

---

# 62. FRONTEND LOADING EXPERIENCE

When user sends:

1. user message appears immediately
2. assistant acknowledgement/loading appears
3. artifact placeholder renders for generation
4. result replaces/updates placeholder
5. on failure show retry

For general chat:
- assistant text appears when response returns
- streaming is optional, not required for Phase C

Do not block Phase C on token streaming.

---

# 63. STREAMING

Streaming general chat would be nice but is NOT required in Phase C.

Prioritize:

- correct routing
- correct persistence
- correct skill integration
- stable artifacts
- good Persian

If existing stack already supports streaming cleanly, PLAN it separately.

Do not introduce SSE/WebSocket complexity unless it materially improves the current
implementation.

---

# 64. IMAGE GENERATION REQUEST TIME

Image generation may take significantly longer than normal chat.

Use the existing Phase A:

> دارم تصویرت رو می‌سازم...

or equivalent based on reply language.

Persian:

> دارم تصویرت رو می‌سازم...

English:

> I'm creating your image...

No fake percentage.

Elapsed time may remain if real.

---

# 65. CONVERSATION TITLE

Phase B deterministic title stays.

Do NOT add another title-generation LLM call.

If the Orchestrator structured result can cheaply include a better
`suggested_conversation_title` in its existing call, that may be used only for a new
conversation.

Do not overwrite user-renamed titles.

Track whether a title is auto-generated vs manually renamed only if current schema can
do this cleanly; otherwise leave deterministic Phase B titles for now.

Title polish is secondary.

---

# 66. GENERAL IMAGE COUNT

Default:

```text
1 image
```

If user explicitly requests multiple images and provider/current cost model supports
it safely, Phase C may support up to 3.

But do not introduce complex multi-image semantics.

For Advertising preserve its existing 1-or-3 behavior.

For Education preserve one image unless current service supports otherwise.

---

# 67. ACTION CHIP AFTER SEND

Current Phase A behavior clears the primary creation-action chip after Send.

Keep that.

Reason:
the chip is an explicit hint for one turn, not persistent conversation identity.

Active theme remains persistent.

Reference artifact chips are next-turn context and should also clear after successful
send.

Attachments clear after successful send.

On send failure before persistence/execution:
restore relevant composer context where safe.

---

# 68. ORCHESTRATOR CONTEXT SECURITY

Never inject:

- signed URL secrets
- storage credentials
- auth tokens
- internal user IDs unnecessarily

into the Orchestrator prompt.

For attachments/artifacts, provide safe descriptive metadata.

Specialist skills can resolve owned storage references server-side.

---

# 69. PROMPT INJECTION / USER CONTENT

Treat uploaded/image text and user content as content, not system instructions.

The Orchestrator system prompt owns routing behavior.

Do not let a user's attached caption or image metadata override:
- available skill list
- internal secrecy rules
- system language policy
- security rules

No need for an elaborate separate security agent.

---

# 70. BACKEND FILE BOUNDARIES

Prefer:

```text
chat API
→ chat turn service
→ orchestrator
→ skill registry
→ skill adapter
→ existing domain service
```

Do not let `chat.py` API route contain large routing logic.

Do not let skill adapters query arbitrary DB tables directly if existing domain
services already own that behavior.

---

# 71. EXISTING DOMAIN API VS SERVICE REUSE

Do NOT make internal HTTP calls from Chat backend to Afarin's own Advertising or
Education endpoints.

Reuse Python service/domain functions directly.

Bad:

```text
ChatSkill
→ HTTP localhost /api/education/generate
```

Good:

```text
ChatSkill
→ existing education service
```

But preserve business validation, quota, cost tracking, and ownership rules that the
public endpoint currently applies.

If important logic currently lives only in API routes, refactor it into shared service
functions carefully without changing old route behavior.

---

# 72. ADVERTISING / EDUCATION REGRESSION SAFETY

Existing routes must behave exactly as before.

Add regression tests proving:

```text
/create advertising path
/create/education education path
```

still call the same services and produce expected results.

Do not alter their frontend UX for Phase C.

---

# 73. GENERAL IMAGE IS CHAT-ONLY FOR NOW

Do not add another standalone `/create/image` page in Phase C.

General image is initially a Chat capability.

If later demand justifies a dedicated route, that can be added independently.

---

# 74. MODEL / PROVIDER CONFIG ISOLATION

Expected conceptual config:

```text
CHAT_ORCHESTRATOR_MODEL=...
GENERAL_IMAGE_MODEL=...
```

Existing:

```text
ADVERTISING_IMAGE_MODEL=...
EDUCATIONAL_IMAGE_MODEL=openai/gpt-image-2
```

or whatever exact names exist in repo.

Do not accidentally route all skills through one model config.

---

# 75. PROVIDER ABSTRACTION

Reuse existing provider clients.

Do not:
- add direct requests in `skills/*.py`
- hardcode OpenRouter URL
- duplicate retry logic
- duplicate cost parsing

If current provider abstraction cannot perform a required structured text call,
extend it minimally and generically.

---

# 76. PERSIAN TYPOGRAPHY QUALITY

For generated images containing Persian text:

Education:
- keep GPT Image 2 behavior already proven to work.

General image:
- choose/configure a capable model for Persian when readable Persian text is required.

Advertising:
- preserve the existing Advertising model/config unless this Phase exposes an actual
  blocker. Do not silently change it.

Do not add frontend Persian text overlays to compensate inside chat.

---

# 77. ADVERTISING STORY / FEED BEHAVIOR

Do not rearchitect advertising rendering.

Current advertising result semantics remain:

- finished feed ads
- Story composed according to existing workflow
- caption/Story text produced by Creative Agent
- no extra Story Seedream call

Chat may initially show the main image artifact and concise associated text.

Do not port the entire old campaign result page into the chat message.

---

# 78. USER REQUESTS EXISTING FORM-SPECIFIC OPTIONS

If user naturally asks:

> سه تا بساز

honor it where supported.

If user asks:

> تم رو خودت انتخاب کن

use auto/no explicit theme.

If user asks a visual instruction:

> بک‌گراند خیلی خلوت باشه

pass that through the relevant skill as natural guidance.

Do not recreate form controls in the conversation.

---

# 79. SKILL-SPECIFIC CLARIFICATION

The skill preflight may return a clarification without model generation.

Example Advertising:

> عکس محصول رو بفرست.

Example General Image:

> دوست داری تصویر چی باشه؟

Example Education:
Usually enough context can be inferred, so ask less.

Clarification must be persisted as assistant message.

The next turn should be rerouted normally using context.

Do not create a hidden "awaiting field X" wizard unless truly necessary.

---

# 80. ROUTING FOLLOW-UP CONTEXT

The Orchestrator must understand follow-ups.

Conversation:

User:
> یه پست آموزشی درباره اعشار بساز

Assistant:
> [poster]

User:
> حالا یه کپشن کوتاه براش بده

Second turn should usually be `general_chat`, not another image-generation Education
call.

Conversation:

User:
> برای این کفش تبلیغ بساز

Assistant:
> [ad]

User:
> یه نسخه دیگه هم بساز

Should infer Advertising from recent context.

Use recent route/artifact metadata.

Do not require user to re-select the action chip.

---

# 81. BASIC FOLLOW-UP ROUTE SIGNAL

Recent messages may include metadata:

```json
{
  "route": "advertising"
}
```

Include recent route metadata in orchestrator context so follow-ups like:

> یکی دیگه بساز

can be interpreted.

Do not permanently set a conversation route.

---

# 82. IMAGE EDITING IS NOT FULLY PHASE C

Requests like:

> این تصویر رو روشن‌تر کن

are important, but full image-editing support can be Phase D unless the currently
chosen General Image provider already supports reference-image edits with almost no
additional architecture.

For Phase C:

- resolve the reference correctly
- if existing provider abstraction supports edits cleanly, PLAN whether to include a
  minimal image-edit path
- otherwise return a natural "editing is not connected yet" response rather than
  pretending regeneration is an edit

Do not expand Phase C into a large editing project.

---

# 83. FIRST PHASE C SCOPE PRIORITY

Priority order:

1. Orchestrator + language behavior
2. General chat
3. Education through Chat
4. Advertising through Chat
5. General image through Chat
6. robust persistence/error/retry
7. follow-up routing
8. optional minimal reference editing only if nearly free architecturally

Do not start with future capabilities.

---

# 84. API RESPONSE LANGUAGE

Backend error messages shown in Chat should follow the conversation reply language
where practical.

Do not translate low-level API validation infrastructure globally.

For chat-turn domain errors, support natural Persian/English messages.

---

# 85. CHAT MESSAGE METADATA

Use minimal metadata.

Examples:

User message:

```json
{
  "explicit_skill_hint": "education",
  "reference_artifact_ids": []
}
```

Assistant message:

```json
{
  "route": "education",
  "status": "ready",
  "educational_post_id": "..."
}
```

Do not persist:
- full prompts unless existing audit requirements require them elsewhere
- chain-of-thought
- entire Orchestrator request/response
- provider secrets

Specialist domain tables may continue storing their normal prompt/debug data.

---

# 86. DATABASE CHANGES

Try to implement Phase C using the Phase B schema.

Do NOT add a migration just because a JSON field is convenient.

Possible no-migration implementation:
- chat message route/status in `metadata_json`
- domain links in `metadata_json`
- artifacts already support state
- theme snapshot already exists

Only propose a migration if there is a concrete correctness requirement.

Explain it in PLAN before implementing.

---

# 87. CONCURRENCY

Prevent duplicate generation from:

- double Send
- browser retry
- client timeout retry

Inspect existing idempotency/job patterns.

At minimum:
- disable Send while the turn is running client-side
- ensure a retry endpoint does not duplicate the user message
- avoid starting two paid skill executions for the same persisted turn

If necessary, use a turn/job id stored in metadata or an existing generation-job
mechanism.

Do not overengineer distributed locks without evidence.

---

# 88. QUOTA CONCURRENCY

Chat must reuse the same quota/cost enforcement as direct Advertising/Education.

Two simultaneous chat requests must not trivially bypass free-generation limits.

Inspect existing transaction/locking behavior and mention this explicitly in PLAN.

---

# 89. FRONTEND CHANGES

Phase C frontend changes should be small because the Phase A/B architecture was
designed for this.

Expected changes mainly in:

- `httpChatApi`
- `useChatSession`
- sending/loading/retry logic
- artifact hydration
- optional result copy presentation

Do not redesign the sidebar/composer/account UI.

Do not add Advertising/Education-specific React flows.

---

# 90. ARTIFACT UI

Generic `ImageArtifact` remains.

It should work whether metadata route is:

- advertising
- education
- general_image

Optional subtle source/context labels are okay if helpful, but do not show internal
skill names.

Do not make separate `EducationArtifact.tsx` and `AdvertisingArtifact.tsx` unless
there is a genuinely different rendering need.

---

# 91. TEXT RESULTS

For text-only general chat, persist/display the assistant content as normal.

For Advertising copy accompanying an image, prefer normal assistant content plus image
artifact.

For Education, usually image plus short assistant framing is enough.

Do not build a technical JSON inspector in normal chat.

---

# 92. LOGGING

Server logs should make a turn debuggable.

Include:

```text
conversation id
user message id
assistant message id
route
skill
model/provider
status
latency
cost
domain record id
```

where applicable.

Do not log auth tokens.

Be cautious about logging full private user prompts if current logging policy avoids
that.

---

# 93. DEVELOPER DEBUGGING

If there is already dev-only tooling, optional Phase C developer metadata may show:

- route
- orchestrator latency
- specialist latency
- model
- cost

Do NOT expose this in production UI.

Do not build a large debug dashboard for this phase.

---

# 94. TEST MATRIX — LANGUAGE

Add deterministic tests for:

| User message | Reply language |
|---|---|
| `یه پست آموزشی بساز` | fa |
| `یه minimal ad بساز` | fa |
| `برای Instagram کپشن بده` | fa |
| `Make an ad for this.` | en |
| `Please answer in English: برای این کپشن بده` | en |
| `فارسی جواب بده: Make an ad` | fa |

Also test:

Persian conversation requesting an English artifact.

English conversation requesting a Persian artifact.

---

# 95. TEST MATRIX — ROUTING

At minimum:

### Advertising
- explicit chip
- inferred Persian request
- inferred English request
- missing product image
- 1 image default
- 3 explicitly requested

### Education
- explicit chip
- inferred Persian
- inferred English
- active theme
- no unnecessary clarification

### General image
- explicit chip
- inferred request
- Persian text request
- insufficient description

### General chat
- caption
- hashtags
- brainstorming
- question about content
- advisory advertising question should NOT generate

### Clarify
- genuinely vague create request

### Unsupported
- music
- video
- voice/subtitle as generation requests

---

# 96. TEST MATRIX — EXPLICIT HINT BYPASS

This is important.

Mock the Orchestrator provider and assert it is NOT called for:

```text
explicit_skill_hint=advertising
explicit_skill_hint=education
explicit_skill_hint=general_image
```

when the request passes deterministic preflight.

If clarification is required, do it without the router LLM where possible.

---

# 97. TEST MATRIX — PERSISTENCE

Test:

1. user message persists before external call
2. assistant ready message persists
3. artifact persists
4. refresh returns both
5. failed generation persists failed state
6. retry does not duplicate user message
7. successful retry updates/adds correct assistant result
8. route/domain metadata survives refresh

---

# 98. TEST MATRIX — SECURITY

- cannot reference another user's artifact
- cannot use another user's attachment
- cannot retry another user's message
- cannot resolve another user's generated artifact
- Chat skill cannot bypass domain ownership
- public direct Advertising/Education APIs remain protected as before

---

# 99. TEST MATRIX — REGRESSION

Run all existing:

- Advertising tests
- Education tests
- Chat Phase A tests
- Chat Phase B tests
- database security tests
- frontend tests
- typecheck
- `verify:chat`

No paid calls in CI.

---

# 100. LIVE INTEGRATION CHECKS

After unit/integration tests pass, manually test with real providers in a controlled
dev account:

## General chat
Persian + English.

## Education
One Persian educational poster with Persian text.

## Advertising
One product photo, Persian request, one ad.

## General image
One Persian prompt.

Verify:
- correct reply language
- correct route
- image appears after refresh
- no duplicate messages
- cost recorded
- domain record link exists
- old `/create` and `/create/education` still work

Do not run repeated expensive generations unnecessarily.

---

# 101. ROUTER EVAL BEFORE RELEASE

Run live router eval separately from image-generation smoke tests.

The router eval should NOT generate images.

Review failures manually.

Particularly inspect Persian conversational quality:

Bad:

> درخواست شما پردازش خواهد شد.

Good:

> حتما، همین سبک رو نگه می‌دارم.

The quality bar is not merely route accuracy.

---

# 102. DOCUMENTATION

After implementation and verification, update:

- `docs/CHAT_ARCHITECTURE.md`
- `docs/MVP_SPEC.md`
- `AGENTS.md`

Mark:

```text
Phase A — Chat UX: done
Phase B — Persistence: done
Phase C — Orchestrator + initial skills: done
Phase D — richer conversational editing/reference workflows: future
```

Document skill boundary and one-call routing rule.

Do not claim future voice/music/video are implemented.

---

# 103. PHASE D — OUT OF SCOPE

Do NOT implement in this task:

- full image editing UX
- long-conversation memory/summarization
- vector retrieval
- cross-conversation asset library
- voice generation
- subtitles
- music
- video
- carousel planner
- educational multi-slide approval workflow
- public conversation sharing
- Projects
- replacing/deleting old Advertising/Education routes
- major homepage redesign

---

# 104. DESIRED FINAL ARCHITECTURE AFTER PHASE C

```text
                       AFARIN CHAT UI
                             │
                             ▼
                         ChatApi
                             │
                             ▼
                         /api/chat
                             │
                             ▼
                     Chat Turn Service
                             │
             ┌───────────────┴────────────────┐
             │                                │
             ▼                                ▼
     Explicit action hint?              No explicit hint
             │                                │
             │                                ▼
             │                       Persian Orchestrator
             │                         one LLM call max
             │                                │
             └───────────────┬────────────────┘
                             ▼
                       Skill Registry
             ┌───────────────┼────────────────┐
             ▼               ▼                ▼
       Advertising       Education       General Image
          Skill             Skill             Skill
             │               │                │
             ▼               ▼                ▼
       existing ad       existing edu      existing
       services          services          image provider
             │               │                │
             └───────────────┼────────────────┘
                             ▼
                    Assistant + Artifacts
                             │
                             ▼
                      chat persistence
```

General text conversation may end at the Orchestrator:

```text
User
→ Orchestrator
→ persisted assistant text
```

---

# 105. SUCCESS CRITERIA

Phase C is complete when:

1. Persian is the default conversational language.
2. Primarily English messages receive English replies.
3. Mixed Persian/English messages remain Persian.
4. Conversation and artifact language are handled separately.
5. Explicit action chips bypass the routing LLM.
6. Unhinted requests are routed by one Orchestrator call maximum.
7. General chat uses only that Orchestrator call.
8. Education generation works from Chat using the existing Educational pipeline.
9. Advertising generation works from Chat using the existing Advertising pipeline.
10. General image generation works through its own minimal skill.
11. Chat React components still know only `ChatApi`.
12. Existing `/create` Advertising remains unchanged.
13. Existing `/create/education` remains unchanged.
14. Assistant messages persist.
15. Generated artifacts persist and survive refresh.
16. Failed generations produce a natural retryable state.
17. Retry does not duplicate the visible user message.
18. Active theme reaches relevant skills.
19. Current-turn attachments reach relevant skills.
20. Owned reference artifacts are safely resolvable.
21. Cross-account references are rejected.
22. No chain-of-thought is stored or returned.
23. No unnecessary secondary prompt agents are introduced.
24. Cost and latency are measurable by route/model.
25. CI contains no live paid calls.
26. Live smoke tests pass for general chat, Education, Advertising, and General Image.
27. Existing Advertising/Education regression suites remain green.

---

# 106. FIRST RESPONSE — PLAN ONLY

Before implementation, inspect the actual Phase B repo.

Then give me a concrete Phase C implementation plan covering:

1. current `/api/chat` first-send and existing-message flow
2. current `ChatApi` / `httpChatApi` result contract
3. current Advertising service entrypoint that Chat should reuse
4. current Educational service entrypoint that Chat should reuse
5. current image-provider abstraction
6. current text-model abstraction
7. proposed Orchestrator model and config key
8. why that model is appropriate for Persian routing/general chat
9. exact structured Orchestrator schema
10. exact Persian-first system prompt approach
11. deterministic language detection
12. explicit action-hint bypass
13. bounded conversation context
14. skill registry and interfaces
15. AdvertisingSkill adapter
16. EducationSkill adapter
17. GeneralImageSkill design and proposed model/config
18. General-chat execution path
19. artifact-language handling
20. active-theme handoff
21. attachment handoff
22. recent/reference-artifact handling
23. domain-record linkage strategy
24. whether generated domain images are referenced or copied into chat storage
25. deletion/ownership implications of that choice
26. chat-turn persistence transaction boundaries
27. loading/generating/ready/failed lifecycle
28. retry semantics
29. quota/free-generation enforcement
30. idempotency/concurrency protection
31. error mapping
32. structured-output failure behavior
33. cost/latency telemetry
34. router evaluation dataset
35. backend tests
36. frontend tests
37. regression tests for existing Advertising/Education
38. live smoke-test procedure
39. exact files to add
40. exact files to change
41. whether any DB migration is genuinely required
42. risks/landmines that could complicate Phase D
43. any blocking question

Do NOT implement until I approve the plan.

The implementation should stay narrow:

> one Persian-native Orchestrator, one skill registry, adapters around the existing
> working creation systems, and one stable ChatApi seam.
