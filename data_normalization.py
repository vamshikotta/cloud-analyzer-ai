import pandas as pd
import json
import sys
from typing import Dict, Any

# Helper to load JSON with debug info
def load_json_file(filename):
    encodings_to_try = ['utf-8-sig', 'utf-16', 'utf-16-le', 'utf-16-be', 'utf-8']
    last_error = None
    for enc in encodings_to_try:
        try:
            with open(filename, 'r', encoding=enc) as f:
                content = f.read()
                if not content.strip():
                    print(f"ERROR: {filename} is empty.")
                    return None
                return json.loads(content)
        except Exception as e:
            last_error = e
            continue
    print(f"ERROR reading {filename}: {last_error}")
    return None

def normalize_to_frame(aws_json: Dict[str, Any], azure_json: Dict[str, Any]) -> pd.DataFrame:
    aws_normalized = normalize_aws_data(aws_json)
    azure_normalized = normalize_azure_data(azure_json)
    return pd.concat([aws_normalized, azure_normalized], ignore_index=True)

aws_data = load_json_file('aws_cost_data.json')
azure_data = load_json_file('azure_cost_data.json')

# Normalize AWS Data
def normalize_aws_data(data):
    normalized_data = []
    if not data:
        return pd.DataFrame(normalized_data)
    for record in data.get('ResultsByTime', []):
        for group in record.get('Groups', []):
            metrics = group.get('Metrics', {})
            # Prefer UnblendedCost; fallback to BlendedCost
            cost_obj = metrics.get('UnblendedCost') or metrics.get('BlendedCost') or {}
            if not cost_obj:
                continue
            tags = group.get('Keys', [])
            service = (
                group.get('Keys', ["Unknown Service"])[:1][0]
                if isinstance(group.get('Keys'), list) and group.get('Keys') else "Unknown Service"
            )
            try:
                cost = float(cost_obj.get('Amount', 0.0))
            except Exception:
                cost = 0.0
            normalized_data.append({
                'provider': 'AWS',
                'service': service,
                'cost': cost,
                'timestamp': record['TimePeriod']['Start'],
                'subscription': '',
                'resource_group': '',
                'tags': ', '.join(tags)
            })
    return pd.DataFrame(normalized_data)

# Normalize Azure Data
def normalize_azure_data(data):
    normalized_data = []
    if not data:
        return pd.DataFrame(normalized_data)
    # Support both SDK-like shapes and simplified samples
    if 'value' in data:
        for record in data.get('value', []):
            props = record.get('properties', {})
            cost_info = props.get('cost', {})
            normalized_data.append({
                'provider': 'Azure',
                'service': props.get('serviceName', "Unknown Service"),
                'cost': cost_info.get('amount', 0.0),
                'timestamp': props.get('date', "Unknown Date"),
                'subscription': record.get('subscriptionId', ''),
                'resource_group': record.get('resourceGroup', ''),
                'tags': ', '.join(record.get('tags', {}).keys())
            })
    elif 'properties' in data and 'rows' in data.get('properties', {}):
        for row in data['properties']['rows']:
            service, amount, date, tags = row[0], row[1], row[2], row[3] if len(row) > 3 else {}
            normalized_data.append({
                'provider': 'Azure',
                'service': service,
                'cost': amount,
                'timestamp': date,
                'subscription': '',
                'resource_group': '',
                'tags': ', '.join(tags.keys()) if isinstance(tags, dict) else ''
            })
    return pd.DataFrame(normalized_data)

if __name__ == '__main__':
    aws_normalized = normalize_aws_data(aws_data)
    azure_normalized = normalize_azure_data(azure_data)
    combined_data = pd.concat([aws_normalized, azure_normalized], ignore_index=True)
    if not combined_data.empty:
        combined_data.to_csv('normalized_cost_data.csv', index=False)
        print("Normalized data saved to normalized_cost_data.csv")
    else:
        print("No valid data to normalize. No CSV file created.")
