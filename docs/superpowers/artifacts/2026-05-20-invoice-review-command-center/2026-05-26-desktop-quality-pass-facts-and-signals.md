# Desktop Quality Pass: Facts and Supporting Signals

Date: 2026-05-26
Figma file: [Invoice Review Command Center Prototype](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf)

## Scope of this pass

This pass addressed the desktop review that identified the `Facts` card as the remaining quality regression.

Kept intact:

- desktop command-center layout
- selected-invoice structure
- `Decision required` card
- action buttons
- queue-card visual style
- evidence preview concept
- mobile screens

Adjusted in this pass:

- `Facts` card presentation and containment
- `Exposure` KPI meaning
- `Saved views` visual priority
- queue/detail blocker wording

Primary desktop frame:

- [Desktop - Today](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf?node-id=6-45)

## Facts card repair

The previous version was technically contained, but it still looked visually patched because `Category` and `VAT` used oversized highlighted blocks.

Applied corrections:

- rebuilt `Facts` into a calmer 2-column field grid
- removed the oversized yellow tile treatment
- kept problem states visible through small status tags instead
- forced `Not assigned` back to a one-line value
- added an explicit VAT explanation via a compact `Exceeds subtotal` note
- preserved the `Evidence and trust` card so both lower cards now feel balanced rather than stylistically disconnected

Final Facts geometry:

- card size: `268 x 298`
- grid row gap: `14`
- `Not assigned` value: `106 x 18`
- `Required` badge: `63 x 22`
- `Exceeds subtotal` note badge: `106 x 22`

## Supporting signal fixes

To remove the last “prototype” signals from the desktop frame:

- renamed `Exposure` to `At-risk amount`
- updated the KPI description to `Today-only invoices waiting for action.`
- demoted `Saved views` from a dark primary button to a secondary outlined control
- shortened the selected queue reason to `Missing category · VAT anomaly`
- replaced `Uncategorized` with `Category required` in the selected invoice and matching queue state

## Acceptance outcome

- `Not assigned` no longer wraps awkwardly.
- The `Facts` card reads as a disciplined field grid instead of a patched tile experiment.
- VAT anomaly is explained instead of only highlighted.
- `Facts` and `Evidence and trust` now feel closer in visual quality.
- `At-risk amount` is clearer than the previous `Exposure` wording.
- `Saved views` no longer competes like a primary action.
- Queue and selected-invoice blocker vocabulary are more consistent.
