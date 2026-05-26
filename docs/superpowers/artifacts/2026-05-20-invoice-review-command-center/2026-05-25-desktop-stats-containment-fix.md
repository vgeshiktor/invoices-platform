# Desktop Stats Containment Fix

Date: 2026-05-25
Figma file: [Invoice Review Command Center Prototype](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf)

## Scope of this pass

This pass followed the focused desktop review exactly:

- desktop dashboard structure was preserved
- mobile frames were not touched
- only the desktop stats-row text containment was corrected

Primary desktop frames:

- [Desktop - Today](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf?node-id=6-45)
- [Desktop - This Month](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf?node-id=6-303)

## Applied fix

The stats cards already used the correct `124px` height from the previous pass. The remaining issue was inside the description text nodes.

Applied corrections:

- kept the existing 4-card layout, accent bars, color treatment, rounded cards, and action pills
- kept card width and horizontal spacing unchanged
- widened each description text node to a safer internal width
- tightened description copy only where needed so each card resolves to a two-line block
- preserved the existing top-right action-pill alignment

## Final description geometry

For both desktop frames, every stat-card description now resolves to:

- `y = 76`
- `height = 36`
- `card height = 124`

That leaves `12px` of bottom breathing room inside every card.

## Acceptance outcome

- All 4 stat cards keep equal height.
- No bottom description text crosses or touches the card border.
- Description text keeps at least `12px` of bottom breathing room.
- Action pills remain aligned top-right.
- Left accent bars still span full card height.
- The desktop layout below the stats row was not redesigned in this pass.
