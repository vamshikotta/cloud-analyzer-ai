import dash
from dash import dcc, html, Input, Output, State
import pandas as pd
import plotly.express as px
import io
from datetime import datetime
from db import init_db, get_session, CostRecord, save_credentials
from scheduler import start_scheduler
import base64
import csv
try:
    import pdfplumber
except Exception:
    pdfplumber = None

def load_data() -> pd.DataFrame:
    try:
        # Prefer DB if available, fallback to CSV
        session = get_session()
        rows = session.query(CostRecord).all()
        if rows:
            df = pd.DataFrame([
                {
                    'provider': r.provider,
                    'service': r.service,
                    'cost': r.cost,
                    'timestamp': r.timestamp,
                    'subscription': r.subscription,
                    'resource_group': r.resource_group,
                    'tags': r.tags,
                }
                for r in rows
            ])
        else:
            df = pd.read_csv('normalized_cost_data.csv')

        # Ensure required columns exist
        expected = ['timestamp', 'cost', 'service']
        for col in expected:
            if col not in df.columns:
                df[col] = '' if col != 'cost' else 0.0
        # Coerce dtypes
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['cost'] = pd.to_numeric(df['cost'], errors='coerce').fillna(0.0)
        # Optional columns
        for col in ['provider', 'subscription', 'resource_group', 'tags']:
            if col not in df.columns:
                df[col] = ''
        return df
    except Exception:
        return pd.DataFrame(columns=['provider','timestamp','cost','service','subscription','resource_group','tags'])

data = load_data()

# Initialize Dash app
app = dash.Dash(__name__)
app.title = "Cloud Cost Dashboard"

# Layout
app.layout = html.Div([
    html.H1("Cloud Cost Dashboard", style={'textAlign': 'center'}),

    html.Div([
        html.Div([
            html.Label('Provider'),
            dcc.Dropdown(
                id='provider-select',
                options=[{'label': p, 'value': p} for p in sorted([x for x in data['provider'].unique() if x]) or ['AWS','Azure']],
                value=None,
                multi=True,
                placeholder='Select provider(s)'
            ),
        ], style={'width': '20%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '0 10px'}),
        html.Div([
            html.Label('Service'),
            dcc.Dropdown(
                id='service-filter',
                options=[{'label': s, 'value': s} for s in sorted([x for x in data['service'].unique() if isinstance(x, str)])],
                value=None,
                multi=True,
                placeholder='Filter by service'
            ),
        ], style={'width': '25%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '0 10px'}),
        html.Div([
            html.Label('Subscription (Azure)'),
            dcc.Dropdown(
                id='subscription-filter',
                options=[{'label': s, 'value': s} for s in sorted([x for x in data['subscription'].unique() if isinstance(x, str) and x])],
                value=None,
                multi=True,
                placeholder='Filter by subscription'
            ),
        ], style={'width': '25%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '0 10px'}),
        html.Div([
            html.Label('Resource Group (Azure)'),
            dcc.Dropdown(
                id='rg-filter',
                options=[{'label': s, 'value': s} for s in sorted([x for x in data['resource_group'].unique() if isinstance(x, str) and x])],
                value=None,
                multi=True,
                placeholder='Filter by resource group'
            ),
        ], style={'width': '25%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '0 10px'}),
    ]),

    html.Div([
        dcc.DatePickerRange(
            id='date-picker',
            start_date=(data['timestamp'].min() if not data.empty else None),
            end_date=(data['timestamp'].max() if not data.empty else None),
            display_format='YYYY-MM-DD',
            style={'margin': '12px 0'}
        ),
        html.Button('Refresh data', id='refresh-btn', n_clicks=0, style={'marginLeft': '12px'}),
        dcc.Upload(
            id='upload-invoice',
            children=html.Div(['Drag and Drop or ', html.A('Select Invoice CSV')]),
            multiple=False,
            style={'marginLeft': '12px', 'display': 'inline-block', 'border': '1px dashed #999', 'padding': '6px 10px'}
        ),
        html.Div(id='upload-status', style={'display': 'inline-block', 'marginLeft': '10px'}),
        html.Button('Download summary CSV', id='download-btn', n_clicks=0, style={'marginLeft': '12px'}),
        dcc.Download(id='download-summary')
    ]),

    dcc.Tabs(id='tabs', value='tab-overview', children=[
        dcc.Tab(label='Overview', value='tab-overview', children=[
            dcc.Graph(id='monthly-spending-trend'),
            dcc.Graph(id='project-cost-distribution'),
        ]),
        dcc.Tab(label='Azure Drilldown', value='tab-azure', children=[
            dcc.Graph(id='azure-subscription-trend'),
            dcc.Graph(id='azure-rg-breakdown'),
        ]),
        dcc.Tab(label='Integrations', value='tab-integrations', children=[
            html.H3('Connect Cloud Accounts'),
            html.Div([
                html.H4('AWS'),
                dcc.Input(id='aws-akid', type='text', placeholder='AWS Access Key ID', style={'width':'40%', 'marginRight':'8px'}),
                dcc.Input(id='aws-secret', type='password', placeholder='AWS Secret Access Key', style={'width':'40%', 'marginRight':'8px'}),
                html.Button('Save AWS', id='save-aws', n_clicks=0),
            ], style={'margin':'8px 0'}),
            html.Div(id='aws-save-status', style={'color':'green'}),
            html.Hr(),
            html.Div([
                html.H4('Azure'),
                dcc.Input(id='az-client-id', type='text', placeholder='Azure Client ID', style={'width':'45%', 'marginRight':'8px'}),
                dcc.Input(id='az-secret', type='password', placeholder='Azure Client Secret', style={'width':'45%', 'marginRight':'8px'}),
                dcc.Input(id='az-tenant', type='text', placeholder='Azure Tenant ID', style={'width':'45%', 'margin':'8px 8px 0 0'}),
                dcc.Input(id='az-sub', type='text', placeholder='Azure Subscription ID', style={'width':'45%', 'marginTop':'8px'}),
                html.Br(),
                html.Button('Save Azure', id='save-azure', n_clicks=0, style={'marginTop':'8px'}),
            ], style={'margin':'8px 0'}),
            html.Div(id='azure-save-status', style={'color':'green'}),
            html.Hr(),
            html.Button('Fetch Now', id='fetch-now', n_clicks=0),
            html.Div(id='fetch-now-status', style={'marginTop':'8px'}),
        ]),
        dcc.Tab(label='Analytics', value='tab-analytics', children=[
            dcc.Graph(id='provider-share'),
            dcc.Graph(id='monthly-totals'),
            dcc.Graph(id='top-services'),
        ]),
        dcc.Tab(label='Recommendations', value='tab-reco', children=[
            html.Pre(id='reco-output', style={'whiteSpace': 'pre-wrap'})
        ]),
    ]),
])

# Callbacks for interactivity
def filter_frame(df: pd.DataFrame, start_date, end_date, providers, services, subs, rgs) -> pd.DataFrame:
    if df.empty:
        return df
    mask = (df['timestamp'] >= pd.to_datetime(start_date)) & (df['timestamp'] <= pd.to_datetime(end_date)) if start_date and end_date else pd.Series(True, index=df.index)
    if providers:
        mask &= df['provider'].isin(providers)
    if services:
        mask &= df['service'].isin(services)
    if subs:
        mask &= df['subscription'].isin(subs)
    if rgs:
        mask &= df['resource_group'].isin(rgs)
    return df[mask]

@app.callback(
    [Output('monthly-spending-trend', 'figure'), Output('project-cost-distribution', 'figure'), Output('azure-subscription-trend', 'figure'), Output('azure-rg-breakdown', 'figure'), Output('reco-output', 'children'), Output('upload-status', 'children'), Output('download-summary', 'data'), Output('provider-share', 'figure'), Output('monthly-totals', 'figure'), Output('top-services', 'figure')],
    [Input('date-picker', 'start_date'), Input('date-picker', 'end_date'), Input('provider-select', 'value'), Input('service-filter', 'value'), Input('subscription-filter', 'value'), Input('rg-filter', 'value'), Input('refresh-btn', 'n_clicks'), Input('upload-invoice', 'contents'), Input('download-btn', 'n_clicks')],
    [State('upload-invoice', 'filename')]
)
def update_all(start_date, end_date, providers, services, subs, rgs, _n, upload_contents, upload_name, download_clicks):
    df = load_data()
    providers = providers or []
    services = services or []
    subs = subs or []
    rgs = rgs or []
    fdf = filter_frame(df, start_date, end_date, providers, services, subs, rgs)

    # Trend figure
    trend_fig = px.line(fdf, x='timestamp', y='cost', color='service', title='Spending Trends') if not fdf.empty else px.line(title='Spending Trends')

    # Distribution
    dist_fig = px.pie(fdf, names='service', values='cost', title='Cost Distribution by Service') if not fdf.empty else px.pie(title='Cost Distribution by Service')

    # Azure drilldowns
    az_df = fdf[fdf['provider'] == 'Azure'] if not fdf.empty else fdf
    sub_trend = px.bar(az_df.groupby(['subscription'], dropna=False)['cost'].sum().reset_index(), x='subscription', y='cost', title='Azure Cost by Subscription') if not az_df.empty else px.bar(title='Azure Cost by Subscription')
    rg_breakdown = px.bar(az_df.groupby(['resource_group'], dropna=False)['cost'].sum().reset_index(), x='resource_group', y='cost', title='Azure Cost by Resource Group') if not az_df.empty else px.bar(title='Azure Cost by Resource Group')

    # Recommendations (simple heuristics placeholder)
    reco_lines = []
    if not fdf.empty:
        top_services = fdf.groupby('service')['cost'].sum().sort_values(ascending=False).head(5)
        for svc, amt in top_services.items():
            reco_lines.append(f"- Consider rightsizing or reserved capacity for {svc} (spend {amt:.2f}).")
        if 'AWS' in fdf['provider'].unique():
            reco_lines.append("- Evaluate AWS Savings Plans or RIs for steady workloads.")
        if 'Azure' in fdf['provider'].unique():
            reco_lines.append("- Review Azure Reservations and Azure Advisor recommendations.")
        reco_lines.append("- Tag untagged resources to improve project-level allocation.")
    else:
        reco_lines.append("No data available. Load data or adjust filters.")

    upload_msg = ''
    if upload_contents and upload_name:
        try:
            content_type, content_string = upload_contents.split(',')
            decoded = base64.b64decode(content_string)
            if upload_name.lower().endswith('.csv'):
                csv_df = pd.read_csv(io.StringIO(decoded.decode('utf-8', errors='ignore')))
                # Basic normalization attempt: map columns if present
                cols = {c.lower(): c for c in csv_df.columns}
                mapped = pd.DataFrame({
                    'provider': csv_df[cols.get('provider')] if cols.get('provider') in csv_df else 'Unknown',
                    'service': csv_df[cols.get('service')] if cols.get('service') in csv_df else csv_df.columns[0],
                    'cost': pd.to_numeric(csv_df[cols.get('cost')] if cols.get('cost') in csv_df else csv_df.select_dtypes(include=['number']).iloc[:,0], errors='coerce').fillna(0.0),
                    'timestamp': pd.to_datetime(csv_df[cols.get('date')] if cols.get('date') in csv_df else datetime.today()),
                    'subscription': csv_df[cols.get('subscription')] if cols.get('subscription') in csv_df else '',
                    'resource_group': csv_df[cols.get('resource_group')] if cols.get('resource_group') in csv_df else '',
                    'tags': ''
                })
                # Insert into DB
                session = get_session()
                try:
                    for _, row in mapped.iterrows():
                        rec = CostRecord(
                            provider=str(row['provider']),
                            service=str(row['service']),
                            cost=float(row['cost']),
                            timestamp=pd.to_datetime(row['timestamp']).to_pydatetime(),
                            subscription=str(row['subscription']),
                            resource_group=str(row['resource_group']),
                            tags=str(row['tags']),
                        )
                        session.add(rec)
                    session.commit()
                    upload_msg = f"Imported {len(mapped)} invoice rows from CSV."
                finally:
                    session.close()
            elif upload_name.lower().endswith('.pdf') and pdfplumber is not None:
                with pdfplumber.open(io.BytesIO(decoded)) as pdf:
                    page_text = "\n".join(page.extract_text() or '' for page in pdf.pages)
                # Very basic PDF handling: not full parser, but stored for future mapping
                upload_msg = f"PDF uploaded ({upload_name}). Extracted text length: {len(page_text)}."
            else:
                upload_msg = f"Unsupported file type or PDF parser missing."
        except Exception as e:
            upload_msg = f"Upload failed: {e}"

    download_data = None
    if download_clicks:
        # Provide summarized CSV of filtered data
        summary = fdf.groupby(['provider','service'], dropna=False)['cost'].sum().reset_index()
        download_data = dcc.send_data_frame(summary.to_csv, filename=f"cost_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", index=False)

    # Analytics figures
    provider_share = px.pie(fdf, names='provider', values='cost', title='Cost Share by Provider') if not fdf.empty else px.pie(title='Cost Share by Provider')
    if not fdf.empty:
        monthly = fdf.copy()
        monthly['month'] = monthly['timestamp'].dt.to_period('M').dt.to_timestamp()
        monthly_totals = monthly.groupby('month')['cost'].sum().reset_index()
        monthly_fig = px.bar(monthly_totals, x='month', y='cost', title='Monthly Total Cost')
        top = fdf.groupby('service')['cost'].sum().sort_values(ascending=False).head(10).reset_index()
        top_fig = px.bar(top, x='service', y='cost', title='Top 10 Services by Spend')
    else:
        monthly_fig = px.bar(title='Monthly Total Cost')
        top_fig = px.bar(title='Top 10 Services by Spend')

    return trend_fig, dist_fig, sub_trend, rg_breakdown, "\n".join(reco_lines), upload_msg, download_data, provider_share, monthly_fig, top_fig

@app.callback(
    [Output('aws-save-status', 'children'), Output('azure-save-status', 'children'), Output('fetch-now-status', 'children')],
    [Input('save-aws', 'n_clicks'), Input('save-azure', 'n_clicks'), Input('fetch-now', 'n_clicks')],
    [State('aws-akid', 'value'), State('aws-secret', 'value'), State('az-client-id', 'value'), State('az-secret', 'value'), State('az-tenant', 'value'), State('az-sub', 'value')]
)
def integrations(aws_clicks, azure_clicks, fetch_clicks, akid, asecret, az_cid, az_sec, az_tenant, az_sub):
    aws_msg = ''
    az_msg = ''
    fetch_msg = ''
    changed = dash.ctx.triggered_id if hasattr(dash, 'ctx') else dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    session = get_session()
    try:
        if changed == 'save-aws' and aws_clicks:
            if akid and asecret:
                save_credentials(session, 'AWS', aws_access_key_id=akid, aws_secret_access_key=asecret)
                aws_msg = 'Saved AWS credentials.'
            else:
                aws_msg = 'Missing AWS Access Key or Secret.'
        if changed == 'save-azure' and azure_clicks:
            if az_cid and az_sec and az_tenant and az_sub:
                save_credentials(session, 'Azure', azure_client_id=az_cid, azure_client_secret=az_sec, azure_tenant_id=az_tenant, azure_subscription_id=az_sub)
                az_msg = 'Saved Azure credentials.'
            else:
                az_msg = 'Missing one or more Azure fields.'
    finally:
        session.close()

    if changed == 'fetch-now' and fetch_clicks:
        try:
            from scheduler import fetch_and_persist
            fetch_and_persist()
            fetch_msg = 'Fetch job executed. Data persisted to DB.'
        except Exception as e:
            fetch_msg = f'Fetch failed: {e}'

    return aws_msg, az_msg, fetch_msg

if __name__ == "__main__":
    init_db()
    start_scheduler()
    app.run(debug=True, host="127.0.0.1", port=8050)
