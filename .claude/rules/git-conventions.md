# Git Conventions

## Commit Messages
- Always use conventional commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`
- Present tense, imperative: "add auth middleware" not "added auth middleware"
- Keep subject line under 72 characters
- Add body for non-trivial commits explaining *why*, not just *what*

## Branching
- `main` / `master` — production only, never commit directly
- `feat/short-description` — new features
- `fix/short-description` — bug fixes
- `chore/short-description` — maintenance, deps, config

## Workflow
- Run tests before every commit where a test suite exists
- `git status` before any destructive operation
- Never `git push --force` to main/master
- Use `gh pr create` for work that warrants a PR
- Prefer atomic commits — one logical change per commit

## Safety
- Never commit secrets, API keys, or credentials
- Check `.gitignore` before first commit on any new project
- Before pushing a new repo, verify no sensitive history with `git log --oneline`
