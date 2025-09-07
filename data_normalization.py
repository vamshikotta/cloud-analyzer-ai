import pandas as pd
import json
import sys

# Helper to load JSON with debug info
def load_json_file(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"\n--- {filename} content ---\n{content}\n--- end ---\n")
            if not content.strip():
                print(f"ERROR: {filename} is empty.")
                return None
            return json.loads(content)
    except Exception as e:
        print(f"ERROR reading {filename}: {e}")
        return None

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
            blended_cost = metrics.get('BlendedCost', {})
            if not blended_cost:
                continue
            tags = group.get('Keys', [])
            service = blended_cost.get('Unit', "Unknown Service")
            cost = float(blended_cost.get('Amount', 0.0))
            normalized_data.append({
                'service': service,
                'cost': cost,
                'timestamp': record['TimePeriod']['Start'],
                'tags': ', '.join(tags)
            })
    return pd.DataFrame(normalized_data)

# Normalize Azure Data
def normalize_azure_data(data):
    normalized_data = []
    if not data:
        return pd.DataFrame(normalized_data)
    for record in data.get('value', []):
        props = record.get('properties', {})
        cost_info = props.get('cost', {})
        normalized_data.append({
            'service': props.get('serviceName', "Unknown Service"),
            'cost': cost_info.get('amount', 0.0),
            'timestamp': props.get('date', "Unknown Date"),
            'tags': ', '.join(record.get('tags', {}).keys())
        })
    return pd.DataFrame(normalized_data)

aws_normalized = normalize_aws_data(aws_data)
azure_normalized = normalize_azure_data(azure_data)

combined_data = pd.concat([aws_normalized, azure_normalized], ignore_index=True)

if not combined_data.empty:
    combined_data.to_csv('normalized_cost_data.csv', index=False)
    print("Normalized data saved to normalized_cost_data.csv")
else:
    print("No valid data to normalize. No CSV file created.")
