"""
Forecast view: Trains models via ForecastManager and renders interactive
Plotly charts with confidence intervals, plus MAE/RMSE metric cards.
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from smartstock.data.cleaner import clean_series
from smartstock.data.loader import filter_series
from smartstock.forecasting.forecast_manager import ForecastManager
from smartstock.forecasting.prophet_forecaster import ProphetForecaster
from smartstock.forecasting.sarima_forecaster import SARIMAForecaster


_MODEL_COLORS = {
    "Prophet": "#636EFA",
    "SARIMA": "#EF553B",
}


def render_forecast_view(cfg: Dict[str, Any]) -> None:
    """
    Entry-point called by app.py for the Forecasting tab.

    Parameters
    ----------
    cfg : dict returned by sidebar.render_sidebar()
    """
    st.markdown('<div class="section-pill">📈 &nbsp;Demand Forecasting</div>', unsafe_allow_html=True)

    if cfg.get("data_mode") == "abc_synthetic":
        item_id = cfg.get("abc_selected_item", "")
        annual_demand = cfg.get("abc_annual_demand", 0)
        st.info(
            f"🤖 **Auto-generated forecast** for **{item_id}** — "
            f"SmartStock synthesised 2 years of realistic daily sales history "
            f"from its annual demand of **{int(annual_demand):,} units/year**. "
            f"Forecasting and optimisation are now fully active."
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

    train = series.iloc[:train_n]
    test = series.iloc[train_n:]

    st.caption(
        f"Training on **{train_n}** days  ·  Testing on **{test_n}** days  ·  "
        f"Forecasting **{cfg['forecast_horizon']}** days ahead"
    )

    with st.spinner("🧠 Training models — this may take a moment…"):
        manager, errors = _build_and_train(cfg["models"], train)

    if errors:
        for e in errors:
            st.warning(e)

    if not manager.models:
        st.error("All models failed to train. Check warnings above.")
        return

    # ── Predictions ───────────────────────────────────────────────────────
    with st.spinner("Generating forecasts…"):
        predictions = manager.predict_all(
            periods=cfg["forecast_horizon"], include_history=True
        )

    if not predictions:
        st.error("No predictions returned.")
        return

    # ── Chart ─────────────────────────────────────────────────────────────
    fig = _build_forecast_chart(series, predictions, train_n)
    st.plotly_chart(fig, use_container_width=True)

    # ── Metrics ──────────────────────────────────────────────────────────
    if not test.empty:
        st.markdown('<div class="section-pill">📊 &nbsp;Model Accuracy on Test Period</div>', unsafe_allow_html=True)
        try:
            metrics_df = manager.compare_models(test)
            _render_metric_cards(metrics_df)
            _render_metrics_table(metrics_df)
        except Exception as exc:
            st.warning(f"Could not compute metrics: {exc}")

    # ── Raw JSON toggle ──────────────────────────────────────────────────
    with st.expander("🔍 Raw Forecast Data (Developer View)", expanded=False):
        for model_name, pred_df in predictions.items():
            st.markdown(f"**{model_name}**")
            st.dataframe(pred_df.tail(cfg["forecast_horizon"] + 5), use_container_width=True)

    # Expose series for other tabs via session state
    st.session_state["train_series"] = train
    st.session_state["test_series"] = test
    st.session_state["predictions"] = predictions
    st.session_state["manager"] = manager


# ── Helpers ──────────────────────────────────────────────────────────────────


def _prepare_series(cfg: Dict[str, Any]) -> pd.DataFrame | None:
    """Return a cleaned sales DataFrame with DatetimeIndex & 'sales' column."""
    mode = cfg.get("data_mode")
    df_raw = cfg.get("df_raw")

    if mode is None:
        return None

    # ── Auto-generate from ABC annual_demand ─────────────────────────────
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


def _generate_series_from_annual_demand(
    annual_demand: float, item_id: str
) -> pd.DataFrame:
    """
    Synthesise 2 years of daily sales history from an annual demand figure.
    Adds realistic weekly seasonality, noise, and a slight growth trend.
    """
    rng = np.random.default_rng(seed=abs(hash(item_id)) % (2**31))
    n_days = 730
    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=n_days, freq="D")

    base_daily = annual_demand / 365.0

    # Weekly seasonality: weekdays slightly higher than weekends (retail pattern)
    day_of_week = np.array([d.dayofweek for d in dates], dtype=float)
    seasonality = np.where(day_of_week < 5, 1.10, 0.75)  # weekday vs weekend

    # Slight upward growth trend (+5% over 2 years)
    trend = 1.0 + 0.05 * np.linspace(0, 1, n_days)

    # Random noise (±25%)
    noise = rng.normal(loc=1.0, scale=0.15, size=n_days)
    noise = np.clip(noise, 0.5, 1.8)

    sales = base_daily * seasonality * trend * noise
    sales = np.maximum(0, np.round(sales, 1))

    series = pd.DataFrame({"sales": sales}, index=dates)
    series.index.name = "date"
    return series


def _build_and_train(
    model_names: list[str], train: pd.DataFrame
) -> tuple[ForecastManager, list[str]]:
    """Instantiate, register and train all requested models."""
    manager = ForecastManager()
    errors: list[str] = []

    for name in model_names:
        try:
            if name == "Prophet":
                model = ProphetForecaster()
            elif name == "SARIMA":
                model = SARIMAForecaster()
            else:
                errors.append(f"Unknown model: {name}")
                continue
            manager.add_model(name, model)
        except Exception as exc:
            errors.append(f"Could not add {name}: {exc}")

    try:
        manager.train_all(train)
    except Exception as exc:
        errors.append(f"Training failed: {exc}")

    return manager, errors


def _build_forecast_chart(
    full_series: pd.DataFrame,
    predictions: Dict[str, pd.DataFrame],
    train_cutoff_idx: int,
) -> go.Figure:
    """Construct the interactive Plotly forecast chart."""
    fig = go.Figure()

    # ── Actual history ──
    fig.add_trace(
        go.Scatter(
            x=full_series.index,
            y=full_series["sales"],
            name="Actual Sales",
            line=dict(color="#2CA02C", width=2),
            mode="lines",
        )
    )

    # ── Train / test split line ──
    # add_vline with annotation crashes in plotly 6.x (tries to sum x-axis values).
    # Use add_shape (xref="x") + add_annotation instead.
    if train_cutoff_idx < len(full_series):
        split_date = full_series.index[train_cutoff_idx].isoformat()
        fig.add_shape(
            type="line",
            x0=split_date, x1=split_date,
            y0=0, y1=1,
            xref="x", yref="paper",
            line=dict(width=1.5, dash="dash", color="grey"),
        )
        fig.add_annotation(
            x=split_date, xref="x",
            y=1, yref="paper",
            text="Train | Test",
            showarrow=False,
            xanchor="left",
            font=dict(color="grey", size=11),
        )

    # ── Model forecasts ──
    for model_name, pred_df in predictions.items():
        color = _MODEL_COLORS.get(model_name, "#7F7F7F")

        # Future-only portion of forecast line
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

            # Confidence bands
            if "ci_upper" in pred_df.columns and "ci_lower" in pred_df.columns:
                ci_upper = pred_df.loc[future_mask, "ci_upper"].fillna(y_future)
                ci_lower = pred_df.loc[future_mask, "ci_lower"].fillna(y_future)

                fig.add_trace(
                    go.Scatter(
                        x=pd.concat(
                            [
                                pd.Series(pred_df.index[future_mask]),
                                pd.Series(pred_df.index[future_mask][::-1]),
                            ]
                        ),
                        y=pd.concat([ci_upper, ci_lower.iloc[::-1]]),
                        fill="toself",
                        fillcolor=color.replace(")", ", 0.15)").replace("rgb", "rgba")
                        if color.startswith("rgb")
                        else color + "26",  # ~15% opacity hex
                        line=dict(color="rgba(255,255,255,0)"),
                        showlegend=True,
                        name=f"{model_name} CI",
                        hoverinfo="skip",
                    )
                )

    fig.update_layout(
        title="Sales History & Demand Forecast",
        xaxis_title="Date",
        yaxis_title="Units Sold",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        height=480,
    )
    return fig


def _render_metric_cards(metrics_df: pd.DataFrame) -> None:
    """Render one column of KPI cards per model."""
    cols = st.columns(len(metrics_df))
    for col, (model_name, row) in zip(cols, metrics_df.iterrows()):
        with col:
            st.markdown(f"**{model_name}**")
            m1, m2 = st.columns(2)
            m1.metric("MAE", f"{row.get('mae', float('nan')):.2f}")
            m2.metric("RMSE", f"{row.get('rmse', float('nan')):.2f}")
            m3, m4 = st.columns(2)
            m3.metric("MAPE", f"{row.get('mape', float('nan')):.1f}%")
            m4.metric("R²", f"{row.get('r2', float('nan')):.3f}")


def _render_metrics_table(metrics_df: pd.DataFrame) -> None:
    """Expandable table showing all metrics."""
    with st.expander("Full metrics table", expanded=False):
        display = metrics_df.copy()
        for col in ["mae", "rmse", "mape", "r2"]:
            if col in display.columns:
                display[col] = display[col].map(lambda v: f"{v:.4f}")
        st.dataframe(display, use_container_width=True)
