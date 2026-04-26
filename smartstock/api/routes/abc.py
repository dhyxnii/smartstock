"""
POST /api/abc - run ABC analysis (Pareto classification) on items.
"""

from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, HTTPException

from smartstock.api.schemas import (
    ABCRequest,
    ABCResponse,
    ABCResultRow,
    ABCSummary,
)
from smartstock.optimization.abc_analyzer import ABCAnalyzer

router = APIRouter()


@router.post("/abc", response_model=ABCResponse, summary="Run ABC inventory classification")
def abc_analysis(req: ABCRequest) -> ABCResponse:
    """Classify inventory items into A/B/C using Pareto cumulative value buckets."""
    records = [r.model_dump() for r in req.items]
    df = pd.DataFrame(records)
    name_map = {r["item_id"]: r.get("item_name") for r in records}

    analyzer = ABCAnalyzer()
    try:
        result_df = analyzer.analyze(df)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ABC analysis failed: {exc}") from exc

    results = [
        ABCResultRow(
            item_id=str(row["item_id"]),
            item_name=name_map.get(str(row["item_id"])),
            unit_cost=float(row["unit_cost"]),
            annual_demand=float(row["annual_demand"]),
            annual_value=float(row["annual_value"]),
            cumulative_value_pct=float(row["cumulative_value_pct"]),
            abc_category=row["abc_category"],
        )
        for _, row in result_df.iterrows()
    ]

    summary: dict[str, ABCSummary] = {}
    for cat in ("A", "B", "C"):
        cat_df = result_df[result_df["abc_category"] == cat]
        summary[cat] = ABCSummary(
            count=int(len(cat_df)),
            total_annual_value=float(cat_df["annual_value"].sum()),
        )

    return ABCResponse(
        results=results,
        summary=summary,
        total_annual_value=float(result_df["annual_value"].sum()),
    )
