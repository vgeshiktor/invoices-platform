# Meta Billing Graph API Explorer URLs

This page collects ready-to-paste `GET` URLs for Meta Graph API Explorer when debugging billing data.

Explorer:
- `https://developers.facebook.com/tools/explorer/`

## Inputs Used in This Project Example

- `api_version`: `v24.0`
- `business_id`: `1351676656106280`
- `ad_account`: `act_1010624901159130`
- `start`: `2026-01-01` (unix: `1767225600`)
- `end`: `2026-02-01` (unix: `1769904000`)

## Ready-to-Paste URLs

Business node sanity:
- `https://graph.facebook.com/v24.0/1351676656106280?fields=id,name`

Business invoices (monthly invoices, may include `download_uri`):
- `https://graph.facebook.com/v24.0/1351676656106280/business_invoices?issue_start_date=2026-01-01&issue_end_date=2026-02-01&limit=200&fields=id,invoice_id,invoice_date,billing_period_start,billing_period_end,amount_due,currency,advertiser_name,type,download_uri`

Ad account sanity:
- `https://graph.facebook.com/v24.0/act_1010624901159130?fields=id,account_id,name,account_status,currency`

Ad account activities (billing-relevant events in time window):
- `https://graph.facebook.com/v24.0/act_1010624901159130/activities?since=1767225600&until=1769904000&limit=500&fields=actor_name,application_name,date_time_in_timezone,event_time,event_type,extra_data,object_name,object_type,translated_event_type`

Businesses visible to token:
- `https://graph.facebook.com/v24.0/me/businesses?fields=id,name&limit=200`

Ad accounts visible to token:
- `https://graph.facebook.com/v24.0/me/adaccounts?fields=id,account_id,name,account_status&limit=200`

## Reusable URL Templates

Use these placeholders:
- `<API_VERSION>` e.g. `v24.0`
- `<BUSINESS_ID>` numeric Business Manager ID
- `<AD_ACCOUNT_ID>` ad account ID with `act_` prefix
- `<START_DATE>` and `<END_DATE>` in `YYYY-MM-DD`
- `<SINCE_UNIX>` and `<UNTIL_UNIX>` UTC unix timestamps

Business node sanity:
- `https://graph.facebook.com/<API_VERSION>/<BUSINESS_ID>?fields=id,name`

Business invoices:
- `https://graph.facebook.com/<API_VERSION>/<BUSINESS_ID>/business_invoices?issue_start_date=<START_DATE>&issue_end_date=<END_DATE>&limit=200&fields=id,invoice_id,invoice_date,billing_period_start,billing_period_end,amount_due,currency,advertiser_name,type,download_uri`

Ad account sanity:
- `https://graph.facebook.com/<API_VERSION>/<AD_ACCOUNT_ID>?fields=id,account_id,name,account_status,currency`

Ad account activities:
- `https://graph.facebook.com/<API_VERSION>/<AD_ACCOUNT_ID>/activities?since=<SINCE_UNIX>&until=<UNTIL_UNIX>&limit=500&fields=actor_name,application_name,date_time_in_timezone,event_time,event_type,extra_data,object_name,object_type,translated_event_type`

Businesses visible to token:
- `https://graph.facebook.com/<API_VERSION>/me/businesses?fields=id,name&limit=200`

Ad accounts visible to token:
- `https://graph.facebook.com/<API_VERSION>/me/adaccounts?fields=id,account_id,name,account_status&limit=200`

Convert dates to unix timestamps (UTC):

```bash
python - <<'PY'
import datetime as dt
for d in ["2026-01-01", "2026-02-01"]:
    x = dt.date.fromisoformat(d)
    ts = int(dt.datetime(x.year, x.month, x.day, tzinfo=dt.timezone.utc).timestamp())
    print(d, ts)
PY
```

## Notes

- Use a token in Graph API Explorer that has access to the target Business and Ad Account.
- For threshold billing flows, `activities` typically includes `transaction_id` per charge but not a direct PDF URL.
- `business_invoices` can legitimately return `[]` for accounts without monthly invoice issuance in that period.
