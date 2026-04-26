"""
Full-page References view for SmartStock dashboard.
"""
from __future__ import annotations
import streamlit as st


def render_references_view() -> None:
    st.markdown(
        """
        <div style="
            background: linear-gradient(135deg, #134e5e, #71b280);
            border-radius: 18px; padding: 2rem 2.5rem; margin-bottom: 2rem;
        ">
            <div style="font-size:2rem; font-weight:800; color:#fff; margin-bottom:.3rem;">
                📚 References & Further Reading
            </div>
            <div style="color:#d1fae5; font-size:.95rem;">
                Academic papers, textbooks, and technical documentation behind
                every algorithm and framework used in SmartStock.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Section 1: Forecasting Models ────────────────────────────────────────
    _section_header("📈", "Forecasting Models")

    _ref_card(
        emoji="🔮",
        title="Prophet — Forecasting at Scale",
        authors="Sean J. Taylor & Benjamin Letham",
        org="Facebook (Meta) Core Data Science",
        year="2017",
        url="https://peerj.com/preprints/3190/",
        tag="Research Paper",
        tag_color="#6366f1",
        description=(
            "The original paper introducing Prophet, the AI model SmartStock uses for "
            "demand forecasting. Prophet works by decomposing a time series into three "
            "components: **trend** (long-term direction), **seasonality** (weekly/yearly "
            "repeating patterns), and **holidays** (one-off events). Unlike ARIMA-based models, "
            "Prophet is robust to missing data, outliers, and trend shifts — making it ideal "
            "for retail inventory data. SmartStock uses Prophet's 80% confidence interval mode "
            "to generate the shaded bands you see on the forecast chart."
        ),
        key_concepts=["Additive decomposition", "Fourier series seasonality", "Changepoint detection", "Uncertainty intervals"],
    )

    _ref_card(
        emoji="📊",
        title="SARIMA — Seasonal AutoRegressive Integrated Moving Average",
        authors="Box & Jenkins",
        org="University of Wisconsin-Madison",
        year="1970 (foundational), updated editions to 2016",
        url="https://otexts.com/fpp3/arima.html",
        tag="Statistical Method",
        tag_color="#0891b2",
        description=(
            "The classical time series forecasting method available as a second model in SmartStock. "
            "SARIMA extends ARIMA with seasonal differencing, making it capable of handling "
            "repeating patterns (e.g. weekly spikes). It is defined by parameters (p,d,q)(P,D,Q)m "
            "where p=autoregressive order, d=differencing, q=moving average order, and m=seasonal period. "
            "**When to prefer SARIMA:** stable, stationary data with a single clear seasonality. "
            "**When to prefer Prophet:** complex patterns, multiple seasonalities, or irregular data."
        ),
        key_concepts=["Autoregression (AR)", "Differencing (I)", "Moving Average (MA)", "Seasonal terms (S)", "Stationarity"],
    )

    _ref_card(
        emoji="📖",
        title="Forecasting: Principles and Practice (3rd ed.)",
        authors="Rob J. Hyndman & George Athanasopoulos",
        org="Monash University, Australia",
        year="2021",
        url="https://otexts.com/fpp3/",
        tag="Free Textbook",
        tag_color="#059669",
        description=(
            "The definitive free online textbook on time series forecasting. "
            "Covers everything from basic exponential smoothing to advanced ARIMA and neural "
            "network models. Chapters 8–10 are particularly relevant to understanding how "
            "SmartStock's Prophet and SARIMA models work. Written for practitioners — "
            "heavy on intuition, light on unnecessary mathematics. All code examples in R "
            "but concepts are universal."
        ),
        key_concepts=["ETS models", "ARIMA families", "Cross-validation for time series", "Accuracy metrics (MAE, RMSE, MAPE)"],
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Section 2: Inventory Optimisation ────────────────────────────────────
    _section_header("📦", "Inventory Optimisation")

    _ref_card(
        emoji="📐",
        title="Economic Order Quantity (EOQ)",
        authors="Ford W. Harris",
        org="Factory: The Magazine of Management",
        year="1913",
        url="https://en.wikipedia.org/wiki/Economic_order_quantity",
        tag="Classical Formula",
        tag_color="#d97706",
        description=(
            "The foundational inventory formula that minimises total cost (ordering cost + holding cost). "
            "SmartStock applies it period-by-period using Prophet's daily demand forecasts. "
            "**Formula:** `EOQ = √(2DS/H)` where D = annual demand, S = ordering cost per order, "
            "H = holding cost per unit per year. "
            "A higher ordering cost → larger, less frequent orders. "
            "A higher holding cost → smaller, more frequent orders. "
            "The EOQ sits exactly at the point where both costs are equal."
        ),
        key_concepts=["Ordering cost vs holding cost trade-off", "Square-root formula", "Batch rounding", "Dynamic EOQ"],
    )

    _ref_card(
        emoji="🛡️",
        title="Safety Stock & Service Level",
        authors="Various (Operations Research literature)",
        org="—",
        year="—",
        url="https://en.wikipedia.org/wiki/Safety_stock",
        tag="Inventory Theory",
        tag_color="#7c3aed",
        description=(
            "Safety stock is the buffer held above expected demand to protect against "
            "forecast uncertainty and supply variability. SmartStock calculates it using "
            "the Z-score method: `SS = Z × σ_demand × √(lead_time)` where Z is the "
            "inverse normal CDF of your chosen service level (e.g. 95% → Z=1.645). "
            "The σ (standard deviation of demand) comes directly from Prophet's confidence "
            "interval width — wider CI = more uncertainty = more safety stock recommended. "
            "**Service level** = the probability of NOT stocking out in any given cycle. "
            "95% means you expect to have stock 19 out of every 20 replenishment cycles."
        ),
        key_concepts=["Z-score method", "Normal distribution", "Service level vs cost trade-off", "Stockout probability"],
    )

    _ref_card(
        emoji="🔁",
        title="Reorder Point (ROP)",
        authors="—",
        org="Supply Chain Management literature",
        year="—",
        url="https://en.wikipedia.org/wiki/Reorder_point",
        tag="Inventory Theory",
        tag_color="#b45309",
        description=(
            "The inventory level at which a new order must be placed to avoid a stockout "
            "during the supplier lead time. SmartStock formula: "
            "`ROP = (Average Daily Demand × Lead Time) + Safety Stock`. "
            "Example: if you sell 100 units/day, lead time is 7 days, and safety stock is 200 → "
            "ROP = 900 units. When your stock hits 900, place a new order. "
            "This is shown in the Inventory Optimisation tab's table as 'Reorder Point'."
        ),
        key_concepts=["Lead time demand", "Safety buffer inclusion", "Continuous review system"],
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Section 3: ABC Analysis ───────────────────────────────────────────────
    _section_header("🏷️", "ABC Analysis & Classification")

    _ref_card(
        emoji="📉",
        title="ABC Analysis — Pareto Principle Applied to Inventory",
        authors="Vilfredo Pareto (1896); applied to inventory by H. Ford Dickie (1951)",
        org="General Electric (Dickie's adaptation)",
        year="1951",
        url="https://en.wikipedia.org/wiki/ABC_analysis",
        tag="Management Method",
        tag_color="#dc2626",
        description=(
            "Based on Pareto's observation that 80% of effects come from 20% of causes. "
            "In inventory: a small number of products generate most of the revenue. "
            "SmartStock classifies every item using annual_value = unit_cost × annual_demand, "
            "sorts them highest-to-lowest, then applies the 80/15/5 cumulative split: "
            "**Class A** = items whose combined value reaches 80% of total. These are your "
            "critical items — never let them stock out. "
            "**Class B** = next 15% of total value. Monitor regularly. "
            "**Class C** = final 5% of total value. Low priority; consider reducing investment. "
            "The Pareto curve in the ABC tab visualises exactly where these thresholds fall."
        ),
        key_concepts=["Pareto principle (80/20 rule)", "Cumulative value ranking", "Selective inventory control", "Annual value calculation"],
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Section 4: Technology ─────────────────────────────────────────────────
    _section_header("⚙️", "Technology & Frameworks")

    col1, col2 = st.columns(2, gap="large")

    with col1:
        _ref_card_small("⚡", "FastAPI", "Sebastián Ramírez", "https://fastapi.tiangolo.com/",
            "Modern, high-performance Python web framework powering the SmartStock API. "
            "Auto-generates OpenAPI documentation and validates request/response schemas using Pydantic. "
            "Used here to expose Prophet and SARIMA as REST endpoints.")

        _ref_card_small("🎈", "Streamlit", "Streamlit Inc.", "https://docs.streamlit.io/",
            "The Python framework that turns Python scripts into interactive web dashboards "
            "without requiring HTML/CSS/JavaScript. All dashboard components (charts, sliders, "
            "file uploads, tabs) are written in pure Python.")

        _ref_card_small("🔮", "Prophet (Python)", "Meta Open Source", "https://facebook.github.io/prophet/",
            "Python library wrapping the Prophet forecasting algorithm. "
            "SmartStock uses prophet.Prophet() with uncertainty_samples=150 and "
            "weekly_seasonality=True for a good accuracy/speed balance.")

    with col2:
        _ref_card_small("🐼", "Pandas", "PyData community", "https://pandas.pydata.org/",
            "The core data manipulation library. Used throughout SmartStock for "
            "loading CSVs, cleaning time series, computing aggregations, and "
            "preparing data for API requests.")

        _ref_card_small("📈", "Plotly", "Plotly Technologies", "https://plotly.com/python/",
            "Interactive charting library used for the forecast chart (with CI bands), "
            "the ABC bar chart, and the Pareto curve. All charts are zoomable/pannable "
            "in the browser.")

        _ref_card_small("🔬", "Statsmodels", "PyData community", "https://www.statsmodels.org/",
            "Statistical library providing the SARIMA implementation used by SmartStock's "
            "second forecasting model option. Also used internally for time series diagnostics.")


# ── UI helpers ────────────────────────────────────────────────────────────────

def _section_header(emoji: str, title: str) -> None:
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:.6rem;
                    margin:1.2rem 0 .9rem; border-bottom:2px solid #e2e8f0; padding-bottom:.5rem;">
            <span style="font-size:1.35rem;">{emoji}</span>
            <span style="font-size:1.15rem; font-weight:800; color:#1e293b;">{title}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _ref_card(emoji, title, authors, org, year, url, tag, tag_color, description, key_concepts):
    concepts_html = "".join(
        f'<span style="background:{tag_color}18; color:{tag_color}; font-size:.7rem; '
        f'font-weight:600; padding:.15rem .5rem; border-radius:20px; margin:.1rem;">{c}</span>'
        for c in key_concepts
    )
    st.markdown(
        f"""
        <div style="border:1px solid #e2e8f0; border-radius:14px;
                    padding:1.3rem 1.5rem; margin-bottom:1.1rem;
                    background:#fff; box-shadow:0 2px 10px rgba(0,0,0,.04);">
            <div style="display:flex; align-items:flex-start; justify-content:space-between; margin-bottom:.5rem;">
                <div style="display:flex; align-items:center; gap:.5rem;">
                    <span style="font-size:1.4rem;">{emoji}</span>
                    <div>
                        <div style="font-weight:800; font-size:.98rem; color:#1e293b;">{title}</div>
                        <div style="font-size:.76rem; color:#94a3b8;">
                            {authors} · {org}{' · ' + year if year != '—' else ''}
                        </div>
                    </div>
                </div>
                <a href="{url}" target="_blank"
                   style="background:{tag_color}18; color:{tag_color}; font-size:.72rem;
                          font-weight:700; padding:.2rem .6rem; border-radius:20px;
                          text-decoration:none; white-space:nowrap; flex-shrink:0; margin-left:.5rem;">
                    {tag} ↗
                </a>
            </div>
            <div style="font-size:.84rem; color:#475569; line-height:1.75; margin-bottom:.8rem;">
                {description}
            </div>
            <div style="display:flex; flex-wrap:wrap; gap:.25rem;">
                <span style="font-size:.7rem; color:#94a3b8; margin-right:.3rem; align-self:center;">Key concepts:</span>
                {concepts_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _ref_card_small(emoji, title, authors, url, description):
    st.markdown(
        f"""
        <div style="border:1px solid #e2e8f0; border-radius:12px;
                    padding:1rem 1.2rem; margin-bottom:.9rem;
                    background:#fafafa;">
            <div style="display:flex; align-items:center; gap:.4rem; margin-bottom:.35rem;">
                <span style="font-size:1.1rem;">{emoji}</span>
                <a href="{url}" target="_blank"
                   style="font-weight:700; font-size:.9rem; color:#4f46e5;
                          text-decoration:none;">{title} ↗</a>
                <span style="font-size:.7rem; color:#94a3b8; margin-left:auto;">{authors}</span>
            </div>
            <div style="font-size:.8rem; color:#64748b; line-height:1.65;">{description}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
