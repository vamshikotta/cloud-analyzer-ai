from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file
import os
from azure.identity import ClientSecretCredential
from azure.mgmt.costmanagement import CostManagementClient

def get_azure_costs():
    azure_client_id = os.getenv("AZURE_CLIENT_ID")
    azure_client_secret = os.getenv("AZURE_CLIENT_SECRET")
    azure_tenant_id = os.getenv("AZURE_TENANT_ID")
    subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")

    credentials = ClientSecretCredential(
        client_id=azure_client_id,
        client_secret=azure_client_secret,
        tenant_id=azure_tenant_id
    )

    client = CostManagementClient(credentials)

    # Define the parameters for the cost query
    parameters = {
        "type": "Usage",
        "timeframe": "MonthToDate",
        "dataset": {
            "granularity": "Daily",
            "aggregation": {
                "totalCost": {
                    "name": "Cost",
                    "function": "Sum"
                }
            },
            "grouping": [
                {
                    "type": "Dimension",
                    "name": "ServiceName"
                }
            ]
        }
    }

    # Perform the cost query
    costs = client.query.usage(
        scope=f'/subscriptions/{subscription_id}',
        parameters=parameters
    )

    print("Azure Cost Response:", costs)
    return costs

# Call function to test
get_azure_costs()
