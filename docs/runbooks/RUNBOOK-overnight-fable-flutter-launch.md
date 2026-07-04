# RUNBOOK — Agent-executed launch of the overnight Fable Flutter run (G-R0 + §3)

**Status:** Active. **Date:** 2026-07-04. **Owner:** Rich (operator: any attended Claude session).
**Parent:** [RUNBOOK-overnight-fable-flutter.md](RUNBOOK-overnight-fable-flutter.md) — that doc owns the gates, hard rules, and morning criteria; this doc only operationalises **G-R0 + §3** so the launch itself is agent-executable instead of hand-typed. If the two disagree, the parent wins.
**Why this exists:** every step of G-R0 except "leave the lid open" is a command with a checkable result. An attended agent runs the checks, launches the unattended session, verifies it is alive, and reports — the human contribution reduces to physical-world items and the go/no-go.

---

## 0. Preconditions (verify, don't assume)

All parent-runbook gates G-P0…G-R1 green. For the 2026-07-04 run these are commits
`1408dc0` (scope + ADR-ARCH-025), `4428b19` (wave-0 scaffold [green]), `002a313` (build plan + instruments) on `main`, with `CONTRACT_SHA=22791afbcdb3b71abbe6bd2f1b8e18218988942f`.

```bash
cd ~/Projects/appmilla_github/study-tutor
git status --porcelain          # must be empty
git worktree list               # no leftover overnight worktree
pmset -g batt                   # must show "AC Power" / "AC attached"
```

**Abort to B2** (parent §1) if any check fails and can't be fixed attended in minutes.

**Physical items the agent cannot do — operator confirms once at go/no-go:**
- MacBook lid stays **open** (or is docked to an external display): `caffeinate` does not prevent lid-close sleep on battery-less-display setups.
- Machine stays on mains overnight.

## 1. Worktree + branch

```bash
cd ~/Projects/appmilla_github/study-tutor
git worktree add -b overnight/fable-flutter-$(date +%F) ../study-tutor-overnight
```

Verify: `git -C ../study-tutor-overnight log --oneline -1` shows the same HEAD as `main`.

## 2. Warm the gate once in the worktree (attended)

The worktree is a fresh checkout; G-F0 was proven in the main checkout. Prove it here so wave-1 doesn't start cold:

```bash
cd ~/Projects/appmilla_github/study-tutor-overnight/app
flutter test && flutter build apk --debug
```

Gradle caches are shared (`~/.gradle`) — expect minutes, not the first-build 4 min. **Red here = do not launch.**

## 3. Kickoff prompt → file

Write the parent-runbook §3 kickoff prompt, SHA and plan path filled in, to a file (avoids shell-quoting damage through tmux):

```bash
cat > /tmp/fable-night-kickoff.txt <<'EOF'
Read docs/research/ideas/flutter-app-scope.md, the build plan at docs/research/ideas/flutter-app-build-plan.md, app/PROGRESS.md, and the pinned session contract at CONTRACT_SHA=22791afbcdb3b71abbe6bd2f1b8e18218988942f. Execute the build plan wave by wave under the hard rules in docs/runbooks/RUNBOOK-overnight-fable-flutter.md §2 — re-read plan + PROGRESS.md at every wave start; green = analyze + test + apk-debug; commit per wave; write only under app/**; contract is pinned, questions go to QUESTIONS.md; stop cleanly per rule 6 when quota ends or two waves block. The morning gate is pre-registered in the build plan §4 — optimise for waves that survive review, not waves attempted.
EOF
```

## 4. Launch inside tmux, caffeinate-wrapped

`caffeinate -dims <cmd>` holds the sleep assertion exactly as long as the session lives — no orphan caffeinate in the morning. "House permissions mode" is operationalised as `--dangerously-skip-permissions` (the run is sandboxed by the parent's blast-radius rules + worktree, and an unattended run must never stall on a prompt).

```bash
tmux new-session -d -s fable-night -c ~/Projects/appmilla_github/study-tutor-overnight
tmux send-keys -t fable-night 'caffeinate -dims claude --model "claude-fable-5[1m]" --dangerously-skip-permissions "$(cat /tmp/fable-night-kickoff.txt)"' Enter
```

If the `[1m]` model alias is rejected, relaunch with `--model claude-fable-5` (model pinned to Fable is the G-R0 requirement; 1M context is preference).

## 5. Verify liveness before walking away (mandatory)

```bash
sleep 90
tmux capture-pane -p -t fable-night | tail -40
```

Expected: Claude Code banner, Fable model, and the session reading the scope/plan/contract. Handle interactively if instead you see:
- a first-time `--dangerously-skip-permissions` acceptance dialog → `tmux send-keys -t fable-night <response>`;
- a model error → relaunch per §4 fallback;
- a shell error → diagnose; do not leave a dead pane and call it launched.

Re-capture after another ~2 min and confirm tool activity (file reads, wave-1 starting). Only then report "launched".

## 6. Morning teardown

Parent §6 is the gate. Mechanics: `tmux attach -t fable-night` (detach: `ctrl-b d`), review `app/PROGRESS.md` + `app/QUESTIONS.md` + `git log main..HEAD` in the worktree, spot re-run analyze/test, emulator-boot to the last wave's checkpoint ("simulator" = Android emulator — build plan §4 note). Keep: merge the branch. Discard: `git worktree remove ../study-tutor-overnight --force` + `git branch -D overnight/fable-flutter-<date>`. Ending the tmux session releases caffeinate automatically: `tmux kill-session -t fable-night`.

## 7. Abort at any point

`tmux kill-session -t fable-night` stops Claude and caffeinate together; green commits are already in the worktree branch; `git worktree remove` + branch delete is the full rollback. Nothing pushes.

---

*Generalisation note (parent's footer applies): on second use, promote alongside the parent to `ai-transition/docs/runbooks/` with repo/toolchain/model parameterised.*
