"""
Sidebar component: Configuration panel for the SmartStock dashboard.

Handles file upload, series selection, model selection and parameter inputs.
Returns a structured config dict consumed by the main app.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st


def render_sidebar() -> Dict[str, Any]:
    """
    Render the full sidebar and return user configuration.

    Returns
    -------
    dict with keys:
        uploaded_file   – raw UploadedFile or None
        df_raw          – parsed DataFrame or None
        data_mode       – "multi_store" | "single_series" | "abc_only"
        store_id        – int | None
        item_id         – int | None
        models          – list[str]  e.g. ["Prophet", "SARIMA"]
        forecast_horizon– int
        test_split_frac – float  (fraction used for test)
        ordering_cost   – float
        holding_cost    – float
        lead_time       – int
        service_level   – float
        batch_size      – int
    """
    cfg: Dict[str, Any] = {
        "uploaded_file": None,
        "df_raw": None,
        "data_mode": None,
        "store_id": None,
        "item_id": None,
        "models": ["Prophet"],
        "forecast_horizon": 30,
        "test_split_frac": 0.2,
        "ordering_cost": 50.0,
        "holding_cost": 0.5,
        "lead_time": 7,
        "service_level": 0.95,
        "batch_size": 1,
    }

    with st.sidebar:
        st.markdown(
            """
            <div style="text-align:center; padding: 1rem 0 .5rem 0;">
                <div style="font-size:2.4rem;">📦</div>
                <div style="font-size:1.4rem; font-weight:800; color:#ffffff; letter-spacing:-.5px;">SmartStock</div>
                <div style="font-size:.78rem; color:#94a3b8; margin-top:.2rem;">Inventory Intelligence Platform</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.divider()

        # ── Navigation buttons ────────────────────────────────────────
        active = st.session_state.get("active_page", "dashboard")

        if st.button("📡  API Docs", use_container_width=True,
                     type="primary" if active == "api_docs" else "secondary"):
            st.session_state["active_page"] = "api_docs"
            st.rerun()

        if st.button("📚  References", use_container_width=True,
                     type="primary" if active == "references" else "secondary"):
            st.session_state["active_page"] = "references"
            st.rerun()

        if active in ("api_docs", "references"):
            if st.button("←  Back to Dashboard", use_container_width=True):
                st.session_state["active_page"] = "dashboard"
                st.rerun()

        st.divider()

        # ── 1. Data Upload ──────────────────────────────────────────────────
        st.markdown("**📂 DATA UPLOAD**")
        uploaded = st.file_uploader(
            "Upload CSV file",
            type=["csv"],
            help=(
                "Accepted formats:\n"
                "• **Sales data**: columns `date, store, item, sales`\n"
                "• **Single series**: columns `date, sales`\n"
                "• **ABC data**: columns `item_id, unit_cost, annual_demand`"
            ),
        )
        cfg["uploaded_file"] = uploaded

        if uploaded is not None:
            df_raw, data_mode = _parse_upload(uploaded)
            cfg["df_raw"] = df_raw
            cfg["data_mode"] = data_mode

            if data_mode == "multi_store" and df_raw is not None:
                stores = sorted(df_raw["store"].unique().tolist())
                store_id = st.selectbox("Store", stores, index=0)
                items = sorted(
                    df_raw[df_raw["store"] == store_id]["item"].unique().tolist()
                )
                item_id = st.selectbox("Item", items, index=0)
                cfg["store_id"] = store_id
                cfg["item_id"] = item_id

            elif data_mode == "single_series":
                st.success("Single-series CSV detected ✓")

            elif data_mode == "abc_only" and df_raw is not None:
                st.markdown(
                    """
                    <div style="background:rgba(52,211,153,.12); border:1px solid rgba(52,211,153,.4);
                                border-radius:10px; padding:.8rem 1rem; margin-top:.5rem;">
                        <div style="font-weight:700; color:#6ee7b7; margin-bottom:.3rem">✨ Forecasting Auto-Enabled</div>
                        <div style="font-size:.8rem; color:#cbd5e1; line-height:1.6">
                            Select an item below — SmartStock will<br>
                            <b>automatically generate</b> realistic sales history<br>
                            from its annual demand and run the full forecast.
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                has_category = "category" in df_raw.columns
                has_item_name = "item_name" in df_raw.columns

                if has_category:
                    # ── Category → Item hierarchical selection ──────────────
                    categories = sorted(df_raw["category"].dropna().unique().tolist())
                    selected_category = st.selectbox(
                        "🏷️ CATEGORY", categories, index=0,
                        label_visibility="visible"
                    )
                    cfg["abc_selected_category"] = selected_category

                    cat_df = df_raw[df_raw["category"] == selected_category]

                    # Build display label: "Item Name (SKU-XXX)" or just item_id
                    if has_item_name:
                        item_labels = [
                            f"{row['item_name']} ({row['item_id']})"
                            for _, row in cat_df.iterrows()
                        ]
                        item_ids = cat_df["item_id"].astype(str).tolist()
                        label_to_id = dict(zip(item_labels, item_ids))
                    else:
                        item_labels = cat_df["item_id"].astype(str).tolist()
                        label_to_id = dict(zip(item_labels, item_labels))

                    selected_label = st.selectbox(
                        "📦 ITEM", item_labels, index=0,
                        label_visibility="visible"
                    )
                    selected_item = label_to_id[selected_label]

                    # Show expandable list of all items in category
                    with st.expander(f"▶  Items in selected category", expanded=False):
                        for lbl in item_labels:
                            st.markdown(
                                f"<div style='font-size:.8rem; color:#cbd5e1; padding:.15rem 0;'>• {lbl}</div>",
                                unsafe_allow_html=True,
                            )
                else:
                    # No category column — flat list
                    if has_item_name:
                        item_labels = [
                            f"{row['item_name']} ({row['item_id']})"
                            for _, row in df_raw.iterrows()
                        ]
                        item_ids = df_raw["item_id"].astype(str).tolist()
                        label_to_id = dict(zip(item_labels, item_ids))
                    else:
                        item_labels = df_raw["item_id"].astype(str).tolist()
                        label_to_id = dict(zip(item_labels, item_labels))
                    selected_label = st.selectbox("📦 ITEM", item_labels, index=0)
                    selected_item = label_to_id[selected_label]
                    selected_category = None
                    cfg["abc_selected_category"] = None

                cfg["abc_selected_item"] = selected_item

                # Expose annual_demand + unit_cost + item_name for the selected item
                row = df_raw[df_raw["item_id"].astype(str) == selected_item].iloc[0]
                cfg["abc_annual_demand"] = float(row["annual_demand"])
                cfg["abc_unit_cost"] = float(row["unit_cost"])
                if has_item_name:
                    cfg["abc_item_name"] = str(row["item_name"])
                # Treat as a synthetic single series so all tabs unlock
                cfg["data_mode"] = "abc_synthetic"

            else:
                st.error("Unrecognised CSV format. See help tooltip above.")

        st.divider()

        # ── 2. Model Selection ──────────────────────────────────────────────
        if cfg["data_mode"] not in (None, "abc_only", "unknown"):
            st.markdown("**🤖 MODEL SELECTION**")
            use_prophet = st.checkbox("Prophet", value=True)
            use_sarima = st.checkbox("SARIMA", value=False)
            selected_models = []
            if use_prophet:
                selected_models.append("Prophet")
            if use_sarima:
                selected_models.append("SARIMA")
            if not selected_models:
                st.warning("Select at least one model.")
                selected_models = ["Prophet"]
            cfg["models"] = selected_models

            st.divider()

            # ── 3. Forecast Settings ────────────────────────────────────────
            st.markdown("**📅 FORECAST SETTINGS**")
            cfg["forecast_horizon"] = st.slider(
                "Forecast horizon (days)", min_value=7, max_value=180, value=30, step=7
            )
            cfg["test_split_frac"] = st.slider(
                "Test split (%)",
                min_value=5,
                max_value=40,
                value=20,
                step=5,
                format="%d%%",
            ) / 100.0

            st.divider()

        # ── 4. Optimization Parameters ──────────────────────────────────────
        if cfg["data_mode"] not in (None, "abc_only", "unknown"):
            with st.expander("⚙️ OPTIMIZATION PARAMETERS", expanded=False):
                cfg["ordering_cost"] = st.number_input(
                    "Ordering cost ($ / order)",
                    min_value=0.0,
                    value=50.0,
                    step=5.0,
                    format="%.2f",
                )
                cfg["holding_cost"] = st.number_input(
                    "Holding cost ($ / unit / period)",
                    min_value=0.01,
                    value=0.50,
                    step=0.05,
                    format="%.2f",
                )
                cfg["lead_time"] = st.number_input(
                    "Lead time (days)", min_value=0, value=7, step=1
                )
                cfg["service_level"] = (
                    st.slider(
                        "Service level (%)",
                        min_value=80,
                        max_value=99,
                        value=95,
                        step=1,
                        format="%d%%",
                    )
                    / 100.0
                )
                cfg["batch_size"] = st.number_input(
                    "Batch / pallet size (units)", min_value=1, value=1, step=1
                )

    return cfg


# ── Helpers ─────────────────────────────────────────────────────────────────


def _parse_upload(uploaded_file) -> tuple[Optional[pd.DataFrame], Optional[str]]:
    """Parse uploaded CSV and detect its format."""
    try:
        df = pd.read_csv(uploaded_file)
        # Normalise: strip whitespace, lowercase, replace spaces with underscores
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    except Exception as exc:
        st.sidebar.error(f"Could not read CSV: {exc}")
        return None, None

    cols = set(df.columns)

    if {"date", "store", "item", "sales"}.issubset(cols):
        df["date"] = pd.to_datetime(df["date"])
        return df, "multi_store"

    if {"date", "sales"}.issubset(cols):
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").set_index("date")
        return df, "single_series"

    if {"item_id", "unit_cost", "annual_demand"}.issubset(cols):
        # Normalise category and item_name columns if present
        if "category" in cols:
            df["category"] = df["category"].astype(str).str.strip()
        if "item_name" in cols:
            df["item_name"] = df["item_name"].astype(str).str.strip()
        return df, "abc_only"

    return df, "unknown"
