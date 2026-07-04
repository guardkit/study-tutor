# QUESTIONS — overnight Flutter build

(no contract doubts, no dependency wants — the closed list in scope §6 was enough)

## Notes for morning review (not questions)

- **`git diff main` shows a phantom deletion of `docs/runbooks/RUNBOOK-overnight-fable-flutter-launch.md`.** Not a blast-radius violation: `main` moved ahead after this branch was cut — commit `3d448ac` (on main only) added that file post-branch, so a plain diff against `main` reports it as "deleted" here. `git log main..HEAD -- docs/` confirms no overnight commit touched anything outside `app/**`. Diffing against the merge-base (`git diff 002a313 --stat`) shows `app/**` only.
