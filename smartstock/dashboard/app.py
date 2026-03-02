"""
SmartStock Dashboard — main entry point.

Run with:
    streamlit run smartstock/dashboard/app.py
"""

from __future__ import annotations

import sys
import os

# Ensure the project root (the folder containing the `smartstock` package)
# is on the path when the file is run directly via `streamlit run`.
# app.py lives at <root>/smartstock/dashboard/app.py → root is two levels up.
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st

# ── Page config must be the FIRST Streamlit call ─────────────────────────────
st.set_page_config(
    page_title="SmartStock — Inventory Intelligence",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/your-repo/smartstock",
        "About": "SmartStock — AI-powered inventory forecasting & optimisation.",
    },
)

# ── Imports ──────────────────────────────────────────────────────────────────
from smartstock.dashboard.components.abc_view import render_abc_view
from smartstock.dashboard.components.forecast_view import render_forecast_view
from smartstock.dashboard.components.optimization_view import render_optimization_view
from smartstock.dashboard.components.sidebar import render_sidebar


# ── Custom CSS ────────────────────────────────────────────────────────────────
def _inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        /* ── Global ── */
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        .block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; }

        /* ── Hero banner ── */
        .hero-banner {
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            border-radius: 18px;
            padding: 2.2rem 2.8rem;
            margin-bottom: 1.6rem;
            display: flex;
            align-items: center;
            gap: 1.4rem;
        }
        .hero-icon { font-size: 3.2rem; line-height: 1; }
        .hero-title {
            font-size: 2rem;
            font-weight: 800;
            color: #ffffff;
            margin: 0 0 .3rem 0;
            letter-spacing: -.5px;
        }
        .hero-title span {
            background: linear-gradient(90deg, #a78bfa, #60a5fa, #34d399);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .hero-sub { color: #94a3b8; font-size: .95rem; margin: 0; }

        /* ── Feature cards (welcome screen) ── */
        .feature-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 1.6rem 1.5rem;
            height: 100%;
            transition: box-shadow .2s, transform .2s;
        }
        .feature-card:hover { box-shadow: 0 8px 30px rgba(99,110,250,.12); transform: translateY(-3px); }
        .feature-card .fc-icon { font-size: 2rem; margin-bottom: .7rem; }
        .feature-card h3 { font-size: 1.05rem; font-weight: 700; color: #1e293b; margin: 0 0 .5rem 0; }
        .feature-card p  { font-size: .88rem; color: #64748b; margin: 0; line-height: 1.6; }
        .feature-card ul { font-size: .88rem; color: #64748b; margin: .4rem 0 0 0; padding-left: 1.1rem; line-height: 1.8; }

        /* ── Format badges ── */
        .fmt-badge {
            display: inline-block;
            background: #f1f5f9;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: .25rem .65rem;
            font-size: .78rem;
            font-weight: 600;
            color: #475569;
            margin-bottom: .6rem;
        }

        /* ── Section heading pill ── */
        .section-pill {
            display: inline-flex;
            align-items: center;
            gap: .4rem;
            background: linear-gradient(135deg, #eef2ff, #e0e7ff);
            border-radius: 999px;
            padding: .35rem 1rem;
            font-size: .82rem;
            font-weight: 700;
            color: #4338ca;
            letter-spacing: .02em;
            margin-bottom: 1rem;
        }

        /* ── Metric cards ── */
        [data-testid="metric-container"] {
            background: linear-gradient(135deg, #f8faff, #eef2ff);
            border: 1px solid #e0e7ff;
            border-radius: 14px;
            padding: 1rem 1.1rem !important;
            transition: box-shadow .2s;
        }
        [data-testid="metric-container"]:hover { box-shadow: 0 4px 18px rgba(99,110,250,.13); }
        [data-testid="metric-container"] label { font-size: .78rem !important; font-weight: 600 !important; color: #6366f1 !important; text-transform: uppercase; letter-spacing: .05em; }
        [data-testid="metric-container"] [data-testid="stMetricValue"] { font-size: 1.55rem !important; font-weight: 800 !important; color: #1e293b !important; }

        /* ── Tabs ── */
        [data-testid="stTabs"] [role="tablist"] { gap: .3rem; border-bottom: 2px solid #e2e8f0; padding-bottom: 0; }
        [data-testid="stTabs"] button {
            font-size: .92rem !important;
            font-weight: 600 !important;
            color: #64748b !important;
            border-radius: 10px 10px 0 0 !important;
            padding: .55rem 1.2rem !important;
            border: none !important;
            background: transparent !important;
        }
        [data-testid="stTabs"] button[aria-selected="true"] {
            color: #4f46e5 !important;
            background: #eef2ff !important;
            border-bottom: 3px solid #4f46e5 !important;
        }

        /* ── Sidebar ── */
        [data-testid="stSidebar"] { background: linear-gradient(180deg, #0f172a 0%, #1e1b4b 100%) !important; }
        [data-testid="stSidebar"] * { color: #e2e8f0 !important; }
        [data-testid="stSidebar"] .stSelectbox label,
        [data-testid="stSidebar"] .stSlider label,
        [data-testid="stSidebar"] .stCheckbox label,
        [data-testid="stSidebar"] .stNumberInput label { color: #a5b4fc !important; font-size: .82rem !important; font-weight: 600 !important; text-transform: uppercase; letter-spacing: .04em; }
        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
            background: rgba(255,255,255,.05) !important;
            border: 2px dashed rgba(165,180,252,.4) !important;
            border-radius: 12px !important;
        }
        [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.1) !important; }
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 { color: #ffffff !important; }
        [data-testid="stSidebar"] .stCaption { color: #94a3b8 !important; }

        /* ── Info / warning / error boxes ── */
        [data-testid="stAlert"] { border-radius: 12px !important; }

        /* ── Expander ── */
        [data-testid="stExpander"] { border-radius: 12px !important; border: 1px solid #e2e8f0 !important; }

        /* ── Divider ── */
        hr { border-color: #e2e8f0 !important; }

        /* ── Scrollbar ── */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #f1f5f9; }
        ::-webkit-scrollbar-thumb { background: #c7d2fe; border-radius: 99px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    _inject_css()

    # ── Hero banner ───────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="hero-banner">
            <div class="hero-icon">📦</div>
            <div>
                <p class="hero-title">Smart<span>Stock</span></p>
                <p class="hero-sub">
                    AI-powered demand forecasting · Inventory optimisation · ABC analysis
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Sidebar (returns config dict) ─────────────────────────────────────
    cfg = render_sidebar()

    # ── Guard: nothing uploaded yet ───────────────────────────────────────
    if cfg["df_raw"] is None:
        _render_welcome_screen()
        return

    if cfg.get("data_mode") == "unknown":
        st.error(
            "⚠️ CSV format not recognised. "
            "Please upload a file with columns:  \n"
            "`date, store, item, sales`  OR  `date, sales`  OR  "
            "`item_id, unit_cost, annual_demand`"
        )
        return

    # ── Main tabs ─────────────────────────────────────────────────────────
    mode = cfg.get("data_mode")

    if mode == "abc_only":
        # Fallback: item selector not yet chosen (shouldn't normally reach here)
        tab_abc, = st.tabs(["🏷️ ABC Analysis"])
        with tab_abc:
            render_abc_view(cfg)
    else:
        # abc_synthetic, multi_store, single_series — all get full 3-tab view
        tab_forecast, tab_opt, tab_abc = st.tabs(
            ["📈 Forecasting", "📦 Inventory Optimisation", "🏷️ ABC Analysis"]
        )

        with tab_forecast:
            render_forecast_view(cfg)

        with tab_opt:
            render_optimization_view(cfg)

        with tab_abc:
            render_abc_view(cfg)


# ── Welcome screen shown before any upload ───────────────────────────────────

def _render_welcome_screen() -> None:
    st.markdown(
        '<div class="section-pill">✨ &nbsp;Get Started — upload a CSV to begin</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        st.markdown(
            """
            <div class="feature-card">
                <div class="fc-icon">📈</div>
                <h3>Demand Forecasting</h3>
                <p>Train <strong>Prophet</strong> and / or <strong>SARIMA</strong> models
                on your historical sales data for accurate future demand predictions,
                complete with confidence bands and accuracy metrics (MAE, RMSE, MAPE, R²).</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            """
            <div class="feature-card">
                <div class="fc-icon">📦</div>
                <h3>Inventory Optimisation</h3>
                <p>Automatically calculates the three numbers every inventory manager needs:</p>
                <ul>
                    <li><strong>EOQ</strong> — exactly how much to order</li>
                    <li><strong>ROP</strong> — precisely when to reorder</li>
                    <li><strong>Safety Stock</strong> — your demand buffer</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            """
            <div class="feature-card">
                <div class="fc-icon">🏷️</div>
                <h3>ABC Analysis</h3>
                <p>Rank every product by annual value using the <strong>Pareto principle</strong>
                (80 / 15 / 5 split) so you can focus management effort on the items
                that generate the most revenue.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<div class="section-pill">📋 &nbsp;Accepted CSV Formats</div>',
        unsafe_allow_html=True,
    )

    fmt_col1, fmt_col2, fmt_col3 = st.columns(3, gap="medium")

    with fmt_col1:
        st.markdown('<div class="fmt-badge">📊 Multi-store sales</div>', unsafe_allow_html=True)
        st.dataframe(
            {"date": ["2024-01-01", "2024-01-02"], "store": [1, 1], "item": [10, 10], "sales": [45, 52]},
            hide_index=True, use_container_width=True,
        )
    with fmt_col2:
        st.markdown('<div class="fmt-badge">📉 Single-series sales</div>', unsafe_allow_html=True)
        st.dataframe(
            {"date": ["2024-01-01", "2024-01-02"], "sales": [45, 52]},
            hide_index=True, use_container_width=True,
        )
    with fmt_col3:
        st.markdown('<div class="fmt-badge">🏷️ ABC items</div>', unsafe_allow_html=True)
        st.dataframe(
            {"item_id": ["SKU-001", "SKU-002"], "unit_cost": [12.50, 3.99], "annual_demand": [5000, 22000]},
            hide_index=True, use_container_width=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.info("⬅️ Use the **sidebar** on the left to upload your CSV file and get started.")


if __name__ == "__main__":
    main()
