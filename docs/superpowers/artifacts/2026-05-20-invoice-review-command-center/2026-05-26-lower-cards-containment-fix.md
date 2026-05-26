# Lower Cards Containment Fix

Date: 2026-05-26
Figma file: [Invoice Review Command Center Prototype](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf)

## Scope of this pass

This pass followed the dedicated desktop lower-card review exactly:

- kept the 2-card structure: `Facts` on the left and `Evidence and trust` on the right
- kept the card style, neutral treatment, titles, yellow highlights, and preview concept
- did not redesign the stats row, queue cards, decision card, action buttons, or mobile screens
- only the desktop selected-invoice lower cards were repaired internally for containment and spacing

Primary desktop frame:

- [Desktop - Today](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf?node-id=6-45)

## Facts card fix

The main issue was the `Category` value overflowing the highlighted area.

Applied corrections:

- rebuilt the card into a stricter 2-column grid
- kept `Category` and `VAT` as highlighted fields, but converted them into proper tiles
- matched `Category` and `VAT` tile sizing
- increased tile height so the `Not assigned` value stays fully inside the tile
- aligned label/value spacing more consistently across all grid cells

Final Facts geometry:

- card size: `268 x 298`
- card padding: `20 / 20 / 20 / 18`
- row gap: `12`
- column gap: `16`
- `Category` tile: `106 x 84`
- `VAT` tile: `106 x 84`
- `Category` value box: `78 x 36`

## Evidence and trust fix

The structure was correct, but the card was vertically overpacked.

Applied corrections:

- kept the same hierarchy: title, source heading, validation copy, preview, trust section
- rebuilt the content into a cleaner vertical stack
- shortened the validation copy so it fits as a compact supporting paragraph
- preserved the preview concept without compressing it unnaturally
- tightened the trust summary into a compact supporting line
- restored bottom breathing room for the trust section

Final Evidence and Trust geometry:

- card size: `268 x 298`
- card padding: `20 / 20 / 20 / 17`
- vertical stack gap: `16`
- source section height: `64`
- preview size: `228 x 80`
- trust section height: `64`

## Acceptance outcome

- `Not assigned` stays fully inside the `Category` tile.
- `Category` and `VAT` read as matched components.
- `Facts` uses a disciplined 2-column grid.
- Label/value spacing is more consistent across the `Facts` card.
- `Evidence and trust` has visible vertical breathing room.
- The `Trust layer` text stays fully contained and readable.
- No content touches or crosses a card border.
- No redesign happened outside these two lower cards.
