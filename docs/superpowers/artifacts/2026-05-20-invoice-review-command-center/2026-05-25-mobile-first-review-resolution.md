# Mobile-First Review Resolution

Date: 2026-05-25
Figma file: [Invoice Review Command Center Prototype](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf)

## Scope of this pass

This pass followed the latest review guidance exactly:

- desktop layout was preserved
- desktop received containment fixes only
- mobile was rebuilt as a mobile-first operator workflow

## Desktop changes

Desktop structure was intentionally kept.

Applied fixes:

- stat cards were increased to a safer height so support text no longer overruns the card body
- `Desktop - This Month` now shows five queue rows plus a `View 3 more invoices` row instead of cramming the full monthly queue into the panel
- the monthly trust card was increased to a safer height

Primary desktop frames:

- [Desktop - Today](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf?node-id=6-45)
- [Desktop - This Month](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf?node-id=6-303)

## Mobile rebuild

### Mobile Today

The mobile landing screen was rebuilt into a feed:

- no back button
- one-row tab strip
- compact summary strip instead of a 2x2 analytics grid
- larger invoice cards with clear review reasons
- fixed-width right-aligned amount area
- separate meta row that no longer collides with chips

Primary frame:

- [Mobile - Today](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf?node-id=6-439)

### Mobile Invoice Detail

The detail screen was rebuilt as a scroll-based review flow:

- amount + status + short summary at the top
- explicit `Decision required` card
- sticky primary action at the bottom
- facts and source preview pushed into the scroll content rather than forced above the fold
- safe bottom spacing preserved inside the sticky action area

Primary frame:

- [Mobile - Invoice Detail](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf?node-id=6-521)

## 360x780 QA variants

To validate the mobile designs beyond the main `390x844` approval frames, two QA variants were added:

- [Mobile - Today / QA 360x780](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf?node-id=65-2)
- [Mobile - Invoice Detail / QA 360x780](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf?node-id=65-71)

These are validation frames, not new approval deliverables.

## Acceptance checklist outcome

- `Mobile Today` has no back button.
- Date tabs are rendered as a single horizontal row.
- First invoice card begins before `y=220`.
- At least two invoice cards remain readable without compression.
- Amounts are right-aligned inside fixed-width slots.
- Meta lines no longer overlap chips.
- The detail screen has one obvious sticky primary action.
- The detail screen now behaves as a scroll-based view instead of trying to fit every section above the fold.
- `390x844` primary frames were rechecked.
- `360x780` QA variants were added and rechecked.

## Geometry verification

Visible tiny-width geometry audit after this pass:

- `Desktop - Today`: `0`
- `Desktop - This Month`: `0`
- `Mobile - Today`: `0`
- `Mobile - Invoice Detail`: `0`
- `Mobile - Today / QA 360x780`: `0`
- `Mobile - Invoice Detail / QA 360x780`: `0`
