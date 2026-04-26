"""
Forecast view: Calls the SmartStock API (/api/forecast) and renders interactive
Plotly charts with confidence intervals, plus MAE/RMSE metric cards.
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from smartstock.dashboard.api_client import call_forecast

_MODEL_COLORS = {
    "Prophet": "#636EFA",
    "SARIMA": "#EF553B",
}


@st.cache_data(show_spinner=False, ttl=1800)
def _cached_call_forecast(
    item_key,
    records: tuple,
    models: tuple,
    forecast_horizon: int,
    test_split_frac: float,
):
    """Cache forecast API results by item + params. Same inputs = instant response."""
    cfg_proxy = {
        "models": list(models),
        "forecast_horizon": forecast_horizon,
        "test_split_frac": test_split_frac,
    }
    records_list = [{"date": d, "sales": s} for d, s in records]
    return call_forecast(cfg_proxy, records_list)


def render_forecast_view(cfg: Dict[str, Any]) -> None:
    st.markdown('<div class="section-pill">📈 &nbsp;Demand Forecasting</div>', unsafe_allow_html=True)

    if cfg.get("data_mode") == "abc_synthetic":
        item_id = cfg.get("abc_selected_item", "")
        item_name = cfg.get("abc_item_name", "")
        annual_demand = cfg.get("abc_annual_demand", 0)
        selected_category = cfg.get("abc_selected_category", "")
        display = f"**{item_name}** ({item_id})" if item_name and item_name != item_id else f"**{item_id}**"
        context_text = f" in {selected_category}" if selected_category else ""
        st.info(
            f"🤖 **Auto-generated forecast** for {display}{context_text} — "
            f"SmartStock synthesized 1 year of realistic daily sales history "
            f"from annual demand of **{int(annual_demand):,} units/year**. "
            f"Forecasting and optimization are now fully active."
        )

    series = _prepare_series(cfg)
    if series is None:
        st.info("Upload a valid CSV using the sidebar to get started.")
        return

    if series.empty:
        st.error("The selected series is empty after cleaning.")
        return

    n = len(series)
    test_n = max(1, int(n * cfg["test_split_frac"]))
    train_n = n - test_n

    if train_n < 14:
        st.error(
            f"Not enough training data ({train_n} rows). "
            "Reduce test split % or upload more data."
        )
        return

    st.caption(
        f"Training on **{train_n}** days  ·  Testing on **{n - train_n}** days  ·  "
        f"Forecasting **{cfg['forecast_horizon']}** days ahead"
    )

    records_df = series.reset_index()
    date_col = records_df.columns[0]
    records = tuple(
        (str(pd.to_datetime(row[date_col]).date()), float(row["sales"]))
        for _, row in records_df.iterrows()
    )

    with st.spinner("🧠 Training models via API — this may take a moment…"):
        response = _cached_call_forecast(
            item_key=cfg.get("abc_selected_item") or str(cfg.get("store_id", "")),
            records=records,
            models=tuple(cfg.get("models", ["Prophet"])),
            forecast_horizon=cfg["forecast_horizon"],
            test_split_frac=cfg["test_split_frac"],
        )

    if response is None:
        return

    raw_predictions = response.get("predictions", {})
    raw_metrics = response.get("metrics", {})
    train_cutoff_date = response.get("train_cutoff_date")

    if not raw_predictions:
        st.error("No predictions returned from the API.")
        return

    predictions: Dict[str, pd.DataFrame] = {}
    for model_name, points in raw_predictions.items():
        rows = []
        for p in points:
            rows.append({
                "date": pd.to_datetime(p["date"]),
                "forecast": p["forecast"],
                "ci_lower": p.get("ci_lower"),
                "ci_upper": p.get("ci_upper"),
            })
        pred_df = pd.DataFrame(rows).set_index("date")
        predictions[model_name] = pred_df

    train_cutoff_idx = train_n
    if train_cutoff_date:
        cutoff_ts = pd.Timestamp(train_cutoff_date)
        matches = [i for i, ts in enumerate(series.index) if ts <= cutoff_ts]
        if matches:
            train_cutoff_idx = matches[-1] + 1

    fig = _build_forecast_chart(series, predictions, train_cutoff_idx)
    st.plotly_chart(fig, use_container_width=True)

    if raw_metrics:
        st.markdown('<div class="section-pill">📊 &nbsp;Model Accuracy on Test Period</div>', unsafe_allow_html=True)
        _render_metric_cards(raw_metrics)
        _render_metrics_table(raw_metrics)

    with st.expander("🔍 Raw Forecast Data (Developer View)", expanded=False):
        for model_name, pred_df in predictions.items():
            st.markdown(f"**{model_name}**")
            st.dataframe(pred_df.tail(cfg["forecast_horizon"] + 5), use_container_width=True)

    st.session_state["train_series"] = series.iloc[:train_cutoff_idx]
    st.session_state["test_series"] = series.iloc[train_cutoff_idx:]
    st.session_state["predictions"] = predictions
    st.session_state["raw_predictions"] = raw_predictions
    st.session_state["train_cutoff_date"] = train_cutoff_date


def _prepare_series(cfg: Dict[str, Any]) -> pd.DataFrame | None:
    from smartstock.data.cleaner import clean_series
    from smartstock.data.loader import filter_series

    mode = cfg.get("data_mode")
    df_raw = cfg.get("df_raw")

    if mode is None:
        return None

    if mode == "abc_synthetic":
        annual_demand = cfg.get("abc_annual_demand")
        item_id = cfg.get("abc_selected_item", "item")
        if annual_demand is None:
            return None
        return _generate_series_from_annual_demand(annual_demand, item_id)

    if df_raw is None:
        return None

    if mode == "multi_store":
        store_id = cfg.get("store_id")
        item_id = cfg.get("item_id")
        if store_id is None or item_id is None:
            return None
        series = filter_series(df_raw, store_id, item_id)
    elif mode == "single_series":
        series = df_raw[["sales"]].copy() if "sales" in df_raw.columns else None
        if series is None:
            return None
    else:
        return None

    try:
        return clean_series(series)
    except AssertionError as e:
        st.error(f"Data cleaning failed: {e}")
        return None


@st.cache_data(show_spinner=False, ttl=3600)
def _generate_series_from_annual_demand(annual_demand: float, item_id: str) -> pd.DataFrame:
    rng = np.random.default_rng(seed=abs(hash(item_id)) % (2**31))
    # 2 full years: gives Prophet enough repetitions of yearly + weekly cycles
    # to learn seasonality properly and generalise to the held-out test split
    n_days = 730
    dates = pd.date_range(end=pd.Timestamp(2025, 1, 1), periods=n_days, freq="D")

    base_daily = annual_demand / 365.0
    day_idx = np.arange(n_days, dtype=float)

    # Weekly seasonality: weekdays +20%, weekends -30%
    dow = np.array([d.dayofweek for d in dates], dtype=float)  # 0=Mon, 6=Sun
    weekly = np.where(dow < 5, 1.20, 0.70)

    # Monthly seasonality: smooth sine wave, ±12% (peaks mid-month)
    monthly = 1.0 + 0.12 * np.sin(2 * np.pi * day_idx / 30.44)

    # Yearly seasonality: ±18% (peaks Nov-Dec, troughs Jan-Feb)
    yearly = 1.0 + 0.18 * np.sin(2 * np.pi * (day_idx / 365.25) - np.pi / 2)

    # Gentle upward trend: +8% over 2 years
    trend = 1.0 + 0.08 * np.linspace(0, 1, n_days)

    # Low noise: ±8% std, clipped to ±20% — enough variation without hiding signal
    noise = rng.normal(loc=1.0, scale=0.08, size=n_days)
    noise = np.clip(noise, 0.80, 1.20)

    sales = base_daily * weekly * monthly * yearly * trend * noise
    sales = np.maximum(0, np.round(sales, 1))

    series = pd.DataFrame({"sales": sales}, index=dates)
    series.index.name = "date"
    return series


def _build_forecast_chart(
    full_series: pd.DataFrame,
    predictions: Dict[str, pd.DataFrame],
    train_cutoff_idx: int,
) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=full_series.index,
            y=full_series["sales"],
            name="Actual Sales",
            line=dict(color="#2CA02C", width=2),
            mode="lines",
        )
    )

    if train_cutoff_idx < len(full_series):
        split_date = full_series.index[train_cutoff_idx].isoformat()
        fig.add_shape(
            type="line",
            x0=split_date,
            x1=split_date,
            y0=0,
            y1=1,
            xref="x",
            yref="paper",
            line=dict(width=1.5, dash="dash", color="grey"),
        )
        fig.add_annotation(
            x=split_date,
            xref="x",
            y=1,
            yref="paper",
            text="Train | Test",
            showarrow=False,
            xanchor="left",
            font=dict(color="grey", size=11),
        )

    for model_name, pred_df in predictions.items():
        color = _MODEL_COLORS.get(model_name, "#7F7F7F")

        future_mask = pred_df.index > full_series.index[-1]
        past_mask = ~future_mask

        if past_mask.any():
            fig.add_trace(
                go.Scatter(
                    x=pred_df.index[past_mask],
                    y=pred_df.loc[past_mask, "forecast"],
                    name=f"{model_name} (fitted)",
                    line=dict(color=color, width=1, dash="dot"),
                    showlegend=True,
                    opacity=0.6,
                )
            )

        if future_mask.any():
            y_future = pred_df.loc[future_mask, "forecast"]
            fig.add_trace(
                go.Scatter(
                    x=pred_df.index[future_mask],
                    y=y_future,
                    name=f"{model_name} (forecast)",
                    line=dict(color=color, width=2.5),
                )
            )

            if "ci_upper" in pred_df.columns and "ci_lower" in pred_df.columns:
                ci_frame = pred_df.loc[future_mask, ["ci_upper", "ci_lower"]].copy()
                y_future_vals = np.asarray(y_future, dtype=float)
                ci_upper_vals = np.asarray(pd.to_numeric(ci_frame["ci_upper"], errors="coerce"), dtype=float)
                ci_lower_vals = np.asarray(pd.to_numeric(ci_frame["ci_lower"], errors="coerce"), dtype=float)

                ci_upper_vals = np.where(np.isnan(ci_upper_vals), y_future_vals, ci_upper_vals)
                ci_lower_vals = np.where(np.isnan(ci_lower_vals), y_future_vals, ci_lower_vals)
                x_future = pred_df.index[future_mask]

                fig.add_trace(
                    go.Scatter(
                        x=list(x_future) + list(x_future[::-1]),
                        y=list(ci_upper_vals) + list(ci_lower_vals[::-1]),
                        fill="toself",
                        fillcolor=color.replace(")", ", 0.15)").replace("rgb", "rgba")
                        if color.startswith("rgb")
                        else color + "26",
                        line=dict(color="rgba(255,255,255,0)"),
                        showlegend=True,
                        name=f"{model_name} CI",
                        hoverinfo="skip",
                    )
                )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Units Sold",
        template="plotly_white",
        height=520,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig


def _render_metric_cards(raw_metrics: Dict[str, dict]) -> None:
    cols = st.columns(len(raw_metrics))
    for col, (model_name, m) in zip(cols, raw_metrics.items()):
        with col:
            st.markdown(f"**{model_name}**")
            m1, m2 = st.columns(2)
            m1.metric("MAE", f"{m.get('mae') or 0:.2f}" if m.get("mae") is not None else "N/A")
            m2.metric("RMSE", f"{m.get('rmse') or 0:.2f}" if m.get("rmse") is not None else "N/A")
            m3, m4 = st.columns(2)
            m3.metric("MAPE", f"{m.get('mape') or 0:.1f}%" if m.get("mape") is not None else "N/A")
            m4.metric("R²", f"{m.get('r2') or 0:.3f}" if m.get("r2") is not None else "N/A")


def _render_metrics_table(raw_metrics: Dict[str, dict]) -> None:
    with st.expander("Full metrics table", expanded=False):
        rows = []
        for model_name, m in raw_metrics.items():
            rows.append(
                {
                    "model": model_name,
                    "mae": f"{m['mae']:.4f}" if m.get("mae") is not None else "N/A",
                    "rmse": f"{m['rmse']:.4f}" if m.get("rmse") is not None else "N/A",
                    "mape": f"{m['mape']:.4f}" if m.get("mape") is not None else "N/A",
                    "r2": f"{m['r2']:.4f}" if m.get("r2") is not None else "N/A",
                }
            )
        display = pd.DataFrame(rows).set_index("model")
        st.dataframe(display, use_container_width=True)
