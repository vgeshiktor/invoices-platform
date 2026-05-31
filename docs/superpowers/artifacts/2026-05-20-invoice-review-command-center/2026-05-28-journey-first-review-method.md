# Journey-First Review Method Adoption

Date: 2026-05-28
Scope: Repo UX review method plus command-center product framing

## Feedback addressed

The stakeholder feedback introduced two important corrections:

1. A screen should not be judged for UX quality without understanding the user's purpose, journey, and available capabilities.
2. A primary CTA must stand out clearly from nearby capsules or secondary controls.

It also raised a more detailed visual caution:

- if peer cards use a contour and a highlighted card drops that contour entirely, users may briefly read the difference as a component change instead of a selected or emphasized state

## Repo decisions

This feedback is now anchored in the repository in two places:

1. Repo-wide method
   [docs/UX_REVIEW_METHOD.md](../../../UX_REVIEW_METHOD.md) defines the standard that UX review in this repo is journey-first, not screen-first.
2. Feature-level application
   [2026-05-20-invoice-review-command-center-design.md](../../specs/2026-05-20-invoice-review-command-center-design.md) now documents the operator goal, journey stage, CTA hierarchy, and selected-state differentiation rules for the invoice review workspace.

## Product interpretation for this prototype

For the invoice review command center, the practical translation is:

- the screen must explain why an invoice is in the queue
- the screen must show what is risky or incomplete
- the screen must make the next valid action obvious

The correct primary CTA depends on state:

- if review is unblocked, the completion action should dominate
- if review is blocked, the unblock action should dominate and `Mark reviewed` should remain visible but unavailable

This keeps the command center faithful to operator workflow instead of treating every selected invoice like a generic record viewer.

## Flow impact

Future design reviews for this workspace should use this order:

1. verify the operator goal and journey step
2. verify the reason the invoice surfaced
3. verify the primary decision on the screen
4. verify CTA prominence for that state
5. verify selected-state visual differentiation

## Outcome

The feedback is no longer just a comment on one mockup. It is now part of the repo's review method and part of the command-center design contract.
