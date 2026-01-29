"""Shared keyword lists and provider hints for invoice discovery."""

HEB_POS = [
    "חשבונית",
    "חשבונית מס",
    "חשבונית מס קבלה",
    "קבלה",
    "ארנונה",
    "שובר תשלום",
    "דרישת תשלום",
    "אגרת",
    "היטל",
    "מספר נכס",
]

EN_POS = ["invoice", "tax invoice", "receipt", "bill"]

HEB_NEG = [
    "תלוש שכר",
    "תלוש",
    "משכורת",
    "שכר",
    "ברוטו",
    "נטו",
    "הפרשות פנסיה",
    "שעות נוספות",
    "פקודות יומן",
    "דוח סיכום סליקה",
    "דוח סליקה מפורט",
    "תלוש שכר לחודש",
    "טופס 161",
    "תמחיר חודשי",
]

EN_NEG = [
    "payslip",
    "pay slip",
    "salary",
    "payroll",
    "net pay",
    "gross pay",
    "employee",
    "employer",
]

HEB_MUNICIPAL = [
    "ארנונה",
    "עיריית",
    "עיריה",
    "שובר תשלום",
    "רשות מקומית",
    "תאגיד מים",
    "מיתב",
]

TRUSTED_PROVIDERS = [
    "myinvoice.bezeq.co.il",
    "my.bezeq.co.il",
    "bmy.bezeq.co.il",
    "icount.co.il",
    "greeninvoice.co.il",
    "ezcount.co.il",
    "tax.gov.il",
    "gov.il",
    "quickbooks.intuit.com",
    "stripe.com",
]

TRUSTED_SENDER_DOMAINS = [
    "ravpass.co.il",
    "hopon.co.il",
]
