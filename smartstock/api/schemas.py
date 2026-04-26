"""
Pydantic v2 request / response schemas for the SmartStock FastAPI layer.
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class SalesRecord(BaseModel):
    """A single date to sales observation."""

    date: str = Field(..., description="ISO date string, e.g. '2024-01-01'")
    sales: float = Field(..., ge=0, description="Non-negative sales value")


class ForecastRequest(BaseModel):
    """Payload sent by Streamlit to POST /api/forecast."""

    records: List[SalesRecord] = Field(
        ..., min_length=14, description="Historical sales records (>=14 rows)"
    )
    models: List[Literal["Prophet", "SARIMA"]] = Field(
        default=["Prophet"], description="Which forecasting models to run"
    )
    forecast_horizon: int = Field(
        default=30, ge=1, le=365, description="Days ahead to forecast"
    )
    test_split_frac: float = Field(
        default=0.2, gt=0.0, lt=1.0, description="Fraction of data held out for testing"
    )

    @model_validator(mode="after")
    def at_least_one_model(self) -> "ForecastRequest":
        if not self.models:
            raise ValueError("At least one model must be specified")
        return self


class ForecastPoint(BaseModel):
    """A single row of forecast output."""

    date: str
    forecast: float
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None


class ModelMetrics(BaseModel):
    """Accuracy metrics for a single model."""

    mae: Optional[float] = None
    rmse: Optional[float] = None
    mape: Optional[float] = None
    r2: Optional[float] = None
    n_samples: Optional[int] = None


class ForecastResponse(BaseModel):
    """Response from POST /api/forecast."""

    predictions: Dict[str, List[ForecastPoint]] = Field(
        description="Model name to list of forecast points (history + future)"
    )
    metrics: Dict[str, ModelMetrics] = Field(
        default_factory=dict,
        description="Model name to accuracy metrics on the test split",
    )
    train_cutoff_date: Optional[str] = Field(
        default=None, description="Last date of the training split"
    )


class OptimizeRequest(BaseModel):
    """Payload sent by Streamlit to POST /api/optimize."""

    forecast_records: List[ForecastPoint] = Field(
        ..., min_length=1, description="Future forecast rows from /api/forecast"
    )
    ordering_cost: float = Field(default=50.0, ge=0.0)
    holding_cost: float = Field(default=0.5, gt=0.0)
    lead_time: int = Field(default=7, ge=0)
    service_level: float = Field(default=0.95, gt=0.0, lt=1.0)
    batch_size: int = Field(default=1, ge=1)


class OptimizePoint(BaseModel):
    """A single row of EOQ optimization output."""

    date: str
    expected_demand: float
    eoq: int
    safety_stock: int
    reorder_point: int
    total_order_quantity: int


class OptimizeResponse(BaseModel):
    """Response from POST /api/optimize."""

    results: List[OptimizePoint]
    avg_eoq: int
    avg_reorder_point: int
    avg_safety_stock: int
    total_forecast_demand: int


class ABCRecord(BaseModel):
    """A single inventory item for ABC classification."""

    item_id: str = Field(..., description="Unique item identifier")
    item_name: Optional[str] = Field(None, description="Human-readable item name")
    unit_cost: float = Field(..., gt=0, description="Cost per unit")
    annual_demand: float = Field(..., ge=0, description="Annual demand in units")


class ABCRequest(BaseModel):
    """Payload sent by Streamlit to POST /api/abc."""

    items: List[ABCRecord] = Field(
        ..., min_length=1, description="List of inventory items to classify"
    )


class ABCResultRow(BaseModel):
    """A single row of ABC classification output."""

    item_id: str
    item_name: Optional[str] = None
    unit_cost: float
    annual_demand: float
    annual_value: float
    cumulative_value_pct: float
    abc_category: Literal["A", "B", "C"]


class ABCSummary(BaseModel):
    """Counts and total annual value per ABC category."""

    count: int
    total_annual_value: float


class ABCResponse(BaseModel):
    """Response from POST /api/abc."""

    results: List[ABCResultRow]
    summary: Dict[str, ABCSummary] = Field(description="Keys are 'A', 'B', 'C'")
    total_annual_value: float
