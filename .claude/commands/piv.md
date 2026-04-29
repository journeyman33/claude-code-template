---
description: Full guided PIV loop — Plan, Implement, Validate with human review at each phase.
argument-hint: [feature description, #issue-number, or path to existing plan]
---

# Workflow 02 — PIV Loop (archon-piv-loop, all 8 phases)

**Input**: $ARGUMENTS

Archon's 8 nodes run here as sequential phases in a single thread.
Three interactive loops → three human gate points.
`context: fresh` nodes → Task tool subagents.
`bash` node → already fired via tasks.json on worktree create.

**Human gates — your role:**
1. After EXPLORE: answer questions, then type **"ready"**
2. After PLAN: review plan, give feedback, then type **"approved"**
3. After IMPLEMENT+REVIEW: test the code, give feedback, then type **"approved"**

Do NOT skip gate phrases — the agent will not proceed without them.

---

# PHASE 1: EXPLORE
### Archon node: `explore` (interactive loop, until PLAN_READY)

You are a senior engineering partner. Goal: deeply understand what to build
before any code is written.

## Step 1: Parse input

**If $ARGUMENTS is a file path** (ends in `.md`):
```bash
cat "$ARGUMENTS"
```
If it's an existing plan → summarise and ask: refine or proceed?
If it's a PRD → identify which specific feature/phase to focus on.

**If $ARGUMENTS is a GitHub issue** (`#NNN`):
```bash
gh issue view {number} --json title,body,labels,comments
```

**If $ARGUMENTS is free text**: use it directly as the feature description.

## Step 2: Do your homework first

Before asking ANY questions:
1. Read `CLAUDE.md` — conventions, constraints, stack
2. Search for related existing code — find what already exists
3. Read key files that will likely change
4. Check recent history: `git log --oneline -20`

## Step 3: Present your understanding

```
## What I Understand
{restated understanding in 2-3 sentences}

## What Already Exists
- {file:line} — {what it does and how it relates}

## Initial Architecture Thoughts
- {approach 1 — extend existing X}
- {approach 2 — fallback}
- {key decision needing human input}
```

## Step 4: Ask targeted questions (4-6 max)

Focus on DECISIONS, not information gathering:
- Scope boundaries, architecture choices, tech decisions
- Extend existing vs build fresh, testing expectations
- Reference actual code found — no generic questions

## Gate — CRITICAL

**Continue conversation** until the human explicitly types one of:
`ready`, `create the plan`, `let's go`, `proceed`

**DO NOT move to Phase 2 until the gate phrase is received.**
If the human asks a question → answer it, stay in Phase 1.
If the human gives feedback → address it, stay in Phase 1.
If unsure whether they are approving → ask. Do not assume.

---

# PHASE 2: CREATE PLAN
### Archon node: `create-plan` (sonnet, context: fresh → Task tool)

The human has said "ready". Spawn a subagent to write the plan.

Use the Task tool with this instruction:

> You are creating a structured implementation plan from a completed
> exploration phase. Read CLAUDE.md. Read every file that will change.
> Generate a kebab-case slug from the feature name.
> Save the plan to `.claude/archon/plans/{slug}.plan.md`
> Use this exact template:
>
> # Feature: {Title}
> ## Summary
> ## Mission
> ## Success Criteria (checkboxes)
> ## Scope (In / Out)
> ## Codebase Context (key files table, patterns to follow)
> ## Architecture (decisions with rationale)
> ## Task List (### Task N: sections, atomic, independently verifiable)
> ## Testing Strategy
> ## Validation Commands
> ## Risks (table)
>
> After writing: verify all file paths exist, verify all patterns cited,
> check task ordering for dependencies, check completeness.
> Report: plan file path, task count, files to change, key decisions.

After the subagent completes, read the plan and present a summary
to the human for review.

---

# PHASE 3: REFINE PLAN
### Archon node: `refine-plan` (interactive loop, until PLAN_APPROVED)

The human is reviewing the plan.

## If no feedback yet (first show):
- Read the plan file
- Present: summary of key decisions + task list
- Ask for feedback

## Gate — CRITICAL

If the human types `approved`, `looks good`, `ship it`, or similar:
- Say "Plan approved. Proceeding to implementation."
- Move to Phase 4.

If the human provides feedback:
1. Read the plan file
2. Edit it directly based on feedback
3. Re-verify file paths and patterns
4. Report changes made
5. Show updated task count
6. Ask: "Review the updated plan, or say 'approved' to begin."

**DO NOT move to Phase 4 without explicit approval.**

---

# PHASE 4: IMPLEMENT SETUP
### Archon node: `implement-setup` (bash)

This was already handled by `tasks.json` when the worktree was created.
Verify state before proceeding:

```bash
PLAN_FILE=$(ls -t .claude/archon/plans/*.plan.md 2>/dev/null | head -1)
[ -z "$PLAN_FILE" ] && echo "ERROR: No plan file found." && exit 1

echo "Plan: $PLAN_FILE"
echo "Branch: $(git branch --show-current)"
echo "Tasks: $(grep -c '^### Task [0-9]' $PLAN_FILE || echo 0)"

# Ensure dependencies installed
npm install 2>&1 | tail -3
```

---

# PHASE 5: IMPLEMENT
### Archon node: `implement` (fresh_context: true per iteration → Task tool per task)

Archon uses `fresh_context: true` in its loop — each iteration gets an
isolated context window. Replicate this by spawning one Task tool subagent
per task in the plan.

For each `### Task N:` in the plan, spawn a subagent via the Task tool:

> You are an autonomous coding agent with NO memory of previous tasks.
> Read everything from disk.
>
> 1. Read plan: `{PLAN_FILE}`
> 2. Read progress: `.claude/archon/plans/progress.txt`
> 3. Read `CLAUDE.md`
> 4. Check git: `git log --oneline -5 && git status`
>
> Your task: Task {N} — {title}
> Implement it following the plan EXACTLY.
> Type-check after every file change.
> Golden Rule: never commit broken code.
>
> After completing:
> - `git add -A && git commit -m "feat: {task description}\n\nPIV Task {N}"`
> - Append to `.claude/archon/plans/progress.txt`:
>   `## Task {N}: {title} — COMPLETED\nCommit: {hash}\nFiles: {list}\n---`
> - Report: task done, files changed, commit hash.

Wait for each subagent to complete before spawning the next.

After all tasks: run full validation:
```bash
npm run validate 2>&1
```

---

# PHASE 6: CODE REVIEW
### Archon node: `code-review` (sonnet, context: fresh → Task tool)

Spawn a subagent for the code review:

> Review ALL changes against the plan.
>
> ```bash
> PLAN_FILE=$(ls -t .claude/archon/plans/*.plan.md | head -1)
> git log --oneline $(git merge-base HEAD main)..HEAD
> git diff $(git merge-base HEAD main)..HEAD --stat
> git diff $(git merge-base HEAD main)..HEAD
> ```
>
> For each task: was it implemented correctly?
> For each file: quality, security, CLAUDE.md conventions.
> Run: `npm run validate 2>&1`
> Fix obvious issues (type errors, lint, formatting). Commit fixes.
>
> Report:
> - Implementation status table (task | DONE/PARTIAL/MISSING | notes)
> - Validation: PASS/FAIL per check
> - Findings (or "No issues found")
> - Recommendation: READY FOR HUMAN REVIEW / NEEDS FIXES

Present the review output to the human.

---

# PHASE 7: FIX FEEDBACK
### Archon node: `fix-feedback` (interactive loop, until VALIDATED)

The human is testing the implementation.

## If no feedback yet (first show):
- Present code review results
- Ask the human to test the implementation

## Gate — CRITICAL

If the human types `approved`, `looks good`, `ship it`, or similar:
- Say "Implementation approved!"
- Move to Phase 8.

If the human provides feedback:
1. Read relevant files
2. Understand each issue
3. Make fixes
4. Type-check after each change
5. Run full validation: `npm run validate 2>&1`
6. Commit: `git commit -m "fix: address review feedback"`
7. Report changes made
8. Ask: "Review again, or say 'approved' to finalize."

**DO NOT move to Phase 8 without explicit approval.**

---

# PHASE 8: FINALIZE
### Archon node: `finalize` (sonnet, context: fresh → /create-pr command)

The human has approved. Invoke the `/create-pr` command for the final push
and PR creation. That command runs with fresh context (reads state from disk).

Tell the human:
"Implementation approved and code reviewed. Run `/create-pr` to push
and open the draft PR, then review the diff in the Zed git panel."
