"""
POST /api/forecast - train models and return predictions + metrics.
"""

from __future__ import annotations

import warnings
from typing import Dict, List

import pandas as pd
from fastapi import APIRouter, HTTPException

from smartstock.api.schemas import (
    ForecastPoint,
    ForecastRequest,
    ForecastResponse,
    ModelMetrics,
)
from smartstock.forecasting.forecast_manager import ForecastManager
from smartstock.forecasting.prophet_forecaster import ProphetForecaster
from smartstock.forecasting.sarima_forecaster import SARIMAForecaster

router = APIRouter()


def _records_to_df(records) -> pd.DataFrame:
    """Convert list[SalesRecord] to DatetimeIndex DataFrame with sales column."""
    df = pd.DataFrame([{"date": r.date, "sales": r.sales} for r in records])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").set_index("date")
    return df


def _df_to_forecast_points(pred_df: pd.DataFrame) -> List[ForecastPoint]:
    """Convert a model prediction DataFrame to a list of ForecastPoint."""
    points: List[ForecastPoint] = []
    for ts, row in pred_df.iterrows():
        points.append(
            ForecastPoint(
                date=str(ts.date()),
                forecast=float(row["forecast"]),
                ci_lower=float(row["ci_lower"])
                if "ci_lower" in row and pd.notna(row["ci_lower"])
                else None,
                ci_upper=float(row["ci_upper"])
                if "ci_upper" in row and pd.notna(row["ci_upper"])
                else None,
            )
        )
    return points


def _build_manager(model_names: List[str]) -> ForecastManager:
    """Instantiate a ForecastManager and register requested models."""
    manager = ForecastManager()
    for name in model_names:
        if name == "Prophet":
            manager.add_model("Prophet", ProphetForecaster())
        elif name == "SARIMA":
            manager.add_model("SARIMA", SARIMAForecaster())
    return manager


@router.post("/forecast", response_model=ForecastResponse, summary="Run demand forecasting")
def forecast(req: ForecastRequest) -> ForecastResponse:
    """Train selected models and return history+future predictions and optional metrics."""
    series = _records_to_df(req.records)
    n = len(series)
    test_n = max(1, int(n * req.test_split_frac))
    train_n = n - test_n

    if train_n < 14:
        raise HTTPException(
            status_code=422,
            detail=f"Not enough training data ({train_n} rows after split). "
            "Reduce test_split_frac or supply more history.",
        )

    train = series.iloc[:train_n]
    test = series.iloc[train_n:]
    train_cutoff = str(train.index[-1].date())

    manager = _build_manager(req.models)
    if not manager.models:
        raise HTTPException(status_code=422, detail="No valid models specified.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            manager.train_all(train)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Training failed: {exc}") from exc

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            raw_predictions = manager.predict_all(
                periods=req.forecast_horizon, include_history=True
            )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}") from exc

    predictions: Dict[str, List[ForecastPoint]] = {
        name: _df_to_forecast_points(pred_df)
        for name, pred_df in raw_predictions.items()
    }

    metrics: Dict[str, ModelMetrics] = {}
    if not test.empty:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                metrics_df = manager.compare_models(test)
            for model_name, row in metrics_df.iterrows():
                metrics[model_name] = ModelMetrics(
                    mae=_safe_float(row.get("mae")),
                    rmse=_safe_float(row.get("rmse")),
                    mape=_safe_float(row.get("mape")),
                    r2=_safe_float(row.get("r2")),
                    n_samples=int(row.get("n_samples", 0)),
                )
        except Exception:
            pass

    return ForecastResponse(
        predictions=predictions,
        metrics=metrics,
        train_cutoff_date=train_cutoff,
    )


def _safe_float(val) -> float | None:
    """Return float or None for NaN and None values."""
    import math

    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None
