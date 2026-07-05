# /feature-complete — FEAT-APP-001 — history

Captured automatically by `.claude/hooks/capture_slash_command.py`.


---

## /feature-complete FEAT-APP-001 — 2026-07-05T15:24:58Z

### Prompt

```
/feature-complete FEAT-APP-001
```

### Assistant response

The user is closing out FEAT-APP-001. This command does destructive things (merges worktrees, archives/deletes feature + autobuild state, moves task files), so let me assess the actual state before touching anything — especially since this feature's code was already merged to main via selective squash, not via live autobuild branches.

Clear picture: FEAT-APP-001's code is fully on `main` (autobuild branches + worktree already cleaned up via the earlier selective squash), all 8 tasks are `completed` (no deferred → no operator-followup panel), and the `guardkit` CLI is available. So this is a **`--no-merge`** finalization: archive + move task files, no worktree merge. Let me dry-run the CLI first to preview exactly what it will do before anything destructive.

The CLI version here doesn't have `--no-merge`. Let me check its actual options:

This CLI is the archive-and-finalize path (no git merge — that's already done). Let me dry-run it:

The CLI's Phase 2/3 are **placeholders** in this version — it validates and shows the panel but does *not* actually move task files, archive, or clean up. So the real finalization is manual (as the slash-command doc describes). Before I move/delete anything, let me learn the established pattern from prior completed features.

Now I understand the repo's *actual* convention (which differs from the generic slash-command doc):
- **Completed features KEEP their `.guardkit/features/*.yaml`** — FEAT-SMP-001/002/003 are all completed-and-merged yet their YAMLs remain. So I should **not** delete FEAT-APP-001.yaml (already `status: completed`).
- **Completed multi-task features get a folder in `tasks/completed/`** (like `deepagents-tutoring-loop` with its README + IMPLEMENTATION-GUIDE).
- Recent features aren't archived to `.guardkit/archive/` (only two old ones there).

So the real finalization = **move the feature's task folder backlog → completed**. Let me confirm the autobuild-state convention and a completed feature's terminal status, then act.

Now I have the full convention: this repo **keeps** completed feature YAMLs *and* autobuild dirs (FEAT-SMP-002/003 and dozens of completed tasks still have theirs) — nothing is deleted. The one meaningful, convention-matching action is **moving the task folder backlog → completed**. Let me run the official CLI (placeholder archival + handoff panel), then do the real finalization it skips.

The CLI refused because the feature is already `status: completed` (from the earlier task rollup) — its archival is placeholder anyway, so no loss. The meaningful action succeeded: the task folder moved cleanly to `tasks/completed/`. Let me run the official completion with `--force` to close it properly, then commit.

Feature officially completed (8/8). Now commit the task-folder move to `completed/`:

Let me verify the commit contains only the task-folder renames (the hook-state files were unstaged and should be excluded):
