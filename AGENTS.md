# Project Instructions

This project is a Persian-first AI SaaS for small businesses,
Instagram sellers, and teachers.

Afarin has two generation paths and a chat workspace:

- Advertising — product-photo campaign generation (wizard under `/create`)
- Educational — one-prompt teaching posts (under `/create/education`)
- Chat — conversational workspace under `/chat` (Phase D: conversational
  image editing). Do not fold chat history into Campaign or EducationalPost.

When implementing a feature, state which path it touches. Do not fold
educational work into the advertising Campaign model.

The canonical product specification is:
docs/MVP_SPEC.md

Chat workspace architecture:
docs/CHAT_ARCHITECTURE.md

Always read the relevant sections of that specification before
implementing a feature.

## Product principles

- The UI is Persian-first and RTL by default. Optional English chrome and dark mode do not change generated campaign copy or PNG exports.
- Mobile-first design.
- Focus on outcomes, not AI models.
- Do not expose prompts, tokens, provider APIs or model names to normal users.
- Keep expensive AI operations behind backend services.
- Maintain provider abstraction.
- Never put provider API keys in frontend code.
- Build only the currently requested development phase.
- Do not add features from future phases without being asked.
- Prefer small reusable components over large files.
- Explain significant architectural decisions.
- Run and test changes before declaring a task complete.