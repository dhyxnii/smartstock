"""
Inventory Optimization view.

Reads predictions stored in st.session_state by forecast_view, then:
  1. Runs EOQCalculator to get period-by-period EOQ/ROP/Safety Stock.
  2. Renders KPI cards for summary stats.
  3. Renders a cost-minimization plot (ordering vs holding vs total).
  4. Renders an inventory simulation (stock depletion + reorder triggers).
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from smartstock.optimization.eoq_calculator import EOQCalculator


def render_optimization_view(cfg: Dict[str, Any]) -> None:
    """Entry-point called by app.py for the Inventory Optimization tab."""
    st.markdown('<div class="section-pill">📦 &nbsp;Inventory Optimisation</div>', unsafe_allow_html=True)

    predictions: dict | None = st.session_state.get("predictions")
    if not predictions:
        st.info("Run a forecast first (Forecasting tab) to unlock optimization.")
        return

    # Pick the first available model's forecast as the basis
    model_name = list(predictions.keys())[0]
    pred_df = predictions[model_name]

    # Future-only slice
    train_series: pd.DataFrame | None = st.session_state.get("train_series")
    if train_series is not None:
        cutoff = train_series.index[-1]
        future_df = pred_df[pred_df.index > cutoff].copy()
    else:
        future_df = pred_df.copy()

    if future_df.empty:
        st.warning("No future forecast periods available.")
        return

    forecast_series = future_df["forecast"]
    uncertainty_series = None
    if "ci_upper" in future_df.columns and "ci_lower" in future_df.columns:
        uncertainty_series = (
            (future_df["ci_upper"] - future_df["ci_lower"]) / 2
        ).clip(lower=0)

    # ── Run EOQ Calculator ────────────────────────────────────────────────
    calc = EOQCalculator()
    try:
        result_df = calc.calculate(
            forecast_series=forecast_series,
            ordering_cost=cfg["ordering_cost"],
            holding_cost_per_period=cfg["holding_cost"],
            lead_time_periods=cfg["lead_time"],
            uncertainty_series=uncertainty_series,
            batch_size=cfg["batch_size"],
            service_level=cfg["service_level"],
        )
    except ValueError as exc:
        st.error(f"EOQ calculation error: {exc}")
        return

    # ── KPI Summary Cards ────────────────────────────────────────────────
    st.markdown('<div class="section-pill">🎯 &nbsp;Key Inventory KPIs — Forecast Period Averages</div>', unsafe_allow_html=True)
    avg_eoq = int(result_df["eoq"].mean())
    avg_rop = int(result_df["reorder_point"].mean())
    avg_ss = int(result_df["safety_stock"].mean())
    total_demand = int(result_df["expected_demand"].sum())

    k1, k2, k3, k4 = st.columns(4)
    k1.metric(
        "Optimal Order Qty (EOQ)",
        f"{avg_eoq} units",
        help="Average Economic Order Quantity — how much to order each time.",
    )
    k2.metric(
        "Reorder Point (ROP)",
        f"{avg_rop} units",
        help="Place a new order when stock falls to this level.",
    )
    k3.metric(
        "Safety Stock",
        f"{avg_ss} units",
        help="Buffer stock to protect against demand uncertainty.",
    )
    k4.metric(
        "Total Forecast Demand",
        f"{total_demand} units",
        help="Sum of expected demand over the forecast horizon.",
    )

    st.divider()

    # ── Cost Minimization Plot ────────────────────────────────────────────
    st.markdown('<div class="section-pill">💰 &nbsp;Cost Minimisation Curve</div>', unsafe_allow_html=True)
    st.caption(
        "Shows how ordering and holding costs balance at different order sizes. "
        "The vertical dashed line marks the EOQ — the sweet spot."
    )
    _render_cost_curve(
        avg_demand=float(result_df["expected_demand"].mean()),
        ordering_cost=cfg["ordering_cost"],
        holding_cost=cfg["holding_cost"],
        eoq=avg_eoq,
    )

    st.divider()

    # ── Inventory Simulation ─────────────────────────────────────────────
    st.markdown('<div class="section-pill">🔄 &nbsp;Inventory Level Simulation</div>', unsafe_allow_html=True)
    st.caption(
        "Simulates how stock depletes day-by-day. "
        "Red dashed line = Reorder Point. Green markers = replenishment events."
    )
    _render_inventory_simulation(result_df, avg_eoq, avg_rop)

    # ── Raw data toggle ──────────────────────────────────────────────────
    with st.expander("🔍 Raw Optimization Data (Developer View)", expanded=False):
        st.dataframe(result_df, use_container_width=True)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _render_cost_curve(
    avg_demand: float,
    ordering_cost: float,
    holding_cost: float,
    eoq: int,
) -> None:
    """Render the classic EOQ cost trade-off chart."""
    if avg_demand <= 0 or holding_cost <= 0:
        st.warning("Cannot render cost curve — demand or holding cost is zero.")
        return

    q_range = np.linspace(max(1, eoq * 0.1), eoq * 3, 300)
    ordering_costs = (avg_demand / q_range) * ordering_cost
    holding_costs = (q_range / 2) * holding_cost
    total_costs = ordering_costs + holding_costs

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=q_range,
            y=ordering_costs,
            name="Ordering Cost",
            line=dict(color="#EF553B", dash="dash"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=q_range,
            y=holding_costs,
            name="Holding Cost",
            line=dict(color="#636EFA", dash="dash"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=q_range,
            y=total_costs,
            name="Total Cost",
            line=dict(color="#2CA02C", width=3),
        )
    )
    # add_vline with annotation crashes in plotly 6.x — use add_shape + add_annotation
    fig.add_shape(
        type="line",
        x0=eoq, x1=eoq,
        y0=0, y1=1,
        xref="x", yref="paper",
        line=dict(dash="dot", color="orange", width=2),
    )
    fig.add_annotation(
        x=eoq, xref="x",
        y=1, yref="paper",
        text=f"EOQ = {eoq}",
        showarrow=False,
        xanchor="left",
        font=dict(color="orange", size=11),
    )
    fig.update_layout(
        xaxis_title="Order Quantity (units)",
        yaxis_title="Cost ($)",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=380,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_inventory_simulation(
    result_df: pd.DataFrame,
    eoq: int,
    rop: int,
) -> None:
    """Simulate stock level over time, triggering replenishments at ROP."""
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
    fig.add_trace(
        go.Scatter(
            x=sim_df.index,
            y=sim_df["stock"],
            name="Stock Level",
            line=dict(color="#636EFA", width=2),
            fill="tozeroy",
            fillcolor="rgba(99,110,250,0.1)",
        )
    )
    # Use add_shape + add_annotation instead of add_hline to avoid
    # plotly + pandas 2.x Timestamp arithmetic error on datetime axes
    fig.add_shape(
        type="line",
        x0=0, x1=1, xref="paper",
        y0=rop, y1=rop,
        line=dict(dash="dash", color="red", width=1.5),
    )
    fig.add_annotation(
        x=1, xref="paper",
        y=rop,
        text=f"ROP = {rop}",
        showarrow=False,
        xanchor="right",
        font=dict(color="red", size=11),
    )
    if reorder_dates:
        reorder_y = [
            float(sim_df.loc[d, "stock"]) for d in reorder_dates if d in sim_df.index
        ]
        fig.add_trace(
            go.Scatter(
                x=reorder_dates,
                y=reorder_y,
                mode="markers",
                marker=dict(color="green", size=10, symbol="triangle-up"),
                name="Replenishment",
            )
        )
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Units in Stock",
        template="plotly_white",
        hovermode="x unified",
        height=380,
    )
    st.plotly_chart(fig, use_container_width=True)
