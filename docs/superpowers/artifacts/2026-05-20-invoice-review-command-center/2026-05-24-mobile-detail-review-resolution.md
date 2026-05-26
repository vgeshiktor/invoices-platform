# Mobile Detail Review Resolution

Date: 2026-05-24
Frame: [Mobile - Invoice Detail](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf?node-id=6-521)

## Summary

The 2026-05-20 mobile invoice detail frame had real structural problems:

- broken header width
- zero-width facts and source-preview containers
- non-wrapping explanatory copy
- action overflow
- weak explanation of why the invoice required review

This review pass rebuilt the mobile detail frame and resolved those issues directly in Figma.

## Resolved

- Header now renders at full width with visible `Back`, `Invoice detail`, vendor, and `Open`.
- Amount, chips, and explanation copy now wrap correctly inside the viewport.
- `Why review is needed` was added as an explicit operator-guidance block.
- Review logic now calls out three causes:
  - category missing
  - VAT exceeding subtotal
  - vendor match still plausible rather than confirmed
- Primary action order now reflects the workflow:
  - `Change category` first
  - `Mark reviewed` visually blocked until category assignment
- Facts now render as a usable two-column mobile grid.
- Category and VAT are highlighted as the fields most likely to need operator attention.
- Source preview is visible inside the viewport.
- `Open source thread` now lives inside the source section instead of competing with the primary action row.

## Intentional Product Behavior

- The screen now makes it clear that review is not complete until categorization is resolved.
- The suspicious VAT-to-subtotal relationship is treated as a review reason, not hidden inside raw fields.
- The source area stays subordinate to the operational facts, but is visible enough to support evidence-based verification.

## Remaining Deferred Items

No new P0 blockers remain in this frame after the 2026-05-24 pass.

Still deferred by design scope:

- tablet-specific adaptation beyond the approved desktop/mobile frames
- richer duplicate-comparison drill-down states outside this uncategorized review scenario
