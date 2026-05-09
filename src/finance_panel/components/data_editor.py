"""Data editor — collapsible sections for editing Alipay/WeChat/Bank/Tax data."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from finance_panel.format import format_cny
from finance_panel.types import BankSpendRow, FinanceState, MonthAgg, TaxYearAgg


def render_data_editors(state: FinanceState) -> None:
    """Render all four collapsible data editor sections."""

    # ---- Alipay editor ----
    with st.expander("支付宝年度汇总", expanded=False):
        _render_year_editor(
            title="支付宝",
            year_data=state.alipay_by_year,
            on_change=lambda y, income, expense: _update_year_agg(
                state.alipay_by_year, y, income, expense
            ),
        )

    # ---- WeChat editor ----
    with st.expander("微信支付年度汇总", expanded=False):
        _render_year_editor(
            title="微信",
            year_data=state.wechat_by_year,
            on_change=lambda y, income, expense: _update_year_agg(
                state.wechat_by_year, y, income, expense
            ),
        )

    # ---- Bank editor ----
    with st.expander("银行卡年度收支", expanded=False):
        _render_bank_editor(state)

    # ---- Tax editor ----
    with st.expander("个人所得税年度汇总", expanded=False):
        _render_tax_editor(state)


def _render_year_editor(
    title: str,
    year_data: dict[str, MonthAgg],
    on_change,
) -> None:
    """Render an editable table for yearly income/expense data."""
    if not year_data:
        st.caption(f"暂无{title}年度数据。")
    else:
        rows = [
            {"年份": y, "收入": v.income, "支出": v.expense}
            for y, v in sorted(year_data.items(), key=lambda x: int(x[0]))
        ]
        edited = st.data_editor(
            pd.DataFrame(rows),
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key=f"editor_{title}",
        )
        if st.button(f"保存{title}修改", key=f"save_{title}"):
            year_data.clear()
            for _, row in edited.iterrows():
                y = str(row["年份"]).strip()
                if not y:
                    continue
                year_data[y] = MonthAgg(
                    income=float(row["收入"]) if pd.notna(row["收入"]) else 0.0,
                    expense=float(row["支出"]) if pd.notna(row["支出"]) else 0.0,
                )


def _render_bank_editor(state: FinanceState) -> None:
    """Render an editable table for bank rows."""
    selected_year = st.session_state.get("bank_selected_year", 2024)

    available_years = sorted({r.year for r in state.bank_rows})
    if available_years:
        selected_year = st.selectbox(
            "筛选年份",
            options=available_years,
            key="bank_editor_year",
        )
        st.session_state["bank_selected_year"] = selected_year

    filtered = [r for r in state.bank_rows if r.year == selected_year]

    if not filtered:
        st.caption(f"{selected_year} 年暂无银行卡数据。")
    else:
        rows = [
            {"ID": r.id, "银行": r.label, "年份": r.year, "收入": r.income, "支出": r.amount}
            for r in filtered
        ]
        edited = st.data_editor(
            pd.DataFrame(rows),
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key="editor_bank",
        )
        if st.button("保存银行卡修改", key="save_bank"):
            # Reconstruct bank_rows
            new_rows = []
            for _, row in edited.iterrows():
                new_rows.append(
                    BankSpendRow(
                        id=str(row["ID"]).strip() if pd.notna(row["ID"]) else "",
                        label=str(row["银行"]).strip(),
                        year=int(row["年份"]) if pd.notna(row["年份"]) else selected_year,
                        income=float(row["收入"]) if pd.notna(row["收入"]) else 0.0,
                        amount=float(row["支出"]) if pd.notna(row["支出"]) else 0.0,
                    )
                )
            # Replace rows for the selected year
            state.bank_rows = [r for r in state.bank_rows if r.year != selected_year] + new_rows


def _render_tax_editor(state: FinanceState) -> None:
    """Render an editable table for tax year data."""
    if not state.tax_by_year:
        st.caption("暂无个税数据。")
    else:
        rows = [
            {"年份": y, "收入": v.income, "已缴税": v.tax_paid, "退税": v.tax_refund}
            for y, v in sorted(state.tax_by_year.items(), key=lambda x: int(x[0]))
        ]
        edited = st.data_editor(
            pd.DataFrame(rows),
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key="editor_tax",
        )
        if st.button("保存个税修改", key="save_tax"):
            state.tax_by_year.clear()
            for _, row in edited.iterrows():
                y = str(row["年份"]).strip()
                if not y:
                    continue
                state.tax_by_year[y] = TaxYearAgg(
                    income=float(row["收入"]) if pd.notna(row["收入"]) else 0.0,
                    tax_paid=float(row["已缴税"]) if pd.notna(row["已缴税"]) else 0.0,
                    tax_refund=float(row["退税"]) if pd.notna(row["退税"]) else 0.0,
                )


def _update_year_agg(
    data: dict[str, MonthAgg],
    year: str,
    income: float,
    expense: float,
) -> None:
    """Update a single year entry."""
    data[year] = MonthAgg(income=max(0.0, income), expense=max(0.0, expense))
