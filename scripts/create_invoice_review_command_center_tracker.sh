#!/usr/bin/env bash

set -euo pipefail

REPO="vgeshiktor/invoices-platform"
MILESTONE_TITLE="Invoice Review Command Center Prototype"

ensure_milestone() {
  local existing_number
  existing_number="$(gh api "repos/${REPO}/milestones?state=all" --jq ".[] | select(.title == \"${MILESTONE_TITLE}\") | .number" | head -n1 || true)"
  if [[ -n "${existing_number}" ]]; then
    echo "${existing_number}"
    return
  fi

  gh api "repos/${REPO}/milestones" \
    --method POST \
    --field title="${MILESTONE_TITLE}" \
    --field state="open" \
    --field description="High-fidelity UX/UI prototype for an operator-grade invoice review workspace spanning Today, Yesterday, This Week, and This Month with desktop split view, mobile detail flow, and exception-first triage." \
    --jq ".number"
}

ensure_label() {
  local name="$1"
  local color="$2"
  local description="$3"

  if gh label list --repo "${REPO}" --limit 200 --json name --jq ".[] | select(.name == \"${name}\") | .name" | grep -qx "${name}"; then
    return
  fi

  gh label create "${name}" \
    --repo "${REPO}" \
    --color "${color}" \
    --description "${description}" >/dev/null
}

ensure_issue() {
  local title="$1"
  local labels="$2"
  local body="$3"
  local milestone_number="$4"

  local issue_number
  issue_number="$(
    gh issue list \
      --repo "${REPO}" \
      --state all \
      --search "\"${title}\" in:title" \
      --limit 100 \
      --json number,title \
      --jq ".[] | select(.title == \"${title}\") | .number" | head -n1 || true
  )"

  if [[ -n "${issue_number}" ]]; then
    echo "${issue_number}"
    return
  fi

  local created_url
  created_url="$(
    gh issue create \
      --repo "${REPO}" \
      --title "${title}" \
      --body "${body}" \
      --label "${labels}" \
      --milestone "${MILESTONE_TITLE}"
  )"

  printf '%s\n' "${created_url##*/}"
}

main() {
  local milestone_number
  milestone_number="$(ensure_milestone)"
  echo "Milestone number: ${milestone_number}"

  ensure_label "epic:E9" "BFD4F2" "Imported by scripts/create_invoice_review_command_center_tracker.sh"
  ensure_label "epic:E10" "BFD4F2" "Imported by scripts/create_invoice_review_command_center_tracker.sh"
  ensure_label "epic:E11" "BFD4F2" "Imported by scripts/create_invoice_review_command_center_tracker.sh"
  ensure_label "epic:E12" "BFD4F2" "Imported by scripts/create_invoice_review_command_center_tracker.sh"

  ensure_issue \
    "Umbrella: Invoice Review Experience" \
    "frontend,priority:P0,type:feature" \
    $'## Objective\nCreate a coherent invoice review experience for finance operators with an exception-first list and a metadata-first drill-down across desktop and mobile.\n\n## Success criteria\n- High-fidelity desktop and mobile approval frames exist\n- All four presets are represented in one responsive workspace\n- Exception-first triage is explicit in list and detail\n- Responsive review is complete\n- Any unresolved UX debt is converted into explicit follow-up issues\n\n## Child epics\n- E9: Invoice Review Information Architecture + Visual System\n- E10: Exception-First Invoice List Experience\n- E11: Invoice Drill-Down and Review Actions\n- E12: Responsive Quality, Review, and Approval Pack' \
    "${milestone_number}" >/dev/null

  ensure_issue \
    "E9: Invoice Review Information Architecture + Visual System" \
    "frontend,priority:P0,type:feature" \
    "Lock the operator workflow, shared shell, visual system, and approval-quality frame set for the invoice review prototype." \
    "${milestone_number}" >/dev/null
  ensure_issue \
    "E10: Exception-First Invoice List Experience" \
    "frontend,priority:P0,type:feature" \
    "Design the list, range presets, summary band, filters, and system states so operators can scan and prioritize exceptions quickly." \
    "${milestone_number}" >/dev/null
  ensure_issue \
    "E11: Invoice Drill-Down and Review Actions" \
    "frontend,priority:P0,type:feature" \
    "Define the selected-invoice experience on desktop and mobile with metadata-first hierarchy, risk interpretation, and review actions." \
    "${milestone_number}" >/dev/null
  ensure_issue \
    "E12: Responsive Quality, Review, and Approval Pack" \
    "frontend,priority:P0,type:feature" \
    "Harden the prototype through responsive review, accessibility/readability checks, screenshot export, and explicit deferral of non-critical UX debt." \
    "${milestone_number}" >/dev/null

  ensure_issue \
    "[FE-801] Define operator task model and invoice review information architecture" \
    "epic:E9,frontend,priority:P1,type:feature" \
    $'Define the operator workflow for reviewing invoices across Today, Yesterday, This Week, and This Month.\n\nAcceptance criteria:\n- Shared workspace model is explicit\n- Exception-first order is documented\n- Desktop and mobile information architecture are aligned\n- List/detail responsibilities are clearly separated' \
    "${milestone_number}" >/dev/null
  ensure_issue \
    "[FE-802] Create desktop high-fidelity command-center frames for Today and This Month" \
    "epic:E9,frontend,priority:P1,type:feature" \
    $'Create approval-quality desktop frames for the Today and This Month presets.\n\nAcceptance criteria:\n- Shared shell is consistent across both frames\n- Today emphasizes triage\n- This Month shows broader analytical context\n- Selected row and detail panel are visually stable' \
    "${milestone_number}" >/dev/null
  ensure_issue \
    "[FE-803] Create mobile high-fidelity frames for Today list and invoice detail" \
    "epic:E9,frontend,priority:P1,type:feature" \
    $'Create approval-quality mobile frames for the Today list and the full-screen invoice detail state.\n\nAcceptance criteria:\n- Preset chips remain usable on mobile\n- Cards replace the desktop table\n- Metadata-first detail hierarchy is preserved\n- Sticky back and action behavior is visible' \
    "${milestone_number}" >/dev/null
  ensure_issue \
    "[FE-804] Build realistic invoice fixture set covering confidence, duplicate, overdue, municipal, and uncategorized states" \
    "epic:E9,frontend,priority:P2,type:feature" \
    $'Create a deterministic prototype fixture set derived from the repo invoice domain.\n\nAcceptance criteria:\n- Includes normal, low-confidence, duplicate, overdue, quarantined, uncategorized, municipal, and mixed-source states\n- Supports all four presets\n- Supports both list and detail views' \
    "${milestone_number}" >/dev/null
  ensure_issue \
    "[FE-901] Design invoice row/card system for dense desktop and mobile scanning" \
    "epic:E10,frontend,priority:P1,type:feature" \
    "Design the row and card system so operators can scan vendor, amount, dates, source, and exception states quickly." \
    "${milestone_number}" >/dev/null
  ensure_issue \
    "[FE-902] Design range presets, summary band, and default sort behavior" \
    "epic:E10,frontend,priority:P1,type:feature" \
    "Design the four time presets, compact summary band, and exception-first default ordering behavior." \
    "${milestone_number}" >/dev/null
  ensure_issue \
    "[FE-903] Design filter drawer, saved filter shortcuts, and active filter chips" \
    "epic:E10,frontend,priority:P1,type:feature" \
    "Design a shallow, operator-fast filtering model with saved shortcuts and active filter visibility." \
    "${milestone_number}" >/dev/null
  ensure_issue \
    "[FE-904] Design empty, no-results, loading, and failure states for the list workspace" \
    "epic:E10,frontend,priority:P1,type:feature" \
    "Design the workspace states that keep the experience useful when data is missing, filtered out, loading, or failed." \
    "${milestone_number}" >/dev/null
  ensure_issue \
    "[FE-1001] Design desktop split-view drill-down hierarchy and metadata grouping" \
    "epic:E11,frontend,priority:P1,type:feature" \
    "Design the desktop detail panel hierarchy so structured facts, trust signals, and grouped metadata dominate over the document preview." \
    "${milestone_number}" >/dev/null
  ensure_issue \
    "[FE-1002] Design invoice action model: review, duplicate flag, note, category change, source open" \
    "epic:E11,frontend,priority:P1,type:feature" \
    "Design the action model for operator workflows directly from the detail pane." \
    "${milestone_number}" >/dev/null
  ensure_issue \
    "[FE-1003] Design mobile full-screen invoice detail flow with sticky facts/actions" \
    "epic:E11,frontend,priority:P1,type:feature" \
    "Design the mobile drill-down so the metadata-first review model survives the smaller viewport." \
    "${milestone_number}" >/dev/null
  ensure_issue \
    "[FE-1004] Validate drill-down behavior for low-confidence, duplicate, overdue, and quarantined invoices" \
    "epic:E11,frontend,priority:P1,type:feature" \
    "Validate that high-risk invoice states change the detail view hierarchy and messaging in useful ways." \
    "${milestone_number}" >/dev/null
  ensure_issue \
    "[FE-1101] Run responsive review across desktop, tablet, and mobile breakpoints" \
    "epic:E12,frontend,priority:P1,type:quality" \
    "Review the prototype at desktop, tablet, and mobile sizes and fix layout issues that compromise readability or workflow." \
    "${milestone_number}" >/dev/null
  ensure_issue \
    "[FE-1102] Run accessibility and readability pass for dense financial UI" \
    "epic:E12,frontend,priority:P1,type:quality" \
    "Review contrast, type sizing, chip readability, spacing, and dense-data clarity across the prototype." \
    "${milestone_number}" >/dev/null
  ensure_issue \
    "[FE-1103] Export stakeholder approval screenshot pack from the prototype" \
    "epic:E12,frontend,priority:P1,type:feature" \
    "Export the four primary approval frames into a clean stakeholder screenshot pack." \
    "${milestone_number}" >/dev/null
  ensure_issue \
    "[FE-1104] Fix critical UX defects or create laser-focused follow-up issues for approved deferrals" \
    "epic:E12,frontend,priority:P1,type:chore" \
    "Resolve critical UX defects before sign-off and explicitly create follow-up issues for non-critical approved deferrals." \
    "${milestone_number}" >/dev/null

  echo "Tracker creation complete."
}

main "$@"
