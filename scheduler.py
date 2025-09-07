from __future__ import annotations

import os
from datetime import date, timedelta
from typing import List, Dict

from apscheduler.schedulers.background import BackgroundScheduler

from aws_cost_explorer import get_aws_costs
from azure_cost_management import get_azure_costs
from data_normalization import normalize_to_frame
from db import init_db, get_session, CostRecord, get_latest_credentials
import pandas as pd


def fetch_and_persist() -> None:
    start = date.today().replace(day=1)
    end = date.today() + timedelta(days=1)

    aws_resp = {}
    try:
        session = get_session()
        aws_creds = get_latest_credentials(session, 'AWS')
        session.close()
        aws_resp = get_aws_costs(
            start_date=start.isoformat(), end_date=end.isoformat(), granularity='DAILY',
            group_by=[{"Type":"DIMENSION","Key":"SERVICE"}],
            aws_access_key_id=(aws_creds.aws_access_key_id if aws_creds else None),
            aws_secret_access_key=(aws_creds.aws_secret_access_key if aws_creds else None),
        )
    except Exception as e:
        print(f"AWS fetch failed: {e}")

    try:
        session = get_session()
        az_creds = get_latest_credentials(session, 'Azure')
        session.close()
        azure_resp = get_azure_costs(
            timeframe="MonthToDate", granularity="Daily", group_by_dimensions=["ServiceName", "SubscriptionId", "ResourceGroup"],
            scope_subscription_id=(az_creds.azure_subscription_id if az_creds else None),
            azure_client_id=(az_creds.azure_client_id if az_creds else None),
            azure_client_secret=(az_creds.azure_client_secret if az_creds else None),
            azure_tenant_id=(az_creds.azure_tenant_id if az_creds else None),
        )
    except Exception as e:
        print(f"Azure fetch failed: {e}")
        azure_resp = {}

    df = normalize_to_frame(aws_resp or {}, azure_resp or {})
    if df.empty:
        print("No data fetched to persist.")
        return

    session = get_session()
    try:
        for _, row in df.iterrows():
            rec = CostRecord(
                provider=str(row.get('provider') or ''),
                service=str(row.get('service') or ''),
                cost=float(row.get('cost') or 0.0),
                timestamp=pd.to_datetime(row.get('timestamp')).to_pydatetime(),
                subscription=str(row.get('subscription') or ''),
                resource_group=str(row.get('resource_group') or ''),
                tags=str(row.get('tags') or ''),
            )
            session.merge(rec)
        session.commit()
        print(f"Persisted {len(df)} records.")
    finally:
        session.close()


def start_scheduler() -> BackgroundScheduler:
    init_db()
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_and_persist, 'interval', minutes=30, id='fetch_costs', replace_existing=True)
    scheduler.start()
    print("Scheduler started: fetch job every 30 minutes")
    return scheduler

