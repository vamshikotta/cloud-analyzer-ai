from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

import os
import boto3

def get_aws_costs():
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    client = boto3.client(
        "ce",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name="us-east-1"
    )
    
    response = client.get_cost_and_usage(
        TimePeriod={'Start': '2024-01-01', 'End': '2024-10-31'},
        Granularity='MONTHLY',
        Metrics=['UnblendedCost']
    )
    print("AWS Cost Response:", response)  # Add this line to print the response
    return response

# Call function to test
get_aws_costs()


