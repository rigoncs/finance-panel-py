"""Annual dashboard view — equivalent to Dashboard.tsx."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from finance_panel.components.chart_utils import (
    LINE_SERIES,
    TAX_ACTUAL,
    TAX_INCOME,
    TAX_PAID,
    TAX_REFUND,
    TOTAL_EXPENSE,
    TOTAL_INCOME,
    create_donut,
    create_dual_axis_line,
    create_grouped_bar,
    create_multi_line,
    create_simple_bars,
)
from finance_panel.format import format_cny
from finance_panel.types import BankSpendRow, MonthAgg, TaxYearAgg


def _build_chart_rows(
    wechat_by_year: dict[str, MonthAgg],
    alipay_by_year: dict[str, MonthAgg],
    bank_rows: list[BankSpendRow],
    enabled_sources: set[str],
) -> pd.DataFrame:
    """Build aggregate year rows like buildChartRows()."""
    years: set[str] = set()
    years.update(wechat_by_year.keys())
    years.update(alipay_by_year.keys())
    for r in bank_rows:
        years.add(str(r.year))

    sorted_years = sorted(int(y) for y in years)

    rows = []
    for y in sorted_years:
        key = str(y)
        w = wechat_by_year.get(key, MonthAgg())
        a = alipay_by_year.get(key, MonthAgg())

        same_year = [r for r in bank_rows if r.year == y]
        bank_expense = sum(r.amount for r in same_year) if "bank" in enabled_sources else 0.0
        bank_income = sum(r.income for r in same_year) if "bank" in enabled_sources else 0.0
        wechat_income = w.income if "wechat" in enabled_sources else 0.0
        alipay_income = a.income if "alipay" in enabled_sources else 0.0
        wechat_expense = w.expense if "wechat" in enabled_sources else 0.0
        alipay_expense = a.expense if "alipay" in enabled_sources else 0.0

        rows.append({
            "year": key,
            "wechatIncome": wechat_income,
            "alipayIncome": alipay_income,
            "bankIncome": bank_income,
            "totalIncome": round(wechat_income + alipay_income + bank_income, 2),
            "wechatExpense": wechat_expense,
            "alipayExpense": alipay_expense,
            "bankExpense": bank_expense,
            "totalExpense": round(wechat_expense + alipay_expense + bank_expense, 2),
        })

    return pd.DataFrame(rows)


def render_annual(
    wechat_by_year: dict[str, MonthAgg],
    alipay_by_year: dict[str, MonthAgg],
    bank_rows: list[BankSpendRow],
    enabled_sources: set[str],
    tax_by_year: dict[str, TaxYearAgg],
) -> None:
    df = _build_chart_rows(wechat_by_year, alipay_by_year, bank_rows, enabled_sources)

    if df.empty:
        st.info("暂无年度数据。请在 JSON 中填写 wechatByYear / alipayByYear，或导入数据。")
        return

    # ---- Total stats ----
    total_income = round(df["totalIncome"].sum(), 2)
    total_expense = round(df["totalExpense"].sum(), 2)
    tax_income_total = round(sum(t.income for t in tax_by_year.values()), 2)
    tax_actual_total = round(sum(t.tax_paid - t.tax_refund for t in tax_by_year.values()), 2)

    with st.expander("全年度总计汇总", expanded=True):
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("累计总收入", format_cny(total_income))
        c2.metric("累计总支出", format_cny(total_expense))
        c3.metric("累计工资总收入", format_cny(tax_income_total))
        c4.metric("累计实际总缴税", format_cny(tax_actual_total))
        c5.metric(
            "累计总结余",
            format_cny(total_income - total_expense),
            delta=None,
        )

    # ---- Chart 1: Grouped bar ----
    with st.expander("年度收入与支出对比", expanded=True):
        bar_groups = []
        if "wechat" in enabled_sources:
            bar_groups.append(("wechatIncome", "收入（微信）", "#22c55e"))
        if "alipay" in enabled_sources:
            bar_groups.append(("alipayIncome", "收入（支付宝）", "#1677ff"))
        if "bank" in enabled_sources:
            bar_groups.append(("bankIncome", "收入（银行卡）", "#14b8a6"))
        if "wechat" in enabled_sources:
            bar_groups.append(("wechatExpense", "支出（微信）", "#f97316"))
        if "alipay" in enabled_sources:
            bar_groups.append(("alipayExpense", "支出（支付宝）", "#38bdf8"))
        if "bank" in enabled_sources:
            bar_groups.append(("bankExpense", "支出（银行卡）", "#a855f7"))

        fig = create_grouped_bar(df, "year", bar_groups, "年度收入与支出对比")
        st.plotly_chart(fig, use_container_width=True)

    # ---- Chart 2: Tax bar chart ----
    tax_df = pd.DataFrame([
        {"year": y, "income": v.income, "taxPaid": v.tax_paid, "taxRefund": v.tax_refund}
        for y, v in sorted(tax_by_year.items(), key=lambda x: int(x[0]))
    ])
    if not tax_df.empty:
        with st.expander("个人所得税年度统计", expanded=True):
            fig = create_grouped_bar(
                tax_df,
                "year",
                [
                    ("income", "年收入合计", TAX_INCOME),
                    ("taxPaid", "已申报税额", TAX_PAID),
                    ("taxRefund", "退税金额", TAX_REFUND),
                ],
                "个人所得税年度统计",
            )
            st.plotly_chart(fig, use_container_width=True)

    # ---- Chart 3: Dual-axis line ----
    tax_trend_df = pd.DataFrame([
        {"year": y, "income": v.income, "actualTax": round(v.tax_paid - v.tax_refund, 2)}
        for y, v in sorted(tax_by_year.items(), key=lambda x: int(x[0]))
    ])
    if not tax_trend_df.empty:
        with st.expander("年度工资与实际缴税趋势", expanded=True):
            fig = create_dual_axis_line(
                tax_trend_df,
                "year",
                [("income", "年收入合计 (工资)", TAX_INCOME)],
                [("actualTax", "实际缴税额", TAX_ACTUAL)],
                "年度工资与实际缴税趋势",
            )
            st.plotly_chart(fig, use_container_width=True)

    # ---- Chart 4: Donut pie ----
    with st.expander("支出结构占比", expanded=True):
        wechat_exp = df["wechatExpense"].sum()
        alipay_exp = df["alipayExpense"].sum()
        bank_exp = df["bankExpense"].sum()
        pie_data = [
            (name, val, color)
            for name, val, color in [
                ("微信支出", wechat_exp, "#22c55e"),
                ("支付宝支出", alipay_exp, "#1677ff"),
                ("银行卡支出", bank_exp, "#14b8a6"),
            ]
            if val > 0
        ]
        if pie_data:
            fig = create_donut(
                [d[0] for d in pie_data],
                [d[1] for d in pie_data],
                [d[2] for d in pie_data],
                "支出结构占比 (所有年度累计)",
            )
            st.plotly_chart(fig, use_container_width=True)

    # ---- Chart 5: Multi-line trend ----
    with st.expander("综合趋势分析", expanded=True):
        hidden = st.session_state.get("hidden_lines_annual", set())

        # Custom legend as multiselect
        all_keys = [s[0] for s in LINE_SERIES]
        all_labels = [s[1] for s in LINE_SERIES]
        visible_labels = st.multiselect(
            "显示系列",
            options=all_labels,
            default=[l for i, l in enumerate(all_labels) if all_keys[i] not in hidden],
            key="annual_multiselect",
        )
        new_hidden = {all_keys[i] for i, l in enumerate(all_labels) if l not in visible_labels}
        st.session_state["hidden_lines_annual"] = new_hidden

        fig = create_multi_line(
            df, "year", LINE_SERIES, new_hidden, enabled_sources, "综合趋势分析"
        )
        st.plotly_chart(fig, use_container_width=True)

    # ---- Chart 6: Per-year summary cards ----
    with st.expander("年度汇总卡片", expanded=False):
        cols = st.columns(3)
        for i, (_, row) in enumerate(df.iterrows()):
            with cols[i % 3]:
                balance = row["totalIncome"] - row["totalExpense"]
                st.markdown(f"**{row['year']} 年**")
                items = [
                    ("微信收入", row["wechatIncome"], "pos"),
                    ("支付宝收入", row["alipayIncome"], "pos"),
                    ("银行卡收入", row["bankIncome"], "pos"),
                    ("总收入", row["totalIncome"], "pos"),
                    ("微信支出", row["wechatExpense"], "neg"),
                    ("支付宝支出", row["alipayExpense"], "neg"),
                    ("银行卡支出", row["bankExpense"], "neg"),
                    ("总支出", row["totalExpense"], "neg"),
                    ("结余", balance, "pos" if balance >= 0 else "neg"),
                ]
                for label, val, _ in items:
                    color = "#22c55e" if "收入" in label or "结余" in label else "#ef4444"
                    st.markdown(
                        f"<small>{label}: <span style='color:{color}'>{format_cny(val)}</span></small>",
                        unsafe_allow_html=True,
                    )
                st.divider()
