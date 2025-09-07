import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.express as px

# Load normalized data
data = pd.read_csv('normalized_cost_data.csv')

# Initialize Dash app
app = dash.Dash(__name__)
app.title = "Cloud Cost Dashboard"

# Layout
app.layout = html.Div([
    html.H1("Cloud Cost Dashboard", style={'textAlign': 'center'}),
    
    dcc.DatePickerRange(
        id='date-picker',
        start_date=data['timestamp'].min(),
        end_date=data['timestamp'].max(),
        display_format='YYYY-MM-DD',
        style={'margin': '20px'}
    ),
    
    dcc.Graph(id='monthly-spending-trend'),
    dcc.Graph(id='project-cost-distribution'),
])

# Callbacks for interactivity
@app.callback(
    [Output('monthly-spending-trend', 'figure'),
     Output('project-cost-distribution', 'figure')],
    [Input('date-picker', 'start_date'),
     Input('date-picker', 'end_date')]
)
def update_charts(start_date, end_date):
    filtered_data = data[(data['timestamp'] >= start_date) & (data['timestamp'] <= end_date)]
    
    # Monthly spending trend
    trend_fig = px.line(
        filtered_data,
        x='timestamp',
        y='cost',
        color='service',
        title='Monthly Spending Trends'
    )

    # Project-wise cost distribution
    cost_dist_fig = px.pie(
        filtered_data,
        names='service',
        values='cost',
        title='Project-Wise Cost Distribution'
    )
    
    return trend_fig, cost_dist_fig

if __name__ == "__main__":
    app.run_server(debug=True)
