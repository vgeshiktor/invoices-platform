# Remaining Design Prompts

Date: 2026-06-02
Scope: Remaining Milestone 11 design follow-up for `#63` and `#64`

## FE-1101 Tablet Validation Note

The missing tablet concept work is no longer blank. The user provided tablet-design links that resolve to one shared Figma Make workspace:

- Tablet Today: [Create Tablet Review Frames](https://www.figma.com/make/ERTkTps2LKHza6lyyUPsRp/Create-Tablet-Review-Frames?fullscreen=1&t=4NFWOG5jwbujrT2A-1&code-node-id=0-9)
- Tablet This Month: [Create Tablet Review Frames](https://www.figma.com/make/ERTkTps2LKHza6lyyUPsRp/Create-Tablet-Review-Frames?fullscreen=1&t=4NFWOG5jwbujrT2A-1&code-node-id=0-9)

Validation note:

- Both links point to the same Figma Make file.
- The Make context includes `TabletToday.tsx` and `TabletThisMonth.tsx`.
- Treat `#63` as a validation and finalization pass, not a from-scratch tablet ideation task.

## FE-1102 Prompt

Use this prompt for the remaining readability and accessibility cleanup on the mobile detail design:

```text
Open the existing Figma file "Invoice Review Command Center Prototype" and run a focused readability/accessibility pass on the mobile invoice detail frame.

Target frame:
- Mobile Invoice Detail: node 6:521

Known issue from the repo audit:
- Inside the "Decision required" card, the small "EVIDENCE" eyebrow label sits too high and visually collides with the main decision block.

Primary goal:
- Fix the mobile detail readability issue without changing the product logic or losing the current premium dense-finance feel.

Constraints:
- Keep the current mobile flow concept:
  - full-screen detail
  - metadata-first hierarchy
  - sticky primary action area
  - facts and source content below the decision block
- Do not redesign the screen from scratch.
- Preserve the existing hierarchy where the operator can quickly answer:
  1. why this invoice is here
  2. what is risky or missing
  3. what the next correct action is

Review and polish:
- section label placement
- vertical spacing inside the Decision required card
- text collision risk
- chip readability
- type sizing for dense fields
- contrast and separation between labels, body text, and supporting notes
- sticky action area clarity
- safe spacing above the bottom action bar

Required acceptance criteria:
- No overlapping or visually colliding text in the Decision required card.
- Section labels must read as deliberate structure, not accidental floating text.
- Dense content must stay readable on mobile without looking oversized or loose.
- The primary CTA must still dominate the action area.
- The final frame should remain visually consistent with the approved desktop/mobile system.

Output:
- Update the existing mobile detail frame or create a clearly named revised variant in the same Figma file.
- Keep the revised frame easy to reference later as the FE-1102 completion artifact.
```

## Combined Prompt

Use this when the same pass should finish both remaining issues:

```text
Finish the remaining Milestone 11 design gaps using the existing command-center design and the provided tablet Make workspace.

Remaining issues:
- FE-1101: validate and finalize the provided tablet-responsive command-center frames
- FE-1102: fix the mobile detail readability/accessibility defect in node 6:521

Approved anchors in the main design file:
- Desktop Today: node 6:45
- Desktop This Month: node 6:303
- Mobile Today: node 6:439
- Mobile Invoice Detail: node 6:521

Provided tablet source:
- https://www.figma.com/make/ERTkTps2LKHza6lyyUPsRp/Create-Tablet-Review-Frames?fullscreen=1&t=4NFWOG5jwbujrT2A-1&code-node-id=0-9

What to do:
1. Validate and finalize the provided tablet Today and tablet This Month states so tablet coverage is explicit and reviewable.
2. Repair the mobile detail typography/spacing issue in the Decision required card.
3. Recheck chip readability, CTA prominence, and section boundaries after the updates.

Non-goals:
- no broad visual redesign
- no new product features
- no changes that weaken the exception-first review flow

Definition of done:
- tablet coverage exists as a clear artifact for FE-1101
- the mobile detail readability issue is visibly resolved for FE-1102
- the resulting frames still look like one coherent invoice review command-center system
```
