"""
Full-page API Documentation view for SmartStock dashboard.
"""
from __future__ import annotations
import streamlit as st


def render_api_docs_view() -> None:
    st.markdown(
        """
        <div style="
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            border-radius: 18px; padding: 2rem 2.5rem; margin-bottom: 2rem;
        ">
            <div style="font-size:2rem; font-weight:800; color:#fff; margin-bottom:.3rem;">
                📡 API Documentation
            </div>
            <div style="color:#94a3b8; font-size:.95rem;">
                SmartStock runs a fully local FastAPI server on your machine.
                All endpoints are available at <code style="color:#a5b4fc;">http://localhost:8000</code>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Quick info row ────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3, gap="medium")
    for col, icon, label, val in [
        (c1, "🌐", "Base URL", "http://localhost:8000"),
        (c2, "📄", "Interactive Docs", "localhost:8000/docs"),
        (c3, "⚡", "Framework", "FastAPI + Uvicorn"),
    ]:
        with col:
            st.markdown(
                f"""
                <div style="background:#f8faff; border:1px solid #e0e7ff;
                            border-radius:12px; padding:1rem 1.2rem;">
                    <div style="font-size:1.4rem;">{icon}</div>
                    <div style="font-size:.78rem; color:#6366f1; font-weight:700;
                                text-transform:uppercase; letter-spacing:.05em; margin:.3rem 0 .1rem;">{label}</div>
                    <code style="font-size:.85rem; color:#1e293b;">{val}</code>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Endpoints ─────────────────────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:1.25rem; font-weight:800; color:#1e293b; margin-bottom:1rem;">🔌 Endpoints</div>',
        unsafe_allow_html=True,
    )

    _render_endpoint(
        method="POST",
        path="/api/forecast",
        tag="Forecasting",
        summary="Train forecasting models and return demand predictions",
        description=(
            "Trains Prophet and/or SARIMA on your historical daily sales records. "
            "Returns day-by-day future predictions with 80% confidence intervals, "
            "plus accuracy metrics evaluated on the held-out test split."
        ),
        request_example="""{
  "records": [
    {"date": "2024-01-01", "sales": 120},
    {"date": "2024-01-02", "sales": 135},
    ...
  ],
  "models": ["Prophet"],
  "forecast_horizon": 30,
  "test_split_frac": 0.2
}""",
        response_example="""{
  "predictions": {
    "Prophet": [
      {"date": "2025-01-02", "forecast": 143.2, "ci_lower": 118.5, "ci_upper": 168.0},
      ...
    ]
  },
  "metrics": {
    "Prophet": {"mae": 12.4, "rmse": 15.8, "mape": 8.3, "r2": 0.91}
  },
  "train_cutoff_date": "2024-10-14"
}""",
        fields=[
            ("records", "array", "Required", "List of {date, sales} objects. Minimum ~30 rows."),
            ("models", "array", "Required", 'List of model names. Options: "Prophet", "SARIMA"'),
            ("forecast_horizon", "integer", "Optional (30)", "Number of future days to predict. Range: 7–180."),
            ("test_split_frac", "float", "Optional (0.2)", "Fraction of data held out for accuracy testing. Range: 0.05–0.40."),
        ],
    )

    _render_endpoint(
        method="POST",
        path="/api/optimize",
        tag="Inventory Optimisation",
        summary="Compute EOQ, Safety Stock, and Reorder Point from a forecast",
        description=(
            "Takes the future-only predictions slice from /api/forecast and computes "
            "period-by-period inventory recommendations using the EOQ formula, "
            "Z-score based safety stock, and a demand-weighted reorder point. "
            "Pass your cost parameters to tune the output to your business."
        ),
        request_example="""{
  "forecast_records": [
    {"date": "2025-01-02", "forecast": 143.2, "ci_lower": 118.5, "ci_upper": 168.0},
    ...
  ],
  "ordering_cost": 50.0,
  "holding_cost": 0.5,
  "lead_time": 7,
  "service_level": 0.95,
  "batch_size": 1
}""",
        response_example="""{
  "results": [
    {
      "date": "2025-01-02",
      "expected_demand": 143.2,
      "eoq": 169,
      "safety_stock": 38,
      "reorder_point": 1039,
      "total_order_quantity": 207
    },
    ...
  ],
  "avg_eoq": 169,
  "avg_reorder_point": 1039,
  "avg_safety_stock": 38,
  "total_forecast_demand": 4360
}""",
        fields=[
            ("forecast_records", "array", "Required", "Future-only predictions from /api/forecast."),
            ("ordering_cost", "float", "Optional (50.0)", "Fixed cost per purchase order placed ($)."),
            ("holding_cost", "float", "Optional (0.5)", "Cost to hold one unit for one period ($/unit/day)."),
            ("lead_time", "integer", "Optional (7)", "Days between placing and receiving an order."),
            ("service_level", "float", "Optional (0.95)", "Target probability of not stocking out. E.g. 0.95 = 95%."),
            ("batch_size", "integer", "Optional (1)", "Minimum order multiple (e.g. 50 if supplier ships pallets of 50)."),
        ],
    )

    _render_endpoint(
        method="POST",
        path="/api/abc",
        tag="Inventory Classification",
        summary="Classify items into A / B / C categories using the Pareto principle",
        description=(
            "Calculates annual_value = unit_cost × annual_demand for each item, "
            "ranks them highest to lowest, and applies the 80/15/5 cumulative value split. "
            "Items in the top 80% of total value = Class A (critical). Next 15% = Class B. "
            "Bottom 5% = Class C (low priority)."
        ),
        request_example="""{
  "items": [
    {"item_id": "SKU-001", "item_name": "Cotton T-Shirt",
     "unit_cost": 12.5, "annual_demand": 5000},
    {"item_id": "SKU-002", "item_name": "Leather Boots",
     "unit_cost": 89.99, "annual_demand": 1200},
    ...
  ]
}""",
        response_example="""{
  "results": [
    {
      "item_id": "SKU-002",
      "item_name": "Leather Boots",
      "unit_cost": 89.99,
      "annual_demand": 1200,
      "annual_value": 107988.0,
      "cumulative_value_pct": 0.34,
      "abc_category": "A"
    },
    ...
  ],
  "summary": {
    "A": {"count": 4, "total_annual_value": 256000.0},
    "B": {"count": 6, "total_annual_value": 48000.0},
    "C": {"count": 10, "total_annual_value": 16000.0}
  },
  "total_annual_value": 320000.0
}""",
        fields=[
            ("items", "array", "Required", "List of items. Each must have item_id, unit_cost, annual_demand. item_name is optional."),
        ],
    )

    _render_endpoint(
        method="GET",
        path="/health",
        tag="Health",
        summary="Liveness probe — confirms the API server is running",
        description="Returns a simple JSON payload confirming the server is alive. Use this to check if the API is up before sending data.",
        request_example="# No request body needed\ncurl http://localhost:8000/health",
        response_example='{"status": "ok", "service": "SmartStock API"}',
        fields=[],
    )

    # ── Python client example ─────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:1.25rem; font-weight:800; color:#1e293b; margin-bottom:.8rem;">🐍 Python Client Example</div>',
        unsafe_allow_html=True,
    )
    st.code(
        """import requests

BASE = "http://localhost:8000"

# 1. Forecast
forecast_resp = requests.post(f"{BASE}/api/forecast", json={
    "records": [{"date": "2024-01-01", "sales": 120}, ...],
    "models": ["Prophet"],
    "forecast_horizon": 30,
    "test_split_frac": 0.2,
})
predictions = forecast_resp.json()["predictions"]["Prophet"]
future_only  = [p for p in predictions if p["date"] > "2024-10-14"]

# 2. Optimise
opt_resp = requests.post(f"{BASE}/api/optimize", json={
    "forecast_records": future_only,
    "ordering_cost": 50,
    "holding_cost": 0.5,
    "lead_time": 7,
    "service_level": 0.95,
})
print(opt_resp.json()["avg_eoq"])       # e.g. 169 units

# 3. ABC classification
abc_resp = requests.post(f"{BASE}/api/abc", json={
    "items": [
        {"item_id": "SKU-001", "unit_cost": 12.5, "annual_demand": 5000},
        {"item_id": "SKU-002", "unit_cost": 89.99, "annual_demand": 1200},
    ]
})
for item in abc_resp.json()["results"]:
    print(item["item_id"], item["abc_category"])
""",
        language="python",
    )


# ── Helper to render one endpoint block ──────────────────────────────────────

def _render_endpoint(method, path, tag, summary, description, request_example, response_example, fields):
    method_color = {"POST": "#34d399", "GET": "#60a5fa"}.get(method, "#a5b4fc")
    method_bg = {"POST": "#d1fae5", "GET": "#dbeafe"}.get(method, "#e0e7ff")
    method_text = {"POST": "#065f46", "GET": "#1e40af"}.get(method, "#3730a3")

    st.markdown(
        f"""
        <div style="border:1px solid #e2e8f0; border-radius:16px;
                    padding:1.4rem 1.6rem; margin-bottom:1.4rem;
                    background:#fff; box-shadow:0 2px 12px rgba(0,0,0,.04);">
            <div style="display:flex; align-items:center; gap:.7rem; margin-bottom:.5rem;">
                <span style="background:{method_bg}; color:{method_text}; font-weight:800;
                             font-size:.76rem; padding:.2rem .65rem; border-radius:6px;
                             letter-spacing:.05em;">{method}</span>
                <code style="font-size:1rem; font-weight:700; color:#1e293b;">{path}</code>
                <span style="margin-left:auto; font-size:.72rem; color:#94a3b8;
                             background:#f1f5f9; padding:.15rem .5rem; border-radius:20px;">{tag}</span>
            </div>
            <div style="font-weight:700; color:#1e293b; font-size:.95rem; margin-bottom:.3rem;">{summary}</div>
            <div style="font-size:.85rem; color:#64748b; line-height:1.7;">{description}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_req, col_res = st.columns(2, gap="medium")

    with col_req:
        if fields:
            st.markdown("**Request Parameters**")
            for fname, ftype, freq, fdesc in fields:
                req_color = "#dc2626" if freq == "Required" else "#64748b"
                st.markdown(
                    f"""
                    <div style="padding:.4rem 0; border-bottom:1px solid #f1f5f9;">
                        <code style="color:#4f46e5; font-size:.82rem;">{fname}</code>
                        <span style="font-size:.72rem; color:#94a3b8; margin:0 .4rem;">{ftype}</span>
                        <span style="font-size:.7rem; color:{req_color}; font-weight:600;">{freq}</span>
                        <div style="font-size:.78rem; color:#64748b; margin-top:.15rem;">{fdesc}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        st.markdown("**Request Body**")
        st.code(request_example, language="json")

    with col_res:
        st.markdown("**Response (200 OK)**")
        st.code(response_example, language="json")
