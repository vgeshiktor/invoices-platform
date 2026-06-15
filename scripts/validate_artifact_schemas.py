#!/usr/bin/env python

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = (
    ROOT
    / "docs"
    / "superpowers"
    / "artifacts"
    / "2026-05-20-invoice-review-command-center"
)
ARTIFACT_README = ARTIFACT_DIR / "README.md"
FIXTURES_JSON = ARTIFACT_DIR / "invoice-fixtures.json"
TRACKER_MANIFEST_JSON = ARTIFACT_DIR / "github-tracker-manifest.json"
TRACKER_RESULTS_JSON = ARTIFACT_DIR / "github-tracker-results.json"
REQUIRED_PRESET_VIEWS = {"today", "yesterday", "thisWeek", "thisMonth"}
REQUIRED_MILESTONE_ISSUES = {"FE-1101", "FE-1102", "FE-1103", "FE-1104"}
RELATIVE_LINK_RE = re.compile(r"\[[^\]]+\]\((?!https?://|mailto:|#)([^)]+)\)")
ISSUE_CODE_RE = re.compile(r"^\[(FE-\d+)\]")


def _load_json(path: Path) -> object:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def validate_fixture_schema() -> None:
    payload = _load_json(FIXTURES_JSON)
    _assert(isinstance(payload, dict), f"{FIXTURES_JSON} must contain an object")

    required_keys = {
        "detailById",
        "listItems",
        "notes",
        "presetViews",
        "referenceDate",
        "referenceTimezone",
        "sourceRecord",
    }
    missing_keys = required_keys - payload.keys()
    _assert(
        not missing_keys, f"{FIXTURES_JSON} is missing keys: {sorted(missing_keys)}"
    )

    list_items = payload["listItems"]
    detail_by_id = payload["detailById"]
    preset_views = payload["presetViews"]
    _assert(
        isinstance(list_items, list) and list_items,
        "invoice fixtures must include listItems",
    )
    _assert(
        isinstance(detail_by_id, dict) and detail_by_id,
        "invoice fixtures must include detailById records",
    )
    _assert(
        isinstance(preset_views, dict) and REQUIRED_PRESET_VIEWS <= preset_views.keys(),
        "invoice fixtures must include today, yesterday, thisWeek, and thisMonth preset views",
    )

    list_item_ids = []
    for item in list_items:
        _assert(isinstance(item, dict), "each fixture list item must be an object")
        invoice_id = item.get("id")
        _assert(
            isinstance(invoice_id, str) and invoice_id,
            "each fixture list item needs an id",
        )
        list_item_ids.append(invoice_id)

    _assert(
        len(list_item_ids) == len(set(list_item_ids)),
        "fixture list item ids must be unique",
    )

    detail_ids = set(detail_by_id.keys())
    _assert(
        set(list_item_ids) == detail_ids, "listItems ids must match detailById keys"
    )

    for detail_id, detail in detail_by_id.items():
        _assert(
            isinstance(detail, dict), f"fixture detail {detail_id} must be an object"
        )
        _assert(
            detail.get("id") == detail_id,
            f"fixture detail {detail_id} must echo its key as id",
        )

    for preset_name, preset in preset_views.items():
        _assert(
            isinstance(preset, dict), f"preset view {preset_name} must be an object"
        )
        invoice_ids = preset.get("invoiceIds")
        selected_id = preset.get("selectedInvoiceId")
        _assert(
            isinstance(invoice_ids, list) and invoice_ids,
            f"preset view {preset_name} must include invoiceIds",
        )
        _assert(
            isinstance(selected_id, str) and selected_id in detail_ids,
            f"preset view {preset_name} must include a valid selectedInvoiceId",
        )
        unknown_ids = sorted(set(invoice_ids) - detail_ids)
        _assert(
            not unknown_ids,
            f"preset view {preset_name} references unknown invoice ids: {unknown_ids}",
        )
        _assert(
            selected_id in invoice_ids,
            f"preset view {preset_name} selectedInvoiceId must be listed in invoiceIds",
        )


def validate_tracker_schema() -> None:
    manifest = _load_json(TRACKER_MANIFEST_JSON)
    results = _load_json(TRACKER_RESULTS_JSON)
    _assert(
        isinstance(manifest, dict), f"{TRACKER_MANIFEST_JSON} must contain an object"
    )
    _assert(isinstance(results, dict), f"{TRACKER_RESULTS_JSON} must contain an object")

    _assert(
        manifest.get("repository") == results.get("repository"),
        "tracker manifest and results must target the same repository",
    )
    _assert(
        manifest.get("milestone", {}).get("title")
        == results.get("milestone", {}).get("title"),
        "tracker manifest and results must agree on milestone title",
    )

    manifest_epic_codes = {epic["code"] for epic in manifest.get("epics", [])}
    result_epic_codes = set(results.get("epics", {}).keys())
    _assert(
        manifest_epic_codes == result_epic_codes,
        "tracker manifest and results must expose the same epic codes",
    )

    manifest_issue_codes = set()
    for issue in manifest.get("issues", []):
        title = issue.get("title", "")
        match = ISSUE_CODE_RE.match(title)
        _assert(
            match is not None,
            f"tracker manifest issue title is missing FE code: {title!r}",
        )
        manifest_issue_codes.add(match.group(1))
        epic_code = issue.get("epic")
        _assert(
            epic_code in manifest_epic_codes,
            f"issue {title!r} references unknown epic {epic_code!r}",
        )

    result_issue_codes = set(results.get("issues", {}).keys())
    _assert(
        manifest_issue_codes == result_issue_codes,
        "tracker manifest and results must expose the same FE issue codes",
    )
    _assert(
        REQUIRED_MILESTONE_ISSUES <= result_issue_codes,
        "tracker results must include FE-1101 through FE-1104",
    )


def validate_artifact_readme_links() -> None:
    readme = ARTIFACT_README.read_text(encoding="utf-8")
    missing_paths: list[str] = []
    for raw_target in RELATIVE_LINK_RE.findall(readme):
        target = raw_target.split("#", 1)[0]
        cleaned = target[2:] if target.startswith("./") else target
        resolved = (ARTIFACT_DIR / cleaned).resolve()
        if not resolved.exists():
            missing_paths.append(raw_target)
    _assert(
        not missing_paths,
        f"artifact README contains broken relative links: {missing_paths}",
    )


def main() -> None:
    validate_fixture_schema()
    validate_tracker_schema()
    validate_artifact_readme_links()


if __name__ == "__main__":
    main()
