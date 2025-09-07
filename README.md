## Cloud Analyzer AI — Unified Cloud Cost Fetching and Dashboard

Cloud Analyzer AI fetches cost data from AWS Cost Explorer and Azure Cost Management, normalizes it, and serves an interactive Dash dashboard with filters, recommendations, background data refresh, and invoice uploads. Data is persisted to a local SQLite DB for fast reloads.

### What this repo contains
- AWS cost fetcher (callable): `aws_cost_explorer.py`
- Azure cost fetcher (callable): `azure_cost_management.py`
- Normalization utilities: `data_normalization.py`
- Dash dashboard (with DB + scheduler): `cloud_cost_dashboard.py`
- SQLite models/engine: `db.py`
- Background scheduler job: `scheduler.py`
- Sample/raw outputs: `aws_cost_data.json`, `azure_cost_data.json`, `azure_file.json`

---

## Prerequisites
- Python 3.10+ (recommended 3.12 if available on your system)
- Access credentials for AWS and/or Azure with billing read permissions

### Python dependencies
Install in a virtual environment:

```bash
pip install dash pandas plotly python-dotenv boto3 azure-identity azure-mgmt-costmanagement apscheduler sqlalchemy pdfplumber
```

Note: The repo includes virtual environment folders (`cloud-cost-env/`, `venv/`) from a local setup. You do not need to use them; creating your own venv is recommended.

---

## Quick start (Dashboard)

### 1) Configure your environment variables
Create a `.env` file in the project root with the following keys. Only populate the provider(s) you plan to use.

```bash
# AWS
AWS_ACCESS_KEY_ID=YOUR_KEY_ID
AWS_SECRET_ACCESS_KEY=YOUR_SECRET

# Azure (Service Principal)
AZURE_CLIENT_ID=YOUR_APP_ID
AZURE_CLIENT_SECRET=YOUR_PASSWORD
AZURE_TENANT_ID=YOUR_TENANT_ID
AZURE_SUBSCRIPTION_ID=YOUR_SUBSCRIPTION_ID
```

Ensure your credentials have the proper read permissions:
- AWS: Cost Explorer access (e.g., `ce:GetCostAndUsage`).
- Azure: Cost Management Reader on the subscription scope.

### 2) Run the dashboard

```bash
python cloud_cost_dashboard.py
```

What happens on startup:
- Initializes a local SQLite DB `cloud_costs.db`.
- Starts a scheduler that fetches AWS/Azure costs every 30 minutes, normalizes, and persists to DB.
- Serves the dashboard at `http://127.0.0.1:8050`.

Dashboard features:
- Provider, service, Azure subscription and resource group filters.
- Overview and Azure drilldown tabs, plus recommendations.
- Refresh button to reload from DB.
- Invoice upload (CSV supported, PDF basic text extraction) with ingestion into DB.
- Download summarized CSV of filtered data.

---

## Important details and schema notes

### AWS response shape and time window
The fetcher in `aws_cost_explorer.py` exposes `get_aws_costs(start_date, end_date, granularity, metrics, group_by)` and defaults to `UnblendedCost`. The normalizer prefers `UnblendedCost` and falls back to `BlendedCost`.

Expected AWS shape for normalization (simplified):

```json
{
  "ResultsByTime": [
    {
      "TimePeriod": { "Start": "YYYY-MM-DD", "End": "YYYY-MM-DD" },
      "Groups": [
        {
          "Keys": ["ServiceOrTagValue"],
          "Metrics": {
            "UnblendedCost": { "Amount": "123.45", "Unit": "USD" }
          },
          "Tags": { "env": "prod" }
        }
      ]
    }
  ]
}
```

### Azure response shape
`azure_cost_management.py` exposes `get_azure_costs(timeframe, granularity, group_by_dimensions, scope_subscription_id)`. Azure responses are often SDK objects; the dashboard converts them to dict where needed.

The normalization script expects a structure shaped like:

```json
{
  "properties": {
    "rows": [
      ["ServiceName", 123.45, "2024-01-01", {"env": "prod"}]
    ]
  }
}
```

If your raw object looks like the one in `azure_file.json` (with `columns` and `rows` at the top level), the normalizer can also adapt from `properties.rows`-style data.

---

## File-by-file overview

- `aws_cost_explorer.py`
  - Loads `.env`
  - Provides `get_aws_costs(...)` for programmatic use

- `azure_cost_management.py`
  - Loads `.env`
  - Provides `get_azure_costs(...)` for programmatic use

- `data_normalization.py`
  - Functions to normalize AWS/Azure responses and return a combined DataFrame
  - CLI mode writes `normalized_cost_data.csv`

- `aws_cost_data.json`, `azure_cost_data.json`, `azure_file.json`
  - Example payloads to help you understand expected shapes

- `db.py`
  - SQLAlchemy models and engine for SQLite `cloud_costs.db`

- `scheduler.py`
  - Background job that periodically fetches, normalizes, and persists cost data

- `cloud_cost_dashboard.py`
  - Dash app with filters, recommendations, invoice upload, DB-backed views, and CSV export

---

## Troubleshooting

- Missing credentials or permissions
  - Ensure `.env` is present and values are correct
  - Verify AWS IAM permissions and Azure role assignments

- Azure response has empty `rows`
  - Confirm there is cost data in the selected time frame
  - Validate the scope string (`/subscriptions/{SUBSCRIPTION_ID}`)

- Normalizer fails with KeyError
  - Confirm input JSONs (`aws_data.json`, `azure_data.json`) match the shapes expected by the normalizer
  - Align on `UnblendedCost` vs `BlendedCost`
  - Ensure files are in the project root if using CLI mode

- Windows PowerShell tips
  - Activate your virtualenv before running scripts: `venv\Scripts\Activate.ps1`
  - Run from the project root unless instructions say otherwise

---

## Roadmap ideas
- Add GCP Billing export ingestion and normalization
- Pluggable cost optimization strategies and advisor integrations
- Role-based access, multi-tenant DB/storage

---

## License
This project currently has no explicit license file. Consider adding one if you plan to distribute it.

