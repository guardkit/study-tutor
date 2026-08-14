# FEAT-AUTH-004 — the digest for Rich's spec word

*One page. The full spec is [`FEAT-AUTH-004-device-pairing-spec.md`](FEAT-AUTH-004-device-pairing-spec.md)
— you rule on this page, not on that one (playbook amendment 6).*
**Date:** 2026-08-14 · **Lane:** Auth (the last step of it) · **Written from files only** —
no live host, realm or container was touched.

## What it is

The robot signs itself in, the way a TV does. Instead of someone typing a secret password
into the robot's settings page, you tap **Pair this robot**, the page shows a short code,
you approve it once in a browser signed in as Lilymay, and the robot holds its own
long-lived sign-in from then on. It refreshes itself. You can cancel it from Keycloak
whenever you like, and nothing on her phone has to change.

When this lands, **no device anywhere is holding a shared password any more**, and the old
static-token system is switched off for good.

## Why now

- **You already ruled it this way.** E3, 7 August: the typed-in token is fine *for now*,
  device pairing comes after — with Dulcie's robot in September as the natural deadline.
  Her robot is the second one, and doing this before it arrives means we pair a robot
  rather than copy a secret twice.
- **August 14 showed the cost of the old way.** Retiring one leaked token meant chasing
  **three** copies on the robot alone — including a backup folder that would have brought
  the dead token back to life — plus rebuilding and re-installing the app on Lilymay's
  phone. After this feature, that same job is one click in an admin console.
- **The hard part is already done.** The robot's sign-in method is switched on in Keycloak
  today (confirmed 14 August), the server already accepts these sign-ins, and the robot's
  tutoring already works end to end. This is joining up parts that exist.

## What we found while writing it

One real snag, and it is a settings change, not a code change: Keycloak would issue the
robot a sign-in that our server **rejects**, because the robot's entry in the realm is
missing one line that the phone's entry has. It is a two-minute fix in the realm file, but
it would have looked like a mysterious "access denied" on the night of the build. It is
now written down with the fix.

**Nothing in the study-tutor server changes.** No app changes either. All the building
happens in the robot's own repo.

## The risks, honestly

- **A robot switched off all summer comes back needing re-pairing.** The sign-in expires
  after ~30 days of no contact. The tutor starts automatically when the robot is on, so
  this only bites after a long break. It will say so plainly and re-pairing is one tap —
  but it is a real thing that will happen one September.
- **If the sign-in fails mid-session, she hears one honest line** — *"The tutor isn't
  reachable right now."* — and nothing else. No prompt, no code on a screen mid-lesson,
  and the session stays safe on the server for her phone to pick up. Nothing ends sadly.
- **The robot signs in as Lilymay, so it can do anything she can.** That is deliberate —
  it is what lets her start on her phone and carry on with the robot. There is no
  reduced-permission robot in this phase.
- **The file on the robot is still a file.** Anyone with full access to the Pi could read
  it. What we gain is that it expires, it can be cancelled remotely, and it is *hers* and
  only that robot's — not a shared secret in three places.
- **The retirement step is the one with real blast radius** — switching the old token
  system off. It happens last, a week after everything is proven, with backups either
  side, and it is reversible with one restart.

## What you tap

Five questions. The recommendation is given for each; a "yes to all" is a valid answer.

1. **Who signs in at the pairing screen?** Someone has to log in as Lilymay to approve it.
   *Recommend: she does, with you there* — it keeps her password hers, and it is the same
   thing she already does on her phone.
2. **Is "off all summer means re-pair" acceptable?** *Recommend: yes* — with an honest
   message and a one-tap fix, rather than adding machinery to avoid it.
3. **When we retire the old system, do we switch the existing address over in place, or
   move everyone to the newer one?** *Recommend: switch in place* — every device already
   points at the current address, so no phone rebuild and no robot re-configuration.
4. **Dulcie's robot in September:** ship this for one child now and add her account when
   her robot arrives? *Recommend: yes* — pairing is per-robot by design; her account is a
   ten-minute job on the day.
5. **How long do we run green before switching the old system off?** *Recommend: a week
   from whichever of phone-or-robot cuts over last*, so both have done real sessions on
   the same server.

## One thing that has to happen first, and it is not ours

Lilymay's phone still needs the build that puts it on the new sign-in (ruling queue #12's
last human step). The robot can be paired before that — but the old system cannot be
switched off until her phone has moved, or she is stranded mid-term.

## What "done" looks like

She starts a session on her phone, walks over to the robot, touches its antenna, and it
carries on the *same* session — because both are signed in as her, not because they share
a password. The old token list is empty. Cancelling the robot's access is one click and
her phone never notices.
