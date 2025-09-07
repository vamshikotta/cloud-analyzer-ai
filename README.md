## Cloud Analezr AI — Unified Cloud Cost Fetching and Normalization

Cloud Analezr AI is a lightweight toolkit to fetch monthly/daily cost data from AWS Cost Explorer and Azure Cost Management, then normalize the outputs into a single JSON you can analyze further or load into BI tools.

### What this repo contains
- AWS cost fetcher: `aws_cost_explorer.py`
- Azure cost fetcher: `azure_cost_management.py`
- Sample/raw outputs: `aws_cost_data.json`, `azure_cost_data.json`, `azure_file.json`
- Normalization script: `cloud-cost-env/normalize-data/normalize_data.py`

The fetchers retrieve cloud billing data using official SDKs and print the API responses. The normalization script converts AWS/Azure responses into a common schema and writes `normalized_data.json`.

---

## Prerequisites
- Python 3.10+ (recommended 3.12 if available on your system)
- Access credentials for AWS and/or Azure with billing read permissions

### Python dependencies
Install these in a virtual environment:

```bash
pip install python-dotenv boto3 azure-identity azure-mgmt-costmanagement
```

Note: The repo includes virtual environment folders (`cloud-cost-env/`, `venv/`) from a local setup. You do not need to use them; creating your own venv is recommended.

---

## Quick start

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

### 2) Fetch cost data

Run the provider script(s) from the project root.

```bash
# AWS monthly unblended cost (prints response)
python aws_cost_explorer.py

# Azure cost (MonthToDate, daily granularity, grouped by ServiceName; prints response)
python azure_cost_management.py
```

These scripts currently print Python objects to stdout for inspection. To feed the normalization step, save the raw responses as JSON files. You can do this in one of two ways:

- Easiest: copy the printed response and save it as JSON.
- Better: update the scripts to `json.dump(...)` the API response to disk.

Suggested filenames for the normalization step:
- `cloud-cost-env/normalize-data/aws_data.json`
- `cloud-cost-env/normalize-data/azure_data.json`

You can also use the included examples for reference:
- `aws_cost_data.json` (example AWS shape)
- `azure_file.json` (example Azure SDK response with columns/rows)
- `azure_cost_data.json` (simplified sample; not the exact SDK shape)

### 3) Normalize to a common schema

From the `cloud-cost-env/normalize-data/` folder, run:

```bash
cd cloud-cost-env/normalize-data
python normalize_data.py
```

This reads `aws_data.json` and `azure_data.json` from the same directory, then writes `normalized_data.json` with a unified schema:

```json
{
  "service": "string",
  "cost": "number or string",
  "timestamp": "YYYY-MM-DD",
  "tags": { "key": "value", ... }
}
```

---

## Important details and schema notes

### AWS response shape and time window
The current code in `aws_cost_explorer.py` uses Cost Explorer with:
- TimePeriod: Start=`2024-01-01`, End=`2024-10-31`
- Granularity: `MONTHLY`
- Metrics: `UnblendedCost`

The normalization script expects `UnblendedCost` under the `Metrics` field. If your raw data uses `BlendedCost` (as seen in `aws_cost_data.json`), either:
- Update the sample file to use `UnblendedCost`, or
- Change the normalization script to read `BlendedCost` instead.

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
`azure_cost_management.py` executes a Cost Management query using the SDK and prints the returned object. The Azure SDK’s `query.usage(...)` typically returns data formatted with `columns` metadata and `rows` values.

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

If your raw object looks like the one in `azure_file.json` (with `columns` and `rows` at the top level), convert or save it to match the above `properties.rows` structure before running normalization, or adjust the script accordingly.

---

## File-by-file overview

- `aws_cost_explorer.py`
  - Loads `.env` for AWS credentials
  - Calls Cost Explorer with monthly granularity and `UnblendedCost`
  - Prints the full response. Modify to write JSON to disk if desired

- `azure_cost_management.py`
  - Loads `.env` for Azure service principal and subscription
  - Runs a MonthToDate, daily granularity query grouped by `ServiceName`
  - Prints the full SDK response. Modify to write JSON to disk if desired

- `cloud-cost-env/normalize-data/normalize_data.py`
  - Reads `aws_data.json` and `azure_data.json`
  - Normalizes both into a common list of records and writes `normalized_data.json`

- `aws_cost_data.json`, `azure_cost_data.json`, `azure_file.json`
  - Example payloads to help you understand expected shapes

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
  - Ensure files are placed in `cloud-cost-env/normalize-data/`

- Windows PowerShell tips
  - Activate your virtualenv before running scripts: `venv\Scripts\Activate.ps1`
  - Run from the project root unless instructions say otherwise

---

## Roadmap ideas
- Write raw fetch results to timestamped JSON files automatically
- Add GCP Billing export ingestion and normalization
- Provide a small CLI and consolidated config (YAML) for time windows and group-bys
- Add an optional Dash/Plotly dashboard for quick visualization

---

## License
This project currently has no explicit license file. Consider adding one if you plan to distribute it.

