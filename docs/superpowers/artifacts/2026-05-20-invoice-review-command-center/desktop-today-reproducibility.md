# Desktop Today Reproducibility Guide

Date: 2026-05-26
Frame: [Desktop - Today](https://www.figma.com/design/ORTJPMYSjhBp8TZGZktrWf?node-id=6-45)

## Goal

Make the approved `Desktop - Today` frame fully traceable, reproducible, and recreatable even if the live Figma file changes later.

## What is already saved

- Canonical Figma reference in [figma-approval-links.json](/Users/vadimgeshiktor/repos/github.com/vgeshiktor/python-projects/invoices-platform/docs/superpowers/artifacts/2026-05-20-invoice-review-command-center/figma-approval-links.json:1)
- Full design spec in [2026-05-20-invoice-review-command-center-design.md](/Users/vadimgeshiktor/repos/github.com/vgeshiktor/python-projects/invoices-platform/docs/superpowers/specs/2026-05-20-invoice-review-command-center-design.md:1)
- Exact review-history trail in the dated review-resolution notes in this directory
- Structured frame snapshot in [desktop-today-reproducibility.json](/Users/vadimgeshiktor/repos/github.com/vgeshiktor/python-projects/invoices-platform/docs/superpowers/artifacts/2026-05-20-invoice-review-command-center/desktop-today-reproducibility.json:1)

## Recommended reproducibility standard

For a design like this, save four layers together:

1. `Live source`
   - Figma file key: `ORTJPMYSjhBp8TZGZktrWf`
   - Frame node: `6:45`

2. `Intent`
   - The design spec
   - The review-resolution notes that explain why the frame looks the way it does

3. `Snapshot`
   - A machine-readable manifest of key geometry, component structure, and critical copy
   - That snapshot is the JSON file saved alongside this guide

4. `Visual export`
   - A PNG export of the approved frame
   - This is the one thing not yet durable in the repo because tool-generated screenshot URLs are ephemeral

## How to recreate it later

If the frame is lost or needs to be rebuilt:

1. Start from the spec and review trail in this folder.
2. Open the live frame link above if it still exists.
3. Use [desktop-today-reproducibility.json](/Users/vadimgeshiktor/repos/github.com/vgeshiktor/python-projects/invoices-platform/docs/superpowers/artifacts/2026-05-20-invoice-review-command-center/desktop-today-reproducibility.json:1) as the exact structural reference:
   - frame size
   - section geometry
   - KPI card copy
   - detail panel dimensions
   - Facts card field/badge geometry
   - key action labels and decision copy
4. Reapply the dated review passes in order if needed:
   - structure
   - stats containment
   - queue containment
   - decision card containment
   - button polish
   - lower-card containment
   - final desktop quality pass

## If you want it fully locked

The strongest possible setup is:

- keep the current Figma node link
- keep the JSON snapshot in git
- export a local PNG into this folder
- optionally duplicate the approved frame into a locked Figma page called `Released Snapshots`

That gives you:

- a live editable source
- a repo-backed structural source of truth
- a static visual source of truth
- a rollback point inside Figma

## Recommendation

The repo is already 80% of the way there. The next best move is to add one durable PNG export and, if you want extra safety, a locked `Released Snapshots` page in Figma containing this exact frame version.
