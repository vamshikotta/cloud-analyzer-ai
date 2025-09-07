from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

import os
from google.cloud import bigquery

def get_gcp_costs():
    # Path to the JSON key file, stored in an environment variable
    gcp_key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    # Set the environment variable for Google Cloud authentication
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = gcp_key_path

    client = bigquery.Client()
    query = """
        SELECT service.description as service, SUM(cost) as total_cost
        FROM `project-id.billing_dataset.gcp_billing_table`
        WHERE usage_start_time >= '2023-01-01'
        GROUP BY service
    """
    query_job = client.query(query)
    return query_job.result()
