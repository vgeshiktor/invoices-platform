# Command Center Structural Rebuild

Date: 2026-05-25
Figma file: [Invoice Review Command Center Prototype](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf)

## Why this pass happened

The previous prototype still had structural Figma problems:

- near-zero-width container frames
- stacked or overflowing content that looked acceptable in screenshots but was not implementation-safe
- desktop work areas starting too low on the canvas
- invoice cards showing metadata without clearly stating why they needed review
- detail views reading like invoice records instead of operator decision surfaces

This pass fixed the file foundation first, then rebuilt the information hierarchy around operator decisions.

## Frames rebuilt

- [Desktop - Today](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf?node-id=6-45)
- [Desktop - This Month](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf?node-id=6-303)
- [Mobile - Today](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf?node-id=6-439)
- [Mobile - Invoice Detail](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf?node-id=6-521)

## Structural outcomes

- All four approval frames now have `0` tiny-width visible nodes in the geometry audit.
- Desktop stats, queue cards, detail facts, and source sections now have stable explicit widths.
- Mobile frames no longer contain collapsed parent containers or desktop-width internals.
- The desktop main work area now begins around the upper-middle of the canvas instead of presentation-style far below the fold.

## Product UX outcomes

### Desktop

- Stats cards now combine metric, implication, and next-step phrasing.
- Queue cards now include an explicit review reason, not just status chips.
- `Desktop - Today` now frames the selected invoice around a clear decision:
  - assign category before approval
  - confirm suspicious VAT extraction against evidence
- `Desktop - This Month` now uses a duplicate-pair review pattern instead of a generic detail page.

### Mobile

- `Mobile - Today` now behaves like an operator queue with decision reasons on every card.
- `Mobile - Invoice Detail` now leads with `Decision required` instead of a generic explanation block.
- Primary mobile actions now support the real flow:
  - resolve the blocking issue first
  - only then mark the invoice reviewed

## What changed in product logic

- The command center is now more exception-first than record-first.
- Every primary frame now answers:
  - why this invoice is here
  - what is missing or risky
  - what the operator should do next
- The monthly duplicate case now explicitly recommends duplicate resolution before approval.

## Verification

The 2026-05-25 geometry audit confirmed:

- `Desktop - Today`: `0` tiny-width visible nodes
- `Desktop - This Month`: `0` tiny-width visible nodes
- `Mobile - Today`: `0` tiny-width visible nodes
- `Mobile - Invoice Detail`: `0` tiny-width visible nodes

## Remaining non-blocking follow-up opportunities

- Refine desktop detail-card typography density even further if stakeholder review asks for a more premium visual tone.
- Add bulk actions and keyboard affordances in a later command-center workflow pass.
- Expand duplicate handling into a richer side-by-side comparison state if the monthly review flow becomes the highest-value operator path.
