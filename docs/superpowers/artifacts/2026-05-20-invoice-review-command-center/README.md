# Invoice Review Command Center Prototype Artifacts

This directory is the repo-backed source package for the invoice review prototype.

## Contents

- Design spec: [2026-05-20-invoice-review-command-center-design.md](/Users/vadimgeshiktor/repos/github.com/vgeshiktor/python-projects/invoices-platform/docs/superpowers/specs/2026-05-20-invoice-review-command-center-design.md:1)
- Implementation plan: [2026-05-20-invoice-review-command-center-prototype.md](/Users/vadimgeshiktor/repos/github.com/vgeshiktor/python-projects/invoices-platform/docs/superpowers/plans/2026-05-20-invoice-review-command-center-prototype.md:1)
- Fixtures: [invoice-fixtures.json](/Users/vadimgeshiktor/repos/github.com/vgeshiktor/python-projects/invoices-platform/docs/superpowers/artifacts/2026-05-20-invoice-review-command-center/invoice-fixtures.json:1)
- Tracker manifest: [github-tracker-manifest.json](/Users/vadimgeshiktor/repos/github.com/vgeshiktor/python-projects/invoices-platform/docs/superpowers/artifacts/2026-05-20-invoice-review-command-center/github-tracker-manifest.json:1)
- Figma review links: [figma-approval-links.json](/Users/vadimgeshiktor/repos/github.com/vgeshiktor/python-projects/invoices-platform/docs/superpowers/artifacts/2026-05-20-invoice-review-command-center/figma-approval-links.json:1)
- Mobile detail review resolution: [2026-05-24-mobile-detail-review-resolution.md](/Users/vadimgeshiktor/repos/github.com/vgeshiktor/python-projects/invoices-platform/docs/superpowers/artifacts/2026-05-20-invoice-review-command-center/2026-05-24-mobile-detail-review-resolution.md:1)
- Structural rebuild review resolution: [2026-05-25-command-center-structural-rebuild.md](/Users/vadimgeshiktor/repos/github.com/vgeshiktor/python-projects/invoices-platform/docs/superpowers/artifacts/2026-05-20-invoice-review-command-center/2026-05-25-command-center-structural-rebuild.md:1)
- Mobile-first review resolution: [2026-05-25-mobile-first-review-resolution.md](/Users/vadimgeshiktor/repos/github.com/vgeshiktor/python-projects/invoices-platform/docs/superpowers/artifacts/2026-05-20-invoice-review-command-center/2026-05-25-mobile-first-review-resolution.md:1)
- Desktop stats containment fix: [2026-05-25-desktop-stats-containment-fix.md](/Users/vadimgeshiktor/repos/github.com/vgeshiktor/python-projects/invoices-platform/docs/superpowers/artifacts/2026-05-20-invoice-review-command-center/2026-05-25-desktop-stats-containment-fix.md:1)
- Desktop queue-row containment fix: [2026-05-25-desktop-queue-row-containment-fix.md](/Users/vadimgeshiktor/repos/github.com/vgeshiktor/python-projects/invoices-platform/docs/superpowers/artifacts/2026-05-20-invoice-review-command-center/2026-05-25-desktop-queue-row-containment-fix.md:1)
- Decision card column containment fix: [2026-05-25-decision-card-column-containment-fix.md](/Users/vadimgeshiktor/repos/github.com/vgeshiktor/python-projects/invoices-platform/docs/superpowers/artifacts/2026-05-20-invoice-review-command-center/2026-05-25-decision-card-column-containment-fix.md:1)
- Decision actions button polish: [2026-05-26-decision-actions-button-polish.md](/Users/vadimgeshiktor/repos/github.com/vgeshiktor/python-projects/invoices-platform/docs/superpowers/artifacts/2026-05-20-invoice-review-command-center/2026-05-26-decision-actions-button-polish.md:1)
- Lower cards containment fix: [2026-05-26-lower-cards-containment-fix.md](/Users/vadimgeshiktor/repos/github.com/vgeshiktor/python-projects/invoices-platform/docs/superpowers/artifacts/2026-05-20-invoice-review-command-center/2026-05-26-lower-cards-containment-fix.md:1)
- Desktop quality pass: Facts and supporting signals: [2026-05-26-desktop-quality-pass-facts-and-signals.md](/Users/vadimgeshiktor/repos/github.com/vgeshiktor/python-projects/invoices-platform/docs/superpowers/artifacts/2026-05-20-invoice-review-command-center/2026-05-26-desktop-quality-pass-facts-and-signals.md:1)
- Desktop Today reproducibility guide: [desktop-today-reproducibility.md](/Users/vadimgeshiktor/repos/github.com/vgeshiktor/python-projects/invoices-platform/docs/superpowers/artifacts/2026-05-20-invoice-review-command-center/desktop-today-reproducibility.md:1)
- Desktop Today reproducibility snapshot: [desktop-today-reproducibility.json](/Users/vadimgeshiktor/repos/github.com/vgeshiktor/python-projects/invoices-platform/docs/superpowers/artifacts/2026-05-20-invoice-review-command-center/desktop-today-reproducibility.json:1)
- GitHub tracker results: [github-tracker-results.json](/Users/vadimgeshiktor/repos/github.com/vgeshiktor/python-projects/invoices-platform/docs/superpowers/artifacts/2026-05-20-invoice-review-command-center/github-tracker-results.json:1)

## Figma

- File URL: [Invoice Review Command Center Prototype](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf)
- File key: `ORTJPMYSjhBp8TZGZktrWf`

## Approval Frames

- Desktop Today: [node 6:45](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf?node-id=6-45)
- Desktop This Month: [node 6:303](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf?node-id=6-303)
- Mobile Today: [node 6:439](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf?node-id=6-439)
- Mobile Detail: [node 6:521](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf?node-id=6-521)
- Screenshot note: screenshot exports generated during execution are ephemeral; regenerate from the node links if needed.
- Review note: the mobile detail frame was rebuilt on 2026-05-24 to resolve collapsed-width layout bugs and strengthen review-state logic.
- Review note: all four approval frames were structurally rebuilt on 2026-05-25 so the geometry audit reports zero visible tiny-width containers.
- Review note: a second 2026-05-25 pass preserved desktop structure, rebuilt mobile for feed-and-scroll behavior, and added 360x780 QA validation frames.
- Review note: a focused 2026-05-25 desktop pass corrected only the stats-card description containment while preserving the rest of the dashboard.
- Review note: a second focused 2026-05-25 desktop pass corrected only the Today queue-row CTA/meta containment while preserving the queue-card styling.
- Review note: a third focused 2026-05-25 desktop pass corrected only the selected-invoice Decision required card column containment while preserving the component style.
- Review note: a focused 2026-05-26 desktop pass adjusted only the selected-invoice action row spacing and disabled-state polish while preserving the button design.
- Review note: a second focused 2026-05-26 desktop pass corrected only the selected-invoice lower-card containment for `Facts` and `Evidence and trust`.
- Review note: a third focused 2026-05-26 desktop pass removed the remaining `Facts`-card regression and tightened supporting desktop signals for a more production-ready finish.
- Reproducibility note: `Desktop - Today` now has a repo-backed structural snapshot and recreate guide, but a durable PNG export is still recommended for a fully locked visual reference.

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

- Tablet-specific layout tuning is deferred to [FE-1101](https://github.com/vgeshiktor/invoices-platform/issues/63). The current approval package covers desktop and mobile only.
- Duplicate-pair comparison messaging can be expanded in a dedicated comparison state under [FE-1004](https://github.com/vgeshiktor/invoices-platform/issues/62) if stakeholder review asks for a side-by-side original versus receipt experience.
