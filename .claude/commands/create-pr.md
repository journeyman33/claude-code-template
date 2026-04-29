---
description: Push current branch and open a draft PR. Run after /implement completes.
argument-hint: (no arguments needed)
---

# Workflow 01 — Create PR (archon-feature-development, node 2)

Archon runs this with `context: fresh` — invoking this as a separate
slash command gives it a fresh context window. It reads all state from disk.

---

## STEP 1: READ STATE FROM DISK

```bash
PLAN_FILE=$(ls -t .claude/archon/plans/*.plan.md 2>/dev/null | head -1)
echo "Plan: $PLAN_FILE"
cat "$PLAN_FILE"
echo "---"
cat .claude/archon/plans/progress.txt 2>/dev/null || echo "(no progress file)"
echo "---"
git log --oneline $(git merge-base HEAD main 2>/dev/null || echo "HEAD~10")..HEAD
git diff --stat $(git merge-base HEAD main 2>/dev/null || echo "HEAD~10")..HEAD
git branch --show-current
```

---

## STEP 2: PUSH

```bash
git push -u origin HEAD 2>&1
```

---

## STEP 3: CHECK FOR EXISTING PR

```bash
gh pr view HEAD --json url,title,state 2>/dev/null || echo "NO_PR"
```

If PR already exists — output the URL and stop.

---

## STEP 4: CREATE DRAFT PR

```bash
gh pr create --draft \
  --title "{feature title from plan}" \
  --body "$(cat <<'PREOF'
## Summary
{1-2 sentences from plan Summary section}

## Tasks Completed
{list from .claude/archon/plans/progress.txt}

## Validation
All checks passed (type-check + lint + build).

## Notes
Implemented via Zed thread + worktree.
Migrated from archon-feature-development.
PREOF
)"
```

---

## STEP 5: FINAL SUMMARY

```
===============================================================
FEATURE DEVELOPMENT — COMPLETE
===============================================================
Plan:    {plan file}
Branch:  {branch}
PR:      {url}

Tasks:   {N} completed
Commits: {git log --oneline}
Files:   {git diff --stat}
===============================================================
```

Open the Zed git panel to review the diff before merging.
