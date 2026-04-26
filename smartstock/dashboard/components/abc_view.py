"""
ABC Analysis and Categorisation view.

Supports CSV and synthetic forecast-backed flows and runs classification via /api/abc.
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from smartstock.dashboard.api_client import call_abc

_CATEGORY_COLORS = {"A": "#EF553B", "B": "#FFA500", "C": "#636EFA"}


def render_abc_view(cfg: Dict[str, Any]) -> None:
    st.markdown('<div class="section-pill">🏷️ &nbsp;ABC Analysis &amp; Prioritisation</div>', unsafe_allow_html=True)

    abc_df = _get_abc_data(cfg)

    if abc_df is None:
        st.info(
            "To run ABC analysis, either:\n"
            "- Upload a CSV with columns: `item_id`, `unit_cost`, `annual_demand`  \n"
            "- Or run a forecast first - the dashboard will auto-generate a "
            "sample ABC dataset from the training data."
        )
        return

    items_payload = []
    for _, row in abc_df.iterrows():
        item = {
            "item_id": str(row["item_id"]),
            "unit_cost": float(row["unit_cost"]),
            "annual_demand": float(row["annual_demand"]),
        }
        if "item_name" in abc_df.columns:
            item["item_name"] = str(row["item_name"])
        items_payload.append(item)

    with st.spinner("🏷️ Running ABC analysis via API..."):
        response = call_abc(items_payload)

    if response is None:
        return

    result = pd.DataFrame(response.get("results", []))
    if result.empty:
        st.error("No results returned from the ABC API.")
        return

    st.markdown('<div class="section-pill">📋 &nbsp;Category Summary</div>', unsafe_allow_html=True)
    _render_category_cards(result)

    st.divider()

    st.markdown('<div class="section-pill">🚨 &nbsp;Action Required - What To Do Next</div>', unsafe_allow_html=True)
    _render_action_recommendations(result)

    st.divider()

    st.markdown('<div class="section-pill">📊 &nbsp;Annual Value by Item</div>', unsafe_allow_html=True)
    st.caption(
        "Items ranked by annual value. "
        "Class A = top 80% of total value; B = next 15%; C = bottom 5%."
    )
    _render_abc_bar(result)

    st.divider()

    st.markdown('<div class="section-pill">📈 &nbsp;Pareto Curve</div>', unsafe_allow_html=True)
    _render_pareto_curve(result)

    st.divider()

    st.markdown('<div class="section-pill">🔦 &nbsp;Item Spotlight - Top 5 Priority Items</div>', unsafe_allow_html=True)
    _render_item_spotlight(result)

    st.divider()

    st.markdown('<div class="section-pill">📄 &nbsp;Full ABC Table</div>', unsafe_allow_html=True)
    _render_abc_table(result)

    with st.expander("🔍 Raw ABC JSON (Developer View)", expanded=False):
        st.json(
            result[["item_id", "annual_value", "cumulative_value_pct", "abc_category"]]
            .head(50)
            .to_dict(orient="records")
        )


def _get_abc_data(cfg: Dict[str, Any]) -> pd.DataFrame | None:
    mode = cfg.get("data_mode")
    df_raw = cfg.get("df_raw")

    if mode in ("abc_only", "abc_synthetic") and df_raw is not None:
        return df_raw.copy()

    if mode == "multi_store" and df_raw is not None:
        try:
            agg = (
                df_raw.groupby("item")["sales"]
                .sum()
                .reset_index()
                .rename(columns={"item": "item_id", "sales": "annual_demand"})
            )
            rng = np.random.default_rng(seed=42)
            agg["unit_cost"] = rng.uniform(1.0, 100.0, size=len(agg)).round(2)
            return agg[["item_id", "unit_cost", "annual_demand"]]
        except Exception:
            pass

    predictions = st.session_state.get("predictions")
    train_series: pd.DataFrame | None = st.session_state.get("train_series")
    if predictions and train_series is not None:
        model_name = list(predictions.keys())[0]
        pred_df = predictions[model_name]
        cutoff = train_series.index[-1]
        future_df = pred_df[pred_df.index > cutoff]
        if not future_df.empty:
            annual_demand = float(future_df["forecast"].sum())
            return pd.DataFrame(
                [
                    {
                        "item_id": "current_item",
                        "unit_cost": 10.0,
                        "annual_demand": annual_demand,
                    }
                ]
            )

    return None


def _display_name(row) -> str:
    name = row.get("item_name") if isinstance(row, dict) else getattr(row, "item_name", None)
    iid = row.get("item_id") if isinstance(row, dict) else getattr(row, "item_id", row.name if hasattr(row, "name") else "")
    if name and str(name).strip():
        return f"{name} ({iid})"
    return str(iid)


def _render_action_recommendations(result: pd.DataFrame) -> None:
    a_items = result[result["abc_category"] == "A"]
    b_items = result[result["abc_category"] == "B"]
    c_items = result[result["abc_category"] == "C"]

    top_a = a_items.head(3).apply(_display_name, axis=1).tolist()
    top_a_str = ", ".join(top_a)
    low_c = c_items.tail(3).apply(_display_name, axis=1).tolist()
    low_c_str = ", ".join(low_c) if low_c else "None"

    col1, col2, col3 = st.columns(3, gap="medium")

    with col1:
        st.markdown(
            f"""
            <div style="background:#fff5f5; border:2px solid #feb2b2; border-radius:14px; padding:1.2rem;">
                <div style="font-size:1.5rem">🔴</div>
                <div style="font-weight:800; color:#c53030; font-size:1rem; margin:.4rem 0">Class A - CRITICAL STOCK</div>
                <div style="font-size:.85rem; color:#744210; line-height:1.7">
                    <b>{len(a_items)} items</b> drive 80% of your revenue.<br>
                    ⚠️ <b>Never let these run out.</b><br><br>
                    <b>Actions:</b>
                    <ul style="margin:.3rem 0; padding-left:1.1rem">
                        <li>Review stock levels <b>weekly</b></li>
                        <li>Set tight reorder points</li>
                        <li>Keep safety stock buffer</li>
                        <li>Use demand forecasting for these</li>
                    </ul>
                    <b>Top items:</b> {top_a_str}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div style="background:#fffbeb; border:2px solid #fbd38d; border-radius:14px; padding:1.2rem;">
                <div style="font-size:1.5rem">🟡</div>
                <div style="font-weight:800; color:#b7791f; font-size:1rem; margin:.4rem 0">Class B - MONITOR REGULARLY</div>
                <div style="font-size:.85rem; color:#744210; line-height:1.7">
                    <b>{len(b_items)} items</b> contribute 15% of revenue.<br>
                    📋 <b>Review monthly.</b><br><br>
                    <b>Actions:</b>
                    <ul style="margin:.3rem 0; padding-left:1.1rem">
                        <li>Review stock levels <b>monthly</b></li>
                        <li>Standard reorder process</li>
                        <li>Watch for movement to Class A</li>
                        <li>Moderate safety stock</li>
                    </ul>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
            <div style="background:#ebf8ff; border:2px solid #90cdf4; border-radius:14px; padding:1.2rem;">
                <div style="font-size:1.5rem">🔵</div>
                <div style="font-weight:800; color:#2b6cb0; font-size:1rem; margin:.4rem 0">Class C - REDUCE INVESTMENT</div>
                <div style="font-size:.85rem; color:#2a4365; line-height:1.7">
                    <b>{len(c_items)} items</b> generate only 5% of revenue.<br>
                    💡 <b>Consider reducing stock.</b><br><br>
                    <b>Actions:</b>
                    <ul style="margin:.3rem 0; padding-left:1.1rem">
                        <li>Review stock <b>quarterly</b></li>
                        <li>Reduce order quantities</li>
                        <li>Consider discontinuing: {low_c_str}</li>
                        <li>Minimal safety stock needed</li>
                    </ul>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    st.warning(
        f"⚠️ **Restock Reminder:** Your top {min(3, len(a_items))} Class A items "
        f"({top_a_str}) account for the largest share of revenue - "
        "ensure these are **never below safety stock levels**."
    )
    if len(c_items) > 0:
        st.info(
            f"💡 **Optimisation Tip:** You have **{len(c_items)} Class C items** with low value. "
            "Consider reducing order frequency or discontinuing the lowest performers "
            "to free up warehouse space and cash."
        )
    st.success(
        "✅ **Next Step:** Upload a CSV with `date` and `sales` columns to unlock "
        "**demand forecasting** and get precise EOQ / Reorder Point calculations for each item."
    )


def _render_item_spotlight(result: pd.DataFrame) -> None:
    top5 = result.head(5).copy()
    total_value = result["annual_value"].sum()

    cols = st.columns(min(5, len(top5)))
    for col, (_, row) in zip(cols, top5.iterrows()):
        cat = row["abc_category"]
        color = {"A": "#c53030", "B": "#b7791f", "C": "#2b6cb0"}.get(cat, "#333")
        bg = {"A": "#fff5f5", "B": "#fffbeb", "C": "#ebf8ff"}.get(cat, "#fff")
        share = row["annual_value"] / total_value * 100
        name = str(row.get("item_name") or "").strip()
        label = f"<b>{name}</b><br><span style='font-size:.75rem;color:#94a3b8'>{row['item_id']}</span>" if name else f"<b>{row['item_id']}</b>"
        with col:
            st.markdown(
                f"""
                <div style="background:{bg}; border:1.5px solid {color}40;
                            border-radius:12px; padding:1rem; text-align:center;">
                    <div style="font-size:.7rem; font-weight:700; color:{color};
                                text-transform:uppercase; letter-spacing:.05em">Class {cat}</div>
                    <div style="font-size:.92rem; font-weight:800; color:#1e293b;
                                margin:.3rem 0; line-height:1.3">{label}</div>
                    <div style="font-size:.82rem; color:#64748b">
                        💰 ${row['annual_value']:,.0f}<br>
                        📦 {int(row['annual_demand']):,} units/yr<br>
                        🏷️ ${row['unit_cost']:.2f} / unit<br>
                        📊 {share:.1f}% of total value
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_category_cards(result: pd.DataFrame) -> None:
    cat_counts = result["abc_category"].value_counts()
    cat_values = result.groupby("abc_category")["annual_value"].sum()

    cols = st.columns(3)
    for col, cat in zip(cols, ["A", "B", "C"]):
        count = cat_counts.get(cat, 0)
        value = cat_values.get(cat, 0.0)
        with col:
            color = _CATEGORY_COLORS[cat]
            st.markdown(
                f"""
                <div style="
                    border-left: 6px solid {color};
                    padding: 12px 16px;
                    border-radius: 8px;
                    background: #f9f9f9;
                ">
                    <h2 style="color:{color}; margin:0">Class {cat}</h2>
                    <p style="margin:4px 0"><b>{count}</b> item(s)</p>
                    <p style="margin:4px 0; color:#555">
                        Annual value: <b>${value:,.0f}</b>
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_abc_bar(result: pd.DataFrame) -> None:
    top_n = min(50, len(result))
    plot_df = result.head(top_n).copy()
    plot_df["item_id"] = plot_df["item_id"].astype(str)

    fig = px.bar(
        plot_df,
        x="item_id",
        y="annual_value",
        color="abc_category",
        color_discrete_map=_CATEGORY_COLORS,
        labels={"item_id": "Item", "annual_value": "Annual Value ($)", "abc_category": "Class"},
        template="plotly_white",
        height=400,
    )
    fig.update_layout(
        xaxis_tickangle=-45,
        legend_title_text="ABC Class",
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_pareto_curve(result: pd.DataFrame) -> None:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=list(range(1, len(result) + 1)),
            y=result["cumulative_value_pct"] * 100,
            mode="lines+markers",
            name="Cumulative Value %",
            line=dict(color="#636EFA", width=2),
            marker=dict(color=[_CATEGORY_COLORS[c] for c in result["abc_category"]], size=6),
        )
    )

    for threshold, label in [(80, "A threshold (80%)"), (95, "B threshold (95%)")]:
        fig.add_shape(
            type="line",
            x0=0,
            x1=1,
            xref="paper",
            y0=threshold,
            y1=threshold,
            line=dict(dash="dash", color="grey", width=1.2),
        )
        fig.add_annotation(
            x=1,
            xref="paper",
            y=threshold,
            text=label,
            showarrow=False,
            xanchor="right",
            font=dict(color="grey", size=10),
        )

    fig.update_layout(
        xaxis_title="Number of Items",
        yaxis_title="Cumulative Value (%)",
        template="plotly_white",
        height=380,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_abc_table(result: pd.DataFrame) -> None:
    display = result.copy()
    if "item_name" in display.columns and display["item_name"].notna().any():
        display["item"] = display.apply(
            lambda r: f"{r['item_name']} ({r['item_id']})" if r.get("item_name") else r["item_id"],
            axis=1,
        )
        cols_order = ["item", "unit_cost", "annual_demand", "annual_value", "cumulative_value_pct", "abc_category"]
        display = display[[c for c in cols_order if c in display.columns]]
    else:
        display = display[[c for c in ["item_id", "unit_cost", "annual_demand", "annual_value", "cumulative_value_pct", "abc_category"] if c in display.columns]]

    display["annual_value"] = display["annual_value"].map("${:,.2f}".format)
    display["cumulative_value_pct"] = (display["cumulative_value_pct"] * 100).map("{:.1f}%".format)

    def _highlight(row):
        color_map = {"A": "#ffd6d6", "B": "#fff3cd", "C": "#d6e4ff"}
        bg = color_map.get(row["abc_category"], "white")
        return [f"background-color: {bg}" if col == "abc_category" else "" for col in row.index]

    st.dataframe(display.style.apply(_highlight, axis=1), use_container_width=True)
