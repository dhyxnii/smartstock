"""
SmartStock API client for the Streamlit dashboard.

Streamlit components should call this module instead of importing model classes directly.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

import httpx
import streamlit as st

_API_BASE_URL = os.environ.get("SMARTSTOCK_API_URL", "http://localhost:8000")
_TIMEOUT = 120.0


def call_forecast(cfg: Dict[str, Any], series_records: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    payload = {
        "records": series_records,
        "models": cfg.get("models", ["Prophet"]),
        "forecast_horizon": cfg.get("forecast_horizon", 30),
        "test_split_frac": cfg.get("test_split_frac", 0.2),
    }
    return _post("/api/forecast", payload)


def call_optimize(cfg: Dict[str, Any], forecast_records: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    payload = {
        "forecast_records": forecast_records,
        "ordering_cost": cfg.get("ordering_cost", 50.0),
        "holding_cost": cfg.get("holding_cost", 0.5),
        "lead_time": cfg.get("lead_time", 7),
        "service_level": cfg.get("service_level", 0.95),
        "batch_size": cfg.get("batch_size", 1),
    }
    return _post("/api/optimize", payload)


def call_abc(items: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    payload = {"items": items}
    return _post("/api/abc", payload)


def _post(path: str, payload: dict) -> Dict[str, Any] | None:
    url = f"{_API_BASE_URL}{path}"
    try:
        response = httpx.post(url, json=payload, timeout=_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except httpx.ConnectError:
        st.error(
            f"Unable to reach the SmartStock API at `{_API_BASE_URL}`.\n"
            "Start the API server first (for example: `uvicorn smartstock.api.main:app --reload --port 8000`)."
        )
        return None
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text
        try:
            detail = exc.response.json().get("detail", exc.response.text)
        except Exception:
            pass
        st.error(f"API error ({exc.response.status_code}): {detail}")
        return None
    except Exception as exc:
        st.error(f"Unexpected API error: {exc}")
        return None
