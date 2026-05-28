# UX Review Method

This repository uses a journey-first method for UX review.

The core rule is simple:

> When discussing user experience, talk about the journey, not just the screen.

A screen can be judged for craft in isolation. It cannot be judged for product quality in isolation. The content, hierarchy, and calls to action on a screen are only correct relative to the user's goal, the step they are in, and the capabilities the product gives them at that moment.

## Why this exists

UI comments often mix two different review modes:

- visual craft review
- product UX review

Those are not the same thing.

### Visual craft review

This is valid even when the reviewer does not know the full product context.

It can evaluate:

- contrast
- spacing
- grouping
- legibility
- consistency
- scanability
- whether the primary action visually stands out

It should not claim that the screen content itself is correct for the user task.

### Product UX review

This is only valid when the reviewer understands all of the following:

- who the user is
- what they are trying to accomplish
- where this screen sits in the journey
- what information they already have
- what actions are currently available
- what success and failure mean on this step

Without that context, feedback on content hierarchy or action strategy is guesswork.

## Required inputs before reviewing a screen

Before giving product-level UX feedback on any screen in this repo, document these inputs:

1. User
   The actor using the screen and the operational context they are in.
2. Goal
   The job to be done on this visit, not the generic product mission.
3. Journey stage
   What happened immediately before this screen, and what should happen immediately after it.
4. Available capabilities
   Which actions the system currently allows, blocks, or defers.
5. Decision
   The main decision the user is expected to make on this step.
6. Success condition
   What "done" looks like for this screen.
7. Failure or blocker condition
   What can prevent completion, and how that is surfaced.

If these inputs are missing, the review must be labeled as a visual craft review, not a product UX review.

## Review flow for UI-heavy work

For feature specs, prototypes, and approval passes, use this order:

1. Define the user and their immediate goal.
2. Map the journey step and surrounding transitions.
3. State the purpose of the screen in that journey.
4. Identify the single primary decision and the single primary action for that state.
5. Review information hierarchy against that decision.
6. Review visual hierarchy against that action.
7. Record any unresolved UX debt as an explicit follow-up.

This sequence prevents a common failure mode: polishing a screen that looks coherent but does not help the user move forward.

## CTA hierarchy rule

Every decision state must have one unmistakable primary action.

- If the user can complete the task now, the completion action should be the most visually salient control in its group.
- If the task is blocked, the unblock action becomes the primary CTA and the completion action should remain visible but clearly disabled or secondary.
- Nearby pills, chips, and secondary controls must not compete with the primary CTA for attention.

The test is simple: a user should be able to identify the next best action as quickly as they would notice a doorbell on a plain wall.

## Visual differentiation rule

When one card, row, or panel is highlighted relative to peers:

- preserve a clear boundary around the highlighted item
- use one dominant emphasis signal first, such as fill, border, or elevation
- avoid relying on a silent shape change that conflicts with the pattern established by sibling elements

Example principle:

- if sibling cards all use a contour, the selected or highlighted card should still preserve a legible boundary rather than dropping the contour and asking color alone to do all the work

This avoids momentary confusion about whether the difference means selection, status, or a different component type.

## What every UI-oriented spec should contain

Any spec in this repo that proposes a screen, workflow, or interactive surface should include:

- user and operating context
- user goal for the visited state
- journey stage and transition in/out
- primary decision on the screen
- primary CTA for each important state
- blocker conditions and how they change CTA hierarchy
- visual differentiation rules for selected, highlighted, risky, and resolved states

## Deliverables for review passes

A design review artifact should capture:

- what feedback was received
- whether it was visual craft feedback or product UX feedback
- what repo document or spec changed because of it
- what follow-up work remains, if any

This keeps review comments from disappearing into chat history and turns them into reusable product knowledge.
