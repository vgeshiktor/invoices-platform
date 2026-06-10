# Invoice Review Command Center Prototype Artifacts

This directory is the repo-backed source package for the invoice review prototype.

## Contents

- Design spec: [2026-05-20-invoice-review-command-center-design.md](../../specs/2026-05-20-invoice-review-command-center-design.md)
- Repo UX review method: [UX_REVIEW_METHOD.md](../../../UX_REVIEW_METHOD.md)
- Implementation plan: [2026-05-20-invoice-review-command-center-prototype.md](../../plans/2026-05-20-invoice-review-command-center-prototype.md)
- Fixtures: [invoice-fixtures.json](./invoice-fixtures.json)
- Tracker manifest: [github-tracker-manifest.json](./github-tracker-manifest.json)
- Figma review links: [figma-approval-links.json](./figma-approval-links.json)
- Journey-first review method adoption: [2026-05-28-journey-first-review-method.md](./2026-05-28-journey-first-review-method.md)
- Mobile detail review resolution: [2026-05-24-mobile-detail-review-resolution.md](./2026-05-24-mobile-detail-review-resolution.md)
- Structural rebuild review resolution: [2026-05-25-command-center-structural-rebuild.md](./2026-05-25-command-center-structural-rebuild.md)
- Mobile-first review resolution: [2026-05-25-mobile-first-review-resolution.md](./2026-05-25-mobile-first-review-resolution.md)
- Desktop stats containment fix: [2026-05-25-desktop-stats-containment-fix.md](./2026-05-25-desktop-stats-containment-fix.md)
- Desktop queue-row containment fix: [2026-05-25-desktop-queue-row-containment-fix.md](./2026-05-25-desktop-queue-row-containment-fix.md)
- Decision card column containment fix: [2026-05-25-decision-card-column-containment-fix.md](./2026-05-25-decision-card-column-containment-fix.md)
- Decision actions button polish: [2026-05-26-decision-actions-button-polish.md](./2026-05-26-decision-actions-button-polish.md)
- Lower cards containment fix: [2026-05-26-lower-cards-containment-fix.md](./2026-05-26-lower-cards-containment-fix.md)
- Desktop quality pass: Facts and supporting signals: [2026-05-26-desktop-quality-pass-facts-and-signals.md](./2026-05-26-desktop-quality-pass-facts-and-signals.md)
- Tablet transfer artifact pack: [2026-06-09-tablet-transfer-artifact-pack.md](./2026-06-09-tablet-transfer-artifact-pack.md)
- E12 gap audit: [2026-05-31-e12-gap-audit.md](./2026-05-31-e12-gap-audit.md)
- Stakeholder approval screenshot pack: [approval-pack/README.md](./approval-pack/README.md)
- Desktop Today reproducibility guide: [desktop-today-reproducibility.md](./desktop-today-reproducibility.md)
- Desktop Today reproducibility snapshot: [desktop-today-reproducibility.json](./desktop-today-reproducibility.json)
- GitHub tracker results: [github-tracker-results.json](./github-tracker-results.json)

## Figma

- File URL: [Invoice Review Command Center Prototype](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf)
- File key: `ORTJPMYSjhBp8TZGZktrWf`
- Tablet Make workspace: [Create Tablet Review Frames](https://www.figma.com/make/ERTkTps2LKHza6lyyUPsRp/Create-Tablet-Review-Frames?t=hSvSYAJhHMpZP8jw-1)
- Tablet Make key: `ERTkTps2LKHza6lyyUPsRp`

## Approval Frames

- Desktop Today: [node 6:45](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf?node-id=6-45)
- Desktop This Month: [node 6:303](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf?node-id=6-303)
- Mobile Today: [node 6:439](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf?node-id=6-439)
- Mobile Detail: [node 6:521](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf?node-id=6-521)
- Screenshot pack: [approval-pack/README.md](./approval-pack/README.md)
- Review note: the mobile detail frame was rebuilt on 2026-05-24 to resolve collapsed-width layout bugs and strengthen review-state logic.
- Review note: all four approval frames were structurally rebuilt on 2026-05-25 so the geometry audit reports zero visible tiny-width containers.
- Review note: a second 2026-05-25 pass preserved desktop structure, rebuilt mobile for feed-and-scroll behavior, and added 360x780 QA validation frames.
- Review note: a focused 2026-05-25 desktop pass corrected only the stats-card description containment while preserving the rest of the dashboard.
- Review note: a second focused 2026-05-25 desktop pass corrected only the Today queue-row CTA/meta containment while preserving the queue-card styling.
- Review note: a third focused 2026-05-25 desktop pass corrected only the selected-invoice Decision required card column containment while preserving the component style.
- Review note: a focused 2026-05-26 desktop pass adjusted only the selected-invoice action row spacing and disabled-state polish while preserving the button design.
- Review note: a second focused 2026-05-26 desktop pass corrected only the selected-invoice lower-card containment for `Facts` and `Evidence and trust`.
- Review note: a third focused 2026-05-26 desktop pass removed the remaining `Facts`-card regression and tightened supporting desktop signals for a more production-ready finish.
- Review note: a 2026-05-28 documentation pass anchored the stakeholder feedback into a repo-wide journey-first UX review method and tightened the command-center spec around CTA hierarchy and selected-state differentiation.
- Reproducibility note: `Desktop - Today` still has the repo-backed structural snapshot and recreate guide, and the approval-pack now adds durable PNG exports for the four primary frames.

## GitHub Tracker

- Milestone: [#11 Invoice Review Command Center Prototype](https://github.com/vgeshiktor/invoices-platform/milestone/11)
- Umbrella epic: [#46](https://github.com/vgeshiktor/invoices-platform/issues/46)
- Epics:
  - [#47 E9](https://github.com/vgeshiktor/invoices-platform/issues/47)
  - [#48 E10](https://github.com/vgeshiktor/invoices-platform/issues/48)
  - [#49 E11](https://github.com/vgeshiktor/invoices-platform/issues/49)
  - [#50 E12](https://github.com/vgeshiktor/invoices-platform/issues/50)
- Issue range:
  - FE-801 to FE-804: [#51](https://github.com/vgeshiktor/invoices-platform/issues/51) to [#54](https://github.com/vgeshiktor/invoices-platform/issues/54)
  - FE-901 to FE-904: [#55](https://github.com/vgeshiktor/invoices-platform/issues/55) to [#58](https://github.com/vgeshiktor/invoices-platform/issues/58)
  - FE-1001 to FE-1004: [#59](https://github.com/vgeshiktor/invoices-platform/issues/59) to [#62](https://github.com/vgeshiktor/invoices-platform/issues/62)
  - FE-1101 to FE-1104: [#63](https://github.com/vgeshiktor/invoices-platform/issues/63) to [#66](https://github.com/vgeshiktor/invoices-platform/issues/66)

## Deferred UX Issues

- Tablet evidence is now anchored in [2026-06-09-tablet-transfer-artifact-pack.md](./2026-06-09-tablet-transfer-artifact-pack.md), which records the shared Figma Make workspace for `Tablet Today`, `Tablet This Month`, and `Tablet Invoice Detail`. Any remaining FE-1101 closeout work is traceability polish, not missing concept coverage.
- Duplicate-pair comparison messaging can be expanded in a dedicated comparison state under [FE-1004](https://github.com/vgeshiktor/invoices-platform/issues/62) if stakeholder review asks for a side-by-side original versus receipt experience.
- The latest E12 audit in [2026-05-31-e12-gap-audit.md](./2026-05-31-e12-gap-audit.md) narrows the remaining milestone blockers to `#63` tablet review and `#64` mobile-detail readability/accessibility cleanup.
