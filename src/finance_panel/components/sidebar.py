"""Sidebar controls: source filters, view mode, year/range selectors, data management."""

from __future__ import annotations

import json
from datetime import datetime

import streamlit as st

from finance_panel.data_loader import load_all_data, state_to_disk_json


def render_sidebar() -> None:
    """Render the sidebar with all controls."""
    with st.sidebar:
        st.header("数据源筛选")

        state = st.session_state.finance_state

        # Source toggle checkboxes — enforce at least one selected
        current_sources = st.session_state.enabled_sources
        if "wechat" not in st.session_state:
            st.session_state._wechat_cb = "wechat" in current_sources
        if "alipay" not in st.session_state:
            st.session_state._alipay_cb = "alipay" in current_sources
        if "bank" not in st.session_state:
            st.session_state._bank_cb = "bank" in current_sources

        def _on_source_change():
            sources = set()
            if st.session_state._wechat_cb:
                sources.add("wechat")
            if st.session_state._alipay_cb:
                sources.add("alipay")
            if st.session_state._bank_cb:
                sources.add("bank")
            # Enforce at least one
            if not sources:
                sources.add("wechat")
                st.session_state._wechat_cb = True
            st.session_state.enabled_sources = sources

        st.checkbox(
            "微信支付",
            key="_wechat_cb",
            on_change=_on_source_change,
            help="微信支付渠道数据",
        )
        st.checkbox(
            "支付宝",
            key="_alipay_cb",
            on_change=_on_source_change,
            help="支付宝渠道数据",
        )
        st.checkbox(
            "银行卡",
            key="_bank_cb",
            on_change=_on_source_change,
            help="银行卡渠道数据",
        )

        st.divider()

        # View mode
        st.header("视图模式")
        view_labels = {
            "annual": "按年度汇总",
            "monthly": "按月份趋势",
            "range": "自定义时间范围",
        }
        selected_label = view_labels.get(
            st.session_state.view_mode, "按年度汇总"
        )
        new_label = st.radio(
            "选择视图",
            options=list(view_labels.values()),
            index=list(view_labels.keys()).index(st.session_state.view_mode),
            label_visibility="collapsed",
        )
        for k, v in view_labels.items():
            if v == new_label:
                st.session_state.view_mode = k
                break

        st.divider()

        # Year selector (only for monthly view)
        if st.session_state.view_mode == "monthly":
            st.header("年份选择")
            available_years = _get_available_years(state)
            if available_years:
                st.selectbox(
                    "选择年份",
                    options=available_years,
                    index=(
                        available_years.index(st.session_state.selected_year)
                        if st.session_state.selected_year in available_years
                        else len(available_years) - 1
                    ),
                    key="selected_year",
                    label_visibility="collapsed",
                )

        # Range selectors (only for range view)
        if st.session_state.view_mode == "range":
            st.header("时间范围")
            available_years = _get_available_years(state)
            months = list(range(1, 13))
            month_labels = ["1月","2月","3月","4月","5月","6月","7月","8月","9月","10月","11月","12月"]

            st.caption("起始年月")
            c1, c2 = st.columns(2)
            with c1:
                start_year = st.selectbox(
                    "起始年",
                    options=available_years,
                    index=(
                        available_years.index(st.session_state.range_start[0])
                        if st.session_state.range_start[0] in available_years
                        else 0
                    ),
                    key="range_start_year",
                    label_visibility="collapsed",
                )
            with c2:
                start_month = st.selectbox(
                    "起始月",
                    options=months,
                    format_func=lambda m: month_labels[m - 1],
                    index=st.session_state.range_start[1] - 1,
                    key="range_start_month",
                    label_visibility="collapsed",
                )
            st.session_state.range_start = (start_year, start_month)

            st.caption("结束年月")
            c3, c4 = st.columns(2)
            with c3:
                end_year = st.selectbox(
                    "结束年",
                    options=available_years,
                    index=(
                        available_years.index(st.session_state.range_end[0])
                        if st.session_state.range_end[0] in available_years
                        else len(available_years) - 1
                    ),
                    key="range_end_year",
                    label_visibility="collapsed",
                )
            with c4:
                end_month = st.selectbox(
                    "结束月",
                    options=months,
                    format_func=lambda m: month_labels[m - 1],
                    index=st.session_state.range_end[1] - 1,
                    key="range_end_month",
                    label_visibility="collapsed",
                )
            st.session_state.range_end = (end_year, end_month)

        st.divider()

        # Data management
        st.header("数据管理")

        if st.button("🔄 重新加载数据", use_container_width=True):
            from finance_panel.app import DATA_DIR

            state, warnings = load_all_data(DATA_DIR)
            st.session_state.finance_state = state
            st.session_state.data_loaded = True
            if warnings:
                st.session_state.status_message = "；".join(warnings)
            else:
                st.session_state.status_message = None
            st.rerun()

        if state:
            export_json = state_to_disk_json(state)
            st.download_button(
                "📥 导出合并数据",
                data=export_json,
                file_name="merged-finance-data.json",
                mime="application/json",
                use_container_width=True,
            )


def _get_available_years(state) -> list[int]:
    """Collect all years present in the data."""
    if state is None:
        return [datetime.now().year]
    years: set[str] = set()
    years.update(state.monthly_by_year.keys())
    years.update(state.wechat_by_year.keys())
    years.update(state.alipay_by_year.keys())
    for r in state.bank_rows:
        years.add(str(r.year))
    nums = []
    for y in years:
        try:
            n = int(y)
            if 1990 <= n <= 2100:
                nums.append(n)
        except ValueError:
            pass
    nums.sort()
    return nums if nums else [datetime.now().year]
