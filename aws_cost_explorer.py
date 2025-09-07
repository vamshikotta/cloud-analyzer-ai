from dotenv import load_dotenv
import os
import boto3
from typing import Dict, List, Optional

# Load environment variables from .env file (safe if not present)
load_dotenv()

def get_aws_costs(
    start_date: str,
    end_date: str,
    granularity: str = 'MONTHLY',
    metrics: Optional[List[str]] = None,
    group_by: Optional[List[Dict[str, str]]] = None,
    aws_access_key_id: Optional[str] = None,
    aws_secret_access_key: Optional[str] = None,
) -> Dict:
    """Fetch AWS Cost Explorer data.

    - start_date/end_date: 'YYYY-MM-DD'
    - granularity: DAILY | MONTHLY
    - metrics: default ['UnblendedCost']
    - group_by: e.g., [{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
    - aws_access_key_id/secret: override env if provided
    """
    if metrics is None:
        metrics = ['UnblendedCost']

    aws_access_key_id = aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY")

    client = boto3.client(
        "ce",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name="us-east-1",
    )

    params: Dict = {
        'TimePeriod': {'Start': start_date, 'End': end_date},
        'Granularity': granularity,
        'Metrics': metrics,
    }
    if group_by:
        params['GroupBy'] = group_by

    response = client.get_cost_and_usage(**params)
    # Return plain dict for easy JSON serialization
    return response

__all__ = ["get_aws_costs"]


