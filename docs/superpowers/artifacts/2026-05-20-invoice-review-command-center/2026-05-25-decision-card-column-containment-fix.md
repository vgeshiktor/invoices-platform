# Decision Card Column Containment Fix

Date: 2026-05-25
Figma file: [Invoice Review Command Center Prototype](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf)

## Scope of this pass

This pass followed the dedicated desktop review exactly:

- desktop selected-invoice structure was preserved
- the Decision required card style was preserved
- queue cards, stats row, monthly comparison, and mobile frames were not redesigned
- only the desktop selected-invoice `Decision required` card was rebuilt internally to prevent column overlap

Primary desktop frame:

- [Desktop - Today](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf?node-id=6-45)

## Applied fix

The card concept was already correct. The problem was that the headline and evidence content were sharing the same horizontal space.

Applied corrections:

- kept the card look, typography direction, and overall selected-invoice layout
- preserved the left decision content and right evidence concept
- converted the card into a true 2-column internal layout
- kept the left column for:
  - decision label
  - decision headline
  - supporting body copy
- kept the right column for:
  - evidence label
  - short bullet-style evidence lines
- converted the evidence side from paragraph-like wrapping into compact proof points
- increased card height slightly so the two-column layout has breathing room

## Final geometry

Final card structure:

- card size: `552 x 188`
- card padding: `20`
- column gap: `24`
- left column: `332 x 148`
- right column: `156 x 148`

Text containment:

- headline width: `332`
- headline height: `60`
- evidence item width: `156`
- each evidence item height: `36`

## Final evidence structure

- `• Vendor recognized with medium confidence`
- `• Category missing blocks routing`
- `• VAT exceeds subtotal in extraction`

## Acceptance outcome

- Headline does not enter the evidence area.
- Evidence label and evidence text stay fully inside the right column.
- Evidence is readable without awkward paragraph wrapping.
- Left and right columns have clear separation.
- Card style stays the same.
- No redesign happened outside this component.
