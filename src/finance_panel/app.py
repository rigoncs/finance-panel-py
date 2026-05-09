"""Personal Finance Panel — Streamlit entry point."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import streamlit as st

from finance_panel.components.data_editor import render_data_editors
from finance_panel.components.sidebar import render_sidebar
from finance_panel.data_loader import load_all_data
from finance_panel.views.annual import render_annual
from finance_panel.views.monthly import render_monthly
from finance_panel.views.range_view import render_range

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def _init_session_state() -> None:
    """Initialize all session_state keys on first run."""
    defaults = {
        "finance_state": None,
        "view_mode": "annual",
        "enabled_sources": {"wechat", "alipay", "bank"},
        "selected_year": datetime.now().year,
        "bank_selected_year": datetime.now().year,
        "range_start": (2018, 1),
        "range_end": (datetime.now().year, datetime.now().month),
        "hidden_lines_annual": set(),
        "hidden_lines_monthly": set(),
        "data_loaded": False,
        "status_message": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def main() -> None:
    st.set_page_config(
        page_title="个人财务面板",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom CSS for metric cards and layout
    st.markdown(
        """
        <style>
        [data-testid="stMetric"] {
            background: var(--st-color-secondary-background, #f8fafc);
            padding: 1rem;
            border-radius: 0.75rem;
            border: 1px solid var(--st-color-border, #e5e7eb);
        }
        [data-testid="stMetric"] label {
            font-size: 0.85rem;
        }
        [data-testid="stMetric"] [data-testid="stMetricValue"] {
            font-size: 1.5rem;
        }
        .stPlotlyChart {
            border: 1px solid var(--st-color-border, #e5e7eb);
            border-radius: 0.75rem;
            padding: 0.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    _init_session_state()

    # Load data
    if not st.session_state.data_loaded:
        with st.spinner("正在加载财务数据..."):
            state, warnings = load_all_data(DATA_DIR)
            st.session_state.finance_state = state
            st.session_state.data_loaded = True
            if warnings:
                st.session_state.status_message = "；".join(warnings)
            if state is None:
                st.session_state.status_message = "无法加载数据，请检查 data/ 目录"

    # Sidebar
    render_sidebar()

    # Main area
    st.title("个人财务面板")
    st.caption("个人财务可视化分析系统 — 数据安全存储在本地 data/ 目录下")

    if st.session_state.status_message and st.session_state.finance_state:
        st.info(st.session_state.status_message)

    state = st.session_state.finance_state
    if state is None:
        st.warning("无法加载数据，请检查 data/ 目录")
        return

    # View routing
    view_mode = st.session_state.view_mode
    enabled = st.session_state.enabled_sources

    # Data editors (collapsible)
    render_data_editors(state)

    if view_mode == "annual":
        render_annual(
            wechat_by_year=state.wechat_by_year,
            alipay_by_year=state.alipay_by_year,
            bank_rows=state.bank_rows,
            enabled_sources=enabled,
            tax_by_year=state.tax_by_year,
        )
    elif view_mode == "monthly":
        render_monthly(
            year=str(st.session_state.selected_year),
            monthly_by_year=state.monthly_by_year,
            enabled_sources=enabled,
        )
    else:
        render_range(
            start=st.session_state.range_start,
            end=st.session_state.range_end,
            monthly_by_year=state.monthly_by_year,
            enabled_sources=enabled,
            tax_by_year=state.tax_by_year,
        )


if __name__ == "__main__":
    main()
