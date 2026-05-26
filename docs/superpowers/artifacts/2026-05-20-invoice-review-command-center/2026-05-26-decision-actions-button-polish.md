# Decision Actions Button Polish

Date: 2026-05-26
Figma file: [Invoice Review Command Center Prototype](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf)

## Scope of this pass

This pass followed the dedicated button review exactly:

- desktop selected-invoice button design was preserved
- the `Decision required` card content was not redesigned
- queue cards, stats row, monthly comparison, and mobile frames were not touched
- only the desktop action buttons under the `Decision required` card were adjusted

Primary desktop frame:

- [Desktop - Today](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf?node-id=6-45)

## Applied fix

The button hierarchy was already correct. The remaining issue was spacing and intentional disabled-state behavior.

Applied corrections:

- kept the 3-button horizontal row
- kept `Change category` as the black primary button
- kept `Mark reviewed` as the disabled grey button
- kept `Open source thread` as the outlined secondary button
- kept the explanatory note below the row
- added more breathing room between the `Decision required` card and the button row
- locked consistent spacing between the buttons
- kept the button row aligned to the same left and right edges as the `Decision required` card
- made the disabled button read more intentionally disabled while preserving text legibility

## Final geometry

- `Decision required` card: `x=24`, `y=172`, `width=552`, `height=188`
- button row top: `y=376`
- gap from card to buttons: `16px`
- button heights: `44px`
- gaps between buttons: `12px`
- note top gap below buttons: `8px`

Row alignment:

- left edge matches the `Decision required` card
- right edge matches the `Decision required` card

Disabled button:

- `Mark reviewed` button opacity: `0.68`
- label remains centered and readable

## Acceptance outcome

- Buttons keep the same hierarchy and style.
- The row no longer feels attached to the `Decision required` card.
- Button spacing is consistent across the row.
- The row stays aligned to the same content width as the `Decision required` card.
- The disabled button reads clearly as disabled but still legible.
- No button text clips or overflows.
