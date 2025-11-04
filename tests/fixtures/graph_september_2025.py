from __future__ import annotations

from typing import Dict, List, Tuple


def _pdf_bytes(label: str) -> bytes:
    """Return minimal, distinct PDF-like bytes for the given label."""
    return (
        "%PDF-1.3\n"
        f"% {label}\n"
        "1 0 obj\n<<>>\nendobj\nxref\n0 1\n0000000000 65535 f \n"
        "trailer\n<<>>\nstartxref\n0\n%%EOF\n"
    ).encode("utf-8")


def build_september_2025_fixture() -> Dict[str, object]:
    """Recorded Outlook data for September 2025 invoice discovery."""
    messages: List[Dict[str, object]] = [
        {
            "id": "AQMkADAwATZiZmYAZC1mMWZmAC1mYmNhLTAwAi0wMAoARgAAA5bGPITkbq9Lhg_vlOo6E28HAAFMZdu9vw5InPGMJpaKhAsAAAIBDAAAAAFMZdu9vw5InPGMJpaKhAsACSfSVRoAAAA=",
            "subject": 'קבלה על תרומה מספר 28847 מעזר בנימין ע"ר  - עבור אינה שרץ הבית החם',
            "preview": "קבלה על תרומה מספר 28847",
            "from_address": "outgoing@out.cardcom.co.il",
            "received": "2025-09-30T08:58:02Z",
            "web_link": "https://outlook.live.com/owa/?ItemID=AQMkADAwATZiZmYAZC1mMWZmAC1mYmNhLTAwAi0wMAoARgAAA5bGPITkbq9Lhg%2BvlOo6E28HAAFMZdu9vw5InPGMJpaKhAsAAAIBDAAAAAFMZdu9vw5InPGMJpaKhAsACSfSVRoAAAA%3D&exvsurl=1&viewmodel=ReadMessageItem",
            "parent": "inbox",
            "hasAttachments": True,
            "attachments": [
                {
                    "id": "att-1",
                    "name": "קבלה_על_תרומה_28847.pdf",
                    "contentType": "application/pdf",
                    "content": _pdf_bytes("donation-28847"),
                },
            ],
            "body_html": "<html></html>",
        },
        {
            "id": "AQMkADAwATZiZmYAZC1mMWZmAC1mYmNhLTAwAi0wMAoARgAAA5bGPITkbq9Lhg_vlOo6E28HAAFMZdu9vw5InPGMJpaKhAsAAAIBDAAAAAFMZdu9vw5InPGMJpaKhAsACSfSVQMAAAA=",
            "subject": "חשבונית מס קבלה מספר 27107 מג'סט סימפל בע\"מ - JUST SIMPLE LTD - עבור הבית החם - אינה שרץ    - אין להשיב למייל זה",
            "preview": "חשבונית מס קבלה מספר 27107",
            "from_address": "outgoing@out.cardcom.co.il",
            "received": "2025-09-28T09:31:06Z",
            "web_link": "https://outlook.live.com/owa/?ItemID=AQMkADAwATZiZmYAZC1mMWZmAC1mYmNhLTAwAi0wMAoARgAAA5bGPITkbq9Lhg%2BvlOo6E28HAAFMZdu9vw5InPGMJpaKhAsAAAIBDAAAAAFMZdu9vw5InPGMJpaKhAsACSfSVQMAAAA%3D&exvsurl=1&viewmodel=ReadMessageItem",
            "parent": "inbox",
            "hasAttachments": True,
            "attachments": [
                {
                    "id": "att-1",
                    "name": "חשבונית_מס_קבלה_27107.pdf",
                    "contentType": "application/pdf",
                    "content": _pdf_bytes("invoice-27107"),
                },
            ],
            "body_html": "<html></html>",
        },
        {
            "id": "AQMkADAwATZiZmYAZC1mMWZmAC1mYmNhLTAwAi0wMAoARgAAA5bGPITkbq9Lhg_vlOo6E28HAAFMZdu9vw5InPGMJpaKhAsAAAIBDAAAAAFMZdu9vw5InPGMJpaKhAsACSfSVQAAAQ==",
            "subject": 'אישור רכישה - מקפת - מרכזים קהילתיים פתח תקווה (מס״ד: 55277 הזמנה: סדנת NLP לצוותי חינוך לגיל הרך בפס"גה - האגף לחינוך הגיל הרך)',
            "preview": "אישור רכישה - קבלה מצורפת",
            "from_address": "makefet@email.smarticket.co.il",
            "received": "2025-09-27T19:14:45Z",
            "web_link": "https://outlook.live.com/owa/?ItemID=AQMkADAwATZiZmYAZC1mMWZmAC1mYmNhLTAwAi0wMAoARgAAA5bGPITkbq9Lhg%2BvlOo6E28HAAFMZdu9vw5InPGMJpaKhAsAAAIBDAAAAAFMZdu9vw5InPGMJpaKhAsACSfSVQAAAQ%3D%3D&exvsurl=1&viewmodel=ReadMessageItem",
            "parent": "inbox",
            "hasAttachments": False,
            "attachments": [],
            "body_html": '<html><body><a href="https://fixtures.example/receipt_23265.pdf">קבלה</a></body></html>',
            "direct_links": [
                {
                    "url": "https://fixtures.example/receipt_23265.pdf",
                    "name": "receipt_23265.pdf",
                    "content": _pdf_bytes("receipt-23265"),
                }
            ],
        },
        {
            "id": "AQMkADAwATZiZmYAZC1mMWZmAC1mYmNhLTAwAi0wMAoARgAAA5bGPITkbq9Lhg_vlOo6E28HAAFMZdu9vw5InPGMJpaKhAsAAAIBDAAAAAFMZdu9vw5InPGMJpaKhAsACSfSVMUAAAA=",
            "subject": "חשבונית רמי לוי תקשורת התקבלה",
            "preview": "חשבונית רמי לוי תקשורת",
            "from_address": "invoice@rami-levy.co.il",
            "received": "2025-09-16T13:07:51Z",
            "web_link": "https://outlook.live.com/owa/?ItemID=AQMkADAwATZiZmYAZC1mMWZmAC1mYmNhLTAwAi0wMAoARgAAA5bGPITkbq9Lhg%2BvlOo6E28HAAFMZdu9vw5InPGMJpaKhAsAAAIBDAAAAAFMZdu9vw5InPGMJpaKhAsACSfSVMUAAAA%3D&exvsurl=1&viewmodel=ReadMessageItem",
            "parent": "inbox",
            "hasAttachments": True,
            "attachments": [
                {
                    "id": "att-1",
                    "name": "5689_0507953_6542095_RAMIPDF.pdf",
                    "contentType": "application/pdf",
                    "content": _pdf_bytes("rami-levy"),
                },
            ],
            "body_html": "<html></html>",
        },
        {
            "id": "AQMkADAwATZiZmYAZC1mMWZmAC1mYmNhLTAwAi0wMAoARgAAA5bGPITkbq9Lhg_vlOo6E28HAAFMZdu9vw5InPGMJpaKhAsAAAIBDAAAAAFMZdu9vw5InPGMJpaKhAsACScPFaoAAAA=",
            "subject": "החשבונית החודשית שלך בבזק כאן",
            "preview": "החשבונית החודשית שלך בבזק כאן",
            "from_address": "bezeq_mail@bezeq.co.il",
            "received": "2025-09-15T14:26:14Z",
            "web_link": "https://outlook.live.com/owa/?ItemID=AQMkADAwATZiZmYAZC1mMWZmAC1mYmNhLTAwAi0wMAoARgAAA5bGPITkbq9Lhg%2BvlOo6E28HAAFMZdu9vw5InPGMJpaKhAsAAAIBDAAAAAFMZdu9vw5InPGMJpaKhAsACScPFaoAAAA%3D&exvsurl=1&viewmodel=ReadMessageItem",
            "parent": "inbox",
            "hasAttachments": False,
            "attachments": [],
            "body_html": '<html><body><a href="https://myinvoice.bezeq.co.il/invoice?id=d161e610-4e10-49c7-b82b-7b89591f279b">בזק</a></body></html>',
            "bezeq_link": {
                "url": "https://myinvoice.bezeq.co.il/invoice?id=d161e610-4e10-49c7-b82b-7b89591f279b",
                "name": "bill__d161e610-4e10-49c7-b82b-7b89591f279b.pdf",
                "content": _pdf_bytes("bezeq-monthly"),
            },
        },
        {
            "id": "AQMkADAwATZiZmYAZC1mMWZmAC1mYmNhLTAwAi0wMAoARgAAA5bGPITkbq9Lhg_vlOo6E28HAAFMZdu9vw5InPGMJpaKhAsAAAIBDAAAAAFMZdu9vw5InPGMJpaKhAsACScPFacAAAA=",
            "subject": "החשבונית החודשית שלך בבזק energy כאן",
            "preview": "החשבונית החודשית שלך בבזק energy",
            "from_address": "bezeq_mail@bezeq.co.il",
            "received": "2025-09-15T13:55:02Z",
            "web_link": "https://outlook.live.com/owa/?ItemID=AQMkADAwATZiZmYAZC1mMWZmAC1mYmNhLTAwAi0wMAoARgAAA5bGPITkbq9Lhg%2BvlOo6E28HAAFMZdu9vw5InPGMJpaKhAsAAAIBDAAAAAFMZdu9vw5InPGMJpaKhAsACScPFacAAAA%3D&exvsurl=1&viewmodel=ReadMessageItem",
            "parent": "inbox",
            "hasAttachments": True,
            "attachments": [
                {
                    "id": "att-1",
                    "name": "80927472_00002_082025_03.pdf",
                    "contentType": "application/pdf",
                    "content": _pdf_bytes("bezeq-energy"),
                },
            ],
            "body_html": "<html></html>",
        },
        {
            "id": "AQMkADAwATZiZmYAZC1mMWZmAC1mYmNhLTAwAi0wMAoARgAAA5bGPITkbq9Lhg_vlOo6E28HAAFMZdu9vw5InPGMJpaKhAsAAAIBDAAAAAFMZdu9vw5InPGMJpaKhAsACSWJz2oAAAA=",
            "subject": "חשבונית מס קבלה 74245 מג'ודוקא - חוגים/ קייטנות/ ימי הולדת",
            "preview": "חשבונית מס קבלה 74245",
            "from_address": "no-reply@tazman.co.il",
            "received": "2025-09-14T15:40:34Z",
            "web_link": "https://outlook.live.com/owa/?ItemID=AQMkADAwATZiZmYAZC1mMWZmAC1mYmNhLTAwAi0wMAoARgAAA5bGPITkbq9Lhg%2BvlOo6E28HAAFMZdu9vw5InPGMJpaKhAsAAAIBDAAAAAFMZdu9vw5InPGMJpaKhAsACSWJz2oAAAA%3D&exvsurl=1&viewmodel=ReadMessageItem",
            "parent": "inbox",
            "hasAttachments": True,
            "attachments": [
                {
                    "id": "att-1",
                    "name": "2025-09-14-invoice-receipt-74245.pdf",
                    "contentType": "application/pdf",
                    "content": _pdf_bytes("judo-74245"),
                },
            ],
            "body_html": "<html></html>",
        },
        {
            "id": "AQMkADAwATZiZmYAZC1mMWZmAC1mYmNhLTAwAi0wMAoARgAAA5bGPITkbq9Lhg_vlOo6E28HAAFMZdu9vw5InPGMJpaKhAsAAAIBDAAAAAFMZdu9vw5InPGMJpaKhAsACSWJz2kAAAA=",
            "subject": "חשבונית מס קבלה 74244 מג'ודוקא - חוגים/ קייטנות/ ימי הולדת",
            "preview": "חשבונית מס קבלה 74244",
            "from_address": "no-reply@tazman.co.il",
            "received": "2025-09-14T15:40:33Z",
            "web_link": "https://outlook.live.com/owa/?ItemID=AQMkADAwATZiZmYAZC1mMWZmAC1mYmNhLTAwAi0wMAoARgAAA5bGPITkbq9Lhg%2BvlOo6E28HAAFMZdu9vw5InPGMJpaKhAsAAAIBDAAAAAFMZdu9vw5InPGMJpaKhAsACSWJz2kAAAA%3D&exvsurl=1&viewmodel=ReadMessageItem",
            "parent": "inbox",
            "hasAttachments": True,
            "attachments": [
                {
                    "id": "att-1",
                    "name": "2025-09-14-invoice-receipt-74244.pdf",
                    "contentType": "application/pdf",
                    "content": _pdf_bytes("judo-74244"),
                },
            ],
            "body_html": "<html></html>",
        },
        {
            "id": "AQMkADAwATZiZmYAZC1mMWZmAC1mYmNhLTAwAi0wMAoARgAAA5bGPITkbq9Lhg_vlOo6E28HAAFMZdu9vw5InPGMJpaKhAsAAAIBDAAAAAFMZdu9vw5InPGMJpaKhAsACSWJz2gAAAA=",
            "subject": "חשבונית מס קבלה 74243 מג'ודוקא - חוגים/ קייטנות/ ימי הולדת",
            "preview": "חשבונית מס קבלה 74243",
            "from_address": "no-reply@tazman.co.il",
            "received": "2025-09-14T15:40:30Z",
            "web_link": "https://outlook.live.com/owa/?ItemID=AQMkADAwATZiZmYAZC1mMWZmAC1mYmNhLTAwAi0wMAoARgAAA5bGPITkbq9Lhg%2BvlOo6E28HAAFMZdu9vw5InPGMJpaKhAsAAAIBDAAAAAFMZdu9vw5InPGMJpaKhAsACSWJz2gAAAA%3D&exvsurl=1&viewmodel=ReadMessageItem",
            "parent": "inbox",
            "hasAttachments": True,
            "attachments": [
                {
                    "id": "att-1",
                    "name": "2025-09-14-invoice-receipt-74243.pdf",
                    "contentType": "application/pdf",
                    "content": _pdf_bytes("judo-74243"),
                },
            ],
            "body_html": "<html></html>",
        },
        {
            "id": "AQMkADAwATZiZmYAZC1mMWZmAC1mYmNhLTAwAi0wMAoARgAAA5bGPITkbq9Lhg_vlOo6E28HAAFMZdu9vw5InPGMJpaKhAsAAAIBDAAAAAFMZdu9vw5InPGMJpaKhAsACR48UhcAAAA=",
            "subject": "שובר תשלום ארנונה - עיריית פתח תקוה לנכס מספר 10200570020",
            "preview": "שובר תשלום ארנונה",
            "from_address": "DoNotReply@onecity.org.il",
            "received": "2025-09-04T07:16:57Z",
            "web_link": "https://outlook.live.com/owa/?ItemID=AQMkADAwATZiZmYAZC1mMWZmAC1mYmNhLTAwAi0wMAoARgAAA5bGPITkbq9Lhg%2BvlOo6E28HAAFMZdu9vw5InPGMJpaKhAsAAAIBDAAAAAFMZdu9vw5InPGMJpaKhAsACR48UhcAAAA%3D&exvsurl=1&viewmodel=ReadMessageItem",
            "parent": "inbox",
            "hasAttachments": True,
            "attachments": [
                {
                    "id": "att-1",
                    "name": "333836120.pdf",
                    "contentType": "application/pdf",
                    "content": _pdf_bytes("arnona-1"),
                },
            ],
            "body_html": "<html></html>",
        },
        {
            "id": "AQMkADAwATZiZmYAZC1mMWZmAC1mYmNhLTAwAi0wMAoARgAAA5bGPITkbq9Lhg_vlOo6E28HAAFMZdu9vw5InPGMJpaKhAsAAAIBDAAAAAFMZdu9vw5InPGMJpaKhAsACR48UhUAAAA=",
            "subject": "שובר תשלום ארנונה - עיריית פתח תקוה לנכס מספר 1020057002009",
            "preview": "שובר תשלום ארנונה",
            "from_address": "DoNotReply@onecity.org.il",
            "received": "2025-09-04T06:38:23Z",
            "web_link": "https://outlook.live.com/owa/?ItemID=AQMkADAwATZiZmYAZC1mMWZmAC1mYmNhLTAwAi0wMAoARgAAA5bGPITkbq9Lhg%2BvlOo6E28HAAFMZdu9vw5InPGMJpaKhAsAAAIBDAAAAAFMZdu9vw5InPGMJpaKhAsACR48UhUAAAA%3D&exvsurl=1&viewmodel=ReadMessageItem",
            "parent": "inbox",
            "hasAttachments": True,
            "attachments": [
                {
                    "id": "att-1",
                    "name": "333836120.pdf",
                    "contentType": "application/pdf",
                    "content": _pdf_bytes("arnona-2"),
                },
            ],
            "body_html": "<html></html>",
        },
    ]

    direct_links: Dict[str, Tuple[str, bytes]] = {}
    bezeq_links: Dict[str, Tuple[str, bytes]] = {}
    for msg in messages:
        for entry in msg.get("direct_links", []):
            direct_links[entry["url"]] = (entry["name"], entry["content"])
        bezeq_entry = msg.get("bezeq_link")
        if bezeq_entry:
            bezeq_links[bezeq_entry["url"]] = (
                bezeq_entry["name"],
                bezeq_entry["content"],
            )

    expected_files = [
        (messages[0]["id"], "קבלה_על_תרומה_28847__SVRoAAAA.pdf"),
        (messages[1]["id"], "חשבונית_מס_קבלה_27107__SVQMAAAA.pdf"),
        (messages[2]["id"], "receipt_23265__fSVQAAAQ.pdf"),
        (messages[3]["id"], "5689_0507953_6542095_RAMIPDF__SVMUAAAA.pdf"),
        (messages[4]["id"], "bill__d161e610-4e10-49c7-b82b-7b89591f279b__PFaoAAAA.pdf"),
        (messages[5]["id"], "80927472_00002_082025_03__PFacAAAA.pdf"),
        (messages[6]["id"], "2025-09-14-invoice-receipt-74245__Jz2oAAAA.pdf"),
        (messages[7]["id"], "2025-09-14-invoice-receipt-74244__Jz2kAAAA.pdf"),
        (messages[8]["id"], "2025-09-14-invoice-receipt-74243__Jz2gAAAA.pdf"),
        (messages[9]["id"], "333836120__8UhcAAAA.pdf"),
        (messages[10]["id"], "333836120__8UhUAAAA.pdf"),
    ]

    return {
        "messages": messages,
        "direct_links": direct_links,
        "bezeq_links": bezeq_links,
        "expected": expected_files,
    }
