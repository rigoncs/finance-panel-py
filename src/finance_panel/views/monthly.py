"""Monthly dashboard view — equivalent to MonthlyDashboard.tsx."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from finance_panel.components.chart_utils import (
    LINE_SERIES,
    TOTAL_EXPENSE,
    TOTAL_INCOME,
    create_multi_line,
    make_hovertemplate,
    base_layout,
)
from finance_panel.format import format_cny
from finance_panel.types import MonthAgg, YearMonthlyChannels
import plotly.graph_objects as go


def _build_month_rows(
    channels: YearMonthlyChannels | None,
    enabled_sources: set[str],
) -> pd.DataFrame:
    """Build 12 month rows like buildMonthRows()."""
    w = channels.wechat.months if channels else {}
    a = channels.alipay.months if channels else {}
    b = channels.bank.months if channels else {}

    rows = []
    for m in range(1, 13):
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
            "monthLabel": f"{m}月",
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


def render_monthly(
    year: str,
    monthly_by_year: dict[str, YearMonthlyChannels],
    enabled_sources: set[str],
) -> None:
    channels = monthly_by_year.get(year)
    df = _build_month_rows(channels, enabled_sources)

    has_any = (df["totalIncome"].sum() > 0) or (df["totalExpense"].sum() > 0)

    if not has_any:
        st.info(
            f"当前年份（{year}）在 monthlyByYear 中无有效月数据（或全为 0），"
            "请在数据文件中按月份补充 wechat / alipay / bank。"
        )
        return

    # ---- Chart 1: Total income/expense line ----
    with st.expander(f"{year} 年 · 月度总收入 / 总支出", expanded=True):
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df["monthLabel"],
                y=df["totalIncome"],
                name="月总收入",
                line=dict(color=TOTAL_INCOME, width=2.5),
                mode="lines+markers",
                marker=dict(size=5),
                hovertemplate=make_hovertemplate("月总收入"),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df["monthLabel"],
                y=df["totalExpense"],
                name="月总支出",
                line=dict(color=TOTAL_EXPENSE, width=2.5),
                mode="lines+markers",
                marker=dict(size=5),
                hovertemplate=make_hovertemplate("月总支出"),
            )
        )
        fig.update_layout(**base_layout(f"{year} 年 · 月度总收支", height=320))
        st.plotly_chart(fig, use_container_width=True)

    # ---- Chart 2: Per-channel multi-line ----
    with st.expander(f"{year} 年 · 各渠道收支", expanded=True):
        hidden = st.session_state.get("hidden_lines_monthly", set())

        all_keys = [s[0] for s in LINE_SERIES]
        all_labels = [s[1] for s in LINE_SERIES]
        visible_labels = st.multiselect(
            "显示系列",
            options=all_labels,
            default=[l for i, l in enumerate(all_labels) if all_keys[i] not in hidden],
            key="monthly_multiselect",
        )
        new_hidden = {all_keys[i] for i, l in enumerate(all_labels) if l not in visible_labels}
        st.session_state["hidden_lines_monthly"] = new_hidden

        fig = create_multi_line(
            df, "monthLabel", LINE_SERIES, new_hidden, enabled_sources,
            f"{year} 年 · 各渠道收支"
        )
        st.plotly_chart(fig, use_container_width=True)

    # ---- Chart 3: Detail table ----
    with st.expander(f"{year} 年 · 月度明细表", expanded=False):
        table_data = []
        for _, row in df.iterrows():
            table_data.append({
                "月份": row["monthLabel"],
                "微信 (收入/支出)": f"{format_cny(row['wechatIncome'])} / {format_cny(row['wechatExpense'])}",
                "支付宝 (收入/支出)": f"{format_cny(row['alipayIncome'])} / {format_cny(row['alipayExpense'])}",
                "银行卡 (收入/支出)": f"{format_cny(row['bankIncome'])} / {format_cny(row['bankExpense'])}",
                "月总收入": format_cny(row["totalIncome"]),
                "月总支出": format_cny(row["totalExpense"]),
                "结余": format_cny(row["totalIncome"] - row["totalExpense"]),
            })
        st.dataframe(
            pd.DataFrame(table_data),
            use_container_width=True,
            hide_index=True,
        )
        st.caption("表中「微信 / 支付宝 / 银行卡」列格式为 收入 / 支出（元）。")
