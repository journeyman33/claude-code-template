---
description: Implement a feature from an existing plan. Input: path to .plan.md or GitHub issue number.
argument-hint: [.claude/archon/plans/name.plan.md or #issue-number]
---

# Workflow 01 — Implement (archon-feature-development, node 1)

**Input**: $ARGUMENTS

---

## PHASE 1: LOAD PLAN

**If $ARGUMENTS is a file path** (ends in `.md`):
```bash
cat "$ARGUMENTS"
```
Confirm: "Plan loaded: {title}. {N} tasks found."

**If $ARGUMENTS is a GitHub issue** (`#NNN`):
```bash
gh issue view {number} --json title,body,labels,comments
```
Extract structured plan from issue body. If none found — stop, do not guess.

**If no $ARGUMENTS**: show available plans and ask:
```bash
ls .claude/archon/plans/*.plan.md 2>/dev/null || echo "No plans found."
```

---

## PHASE 2: SETUP

```bash
git status && git branch --show-current
npm install 2>&1 | tail -3
```

Read `CLAUDE.md` before touching any code.

---

## PHASE 3: IMPLEMENT

Work through each `### Task N:` in the plan **sequentially**.

For every task:

1. Announce the task:
```
-- Task N: {title} --
Action: {CREATE / UPDATE}
File:   {path}
```

2. Read the target file before editing (if it exists)
3. Read any pattern file referenced in the plan
4. Implement the change following the plan EXACTLY — no improvisation
5. Type-check after every file change:
```bash
npm run type-check 2>&1 | tail -10
```
Fix errors before moving to the next task.

**Golden Rule**: Never commit broken code.
If validation fails after 3 fix attempts — write the failure to
`.claude/archon/plans/progress.txt` and STOP. Report clearly.

After each completed task:
```bash
git add -A
git commit -m "{type}: {task description}

PIV Task {N}: {brief details}"
```

Append to `.claude/archon/plans/progress.txt`:
```
## Task {N}: {title} — COMPLETED
Commit: {short hash}
Files:  {list}
---
```

---

## PHASE 4: VALIDATE

After all tasks complete:
```bash
npm run validate 2>&1
```

Fix any failures and commit:
```bash
git add -A && git commit -m "fix: post-implementation validation"
```

---

## PHASE 5: HANDOFF

Output this summary block:
```
=== IMPLEMENTATION COMPLETE ===
Plan:       {plan file path}
Branch:     {git branch --show-current}
Tasks:      {N} completed
Commits:    {git log --oneline from main}
Validation: PASS
=== END ===
```

Tell the human: "Implementation complete. Run `/create-pr` to push and open the draft PR."
