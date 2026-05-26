# Invoice Review Command Center Design Spec

Date: 2026-05-20
Status: Approved for prototype implementation
Audience: Finance operators reviewing invoices across Gmail and Outlook sourced workflows

## Summary

This design defines a high-fidelity invoice review prototype for an operator-grade command center. The experience is built around one responsive workspace with four time presets:

- Today
- Yesterday
- This Week
- This Month

The workspace is exception-first. It helps an operator quickly identify which invoices need attention, understand why, and drill into the selected invoice without losing list context on desktop.

The source invoice domain comes from the existing `InvoiceRecord` shape in [apps/workers-py/src/invplatform/cli/invoices_report.py](/Users/vadimgeshiktor/repos/github.com/vgeshiktor/python-projects/invoices-platform/apps/workers-py/src/invplatform/cli/invoices_report.py:103).

## Goals

- Create a premium, practical, responsive UX/UI prototype for invoice review.
- Keep the list as the primary surface and the detail view as the secondary surface.
- Surface exceptions before routine items.
- Reflect existing invoice metadata, trust signals, and parsing outcomes already present in the repo.
- Produce an approval package suitable for stakeholder review before browser-based validation or frontend implementation.

## Product Shape

The prototype is one shared workspace, not four different products. The selected time preset changes emphasis and dataset shape, but not the interaction model.

### Default behavior

- Audience: finance operator
- Sort order: exception severity, due-date urgency, then recency
- Drill-down pattern: split view on desktop, full-screen detail on mobile
- Detail emphasis: structured metadata and actions first, document preview second

### Time preset intent

- `Today`: active triage mode with strongest exception emphasis
- `Yesterday`: catch-up mode for unresolved items
- `This Week`: broader scan for patterns and clusters
- `This Month`: analytical review with mixed-source context and total awareness

## Information Architecture

### Desktop layout

- Top header
- Summary band
- Main list pane at approximately 60% width
- Detail pane at approximately 40% width

### Mobile layout

- Sticky preset chips
- Compact summary band
- Invoice cards instead of table rows
- Full-screen detail view with sticky header and actions

## Screen Anatomy

### Header

- Product title: `Invoices Command Center`
- Context subtitle: count for the active preset
- Four top-level range presets
- Global search
- `Filters` entry point
- Active filter pills and sort state beneath the primary header row

### Summary band

Four compact summary cards:

- `Needs review`
- `Duplicates / suspicious`
- `Due soon / overdue`
- `Total amount`

The summary band is intentionally compact and informational. It should not visually compete with the list.

### List content

Each desktop row and mobile card must show:

- vendor
- description
- amount and currency
- invoice date
- due date
- source/provider
- confidence or trust signal
- exception chips when relevant

### Required exception chips

- `Low confidence`
- `Duplicate`
- `Overdue`
- `Quarantined`
- `Uncategorized`
- `Municipal`

### Detail content

The detail view must prioritize:

- vendor
- amount
- invoice id
- confidence or trust state
- primary exception/status chips
- invoice date
- due date
- category
- provider/source
- period
- subtotal, VAT, total
- reference numbers
- parse/risk interpretation
- operator actions
- document preview

### Operator actions

The prototype should visibly support:

- Mark reviewed
- Flag duplicate
- Add note
- Reclassify category
- Open source document
- Open source message/thread
- Export/share

## Visual System

### Tone

- Bright, high-trust, enterprise-grade
- Calm control under operational pressure
- Dense but never cluttered

### Color direction

- Warm off-white shell background
- Crisp white work surfaces
- Charcoal text
- Deep blue for selection and trusted actions
- Amber for warning
- Brick red for risk
- Muted green for resolved/safe states

Color must communicate meaning, not decoration.

### Typography

- Strong numeric emphasis for totals and urgency
- Slightly elevated vendor name hierarchy
- Compact metadata typography
- Premium, dense editorial tone rather than generic dashboard text treatment

### Row/panel styling

- Subtle separators instead of heavy gridlines
- Stable selected-row treatment
- Compact semantic chips
- Amounts aligned for scan speed
- Detail pane grouped into concise, readable fact clusters

## Responsive Approval Frames

The approval package must contain exactly four primary high-fidelity frames:

1. Desktop `Today` with selected high-risk invoice
2. Desktop `This Month` with broader analytical context
3. Mobile `Today` list
4. Mobile invoice detail

Optional follow-up frames may be added later, but the initial approval pass is anchored on the four frames above.

## Data Contract

No backend API change is required for the prototype.

### InvoiceListItem

```ts
type InvoiceListItem = {
  id: string
  vendor: string
  description: string | null
  amount: number | null
  currency: string | null
  invoiceDate: string | null
  dueDate: string | null
  source: "gmail" | "outlook" | "other"
  confidence: number | null
  category: string | null
  isDuplicate: boolean
  isQuarantined: boolean
  isMunicipal: boolean
  isOverdue: boolean
  needsReview: boolean
}
```

### InvoiceDetailViewModel

```ts
type InvoiceDetailViewModel = InvoiceListItem & {
  invoiceId: string | null
  subtotalBeforeVat: number | null
  vatAmount: number | null
  totalAmount: number | null
  periodStart: string | null
  periodEnd: string | null
  periodLabel: string | null
  referenceNumbers: string[]
  notes: string | null
  categoryConfidence: number | null
  categoryRule: string | null
  duplicateHash: string | null
  parseConfidence: number | null
  documentPreviewUrl: string | null
  sourceMessageUrl: string | null
}
```

## Prototype Fixture Set

The fixture set must include:

- normal invoice
- low-confidence invoice
- duplicate invoice
- overdue invoice
- quarantined invoice
- uncategorized invoice
- municipal invoice
- mixed-source month view

## Design QA Checklist

- All four presets exist inside one workspace model
- Exception-first behavior is visible in list ordering and chip design
- Desktop uses split view
- Mobile uses list-to-detail
- Structured facts and actions dominate the detail view
- Document preview is present but secondary
- Dense information remains readable at desktop and mobile sizes
- Any unresolved UX issue is fixed or captured as an explicit follow-up issue

## Delivery Structure

### Milestone

`Invoice Review Command Center Prototype`

### Umbrella epic

`Umbrella: Invoice Review Experience`

### Epics

- `E9: Invoice Review Information Architecture + Visual System`
- `E10: Exception-First Invoice List Experience`
- `E11: Invoice Drill-Down and Review Actions`
- `E12: Responsive Quality, Review, and Approval Pack`

### Issues

- `FE-801` Define operator task model and invoice review information architecture
- `FE-802` Create desktop high-fidelity command-center frames for `Today` and `This Month`
- `FE-803` Create mobile high-fidelity frames for `Today` list and invoice detail
- `FE-804` Build realistic invoice fixture set covering confidence, duplicate, overdue, municipal, and uncategorized states
- `FE-901` Design invoice row/card system for dense desktop and mobile scanning
- `FE-902` Design range presets, summary band, and default sort behavior
- `FE-903` Design filter drawer, saved filter shortcuts, and active filter chips
- `FE-904` Design empty, no-results, loading, and failure states for the list workspace
- `FE-1001` Design desktop split-view drill-down hierarchy and metadata grouping
- `FE-1002` Design invoice action model: review, duplicate flag, note, category change, source open
- `FE-1003` Design mobile full-screen invoice detail flow with sticky facts/actions
- `FE-1004` Validate drill-down behavior for low-confidence, duplicate, overdue, and quarantined invoices
- `FE-1101` Run responsive review across desktop, tablet, and mobile breakpoints
- `FE-1102` Run accessibility and readability pass for dense financial UI
- `FE-1103` Export stakeholder approval screenshot pack from the prototype
- `FE-1104` Fix critical UX defects or create laser-focused follow-up issues for approved deferrals
