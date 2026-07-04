# QUESTIONS — overnight Flutter build

(no contract doubts, no dependency wants — the closed list in scope §6 was enough)

## Contract ambiguities (for FEAT-SMP-003 / next contract revision)

- **Contract §5 `resume_if_active` with duplicate `(student, subject)` actives.** The contract's wording is singular ("an active session … returns *it*") but nothing forbids duplicates — `start_session` without the flag always creates another active session (pinned by the contract test suite). Which one should the flag resume? The fake now picks the **most recently active** (aligned with `list_sessions`' "resume where you left off" ordering) and a contract test pins that choice; the real backend must either match it or the contract should gain a uniqueness rule. Raised by the 2026-07-04 morning-gate review.

## Notes for morning review (not questions)

- **`git diff main` shows a phantom deletion of `docs/runbooks/RUNBOOK-overnight-fable-flutter-launch.md`.** Not a blast-radius violation: `main` moved ahead after this branch was cut — commit `3d448ac` (on main only) added that file post-branch, so a plain diff against `main` reports it as "deleted" here. `git log main..HEAD -- docs/` confirms no overnight commit touched anything outside `app/**`. Diffing against the merge-base (`git diff 002a313 --stat`) shows `app/**` only.
