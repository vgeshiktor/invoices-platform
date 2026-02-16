from __future__ import annotations

from invplatform.cli import meta_billing_export as mbe


def test_unit_iso_to_unix_uses_utc_midnight():
    assert mbe.iso_to_unix("2026-01-01") == 1767225600


def test_unit_parse_extra_data_handles_json_and_passthrough():
    payload = '{"transaction_id":"abc-123","new_value":700,"currency":"ILS"}'
    parsed = mbe.parse_extra_data(payload)
    assert isinstance(parsed, dict)
    assert parsed["transaction_id"] == "abc-123"

    broken = '{"transaction_id"'
    assert mbe.parse_extra_data(broken) == broken
    assert mbe.parse_extra_data({"ok": True}) == {"ok": True}


def test_unit_normalize_ad_account_and_token_in_url():
    assert mbe.normalize_ad_account("1010624901159130") == "act_1010624901159130"
    assert mbe.normalize_ad_account(" act_1010624901159130 ") == "act_1010624901159130"
    assert mbe.normalize_ad_account("acct_custom") == "acct_custom"

    raw = "https://files.example.com/invoice.pdf?foo=1"
    with_token = mbe.ensure_access_token_in_url(raw, "tok-1")
    assert "foo=1" in with_token
    assert "access_token=tok-1" in with_token

    # Existing token should remain unchanged.
    again = mbe.ensure_access_token_in_url(with_token, "tok-2")
    assert again == with_token


def test_unit_enrich_charges_extracts_transaction_amount_and_currency():
    charges = [
        {
            "event_type": "ad_account_billing_charge",
            "extra_data": '{"transaction_id":"tx-1","new_value":1600,"currency":"ILS"}',
        },
        {
            "event_type": "ad_account_billing_charge",
            "extra_data": {
                "transaction_id": "tx-2",
                "new_value": 700,
                "currency": "USD",
            },
        },
    ]

    enriched = mbe.enrich_charges(charges)
    assert len(enriched) == 2
    assert enriched[0]["transaction_id"] == "tx-1"
    assert enriched[0]["amount_minor"] == 1600
    assert enriched[0]["amount"] == 16.0
    assert enriched[0]["currency"] == "ILS"
    assert enriched[1]["transaction_id"] == "tx-2"
    assert enriched[1]["amount"] == 7.0
