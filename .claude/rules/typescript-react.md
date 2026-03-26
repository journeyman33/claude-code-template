---
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/tsconfig*.json"
  - "**/package.json"
---

# TypeScript / React Rules

## TypeScript
- Strict mode always: `"strict": true` in tsconfig
- No `any` types — use `unknown` and narrow properly
- Prefer interfaces over types for object shapes
- Explicit return types on all exported functions

## React
- Functional components only — no class components
- Custom hooks in `src/hooks/`, prefixed with `use`
- TanStack Query for all server state — no `useEffect` for data fetching
- Tailwind CSS for styling — no CSS modules, no styled-components

## Next.js (where applicable)
- App Router (not Pages Router) for new projects
- Server components by default, `"use client"` only when necessary
- API routes in `app/api/` following REST conventions
- Environment variables: `.env.local` for secrets, never committed

## File Naming
- Components: `PascalCase.tsx`
- Hooks: `useCamelCase.ts`
- Utils: `camelCase.ts`
- Pages/routes: `kebab-case/page.tsx`

## Validation Commands
```bash
bun run typecheck
bun run lint
bun run test
bun run build
```
