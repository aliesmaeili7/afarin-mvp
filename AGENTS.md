# Project Instructions

This project is a Persian-first AI SaaS for small businesses and
Instagram sellers.

The canonical product specification is:
docs/MVP_SPEC.md

Always read the relevant sections of that specification before
implementing a feature.

## Product principles

- The UI is Persian-first and RTL.
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