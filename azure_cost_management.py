from dotenv import load_dotenv
import os
from typing import Dict, List, Optional
from azure.identity import ClientSecretCredential
from azure.mgmt.costmanagement import CostManagementClient

load_dotenv()

def get_azure_costs(
    timeframe: str = "MonthToDate",
    granularity: str = "Daily",
    group_by_dimensions: Optional[List[str]] = None,
    scope_subscription_id: Optional[str] = None,
    azure_client_id: Optional[str] = None,
    azure_client_secret: Optional[str] = None,
    azure_tenant_id: Optional[str] = None,
) -> Dict:
    """Fetch Azure cost data using Cost Management query.

    - timeframe: Custom | MonthToDate | BillingMonthToDate | TheLastMonth etc.
    - granularity: Daily | Monthly
    - group_by_dimensions: e.g., ["ServiceName", "ResourceGroup", "SubscriptionId"]
    - scope_subscription_id: defaults to AZURE_SUBSCRIPTION_ID from env
    """
    azure_client_id = azure_client_id or os.getenv("AZURE_CLIENT_ID")
    azure_client_secret = azure_client_secret or os.getenv("AZURE_CLIENT_SECRET")
    azure_tenant_id = azure_tenant_id or os.getenv("AZURE_TENANT_ID")
    subscription_id = scope_subscription_id or os.getenv("AZURE_SUBSCRIPTION_ID")

    credentials = ClientSecretCredential(
        client_id=azure_client_id,
        client_secret=azure_client_secret,
        tenant_id=azure_tenant_id,
    )

    client = CostManagementClient(credentials)

    grouping: List[Dict[str, str]] = []
    for name in (group_by_dimensions or ["ServiceName"]):
        grouping.append({"type": "Dimension", "name": name})

    parameters: Dict = {
        "type": "Usage",
        "timeframe": timeframe,
        "dataset": {
            "granularity": granularity,
            "aggregation": {"totalCost": {"name": "Cost", "function": "Sum"}},
            "grouping": grouping,
        },
    }

    costs = client.query.usage(
        scope=f"/subscriptions/{subscription_id}",
        parameters=parameters,
    )

    # Return as plain dict-like structure
    return costs.as_dict() if hasattr(costs, 'as_dict') else costs

__all__ = ["get_azure_costs"]
