---
description: Prime agent with context from a remote server (memory + codebase) via SSH
---

# Prime Remote

Load full context from a remote server so you can work cross-server without switching terminals.

## Usage

```
/prime-remote <server> [project-path]
```

- `<server>` — one of: `cogstack`, `bigtorig`, `pi4`
- `[project-path]` — optional path to a specific project (e.g. `/opt/cogstack`). Defaults to `~`.

## Process

### 1. Read all memory contexts on the remote server

```bash
ssh <server> "cat ~/.claude/projects/*/memory/MEMORY.md 2>/dev/null"
```

Then for each memory file referenced in those MEMORY.md indexes, read it:

```bash
ssh <server> "cat ~/.claude/projects/*/memory/*.md 2>/dev/null"
```

### 2. Read project structure at the specified path

```bash
ssh <server> "cd <project-path> && git ls-files 2>/dev/null | head -60"
ssh <server> "cd <project-path> && tree -L 3 -I 'node_modules|__pycache__|.git|dist|build' 2>/dev/null || find . -maxdepth 3 -not -path '*/.git/*' | head -60"
```

### 3. Read core documentation

```bash
ssh <server> "cd <project-path> && cat CLAUDE.md 2>/dev/null"
ssh <server> "cd <project-path> && cat README.md 2>/dev/null"
ssh <server> "cd <project-path> && cat .claude/PRD.md 2>/dev/null"
```

### 4. Check recent git activity

```bash
ssh <server> "cd <project-path> && git log --oneline -10 2>/dev/null"
ssh <server> "cd <project-path> && git status 2>/dev/null"
```

### 5. List active plans

```bash
ssh <server> "ls <project-path>/.agents/plans/ 2>/dev/null && echo '---' && ls ~/.agents/plans/ 2>/dev/null"
```

## Output Report

Produce a concise summary covering:

### Server: `<server>`
- Project path primed

### Memory Context
- Key projects and their status
- Recent decisions or gotchas from memory files

### Codebase Overview
- Purpose and tech stack
- Key directories

### Current State
- Active branch and recent commits
- Uncommitted changes if any

### Active Plans
- List of `.agents/plans/` files awaiting execution

### Suggested Next Step
- Based on memory + codebase state, what is the most logical next action?

**Keep the summary scannable — bullets and headers, no prose paragraphs.**
