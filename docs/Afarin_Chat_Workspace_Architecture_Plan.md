# Afarin Conversational Workspace & Orchestrator Plan

## Status

**Purpose:** Build a chat-first Afarin experience that can become the primary interface for the product.

**Recommended branch:** `feature/chat-workspace`

**Current product paths to preserve while this branch is tested:**
- Advertising generation
- Educational post generation
- Existing authentication, storage, model-provider, cost, and timing infrastructure

**Important:** Do not delete the existing advertising or educational flows during the first chat implementation. The chat should initially become a new UX/orchestration layer over working capabilities. Retire old entry flows only after the chat experience is proven.

---

# 1. Product vision

Afarin becomes a **Persian-first conversational creative workspace**.

The user should not need to decide which internal page, form, agent, skill, or model to use. They simply tell Afarin what they want.

Examples:

> برای این کفش یه تبلیغ مینیمال و لوکس بساز.

> برای کلاس ششم یه پست بامزه درباره اعداد اعشاری درست کن.

> همین تصویر رو روشن‌تر کن و شخصیت رو کوچیک‌تر کن.

> با تم خمیری و بازیگوش من ادامه بده.

> برای این عکس یه کپشن دوستانه بنویس.

The user interacts with **one chatbot**. Behind it is an **Orchestrator** that chooses the appropriate Afarin skill.

```text
                         AFARIN CHAT
                              │
                              ▼
                       ORCHESTRATOR
                              │
            ┌─────────────────┼──────────────────┐
            │                 │                  │
            ▼                 ▼                  ▼
      Advertising         Education        General creative
         skill              skill               skill
            │                 │                  │
            ▼                 ▼                  ▼
      current ad          educational        text/image
      generation          generation         utilities
      services            services
            │                 │
            └─────────────────┼──────────────────┘
                              │
                              ▼
                          ARTIFACTS
                    image / text / future media
```

Future skills can include voice, subtitles, music, video, image editing, carousel creation, educational series, localization, and other creator tools without redesigning the main UX.

---

# 2. Architecture principle: Orchestrator + Skills, not an agent swarm

Use the term **Skill** for capabilities exposed to the Orchestrator.

A skill may internally use an LLM/agent when intelligence is necessary, but avoid chains of agents talking to agents.

Avoid:

```text
Orchestrator → agent → another agent → prompt agent → copy agent → model
```

Prefer:

```text
Orchestrator → skill → only the model/service calls that skill actually needs
```

Examples:

```text
Orchestrator → advertising skill → existing advertising Creative Agent → image model
Orchestrator → education skill → existing Educational Agent → GPT Image 2
Orchestrator → caption skill → one text model
```

Goals:
- lower latency
- lower cost
- easier debugging
- fewer duplicated prompts
- clearer ownership of behavior

---

# 3. Orchestrator language behavior — non-negotiable

The Orchestrator is **native Persian by default**.

Its normal personality and system prompt should be written with Persian users as the primary audience.

## 3.1 Persian default

If the user's latest message is primarily Persian, or Persian with ordinary embedded English terms, reply in **natural conversational Persian**.

Good:

> حتما. یه مسیر تمیز و رنگی می‌سازم که برای دانش‌آموزها جذاب باشه ولی زیادی کودکانه نشه.

Bad:

> درخواست شما دریافت شد. یک محتوای آموزشی متناسب با مخاطب مورد نظر تولید خواهد شد.

The Persian should be:
- conversational
- modern
- concise
- warm but not overfriendly
- not bureaucratic
- not literal machine translation

## 3.2 English only when the user writes in English

If the user's latest message is primarily written in English, reply in English.

User:

> Make an elegant Instagram ad for this shoe.

Assistant:

> Sure — I’ll keep the shoe prominent and use a clean editorial direction.

## 3.3 Mixed Persian/English

If Persian is the conversational structure, stay in Persian even when the message includes English terms:

> برای این محصول یه luxury ad با vibe مینیمال بساز

Reply in Persian.

Terms such as `Instagram`, `GPT`, `Clay`, `minimal`, `luxury`, `caption`, `Seedream`, `reel`, brand names, and model names do not make the message English.

## 3.4 Explicit override

If the user explicitly asks to answer in another language, follow that request.

Keep separate concepts for:
- **conversation language** — language Afarin uses to talk to the user
- **artifact/output language** — language requested for a generated caption/post/etc.

Example: a Persian user can ask for an English caption. Afarin still talks to them in Persian while generating the caption in English.

---

# 4. Orchestrator personality

The Orchestrator should:
- understand informal Persian
- tolerate spelling mistakes and casual language
- infer obvious intent instead of asking unnecessary questions
- ask only when an important missing detail blocks execution
- prefer doing over explaining
- keep acknowledgements short
- avoid exposing models/skills/internal architecture unless asked
- avoid corporate support language
- resolve conversational references such as `همین`, `قبلی`, `اون عکس`, `با همون تم`, `روشن‌ترش کن`

Good:

> باشه، با همون تم ادامه می‌دم و این بار پس‌زمینه رو روشن‌تر می‌کنم.

Bad:

> Skill مناسب برای درخواست شما انتخاب شد.

---

# 5. UX principle

The **conversation is the workspace**.

The user sees:
- conversation history
- messages
- attachments
- active theme
- generated images
- generated text
- future audio/video artifacts

They do not see a collection of separate mini-apps.

A conversation should preserve enough context that natural follow-ups work:

> همینو روشن‌تر کن

> تیتر قبلی بهتر بود

> از همون تم استفاده کن

> حالا یه نسخه برای استوری بساز

---

# 6. Routes

Recommended:

```text
/chat
/chat/[conversationId]
```

`/chat` = new conversation.

`/chat/[conversationId]` = saved conversation with history, active theme, and artifacts.

Do not build a wizard inside `/chat`.

---

# 7. Desktop layout

```text
┌──────────────────────────────────────────────────────────────┐
│ Sidebar               │ Conversation                         │
│                       │                                      │
│ + New chat            │                                      │
│ Search                │          message history             │
│                       │                                      │
│ Today                 │                                      │
│ • Math decimals       │                                      │
│ • Shoe campaign       │                                      │
│                       │                                      │
│ Previous              │                                      │
│ • Science post        │                                      │
│                       │                                      │
│ Account/settings      │        floating composer             │
└──────────────────────────────────────────────────────────────┘
```

Sidebar:
- ~260–290px desktop
- collapsible
- visually quiet
- Afarin mark/name
- New chat
- Search
- history grouped by date
- account/settings at bottom

Avoid dashboard cards, metrics, tables, or thick borders.

Main conversation:
- centered content column
- max width roughly 760–900px
- generous whitespace
- artifacts allowed to be wider when useful

---

# 8. Mobile layout

Mobile is a first-class design target.

```text
┌─────────────────────────────┐
│ ☰       Conversation     •••│
├─────────────────────────────┤
│                             │
│        messages             │
│                             │
├─────────────────────────────┤
│ [ + ]  پیام...          [↑] │
│       [active theme chip]   │
└─────────────────────────────┘
```

Sidebar becomes an iOS-style sheet/drawer.

Composer:
- stays above keyboard
- uses safe-area inset
- does not jump when keyboard opens

Use `env(safe-area-inset-bottom)`.

---

# 9. Visual direction

The workspace should feel **iOS-inspired**, not like an Apple clone.

Desired qualities:
- minimal
- calm
- premium
- soft translucency in selected surfaces only
- rounded geometry
- subtle shadows
- generous spacing
- typography-first
- content-first
- fast and functional

Reference feeling:

```text
ChatGPT simplicity + modern iOS polish + Afarin identity
```

Avoid:
- cyberpunk styling
- purple everywhere
- heavy glassmorphism
- thick shadows
- card around every block
- dashboard look
- flashy gradients
- excessive animation

---

# 10. Design tokens

Use semantic CSS/Tailwind tokens rather than hard-coded colors throughout components.

```css
--chat-bg
--chat-surface
--chat-surface-secondary
--chat-surface-elevated
--chat-border-subtle
--chat-text
--chat-text-secondary
--chat-accent
--chat-accent-soft
--chat-danger
--chat-shadow-soft
--chat-radius-md
--chat-radius-lg
--chat-radius-xl
--chat-blur
```

Afarin purple is an accent for:
- send button
- active state
- selected theme
- focus state
- small highlights

Base UI should be neutral so generated content dominates visually.

---

# 11. RTL/LTR and typography

Persian must look intentional, not adapted afterward.

Requirements:
- correct RTL flow
- comfortable Persian line height
- proper punctuation behavior
- mixed Persian/English terms should not break layout
- direction is determined per message
- English messages render LTR
- conversations may contain both

Use message metadata when available; otherwise infer direction from text.

---

# 12. New conversation empty state

Keep sparse:

```text
آفرین
امروز چی می‌خوای بسازی؟
```

Composer immediately visible.

Optional shortcut chips:
- تبلیغ بساز
- پست آموزشی
- تصویر بساز
- کپشن بنویس

These shortcuts insert intent/context. They do **not** navigate to separate forms.

---

# 13. Composer — primary product control

Target:

```text
┌───────────────────────────────────────────────┐
│  +   پیام خود را بنویسید...              ↑   │
│      🎨 خمیری و بازیگوش ×                   │
└───────────────────────────────────────────────┘
```

Requirements:
- multiline textarea
- auto-grow
- sensible max height then internal scroll
- send button
- disabled state when empty
- keyboard shortcuts
- RTL/LTR aware
- minimum ~44px touch targets
- sticky/floating at bottom
- rounded ~22–28px
- subtle elevated background

Desktop default:
- Enter sends
- Shift+Enter newline

If Persian/mobile typing proves better with Enter=newline, preserve an explicit send button there.

Do not overload the composer with a toolbar.

---

# 14. `+` menu

Phase 1 options:
- Upload image/file
- Generate image
- Choose theme

Future:
- Voice
- Video
- Music
- Subtitle

Do not show future disabled items if they make the menu noisy.

Desktop: popover above composer.

Mobile: bottom sheet.

---

# 15. Context chips

Compact removable chips near the composer represent active context.

Examples:

```text
🎨 خمیری و بازیگوش ×
🖼 ویرایش آخرین تصویر ×
📎 shoe.jpg ×
```

Theme can remain persistent across turns; attachments/edit target may apply only to the next turn depending on semantics.

---

# 16. Theme behavior

Theme selection lives under `+ → Theme`.

Picker sections:

```text
تم

✓ آفرین انتخاب کند

تم‌های من
خمیری و بازیگوش
ریاضی بنفش
مینیمال روشن

تم‌های آماده
Clay
Pastel
Modern
```

Selected theme becomes the conversation's `active_theme` and appears as a chip.

It remains active for future relevant generations until removed/replaced.

Do not apply it retroactively to old artifacts.

---

# 17. Message design

Avoid WhatsApp-like bubbles for everything.

## User
- compact rounded surface
- slightly stronger fill
- natural RTL/LTR alignment
- max width around 70–78%

## Assistant
- mostly borderless
- clean text blocks
- generous spacing
- artifacts inline
- actions only when relevant

Do not wrap every long assistant answer in a giant card.

---

# 18. Generated image artifacts

Images are first-class chat artifacts.

```text
آفرین

این نسخه رو ساختم:

┌─────────────────────────────┐
│                             │
│       generated image       │
│                             │
└─────────────────────────────┘

دانلود   استفاده به‌عنوان مرجع   •••
```

Treatment:
- 18–24px radius
- subtle shadow
- responsive sizing
- aspect ratio preserved
- large enough to evaluate

Primary actions:
- Download
- Use as reference
- overflow menu

Do not display many permanent action buttons.

---

# 19. Generation loading/error

On generation start, insert a subtle assistant placeholder:

> دارم تصویرت رو می‌سازم...

Use subtle shimmer/progress styling. Show elapsed time only if backed by real timing.

Do not show fake percentages.

If cancellation is not supported, do not show Cancel.

Failure copy should be natural Persian, e.g.:

> ساخت تصویر کامل نشد. دوباره امتحان کنم؟

Never expose provider stack traces in normal UI.

---

# 20. Conversational revisions

Long-term target:

User:

> شخصیت رو کوچیک‌تر کن و پس‌زمینه رو روشن‌تر کن

The system resolves the relevant recent artifact.

UI can show a subtle edit target chip:

```text
🖼 ویرایش: آخرین تصویر ×
```

Backend later passes the prior artifact/image reference to an editing skill/model.

---

# 21. Conversation history

Sidebar groups:
- Today
- Yesterday
- Previous 7 days
- Older

Conversation item:
- short title
- optional subtle icon
- contextual menu

Eventually support:
- rename
- delete
- search

Example titles:
- ماموریت ممیز کوچولو
- تبلیغ کفش سفید
- تمرین کسرها
- کمپین نوروز

Do not add large subtitles/metadata to every history row.

---

# 22. Conversation persistence model — Phase B

Recommended generic domain:

## `conversations`

```text
id
user_id
title
language
active_theme_id nullable
created_at
updated_at
```

## `conversation_messages`

```text
id
conversation_id
role
content
language
metadata_json
created_at
```

Roles may include user, assistant, and internal tool/system records where needed. Internal tool messages should not automatically render as user-visible bubbles.

## `conversation_artifacts`

```text
id
conversation_id
message_id nullable
artifact_type
storage_path
metadata_json
created_at
```

Initial artifact type: `image`.

Future: audio, video, subtitle, document, etc.

---

# 23. Existing advertising/education domain records

Do not migrate/delete them immediately.

Conversation is initially the **UX/orchestration layer**.

Skills can continue creating existing advertising campaign or educational post records.

Link them through metadata:

```json
{ "skill": "education", "educational_post_id": "..." }
```

or:

```json
{ "skill": "advertising", "campaign_id": "..." }
```

This reduces migration risk.

---

# 24. Orchestrator contract — Phase C

Conceptual backend interface:

```python
class Orchestrator(Protocol):
    async def handle_turn(
        self,
        context: ConversationContext,
    ) -> OrchestratorResult:
        ...
```

Context includes:
- latest user message
- recent relevant messages
- attachments
- active theme
- recent artifacts
- conversation language
- authenticated user/permissions

Result conceptually:

```json
{
  "language": "fa",
  "assistant_message": "باشه، یه نسخه خمیری و بازیگوش می‌سازم.",
  "skill": "education",
  "skill_input": {},
  "suggested_conversation_title": "ماموریت ممیز کوچولو"
}
```

No chain-of-thought.

---

# 25. Initial skills

Phase C initial registry:

```text
education
advertising
general_chat
```

Near-term optional additions:
- image_edit
- caption

Examples:

> یه پست آموزشی درباره کسرهای مساوی بساز

→ education

> برای این کفش یه تبلیغ لوکس بساز

→ advertising

> فرق کپشن رسمی و دوستانه چیه؟

→ general_chat

Ambiguous:

> یه چیزی برام بساز

→ ask one concise clarification.

---

# 26. Skill registry

Avoid giant distributed `if/elif` routing.

Conceptually:

```python
SKILLS = {
    "education": EducationSkill(...),
    "advertising": AdvertisingSkill(...),
    "general_chat": GeneralChatSkill(...),
}
```

Future:

```python
SKILLS.update({
    "voice": VoiceSkill(...),
    "subtitle": SubtitleSkill(...),
    "music": MusicSkill(...),
    "video": VideoSkill(...),
})
```

A skill may wrap existing services instead of rewriting them.

---

# 27. Educational skill

Wrap the existing Educational path.

Input from Orchestrator:
- user request
- active theme if relevant
- conversation language
- future reference artifact when editing is supported

Current execution remains:
- Educational Agent
- GPT Image 2
- one finished image

Return the generated artifact to the conversation.

The Orchestrator should not rewrite the educational image prompt.

---

# 28. Advertising skill

Wrap existing advertising generation.

Input may include:
- product photo/reference
- user instruction
- conversation context
- active theme/template if relevant

Reuse the current simplified advertising services. Do not reintroduce removed Planner/Prompt Architect chains.

---

# 29. General chat skill

Use a fast, low-cost conversational model for ordinary questions.

It should:
- answer Persian by default according to the language rules above
- answer English when user writes English
- understand Afarin's capabilities
- not trigger image generation unnecessarily

---

# 30. Orchestrator cost/latency strategy

The Orchestrator should be fast and relatively inexpensive.

It performs:
- intent understanding
- skill selection
- parameter extraction
- short conversational response

It should not duplicate specialist work already done by the skill.

Use **at most one orchestrator LLM call per ordinary user turn**.

If intent is already explicit from UI/tool context, skip the Orchestrator model call when safe.

Example: if the user explicitly selected a known generation action and supplied all required context, do not pay an LLM just to rediscover that intent.

---

# 31. Chat API seam

Frontend components should speak to a chat-specific API, not directly to campaign/education endpoints.

Conceptual:

```ts
interface ChatApi {
  createConversation(): Promise<Conversation>
  listConversations(): Promise<ConversationSummary[]>
  getConversation(id: string): Promise<Conversation>
  sendMessage(conversationId: string, input: SendMessageInput): Promise<ChatTurnResult>
  setActiveTheme(conversationId: string, themeId: string | null): Promise<void>
}
```

Phase A can use a mock implementation.

Later HTTP implementation calls the Orchestrator backend.

---

# 32. Event/streaming model

Future event contract can support:

```ts
type ChatEvent =
  | { type: "assistant_text_delta"; text: string }
  | { type: "assistant_message"; message: ChatMessage }
  | { type: "generation_started"; artifactId: string }
  | { type: "artifact_ready"; artifact: ConversationArtifact }
  | { type: "generation_failed"; artifactId: string; message: string }
```

Phase A frontend prototype must not depend on streaming backend being implemented.

---

# 33. Proposed component tree

Adapt names to project conventions after inspection.

```text
features/chat/
├── ChatWorkspace.tsx
├── ChatSidebar.tsx
├── ChatTopBar.tsx
├── ConversationView.tsx
├── ConversationMessage.tsx
├── UserMessage.tsx
├── AssistantMessage.tsx
├── ChatComposer.tsx
├── ComposerAttachmentStrip.tsx
├── ChatPlusMenu.tsx
├── ThemePickerSheet.tsx
├── ActiveThemeChip.tsx
├── artifacts/
│   ├── ArtifactCard.tsx
│   ├── ImageArtifact.tsx
│   └── GenerationPlaceholder.tsx
├── history/
│   ├── ConversationList.tsx
│   ├── ConversationListItem.tsx
│   └── ConversationSearch.tsx
├── mobile/
│   └── ChatSidebarSheet.tsx
├── chatTypes.ts
├── mockChatData.ts
└── chatTokens.css (or project-equivalent Tailwind tokens)
```

---

# 34. Reuse policy

Inspect current components before building.

Potentially reuse clean primitives:
- buttons
- icons
- popovers
- modal/sheet
- avatar
- textarea
- tooltip
- dropdown
- toast

Do **not** reuse components just because they exist if they make chat look like the existing dashboard/wizard.

Create light chat-specific primitives where needed:
- FloatingComposer
- FrostedPanel
- ChatSheet
- ArtifactSurface
- ThemeChip
- IconButton

Guidelines:
- 16–28px corner radius depending on surface
- subtle borders
- low-opacity shadows
- backdrop blur sparingly
- minimum 44px touch target

---

# 35. Dark mode

If current app already supports dark mode robustly, provide chat tokens for both modes.

Otherwise:
- make light mode polished first
- use semantic tokens that allow dark mode later
- do not delay Phase A for a global dark-mode rewrite

---

# 36. Animation

Restrained motion only:
- 150–250ms
- ease-out
- opacity
- small translate/scale

Animate:
- sidebar
- sheets/popovers
- plus menu
- theme picker
- new message
- artifact completion

Avoid bouncing or decorative loops.

Respect `prefers-reduced-motion`.

---

# 37. Scroll behavior

Must behave like a real chat:
- open at bottom
- sending message scrolls naturally
- auto-scroll assistant completion only if user is already near bottom
- if user scrolls upward, never yank them back down
- show subtle `jump to latest` when needed
- preserve scroll when sidebar/theme picker opens
- avoid layout jumps when images load

---

# 38. Accessibility

Required:
- keyboard navigation
- visible focus states
- aria-labels on icon buttons
- minimum 44x44 touch targets
- proper textarea/button semantics
- focus trapping in sheets/dialogs
- Escape closes overlays
- RTL/LTR accessibility
- sufficient contrast
- reduced-motion support

---

# 39. Attachments

`+ → Upload` lets the user attach a file/image.

Selected image appears near the composer:

```text
[thumbnail] shoe.jpg ×
```

The user can still type before sending.

Do not trigger generation just because a file was selected.

---

# 40. Homepage evolution

Do not immediately delete the current homepage.

Prototype a chat-first entry with a strong route to `/chat`.

Potential future signed-in hero:

```text
آفرین
چی می‌خوای بسازی؟

[ composer ]

تبلیغ بساز   پست آموزشی   تصویر بساز
```

Existing Advertising/Education routes can remain secondary during transition.

---

# 41. Authentication behavior

Preserve current policy unless explicitly changed:
- anonymous user may explore/type
- paid generation requires authentication

Important chat behavior:
- preserve drafted message/context through signup
- resume intended turn afterward where feasible
- never force the user to retype a long prompt after signing in

---

# 42. Error handling

Errors are conversational.

Bad:

> HTTP 500 provider_failure

Good:

> ساخت تصویر کامل نشد. دوباره امتحان کنم؟

Missing required input:

> برای تبلیغ، عکس محصول رو هم بفرست تا بتونم درست بسازمش.

Provider/model details remain developer-only.

---

# 43. Privacy/history

Conversations are private to the user.

Initial user controls:
- rename
- delete

Future:
- archive
- export

No public sharing in the initial chat project.

---

# 44. Phase implementation strategy

## Phase A — Visual chat prototype (BUILD FIRST)

Goal: validate whether the chat UX is substantially better than forms/wizards before changing backend architecture.

Build with mock data:
- `/chat`
- desktop shell
- mobile shell
- mock sidebar/history
- empty state
- Persian and English message examples
- composer
- + menu
- theme picker
- active theme chip
- attachment mock
- generation loading state
- generated image artifact
- responsive behavior
- accessibility basics
- polished light-mode iOS-inspired styling

**Do not modify generation backend in Phase A.**

## Phase B — Conversation persistence

After Phase A approval:
- conversations table
- messages table
- artifacts table
- history/list/get/create/delete/rename
- active theme persistence

## Phase C — Persian-native Orchestrator

After persistence:
- Orchestrator protocol
- Persian-native system prompt
- language detection
- skill registry
- education skill
- advertising skill
- general chat
- one-call-per-turn policy

## Phase D — Conversational revision

- reference recent artifacts
- image editing
- “make this brighter”
- “use the previous image”
- regeneration/revisions

## Phase E — Additional skills

- voice
- subtitle
- music
- video
- carousel
- image editing
- other creator tools

## Phase F — Make chat primary

Only after UX/metrics prove it:
- make chat the main creation entry
- gradually retire redundant forms/wizards
- keep direct routes where useful for deep links/admin

---

# 45. Phase A acceptance checklist

Manually inspect at least:

## Desktop
1. Empty `/chat`
2. Persian conversation
3. English conversation
4. Mixed Persian/English conversation
5. Generated 1:1 image artifact
6. Generated 4:5 image artifact
7. Generation loading state
8. + menu open
9. Theme picker open
10. Active theme selected
11. Attachment selected
12. Long conversation scroll
13. Collapsed sidebar

## Mobile
1. Empty chat
2. Composer above keyboard
3. Sidebar sheet
4. + bottom sheet
5. Theme picker
6. Generated image
7. Long Persian message
8. Mixed Persian/English text
9. Attachment chip
10. safe-area behavior

The prototype must feel like a product, not a wireframe.

---

# 46. Phase A performance requirements

- no giant UI framework added solely for chat
- lazy-load large artifact images
- reserve dimensions to avoid layout shift
- avoid unnecessary rerenders
- no persistent animation loops
- preserve scroll state
- responsive first paint

---

# 47. Phase A tests

Frontend tests should cover:
- `/chat` renders
- new chat empty state
- Persian composer/message RTL
- English message LTR
- send button states
- plus menu
- theme picker
- selecting/removing theme
- attachment chip
- user/assistant message rendering
- image artifact
- loading artifact
- sidebar open/close
- mobile sheet behavior
- keyboard accessibility
- reduced motion where testable

No paid/model calls.

---

# 48. Orchestrator system prompt requirements — Phase C

When Phase C starts, use a system prompt with behavior equivalent to:

```text
You are Afarin's conversational orchestrator.

Your default language is natural conversational Persian.

If the user's latest message is primarily Persian, answer in Persian.
Persian messages may contain English technical, brand, product, or model names;
that does not make the message English.

Reply in English only when:
1. the user's latest message is primarily written in English, or
2. the user explicitly asks you to answer in English.

Do not use stiff or bureaucratic Persian.
Use concise, natural everyday Persian appropriate for a modern creative assistant.

Understand what the user wants, select the appropriate Afarin skill, extract only
the information that skill needs, and give the user a short natural response.

Do not expose internal routing, skill names, model names, chain-of-thought, or
implementation details unless explicitly asked.

Do not ask unnecessary questions. If the request can reasonably be completed from
context, proceed.

Use recent messages, attachments, active theme, and recent artifacts to resolve
references such as: همین، همون عکس، قبلی، روشن‌ترش کن، با همون تم.

Return only the required structured orchestration result.
```

Do not request or persist chain-of-thought.

---

# 49. Language detection — Phase C

Recommended behavior:
1. inspect latest user message
2. detect Persian/Arabic script proportion
3. clearly Persian → `fa`
4. clearly English/Latin → `en`
5. mixed → Persian if Persian is the conversational structure
6. explicit user language instruction overrides detection

Structured orchestrator result should include language:

```json
{ "language": "fa" }
```

Do not translate the user prompt merely to route it.

Downstream skills should receive both:

```text
conversation_language
requested_output_language
```

where needed.

---

# 50. Future generic artifact model

Do not design the conversation layer around images only.

`ConversationArtifact` should be generic enough for:
- image
- audio
- video
- subtitle
- document
- future media

This makes voice/music/video skills additive later rather than architectural rewrites.

---

# 51. Developer/debug mode

Future dev-only surfaces may show:
- routed skill
- model/provider
- timing
- cost
- raw structured orchestration result

Never show these details to normal users by default.

---

# 52. Migration safety

Phase A:
- frontend only
- no DB migration
- no provider changes
- no deletion of working flows

Phase B:
- additive conversation tables

Phase C:
- additive Orchestrator/API
- skills wrap existing domain services

Only after the chat architecture is proven should old wizard/form code be considered for deletion.

---

# 53. Clean-code rule

Frontend:

```text
Chat UI → ChatApi
```

Backend later:

```text
Chat API → Orchestrator → Skill → existing service/model
```

React chat components must not directly call:
- education endpoints
- campaign endpoints
- OpenRouter
- image providers

Keep the orchestration boundary clear.

---

# 54. Documentation

After Phase A approval, update:
- `AGENTS.md`
- `docs/MVP_SPEC.md`
- optionally add `docs/CHAT_ARCHITECTURE.md`

One-sentence architecture:

> Afarin is a Persian-first conversational creative workspace where users describe what they want in chat; an orchestrator routes each request to specialized creative skills that generate and manage the resulting artifacts.

---

# 55. Instructions for Cursor

When Cursor receives this file:

1. Read this entire document.
2. Read `AGENTS.md`.
3. Read `docs/MVP_SPEC.md`.
4. Inspect existing frontend architecture before proposing files.
5. Do not assume component names from this plan already exist.
6. Reuse current project conventions where clean.
7. Do not change backend generation during Phase A.
8. First produce a concrete Phase A implementation plan.
9. Identify what existing components should be reused and what should not.
10. Do not implement until the plan is approved.

---

# 56. Cursor first response — PLAN ONLY

Before implementing Phase A, report:

1. Current frontend route/layout structure relevant to `/chat`
2. Exact files to add
3. Exact existing files to change
4. Existing UI primitives to reuse
5. Existing dashboard/wizard components that should not be reused
6. Proposed component tree
7. Desktop layout implementation
8. Mobile layout implementation
9. Composer behavior
10. `+` menu behavior
11. Theme picker behavior
12. RTL/LTR strategy
13. Message rendering strategy
14. Artifact rendering strategy
15. Loading/error states
16. Design tokens
17. Animation approach
18. Accessibility
19. Test plan
20. Manual screenshot checklist
21. Any blocking issue

Do **not** implement until approved.

---

# 57. Final objective

The user should feel:

> I can simply tell Afarin what I want to create.

They should not need to understand:
- campaigns
- educational modes
- agents
- skills
- image models
- internal routing
- templates versus tools unless they explicitly choose one

**The composer is the primary control.**

**The conversation is the workspace.**

**Generated content is the artifact.**

**The Orchestrator and Skills remain invisible infrastructure.**
