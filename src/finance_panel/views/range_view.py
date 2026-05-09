"""Custom range dashboard view — equivalent to RangeDashboard.tsx."""

from __future__ import annotations

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from finance_panel.components.chart_utils import (
    TAX_INCOME,
    TOTAL_EXPENSE,
    TOTAL_INCOME,
    create_donut,
    create_simple_bars,
    make_hovertemplate,
    base_layout,
)
from finance_panel.format import format_cny
from finance_panel.types import MonthAgg, TaxYearAgg, YearMonthlyChannels


def _build_range_rows(
    start: tuple[int, int],
    end: tuple[int, int],
    monthly_by_year: dict[str, YearMonthlyChannels],
    enabled_sources: set[str],
) -> pd.DataFrame:
    """Build monthly rows within a date range like buildRangeRows()."""
    start_val = start[0] * 100 + start[1]
    end_val = end[0] * 100 + end[1]

    rows = []
    for y in range(start[0], end[0] + 1):
        channels = monthly_by_year.get(str(y))
        w = channels.wechat.months if channels else {}
        a = channels.alipay.months if channels else {}
        b = channels.bank.months if channels else {}

        for m in range(1, 13):
            current_val = y * 100 + m
            if current_val < start_val or current_val > end_val:
                continue

            key = str(m)
            wm = w.get(key, MonthAgg())
            am = a.get(key, MonthAgg())
            bm = b.get(key, MonthAgg())

            wechat_income = wm.income if "wechat" in enabled_sources else 0.0
            alipay_income = am.income if "alipay" in enabled_sources else 0.0
            bank_income = bm.income if "bank" in enabled_sources else 0.0
            wechat_expense = wm.expense if "wechat" in enabled_sources else 0.0
            alipay_expense = am.expense if "alipay" in enabled_sources else 0.0
            bank_expense = bm.expense if "bank" in enabled_sources else 0.0

            rows.append({
                "label": f"{y}-{m:02d}",
                "timestamp": current_val,
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


def render_range(
    start: tuple[int, int],
    end: tuple[int, int],
    monthly_by_year: dict[str, YearMonthlyChannels],
    enabled_sources: set[str],
    tax_by_year: dict[str, TaxYearAgg],
) -> None:
    df = _build_range_rows(start, end, monthly_by_year, enabled_sources)

    if df.empty:
        st.info("该时间范围内暂无月度明细数据。请检查数据文件中的 monthlyByYear 是否覆盖此范围。")
        return

    # ---- Stats ----
    total_income = round(df["totalIncome"].sum(), 2)
    total_expense = round(df["totalExpense"].sum(), 2)
    tax_income_total = round(
        sum(
            t.income
            for y_str, t in tax_by_year.items()
            if start[0] <= int(y_str) <= end[0]
        ),
        2,
    )
    tax_actual_total = round(
        sum(
            t.tax_paid - t.tax_refund
            for y_str, t in tax_by_year.items()
            if start[0] <= int(y_str) <= end[0]
        ),
        2,
    )

    first_label = df["label"].iloc[0]
    last_label = df["label"].iloc[-1]

    with st.expander(f"时间范围汇总 ({first_label} 至 {last_label})", expanded=True):
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("范围内总收入", format_cny(total_income))
        c2.metric("范围内总支出", format_cny(total_expense))
        c3.metric("范围内工资总收入", format_cny(tax_income_total))
        c4.metric("范围内实际总缴税", format_cny(tax_actual_total))
        c5.metric("范围内总结余", format_cny(total_income - total_expense))

    # ---- Chart 1: Income vs expense bar ----
    with st.expander("收支对比趋势", expanded=True):
        fig = create_simple_bars(
            df,
            "label",
            [
                ("totalIncome", "总收入", TOTAL_INCOME),
                ("totalExpense", "总支出", TOTAL_EXPENSE),
            ],
            "收支对比趋势",
            height=350,
        )
        st.plotly_chart(fig, use_container_width=True)

    # ---- Chart 2: Donut pie ----
    with st.expander("支出结构 (范围内累计)", expanded=True):
        wechat_exp = df["wechatExpense"].sum()
        alipay_exp = df["alipayExpense"].sum()
        bank_exp = df["bankExpense"].sum()
        pie_data = [
            (name, val, color)
            for name, val, color in [
                ("微信", wechat_exp, "#22c55e"),
                ("支付宝", alipay_exp, "#1677ff"),
                ("银行卡", bank_exp, "#14b8a6"),
            ]
            if val > 0
        ]
        if pie_data:
            fig = create_donut(
                [d[0] for d in pie_data],
                [d[1] for d in pie_data],
                [d[2] for d in pie_data],
                "支出结构 (范围内累计)",
                height=350,
            )
            st.plotly_chart(fig, use_container_width=True)

    # ---- Chart 3: Detailed expense line chart ----
    with st.expander("详细收支波动图", expanded=True):
        fig = go.Figure()
        if "wechat" in enabled_sources:
            fig.add_trace(
                go.Scatter(
                    x=df["label"],
                    y=df["wechatExpense"],
                    name="微信支出",
                    line=dict(color="#f97316", width=2),
                    mode="lines",
                    hovertemplate=make_hovertemplate("微信支出"),
                )
            )
        if "alipay" in enabled_sources:
            fig.add_trace(
                go.Scatter(
                    x=df["label"],
                    y=df["alipayExpense"],
                    name="支付宝支出",
                    line=dict(color="#38bdf8", width=2),
                    mode="lines",
                    hovertemplate=make_hovertemplate("支付宝支出"),
                )
            )
        if "bank" in enabled_sources:
            fig.add_trace(
                go.Scatter(
                    x=df["label"],
                    y=df["bankExpense"],
                    name="银行卡支出",
                    line=dict(color="#a855f7", width=2),
                    mode="lines",
                    hovertemplate=make_hovertemplate("银行卡支出"),
                )
            )
        fig.add_trace(
            go.Scatter(
                x=df["label"],
                y=df["totalExpense"],
                name="总支出趋势",
                line=dict(color="#dc2626", width=3),
                mode="lines+markers",
                marker=dict(size=4),
                hovertemplate=make_hovertemplate("总支出趋势"),
            )
        )
        fig.update_layout(**base_layout("详细收支波动图", height=400))
        st.plotly_chart(fig, use_container_width=True)

    # ---- Chart 4: Tax trend (if data overlaps) ----
    tax_df = pd.DataFrame([
        {"year": y_str, "income": v.income}
        for y_str, v in sorted(tax_by_year.items(), key=lambda x: int(x[0]))
        if start[0] <= int(y_str) <= end[0]
    ])
    if not tax_df.empty:
        with st.expander("年度工资收入趋势 (个税申报口径)", expanded=False):
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=tax_df["year"],
                    y=tax_df["income"],
                    name="年收入合计 (工资)",
                    line=dict(color=TAX_INCOME, width=3),
                    mode="lines+markers",
                    marker=dict(size=8, color=TAX_INCOME),
                    hovertemplate=make_hovertemplate("年收入合计"),
                )
            )
            fig.update_layout(**base_layout("年度工资收入趋势", height=350))
            st.plotly_chart(fig, use_container_width=True)
