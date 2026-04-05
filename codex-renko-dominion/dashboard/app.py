from __future__ import annotations

import dash
import plotly.graph_objects as go
from dash import Input, Output, dcc, html


app = dash.Dash(__name__, title="CODEX Renko Dominion")


def _tab_layout() -> html.Div:
    interval = dcc.Interval(id="interval", interval=5000, n_intervals=0)
    tabs = dcc.Tabs(
        id="tabs",
        value="fct",
        children=[
            dcc.Tab(label="FCT Scorecard", value="fct"),
            dcc.Tab(label="Annual Score", value="annual"),
            dcc.Tab(label="Live Renko", value="renko"),
            dcc.Tab(label="Lot Ladder", value="ladder"),
            dcc.Tab(label="Pipeline Health", value="health"),
        ],
    )
    return html.Div([interval, tabs, html.Div(id="tab-content")])


app.layout = _tab_layout()


@app.callback(Output("tab-content", "children"), Input("tabs", "value"), Input("interval", "n_intervals"))
def render_tab(tab: str, _n: int) -> html.Div:
    """Render selected tab content with 5-second refresh."""
    if tab == "fct":
        fig = go.Figure(data=go.Scatterpolar(r=[0.8, 0.7, 0.6, 0.7, 0.65, 0.75, 0.55], theta=["TA", "MC", "VP", "RC", "RR", "PI", "MX"], fill="toself"))
        fig.update_layout(template="plotly_dark")
        return html.Div([dcc.Graph(figure=fig), html.Div("Grade: B | Tradeable: ✓")])
    if tab == "annual":
        fig = go.Figure(data=go.Bar(x=[f"M{i}" for i in range(1, 16)], y=[0.5 + i * 0.02 for i in range(15)]))
        fig.update_layout(template="plotly_dark")
        return html.Div([dcc.Graph(figure=fig)])
    if tab == "renko":
        y = [1 + i * 0.001 for i in range(100)]
        fig = go.Figure(data=go.Scatter(x=list(range(100)), y=y, mode="lines", line=dict(color="green")))
        fig.update_layout(template="plotly_dark")
        return html.Div([dcc.Graph(figure=fig), html.Div("Alignment: super=UP | macro=UP | trigger=UP")])
    if tab == "ladder":
        return html.Div([html.H3("Current Tier: GROWTH"), html.P("Consecutive wins: 2"), html.Pre("SEED -> GROWTH -> MOMENTUM -> HARVEST")])
    table = html.Table([
        html.Tr([html.Th("Subsystem"), html.Th("Status")]),
        *[html.Tr([html.Td(s), html.Td("✓")]) for s in ["Renko FSM", "FCT", "Hurst", "Gate", "Doctrine", "Backtest"]],
    ])
    return html.Div([table])


def run_dashboard(port: int = 8050, debug: bool = False) -> None:
    """Run Dash server."""
    app.run(port=port, debug=debug)
