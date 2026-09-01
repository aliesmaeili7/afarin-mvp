# Persian AI Instagram Campaign Builder — MVP Specification

## 1. Product definition

### Working concept

A Persian-first AI product that creates ready-to-use Instagram visual content
for small businesses, Instagram sellers, and teachers.

There are two first-class paths:

* **Advertising** — upload a product photo, receive a campaign package
* **Educational** — write one sentence, receive a square teaching post

The product should feel like a creative assistant, **not an interface for AI models**.

### Core promise

**Upload one product photo → receive a ready-to-post Persian Instagram campaign.**

The product should feel like a creative/marketing assistant, **not an interface for AI models**.

Users should not need to understand:

* prompting
* image-generation models
* LLMs
* aspect ratios
* API providers
* model parameters

They should primarily make simple business and creative decisions.

---

# 2. Target user

Initial target:

**Persian-speaking Instagram sellers and small businesses globally.**

Examples:

* clothing boutiques
* cosmetics sellers
* jewellery shops
* handmade-product sellers
* cafés and food businesses
* home businesses
* online shops
* small consumer brands

The user may know Instagram well but should be assumed to know little or nothing about AI prompting or professional advertising.

### Primary user need

> “I have a product. Help me create something professional-looking that I can actually post.”

---

# 3. MVP hypothesis

The MVP should test:

> Will Persian-speaking small businesses repeatedly use and eventually pay for an AI workflow that produces finished marketing content instead of simply giving them access to AI models?

The MVP is **not** intended to test whether AI APIs technically work.

---

# 4. Core MVP outcome

Each completed campaign produces a:

## پکیج تبلیغاتی اینستاگرام

Containing:

### Visual assets

1. **Instagram Feed Ad**

   * 4:5 format
   * product-focused
   * Persian headline
   * optional price/promotion
   * optional CTA
   * logo/brand name

2. **Instagram Story Ad**

   * 9:16
   * derived from the same campaign
   * separately composed for vertical layout

3. **Three-slide Carousel**

   * Slide 1: hook
   * Slide 2: product/benefit
   * Slide 3: CTA

The first MVP does **not** need three independent AI-generated images.

One strong campaign visual can be reused/recomposed across Feed, Story and Carousel to control cost.

### Written assets

4. **Three Persian captions**

   * short/direct
   * friendly/conversational
   * persuasive/storytelling

5. **Three Story text suggestions**

6. **CTA suggestions**

7. **Hashtag suggestions**

8. **Reel concept**

   * 10–15 second concept
   * hook
   * shot sequence
   * voiceover/text idea
   * CTA

The Reel is initially a **concept/storyboard only**.

Actual AI video generation is not required for MVP launch.

The result page can nevertheless contain:

**«این تبلیغ رو به ویدیو تبدیل کن»**

as a disabled/coming-soon or later paid feature.

---

# 5. Product principles

These principles should guide every implementation decision.

### 5.1 Outcome first

Never make “choose your AI model” the main interaction.

Prefer:

**ساخت تبلیغ محصول**

over:

**Generate with FLUX / GPT / Kling**

---

### 5.2 Persian first

The product UI is Persian-first and RTL by default.

Sellers may switch chrome to English (LTR) and appearance to system, light, or dark. Those preferences are cookies (`afarin_locale`, `afarin_theme`); routes stay the same — there is no `/fa` or `/en`.

UI language is not campaign language. Generated copy, captions, planner recipe titles, and PNG exports stay Persian and are not recolored by app theme.

Code, API schemas and database fields should remain in English.

---

### 5.3 Mobile first

A large percentage of target users will arrive from Instagram on mobile.

Every core workflow must work comfortably on a phone.

Desktop should remain polished, but mobile is the priority.

---

### 5.4 Avoid blank prompt boxes

Whenever possible, ask the user to choose or answer simple questions.

Bad:

> Prompt: _______

Better:

> چه نوع تبلیغی می‌خوای؟

> لوکس / مینیمال / صمیمی / رنگی / سنتی / مدرن

Advanced prompting can eventually exist under an “Advanced” option but is not part of MVP.

---

### 5.5 AI recommends; user decides

The system should frequently offer:

**«خودت پیشنهاد بده»**

Users should never feel blocked because they do not understand marketing.

---

### 5.6 Do not depend on image models for Persian typography

AI-generated base artwork should generally contain **no important text**.

Persian headlines, prices, CTAs, logos and brand text must be composed by our own application.

This ensures:

* correct Persian
* correct RTL layout
* correct نیم‌فاصله
* correct logo
* editable text
* predictable typography
* consistent branding

---

# 6. User journey

## Screen 1 — Landing page

Route:

`/`

### Hero

Main headline:

**از عکس محصولت، تبلیغ اینستاگرام بساز**

Supporting copy:

**عکس محصولت رو بده؛ پست، استوری، کپشن و ایده ریلز آماده بگیر.**

Primary CTA:

**اولین کمپینت رو رایگان بساز**

No credit card required.

### Hero demonstration

Show an immediate before/after:

**Before**
ordinary product photo

→

**After**
finished Persian Instagram advertisement

Ideally show transformation visually rather than explaining the technology.

### Supporting examples

Three categories, for example:

* perfume/cosmetics
* clothing
* food/product packaging

Each demonstrates:

original photo → generated campaign

### Secondary sections

Keep landing page compact.

Include:

#### چطور کار می‌کنه؟

1. عکس محصولت رو آپلود کن
2. سبک تبلیغت رو انتخاب کن
3. کمپین آماده تحویل بگیر

#### چه چیزهایی دریافت می‌کنی؟

* پست
* استوری
* کپشن
* کاروسل
* ایده ریلز

Do not prominently advertise underlying AI model names.

---

# 7. Campaign creation wizard

The campaign creation experience should be a guided wizard.

Use a progress indicator such as:

`1 / 5`

Do not overwhelm the user with one large form.

---

## Step 1 — Product photo

Route:

`/create`

Heading:

**عکس محصولت رو آپلود کن**

Allow:

* JPG
* PNG
* WEBP

MVP limit:

1–3 images.

Primary image is required.

Optional secondary text:

**یه عکس معمولی با موبایل هم کافیه.**

Provide:

**عکس ندارم، با نمونه امتحان می‌کنم**

This loads a demo product.

### Technical behavior

At this stage, the user does not need an account.

Create an anonymous session ID and associate the temporary campaign with it.

Do not expose provider storage URLs publicly.

---

## Step 2 — Product information

Heading:

**کمی درباره محصولت بگو**

Fields:

### Product name

Required.

Example:

`زعفران ممتاز`

### Short description

Optional but encouraged.

Example:

`زعفران یک گرمی مناسب هدیه`

### Price / promotion

Optional.

Examples:

`۳۹۹ هزار تومان`

`۲۰٪ تخفیف`

### Main advantage

Optional.

Prompt:

**چرا مشتری باید این محصول رو انتخاب کنه؟**

Example:

`بسته‌بندی هدیه و کیفیت صادراتی`

### Brand/business name

Optional for first campaign.

Example:

`Sahand`

Provide:

**نمی‌دونم چی بنویسم**

Later this can trigger AI assistance.

For the first implementation, simply allow optional fields.

---

# 8. Step 3 — Campaign objective

Heading:

**از این تبلیغ چه نتیجه‌ای می‌خوای؟**

Selectable cards:

### فروش محصول

### معرفی محصول جدید

### تبلیغ تخفیف

### افزایش آگاهی از برند

Only one required.

---

## Audience

Heading:

**این محصول بیشتر برای چه کسیه؟**

Simple free-text input plus suggestions.

Examples:

* خانم‌های ۲۰ تا ۳۵ سال
* خانواده‌ها
* کسانی که دنبال هدیه لوکس هستن
* دانشجوها

Also provide:

**مطمئن نیستم — خودت پیشنهاد بده**

---

# 9. Step 4 — Visual direction

Heading:

**دوست داری تبلیغت چه حسی داشته باشه؟**

Use visual cards, not a dropdown.

Initial styles:

### لوکس

### مینیمال

### صمیمی

### جسور و رنگی

### سنتی ایرانی

### مدرن

Each card should eventually have a small example image.

Also provide:

**خودت بهترین سبک رو انتخاب کن**

---

# 10. Step 5 — AI campaign concepts

This is the first important AI interaction.

The system uses the campaign brief to create **three campaign concepts**.

No expensive image generation occurs yet.

Example:

## ایده ۱ — هدیه لوکس ایرانی

**Headline:**
هدیه‌ای با عطر ایران

**Creative direction:**
Dark premium background, elegant Persian-inspired details, gift-oriented presentation.

---

## ایده ۲ — اصالت و کیفیت

**Headline:**
طعم اصیل ایران

**Creative direction:**
Traditional warm styling emphasizing origin and authenticity.

---

## ایده ۳ — مینیمال مدرن

**Headline:**
یک انتخاب ساده، یک کیفیت متفاوت

**Creative direction:**
Clean contemporary product photography.

Each concept card has:

**این رو انتخاب کن**

The user selects one.

Also offer:

**سه ایده جدید بده**

This should be cheap/free within reasonable limits.

---

# 11. Signup gate

Only after the user has:

* uploaded a product
* filled the brief
* seen their campaign ideas
* selected one

show:

**کمپینت آماده ساخته شدنه ✨**

Supporting text:

**برای ساخت و ذخیره کمپین، حساب رایگان بساز.**

Authentication options:

* Google
* email + password
* email OTP, as an alternative
* password recovery / first-time password setup for accounts that were created with OTP

Existing OTP-only accounts must be able to set a password through
**رمز عبور را فراموش کرده‌ام**. They are never told to sign up again.

After signup, immediately continue campaign generation.

Do **not** redirect the user to an empty dashboard.

The anonymous campaign must become owned by the new account.

---

# 12. Generation pipeline

After signup, user presses:

**ساخت کمپین**

The backend begins the generation workflow.

Campaign state:

`queued`

then:

`generating`

then:

`ready`

or:

`partial_failed`

or:

`failed`

### Progress UI

Do not show only a generic spinner.

Display stages such as:

**در حال آماده کردن ایده تبلیغ…**

**در حال ساخت تصویر محصول…**

**در حال نوشتن کپشن‌ها…**

**در حال آماده کردن استوری…**

**تقریباً آماده‌ست…**

The frontend should poll campaign/job status or receive equivalent asynchronous updates.

Generation must survive the user refreshing or closing the page.

---

# 13. AI generation architecture

## A. Campaign planner

Input:

* product information
* business information
* objective
* audience
* visual style

Output must be strict structured JSON.

Example:

```json
{
  "campaign_title": "Luxury Persian Gift",
  "headline_fa": "هدیه‌ای با عطر ایران",
  "subheadline_fa": "زعفران ممتاز برای یک هدیه متفاوت",
  "cta_fa": "همین حالا سفارش بده",
  "visual_direction": "...",
  "background_prompt": "...",
  "tone": "premium",
  "captions": [],
  "story_copy": [],
  "reel_concept": {}
}
```

Do not parse arbitrary prose when structured JSON can be used.

---

# 14. Product visual pipeline

Preserving the actual product is important.

The product packaging/logo should not randomly mutate.

Preferred MVP architecture:

### Step A

Create or obtain a product cutout/background removal.

### Step B

Generate a campaign background/environment based on the selected concept.

The generated background should **not contain the Persian headline**.

### Step C

Composite the real product cutout into the generated environment.

### Step D

Apply simple styling if needed:

* shadow
* scale
* position
* mild color adjustment

### Step E

Add:

* Persian headline
* brand name
* price
* CTA
* logo

using our own layout engine.

If a product-preserving image-edit model proves sufficiently reliable, it can later replace or complement this workflow.

Provider-specific implementation must remain behind an abstraction layer.

---

# 15. Campaign layout engine

Create reusable campaign templates.

A template describes:

* background
* product position
* headline area
* optional subheadline
* CTA area
* logo position
* price/promotion area

The same campaign should be rendered into multiple formats.

Initial formats:

### Feed

1080 × 1350

### Story

1080 × 1920

### Carousel

1080 × 1350

Text must remain editable before export.

Use browser/SVG/Canvas-style composition or another approach that reliably supports Persian text rendering.

Do not burn important Persian text permanently into the AI-generated source image.

---

# 16. Result page

Route:

`/campaigns/{campaign_id}`

This is the most important application page.

At the top:

# کمپینت آماده‌ست ✨

---

## Section 1 — Feed Ad

Large preview.

Actions:

**دانلود**

**ویرایش متن**

**نسخه جدید**

---

## Section 2 — Story

Vertical preview.

Actions:

**دانلود**

**ویرایش متن**

---

## Section 3 — Carousel

Show three slide thumbnails.

Each individually downloadable.

Provide:

**دانلود همه**

---

## Section 4 — Captions

Tabs/cards:

### کوتاه و مستقیم

### صمیمی

### تبلیغاتی

Each has:

**کپی**

**ویرایش**

---

## Section 5 — Story ideas

Three short pieces of copy.

Copy button.

---

## Section 6 — Reel concept

Display:

### Hook

### Scene 1

### Scene 2

### Scene 3

### CTA

Eventually:

**این ایده رو به ویدیو تبدیل کن**

For launch this may display:

**به‌زودی**

---

# 17. Contextual campaign assistant

The result page includes a small chat assistant.

Heading:

**چی رو می‌خوای تغییر بدی؟**

Suggested actions:

* کپشن رو خودمونی‌تر کن
* متن رو کوتاه‌تر کن
* CTA قوی‌تر بده
* یه تیتر جدید بده
* تبلیغ رو لوکس‌تر کن

The assistant already receives the campaign context.

Users should not need to re-explain the product.

### Free operations

Textual modifications should generally be free.

Examples:

* rewrite caption
* generate headlines
* adjust tone
* create CTA
* give campaign ideas

### Paid/credit-consuming operations

Anything that invokes materially expensive media generation.

Examples:

* new AI image
* additional visual variation
* future video generation

Before consuming credits, explicitly show the cost.

---

# 18. Brand Kit

After the user's first successful campaign, show:

**این اطلاعات رو برای کمپین بعدی ذخیره کنیم؟**

Automatically create a Brand Kit using known information.

Route:

`/brands/{brand_id}`

Store:

* brand name
* logo
* Instagram handle
* business description
* industry/category
* target audience
* preferred tone
* preferred visual style
* brand colors
* optional website

The user can edit any field.

Future campaign creation begins with:

**برای کدوم برند؟**

Existing users therefore skip repeated setup.

---

# 19. Dashboard

Route:

`/dashboard`

Keep it simple.

Primary CTA:

**کمپین جدید بساز**

Show:

### برندهای من

### کمپین‌های اخیر

Campaign card includes:

* thumbnail
* product name
* brand
* date
* status

Actions:

* مشاهده
* ساخت نسخه جدید
* duplicate campaign

Do not clutter the MVP dashboard with analytics.

---

# 20. Credits

## Product philosophy

Cheap reasoning/writing should feel nearly free.

Expensive media generation should consume credits.

### Initial free experience

New user receives:

**1 complete first campaign free**

Potentially later:

* additional introductory credits
* referral credits

### Free or nearly free

* campaign concept generation
* caption rewrites
* headline generation
* CTA generation
* contextual chat
* basic brand assistance

Set abuse/rate limits.

### Credits required

Examples:

* generate another campaign visual
* generate several visual variants
* premium image generation
* future video generation

Do not hard-code credit prices into frontend components.

Credit costs must come from backend configuration.

---

# 21. Chat

Standalone chat is a third surface (`/chat`), not a Campaign and not an
EducationalPost. See `docs/CHAT_ARCHITECTURE.md`.

Phase A is the Persian-first chat UX. Phase B persists user-owned
conversations, messages, artifacts, and theme snapshots. Phase C connects a
Persian-native Orchestrator and skills (Advertising, Education, general image,
general chat). Phase D is conversational image editing and reference handling
in the current conversation (reference-conditioned generation, not
inpainting). Memory, voice, and cross-chat assets remain later work.

Do not call advertising or education generation from the chat UI. Chat
components speak only to `ChatApi`.

Credits / premium model routing are not part of Phase C.

---

# 22. Database model

Use PostgreSQL.

Authentication may be handled by Supabase Auth.

## profiles

```text
id
user_id
display_name
locale
credit_balance_cached
free_campaigns_remaining
created_at
updated_at
```

The cached balance is for fast UI display.

The ledger remains the audit trail.

---

## brands

```text
id
user_id
name
description
category
instagram_handle
website
target_audience
tone
visual_style
primary_color
secondary_color
created_at
updated_at
```

---

## brand_assets

```text
id
brand_id
asset_type
storage_path
metadata_json
created_at
```

Asset types may include:

* logo
* reference_image
* product_reference

---

## products

```text
id
user_id
brand_id
name
description
price_text
main_benefit
created_at
updated_at
```

---

## product_images

```text
id
product_id
storage_path
is_primary
created_at
```

---

## campaigns

```text
id
user_id nullable
anonymous_session_id nullable
brand_id nullable
product_id
objective
audience
visual_style
selected_concept_id nullable
status
is_free_campaign
created_at
updated_at
```

Possible status values:

```text
draft
brief_complete
concepts_ready
concept_selected
queued
generating
ready
partial_failed
failed
```

---

## campaign_concepts

```text
id
campaign_id
concept_number
title_fa
headline_fa
description_fa
visual_direction
background_prompt
raw_json
selected
created_at
```

---

## campaign_copy

```text
id
campaign_id
copy_type
content
metadata_json
created_at
updated_at
```

Possible types:

```text
caption_short
caption_friendly
caption_persuasive
story
cta
hashtags
reel_concept
```

---

## campaign_assets

```text
id
campaign_id
asset_type
storage_path
width
height
template_id
metadata_json
created_at
```

Possible types:

```text
uploaded_product
product_cutout
generated_background
feed_final
story_final
carousel_1
carousel_2
carousel_3
```

---

## generation_jobs

```text
id
campaign_id          nullable; XOR with educational_post_id
educational_post_id  nullable; XOR with campaign_id
user_id
job_type
provider
model
provider_job_id
status
input_json
output_json
estimated_cost_usd
actual_cost_usd
credits_reserved
error_message
created_at
started_at
completed_at
```

Status:

```text
queued
processing
succeeded
failed
cancelled
```

---

## educational_posts

Separate from `campaigns`. Authenticated-only: `user_id` is NOT NULL and there
is no anonymous owner.

```text
id
user_id
user_prompt
selected_theme_id
selected_builtin_theme_id
language
headline
agent_json
theme_json
render_spec_json
image_storage_path
status
error_message
wall_time_ms
created_at
updated_at
```

Status: `queued`, `generating`, `ready`, `failed`.

---

## educational_themes

Reusable visual systems, never a copied post.

```text
id
user_id
name
theme_json
source
created_at
updated_at
```

Source: `builtin` (catalog, not stored here) or `user`.

---

## chat_conversations

Generic chat domain. Authenticated-only. Not a campaign and not an
educational post. Created on first send, never merely because `/chat` opened.

```text
id
user_id
title
language nullable
active_theme_json nullable
pinned
pinned_at nullable
archived
created_at
updated_at
```

`active_theme_json` is a semantic snapshot (`id`, `source`, `name`, `style_json`).

## chat_messages

```text
id
conversation_id
role
content
language nullable
metadata_json
created_at
```

Roles: `user` | `assistant`. Skill hints live in `metadata_json`, not columns.

## chat_artifacts

```text
id
conversation_id
message_id nullable
artifact_type
storage_path
mime_type
width
height
aspect_ratio
status
metadata_json
created_at
```

`artifact_type` includes future media (`image`, `audio`, `video`, `subtitle`,
`document`). Phase B only writes `image`.

---

## credit_ledger

```text
id
user_id
amount
reason
campaign_id nullable
generation_job_id nullable
provider_cost_usd nullable
metadata_json
created_at
```

Positive examples:

```text
+100 signup_bonus
+50 referral_bonus
+100 admin_credit
```

Negative examples:

```text
-5 image_generation
-30 video_generation
```

Never rely solely on overwriting a user's balance.

Every change must have a corresponding ledger entry.

---

# 23. Provider abstraction

Do not scatter direct provider calls throughout business logic.

Create interfaces such as:

```text
LLMProvider
ImageProvider
BackgroundRemovalProvider
VideoProvider
CreativeAgent          # advertising, multimodal
EducationalAgent       # educational, text-only
```

Example methods:

```text
generate_campaign_concepts()
generate_campaign_copy()
generate_background()
remove_background()
regenerate_image()
```

Provider selection belongs in configuration/backend services.

Do not expose provider API keys to frontend.

Do not put provider/model names into the primary customer experience.

---

# 24. API endpoints

Exact naming may evolve, but approximately:

## Campaign

```text
POST   /api/campaigns
GET    /api/campaigns/{id}
PATCH  /api/campaigns/{id}
```

## Product

```text
POST   /api/campaigns/{id}/product
POST   /api/campaigns/{id}/images
```

## Concepts

```text
POST   /api/campaigns/{id}/concepts/generate
POST   /api/campaigns/{id}/concepts/{concept_id}/select
```

## Generation

```text
POST   /api/campaigns/{id}/generate
GET    /api/campaigns/{id}/status
```

## Copy

```text
PATCH  /api/campaigns/{id}/copy/{copy_id}
POST   /api/campaigns/{id}/copy/{copy_id}/rewrite
```

## Campaign assistant

```text
POST   /api/campaigns/{id}/assistant
```

## Brands

```text
GET    /api/brands
POST   /api/brands
GET    /api/brands/{id}
PATCH  /api/brands/{id}
```

## Educational posts

Authenticated-only. No row is created until the user is signed in.

```text
POST   /api/education/posts
GET    /api/education/posts
GET    /api/education/posts/{id}
GET    /api/education/posts/{id}/status
PATCH  /api/education/posts/{id}/text
DELETE /api/education/posts/{id}
```

## Educational themes

`GET /themes` is open so a visitor can browse built-ins before signup.
Saving, renaming and deleting require an account.

```text
GET    /api/education/themes
POST   /api/education/themes
PATCH  /api/education/themes/{id}
DELETE /api/education/themes/{id}
```

## Chat

Authenticated writes. Anonymous `GET /conversations` returns `[]`.
Unknown and foreign ids both 404. First send is `POST /conversations`
(conversation + first user message, then the Orchestrator turn).

```text
POST   /api/chat/conversations
GET    /api/chat/conversations
GET    /api/chat/conversations/{id}
PATCH  /api/chat/conversations/{id}
DELETE /api/chat/conversations/{id}
POST   /api/chat/conversations/{id}/messages
POST   /api/chat/conversations/{id}/messages/{message_id}/retry
```

## Credits

```text
GET    /api/credits/balance
GET    /api/credits/history
```

## Admin

```text
GET    /api/admin/users
GET    /api/admin/campaigns
GET    /api/admin/generations
```

---

# 25. Admin dashboard

Build a basic internal admin interface from the beginning.

It does not need to be beautiful.

Display:

### Users

* total users
* recent users

### Campaigns

* total
* completed
* failed

### Generations

* count by type
* count by provider
* failure rate

### Cost

* approximate API cost
* cost by campaign
* cost by user

### Credits

* issued
* consumed

Admin should be able to inspect a generation:

```text
user
campaign
provider
model
input
status
provider cost
credits charged
error
```

Admin should also be able to manually grant credits during beta.

---

# 26. Analytics events

Track product behavior independently of Google Analytics or another vendor.

Important events:

```text
landing_viewed
campaign_started
photo_uploaded
brief_completed
style_selected
concepts_generated
concept_selected
signup_started
signup_completed
generation_started
campaign_completed
asset_downloaded
caption_copied
campaign_repeated
regeneration_requested
brand_saved
```

These events should let us calculate:

```text
visitor
→ campaign start
→ upload
→ concept selection
→ signup
→ finished campaign
→ download
→ second campaign
```

The second-campaign rate is particularly important.

---

# 27. Security and reliability requirements

### API keys

Never store provider keys in frontend code.

### Uploads

Validate:

* MIME type
* maximum size
* image dimensions where appropriate

### Storage

Use non-public/private storage where appropriate.

Serve files through controlled/signed URLs.

### Ownership

Every authenticated resource endpoint must verify ownership.

A user must not be able to access another user's campaign by changing an ID.

### Generation idempotency

Repeated clicks on:

**ساخت کمپین**

must not launch several expensive jobs.

Use idempotency/state checks.

### Credit reservation

Before an expensive generation:

1. verify balance
2. reserve/deduct credits transactionally
3. launch generation
4. refund according to failure policy if provider generation fails

### Rate limiting

Apply limits to:

* free concept generations
* free rewriting
* chat
* anonymous sessions
* campaign generation

### Errors

Do not expose raw provider errors to end users.

Store detailed errors for admin/debugging.

---

# 28. RTL and Persian UX requirements

Default document:

```html
dir="rtl"
lang="fa"
```

English chrome uses `dir="ltr"` and `lang="en"` on the same routes. Ad canvases stay `dir="rtl"` so generated Persian type never inherits LTR.

Requirements:

* Persian-friendly font
* correct RTL form layout (and LTR when English chrome is on)
* correct mixed Persian/English handling
* number and relative-date display follow UI locale in chrome only; prices inside ads stay as generated
* proper ی/ي and ک/ك normalization where useful
* preserve نیم‌فاصله
* buttons and icons must make sense in RTL and LTR
* mobile forms must be comfortable with Persian keyboards
* dark mode is chrome-only; exported ads keep spec colors

---

# 29. What NOT to build for core MVP

Do not implement these until the primary workflow is working:

* dozens of selectable AI models
* music generation
* generic video-generation studio
* AI avatar platform
* dubbing studio
* social-media scheduling
* Instagram publishing
* team accounts
* subscriptions
* marketplace
* mobile application
* analytics for customers
* influencer marketplace
* advanced prompt editor
* custom model training
* monthly content calendar
* automatic Instagram account analysis

These are potential later features.

---

# 30. MVP phases

## Phase 1 — Fully mocked product experience

No AI API integration.

Implement:

* landing page
* RTL Persian design system
* campaign wizard
* product upload UI
* brief
* objective
* audience
* style selection
* three mocked concepts
* signup flow
* mocked generation progress
* result page
* mocked campaign assets
* captions
* Reel concept
* dashboard
* basic Brand Kit

Goal:

The application should already feel like a complete product even though outputs are mocked.

---

## Phase 2 — Database and authentication

Implement:

* PostgreSQL schema
* Supabase authentication
* persistent campaigns
* temporary anonymous campaigns
* ownership rules
* storage
* campaign history
* Brand Kit persistence

Do not integrate image generation yet.

### Open question — authentication method

Section 11 specifies Google and email as the signup options, and Phase 1
implements exactly that.

Before wiring real authentication, decide whether this is right for the target
market. Iranian Instagram sellers typically cannot reach Google sign-in without
a VPN, and phone/SMS is the login method they are used to. If phone/OTP is
chosen instead, section 11 and the Phase 1 signup gate both need updating.

---

## Phase 3 — Real campaign reasoning

Integrate LLM provider abstraction.

Implement:

* campaign concept generation
* strict JSON validation
* campaign copy
* captions
* Story text
* CTA
* Reel concept
* contextual copy rewriting

Images remain mocked.

---

## Phase 4 — Real product creative generation

Implement:

* product cutout/background-removal pipeline
* campaign background generation
* product compositing
* generation job persistence
* failure handling
* generated background storage
* **Phase 4B** two visual modes:
  * `accurate` (دقیق): empty scene + preserved product pixels (2 image outputs)
  * `creative` (خلاقانه): reference-image generation, 3 candidates + 1 Story adaptation (4 image outputs; at most 1 extra repair). Campaign cap: `MAX_CREATIVE_ATTEMPTS_PER_CAMPAIGN` (default 3).
* Visual planner (multimodal LLM) and Visual Recipe catalog (style × template)
* Candidate selection UI; Persian type remains AdCanvas, never in the image model

Cost accounting counts **image outputs**, not HTTP requests.

---

## Phase 5 — Persian layout/export engine

Implement reusable visual templates.

Generate:

* Feed
* Story
* Carousel

Allow editing:

* headline
* subheadline
* price
* CTA

Allow:

* download image
* copy caption
* download carousel assets

---

## Phase 6 — Brand memory

Implement:

* automatic Brand Kit suggestion after first campaign
* save brand
* reuse brand on new campaign
* prefill audience/tone/style
* upload logo
* persistent brand styling

---

## Phase 7 — Credits

Implement:

* credit ledger
* balance
* free first campaign
* credit reservation
* refunds
* configurable generation prices
* admin credit grants

No payment gateway is required yet.

Beta users can receive credits manually.

---

## Phase 8 — Admin + analytics + beta hardening

Implement:

* admin dashboard
* generation inspection
* provider costs
* user funnel events
* abuse prevention
* rate limits
* error states
* empty states
* mobile QA
* retry handling

---

# 31. Cursor development rules

Cursor must follow these rules throughout the project.

### Rule 1

Do not implement functionality from future phases unless explicitly requested.

### Rule 2

Before making a large architectural change, explain the proposed change.

### Rule 3

Prefer small reusable modules to large files.

### Rule 4

Do not call external AI providers directly from frontend code.

### Rule 5

Keep provider-specific logic behind adapters.

### Rule 6

Use mocks/interfaces before real provider integrations.

### Rule 7

Avoid introducing dependencies unnecessarily.

### Rule 8

Maintain strict types/interfaces between frontend and backend.

### Rule 9

Add database migrations rather than manually changing production schema.

### Rule 10

Every expensive generation must be traceable to a `generation_job`.

### Rule 11

Every credit movement must be traceable in `credit_ledger`.

### Rule 12

UI must remain Persian-first and RTL by default. Optional English chrome does not change generated campaign language.

### Rule 13

Do not expose internal AI model terminology unless specifically required.

### Rule 14

All user-visible failures should be friendly and recoverable.

### Rule 15

After completing each development phase:

1. run tests
2. report files changed
3. explain architectural decisions
4. list known limitations
5. stop and wait for the next requested phase

---

# 32. Recommended repository structure

```text
/
├── frontend/
│   ├── app/
│   ├── components/
│   ├── features/
│   │   ├── campaign/
│   │   ├── brand/
│   │   ├── credits/
│   │   └── auth/
│   ├── lib/
│   └── types/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── ai/
│   │   │   ├── campaigns/
│   │   │   ├── credits/
│   │   │   └── storage/
│   │   ├── providers/
│   │   │   ├── llm/
│   │   │   ├── image/
│   │   │   └── background_removal/
│   │   └── core/
│   └── tests/
│
├── docs/
│   ├── MVP_SPEC.md
│   ├── ARCHITECTURE.md
│   └── DECISIONS.md
│
└── README.md
```

---

# 33. Definition of MVP success

A completely new user should be able to:

1. arrive on the homepage
2. immediately understand what the product does
3. upload a product photo
4. describe their product
5. choose a marketing objective
6. select a visual style
7. receive three campaign concepts
8. select one
9. create an account
10. generate a campaign
11. receive a polished Feed ad
12. receive a Story
13. receive a Carousel
14. receive Persian captions
15. receive a Reel idea
16. edit basic copy
17. download their assets
18. save their brand
19. return and start another campaign

without ever needing to understand which AI model generated anything.

---

# 34. First business metrics

During beta, prioritize:

### Activation

Percentage of visitors who upload a photo.

### Campaign completion

Percentage of uploaders who finish a campaign.

### Download rate

Percentage of completed campaigns where at least one asset is downloaded.

### Repeat usage

Percentage who create a second campaign.

### Regeneration demand

How often users request another visual.

### Qualitative result quality

Ask after download:

**این کمپین چقدر برات قابل استفاده بود؟**

1–5 rating.

Optional:

**چی بهتر می‌شد؟**

The most important signal is not signup count.

It is:

> Did users actually download the result, and did they come back to make another one?

---

# 35. Initial Cursor instruction

When beginning implementation, give Cursor this specification and then use:

> Read `docs/MVP_SPEC.md` completely before making any changes.
>
> We are beginning **Phase 1 only: Fully Mocked Product Experience**.
>
> Build a Persian-first, RTL, mobile-first product experience for the campaign workflow described in the specification.
>
> Tech stack:
>
> * Next.js/React frontend
> * FastAPI backend
> * PostgreSQL later
> * Supabase later for auth/storage
>
> For Phase 1:
>
> * Do NOT integrate Supabase yet.
> * Do NOT integrate any AI APIs.
> * Do NOT implement payments.
> * Do NOT implement real credits.
> * Do NOT implement video.
> * Use local mocked data and mocked delays/states.
>
> Implement:
>
> 1. Landing page
> 2. Campaign wizard
> 3. Product upload interface
> 4. Product information step
> 5. Objective/audience step
> 6. Visual-style selection
> 7. Three mocked campaign concepts
> 8. Mock signup gate
> 9. Generation progress experience
> 10. Complete campaign results page
> 11. Simple dashboard
> 12. Simple Brand Kit page
>
> Use realistic Persian copy throughout.
>
> Create reusable components rather than one giant page.
>
> Keep application/domain types explicit.
>
> Create mock campaign data in a dedicated mock-data module so it can later be replaced by backend API calls.
>
> The visual identity should feel modern, simple and aimed at small Instagram businesses — not like a developer AI dashboard.
>
> Do not show model selectors, prompt-engineering controls, token usage or API terminology.
>
> After implementation:
>
> * run the project
> * fix compilation/runtime errors
> * report the resulting route structure
> * report the important components created
> * identify any decisions you had to make that were not specified
> * do not proceed to Phase 2.

---

# 36. Educational content

Afarin also makes teaching posts. This is a separate domain from advertising
campaigns: one natural-language prompt in, one square Instagram post out.

## Phase 1 flow

Homepage → Educational → one prompt → optional theme → signup if needed →
Generate → result.

The only required input is the prompt. Topic, grade, tone, title, caption and
image direction are inferred. The only optional choice is a theme (default:
Afarin designs one).

No questionnaire. No direction-selection step. No three image variations. No
Story or carousel in Phase 1.

Educational generation is authenticated-only. A visitor may type the prompt
and pick a theme in the browser; the `educational_posts` row is created only
after signup, with `user_id` NOT NULL. There is no `anonymous_session_id` on
the educational domain.

## Agent

One `EducationalAgent` call produces JSON: `language`, `final_prompt`, a
style-only `theme`, and optional `theme_style_notes` / `safety_notes`. One
semantic retry maximum.

The image model receives `final_prompt` unchanged, `1:1`, `n=1`, no
reference images, via `EDUCATIONAL_IMAGE_MODEL` (`openai/gpt-image-2`).
Advertising campaigns keep using Seedream (`IMAGE_MODEL`). The generated
image is the result: Afarin does not overlay headline, CTA, badge or price
layers afterwards. If the teacher already wrote exact poster wording, the
agent preserves it inside `final_prompt` so the image model can paint it.

## Themes

Built-in starter set plus user-saved visual systems (palette, illustration
language, mood, lighting, motifs). A theme is style memory only: it must not
create text layers, CTAs, badges or advertising template chrome. A saved theme
is not a duplicated post: topic and the previous image prompt are dropped on
save.

## Tables

`educational_posts` and `educational_themes`, both owned by `user_id`.
Telemetry reuses `generation_jobs` with a nullable `educational_post_id` and
an XOR check against `campaign_id`.

## Future Phase 2 — Educational series / carousel (do not implement now)

Phase 2 is PLAN FIRST → USER APPROVES → GENERATE SERIES.

```text
user prompt + optional saved theme
  → Educational Agent proposes a slide-by-slide outline
  → user reviews the outline BEFORE paying for image generation
  → user can edit / remove / reorder slides
  → user confirms
  → each slide generated one by one using the SAME saved/generated theme
  → AdCanvas overlays exact text consistently across the series
```

Each slide in the plan carries: educational purpose, headline/text, visual
concept. The point is that the user approves the outline before any image
spend.

