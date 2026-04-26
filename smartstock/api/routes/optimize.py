"""
POST /api/optimize - run EOQ / safety-stock / ROP calculation on a forecast.
"""

from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, HTTPException

from smartstock.api.schemas import OptimizePoint, OptimizeRequest, OptimizeResponse
from smartstock.optimization.eoq_calculator import EOQCalculator

router = APIRouter()


@router.post("/optimize", response_model=OptimizeResponse, summary="Run inventory optimization")
def optimize(req: OptimizeRequest) -> OptimizeResponse:
    """Compute period-wise EOQ, safety stock, and reorder point from forecast rows."""
    dates = pd.to_datetime([r.date for r in req.forecast_records])
    forecast_values = [r.forecast for r in req.forecast_records]
    forecast_series = pd.Series(forecast_values, index=dates, name="forecast")

    uncertainty_series: pd.Series | None = None
    has_ci = all(
        r.ci_upper is not None and r.ci_lower is not None for r in req.forecast_records
    )
    if has_ci:
        uncertainty_values = [
            (r.ci_upper - r.ci_lower) / 2 for r in req.forecast_records  # type: ignore[operator]
        ]
        uncertainty_series = pd.Series(uncertainty_values, index=dates)

    calc = EOQCalculator()
    try:
        result_df = calc.calculate(
            forecast_series=forecast_series,
            ordering_cost=req.ordering_cost,
            holding_cost_per_period=req.holding_cost,
            lead_time_periods=req.lead_time,
            uncertainty_series=uncertainty_series,
            batch_size=req.batch_size,
            service_level=req.service_level,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {exc}") from exc

    results = [
        OptimizePoint(
            date=str(idx.date()),
            expected_demand=float(row["expected_demand"]),
            eoq=int(row["eoq"]),
            safety_stock=int(row["safety_stock"]),
            reorder_point=int(row["reorder_point"]),
            total_order_quantity=int(row["total_order_quantity"]),
        )
        for idx, row in result_df.iterrows()
    ]

    return OptimizeResponse(
        results=results,
        avg_eoq=int(result_df["eoq"].mean()),
        avg_reorder_point=int(result_df["reorder_point"].mean()),
        avg_safety_stock=int(result_df["safety_stock"].mean()),
        total_forecast_demand=int(result_df["expected_demand"].sum()),
    )
