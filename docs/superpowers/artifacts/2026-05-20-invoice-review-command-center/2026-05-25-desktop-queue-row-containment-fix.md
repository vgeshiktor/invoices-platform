# Desktop Queue Row Containment Fix

Date: 2026-05-25
Figma file: [Invoice Review Command Center Prototype](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf)

## Scope of this pass

This pass followed the queue-row review exactly:

- desktop queue-card visual style was preserved
- stats row, detail panel, and mobile frames were not redesigned
- only the desktop Today queue-row internals were rebuilt to prevent text and CTA overlap

Primary desktop frame:

- [Desktop - Today](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf?node-id=6-45)

Reference desktop frame left untouched in this pass:

- [Desktop - This Month](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf?node-id=6-303)

## Applied fix

The overlap came from three competing elements sharing the same lower band inside each queue card:

- chips
- metadata text
- CTA button

Applied corrections:

- kept the existing card appearance, blue selected state, chips, button styling, and top-row vendor/amount hierarchy
- increased each Today queue-row card height to `188px`
- created a dedicated lower-left content stack inside each card
- stacked the bottom-left content as:
  - chips row
  - meta row
- created a fixed `150px` CTA column on the right side of each card
- kept the CTA button at `128px` width and bottom-right aligned inside that column
- preserved a fixed `24px` gap between the left content region and the CTA column

## Final geometry

For all three Today queue cards:

- card height: `188`
- left content block: `x=24`, `y=126`, `width=490`, `height=49`
- CTA column: `x=538`, `y=24`, `width=150`, `height=140`
- CTA button: `128x34`
- protected gap between content and CTA: `24px`
- meta text width: `490px`

## Acceptance outcome

- Button never overlaps meta text.
- Meta text never enters the button area.
- Chips and meta are visually separated.
- Reason text remains readable.
- All three row cards share the same internal alignment.
- CTA buttons stay aligned right.
- No redesign of colors, card shape, or overall style happened in this pass.
