"""
Inventory Optimization view.

Reads predictions stored in st.session_state by forecast_view, then POSTs
those to /api/optimize to get EOQ / Safety Stock / ROP and renders KPIs/charts.
"""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from smartstock.dashboard.api_client import call_optimize


@st.cache_data(show_spinner=False, ttl=1800)
def _cached_call_optimize(
    future_points_key: tuple,
    ordering_cost: float,
    holding_cost: float,
    lead_time: int,
    service_level: float,
    batch_size: int,
):
    """Cache optimization results. Same forecast + params = instant."""
    cfg_proxy = {
        "ordering_cost": ordering_cost,
        "holding_cost": holding_cost,
        "lead_time": lead_time,
        "service_level": service_level,
        "batch_size": batch_size,
    }
    future_points = [
        {"date": p[0], "forecast": p[1], "ci_lower": p[2], "ci_upper": p[3]}
        for p in future_points_key
    ]
    return call_optimize(cfg_proxy, future_points)


def render_optimization_view(cfg: Dict[str, Any]) -> None:
    st.markdown('<div class="section-pill">📦 &nbsp;Inventory Optimisation</div>', unsafe_allow_html=True)

    predictions: dict | None = st.session_state.get("predictions")
    raw_predictions: dict | None = st.session_state.get("raw_predictions")

    if not predictions or not raw_predictions:
        st.info("Run a forecast first (Forecasting tab) to unlock optimization.")
        return

    model_name = list(raw_predictions.keys())[0]
    raw_points: List[dict] = raw_predictions[model_name]

    pred_df = predictions[model_name]

    train_series: pd.DataFrame | None = st.session_state.get("train_series")
    train_cutoff_date: str | None = st.session_state.get("train_cutoff_date")

    if train_cutoff_date:
        cutoff_ts = pd.Timestamp(train_cutoff_date)
        future_points = [p for p in raw_points if pd.Timestamp(p["date"]) > cutoff_ts]
    elif train_series is not None:
        cutoff = train_series.index[-1]
        future_points = [p for p in raw_points if pd.Timestamp(p["date"]) > cutoff]
    else:
        future_points = raw_points

    if not future_points:
        st.warning("No future forecast periods available.")
        return

    with st.spinner("⚙️ Running inventory optimization via API..."):
        response = _cached_call_optimize(
            future_points_key=tuple(
                (p["date"], p["forecast"], p.get("ci_lower"), p.get("ci_upper"))
                for p in future_points
            ),
            ordering_cost=cfg["ordering_cost"],
            holding_cost=cfg["holding_cost"],
            lead_time=cfg["lead_time"],
            service_level=cfg["service_level"],
            batch_size=cfg["batch_size"],
        )

    if response is None:
        return

    results: List[dict] = response.get("results", [])
    if not results:
        st.error("No optimization results returned from the API.")
        return

    avg_eoq = response.get("avg_eoq", 0)
    avg_rop = response.get("avg_reorder_point", 0)
    avg_ss = response.get("avg_safety_stock", 0)
    total_demand = response.get("total_forecast_demand", 0)

    result_df = pd.DataFrame(results)
    result_df["date"] = pd.to_datetime(result_df["date"])
    result_df = result_df.set_index("date")

    st.markdown('<div class="section-pill">🎯 &nbsp;Key Inventory KPIs — Forecast Period Averages</div>', unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Optimal Order Qty (EOQ)", f"{int(avg_eoq)} units")
    k2.metric("Reorder Point (ROP)", f"{int(avg_rop)} units")
    k3.metric("Safety Stock", f"{int(avg_ss)} units")
    k4.metric("Total Forecast Demand", f"{int(total_demand)} units")

    st.divider()

    st.markdown('<div class="section-pill">💰 &nbsp;Cost Minimisation Curve</div>', unsafe_allow_html=True)
    st.caption(
        "Shows how ordering and holding costs balance at different order sizes. "
        "The vertical dashed line marks the EOQ — the sweet spot."
    )
    _render_cost_curve(
        avg_demand=float(result_df["expected_demand"].mean()),
        ordering_cost=cfg["ordering_cost"],
        holding_cost=cfg["holding_cost"],
        eoq=max(1, int(avg_eoq)),
    )

    st.divider()

    st.markdown('<div class="section-pill">🔄 &nbsp;Inventory Level Simulation</div>', unsafe_allow_html=True)
    st.caption(
        "Simulates how stock depletes day-by-day. "
        "Red dashed line = Reorder Point. Green markers = replenishment events."
    )
    _render_inventory_simulation(result_df, max(1, int(avg_eoq)), int(avg_rop))

    with st.expander("🔍 Raw Optimization Data (Developer View)", expanded=False):
        st.dataframe(result_df, use_container_width=True)


def _render_cost_curve(
    avg_demand: float,
    ordering_cost: float,
    holding_cost: float,
    eoq: int,
) -> None:
    if avg_demand <= 0 or holding_cost <= 0:
        st.warning("Cannot render cost curve — demand or holding cost is zero.")
        return

    q_range = np.linspace(max(1, eoq * 0.1), eoq * 3, 300)
    ordering_costs = (avg_demand / q_range) * ordering_cost
    holding_costs = (q_range / 2) * holding_cost
    total_costs = ordering_costs + holding_costs

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=q_range, y=ordering_costs, name="Ordering Cost", line=dict(color="#EF553B", dash="dash")))
    fig.add_trace(go.Scatter(x=q_range, y=holding_costs, name="Holding Cost", line=dict(color="#636EFA", dash="dash")))
    fig.add_trace(go.Scatter(x=q_range, y=total_costs, name="Total Cost", line=dict(color="#2CA02C", width=3)))
    fig.add_shape(type="line", x0=eoq, x1=eoq, y0=0, y1=1, xref="x", yref="paper", line=dict(dash="dot", color="orange", width=2))
    fig.add_annotation(x=eoq, xref="x", y=1, yref="paper", text=f"EOQ = {eoq}", showarrow=False, xanchor="left", font=dict(color="orange", size=11))
    fig.update_layout(
        xaxis_title="Order Quantity (units)",
        yaxis_title="Cost ($)",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=380,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_inventory_simulation(result_df: pd.DataFrame, eoq: int, rop: int) -> None:
    stock = float(eoq)
    stock_levels = []
    reorder_dates = []

    for idx, row in result_df.iterrows():
        demand = max(0.0, float(row["expected_demand"]))
        stock -= demand
        if stock <= rop:
            stock += eoq
            reorder_dates.append(idx)
        stock = max(0.0, stock)
        stock_levels.append(stock)

    sim_df = pd.DataFrame({"stock": stock_levels}, index=result_df.index)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=sim_df.index, y=sim_df["stock"], name="Stock Level", line=dict(color="#636EFA", width=2), fill="tozeroy", fillcolor="rgba(99,110,250,0.1)"))
    fig.add_shape(type="line", x0=0, x1=1, xref="paper", y0=rop, y1=rop, line=dict(dash="dash", color="red", width=1.5))
    fig.add_annotation(x=1, xref="paper", y=rop, text=f"ROP = {rop}", showarrow=False, xanchor="right", font=dict(color="red", size=11))
    if reorder_dates:
        reorder_y = [float(sim_df.loc[d, "stock"]) for d in reorder_dates if d in sim_df.index]
        fig.add_trace(go.Scatter(x=reorder_dates, y=reorder_y, mode="markers", marker=dict(color="green", size=10, symbol="triangle-up"), name="Replenishment"))
    fig.update_layout(xaxis_title="Date", yaxis_title="Units in Stock", template="plotly_white", hovermode="x unified", height=380)
    st.plotly_chart(fig, use_container_width=True)
