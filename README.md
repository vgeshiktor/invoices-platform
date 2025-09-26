# Invoices Platform

invoices-platform/
├─ apps/
│  ├─ api-go/                # שירות Go (REST/GRPC) לניהול חשבוניות/ספקים
│  │  ├─ cmd/invoicer/
│  │  │  └─ main.go
│  │  ├─ internal/
│  │  │  ├─ domain/          # ישויות/ערכי־אובייקט (Invoice, Vendor, Payment)
│  │  │  ├─ adapters/        # אינטגרציות (email, s3, zapier וכו׳)
│  │  │  └─ usecase/         # לוגיקה אפליקטיבית (CreateInvoice, MatchEmail)
│  │  ├─ pkg/                # קוד לשימוש חיצוני (אם צריך)
│  │  ├─ go.mod
│  │  └─ Makefile
│  └─ workers-py/            # עיבוד אסינכרוני/ETL/זיהוי נתונים
│     ├─ src/
│     │  ├─ workers/         # קונסיומרים/טסק־ראנרים
│     │  ├─ pipelines/       # צינורות ETL (מייל→PDF→OCR→JSON)
│     │  └─ adapters/        # חיבורים (IMAP/Gmail, S3, DB)
│     ├─ pyproject.toml      # poetry/uv
│     ├─ Makefile
│     └─ README.md
├─ integrations/
│  ├─ n8n/                   # תצורת n8n (docker-compose + export of workflows)
│  │  ├─ docker-compose.yml
│  │  ├─ n8n.env.example
│  │  └─ workflows/          # קבצי export של n8n (JSON)
│  └─ openapi/               # חוזים בין שירותים (OpenAPI)
│     └─ invoices.yaml
├─ deploy/
│  ├─ docker/                # Dockerfiles לפי שירות
│  ├─ compose/               # docker-compose.dev.yml (db, mq, n8n, api, workers)
│  └─ k8s/                   # מאניפסטים בסיסיים לקוברנטיס (בהמשך)
├─ docs/
│  ├─ ADR/                   # החלטות ארכיטקטורה (Architecture Decision Records)
│  ├─ CONTRIBUTING.md
│  ├─ ONBOARDING.md
│  └─ ARCHITECTURE.md
├─ .pre-commit-config.yaml
├─ Makefile                  # פקודות על למונוריפו כולו
└─ .github/workflows/ci.yml  # CI בסיסי
