"""Shared Plotly chart colors, layout helpers, and factory functions."""

import plotly.graph_objects as go
import plotly.express as px

# ---- Color scheme ----
WECHAT_INCOME = "#22c55e"
ALIPAY_INCOME = "#1677ff"
BANK_INCOME = "#14b8a6"
TOTAL_INCOME = "#15803d"
WECHAT_EXPENSE = "#f97316"
ALIPAY_EXPENSE = "#38bdf8"
BANK_EXPENSE = "#a855f7"
TOTAL_EXPENSE = "#ef4444"

TAX_INCOME = "#6366f1"
TAX_PAID = "#f43f5e"
TAX_REFUND = "#10b981"
TAX_ACTUAL = "#f43f5e"

CHART_BG = "rgba(0,0,0,0)"
GRID_COLOR = "#e5e7eb"
FONT_COLOR = "#374151"

# Series definitions matching the React app's COMBINED_LINE_SERIES and M_SERIES
LINE_SERIES = [
    ("wechatIncome", "收入（微信）", WECHAT_INCOME, "wechat"),
    ("alipayIncome", "收入（支付宝）", ALIPAY_INCOME, "alipay"),
    ("bankIncome", "收入（银行卡）", BANK_INCOME, "bank"),
    ("totalIncome", "总收入", TOTAL_INCOME, "all"),
    ("wechatExpense", "支出（微信）", WECHAT_EXPENSE, "wechat"),
    ("alipayExpense", "支出（支付宝）", ALIPAY_EXPENSE, "alipay"),
    ("bankExpense", "支出（银行卡）", BANK_EXPENSE, "bank"),
    ("totalExpense", "总支出", TOTAL_EXPENSE, "all"),
]

INCOME_BAR_COLORS = {
    "wechat": WECHAT_INCOME,
    "alipay": ALIPAY_INCOME,
    "bank": BANK_INCOME,
}

EXPENSE_BAR_COLORS = {
    "wechat": WECHAT_EXPENSE,
    "alipay": ALIPAY_EXPENSE,
    "bank": BANK_EXPENSE,
}

DONUT_COLORS = [WECHAT_EXPENSE, ALIPAY_EXPENSE, BANK_EXPENSE]


def base_layout(
    title: str,
    height: int = 400,
    xaxis_title: str | None = None,
    yaxis_title: str | None = None,
    **kwargs,
) -> dict:
    """Consistent Plotly layout defaults."""
    return dict(
        title=dict(text=title, font=dict(size=16, color=FONT_COLOR)),
        plot_bgcolor=CHART_BG,
        paper_bgcolor=CHART_BG,
        font=dict(color=FONT_COLOR, size=12),
        xaxis=dict(
            title=xaxis_title,
            gridcolor=GRID_COLOR,
            zeroline=False,
        ),
        yaxis=dict(
            title=yaxis_title,
            gridcolor=GRID_COLOR,
            zeroline=False,
        ),
        height=height,
        margin=dict(l=20, r=20, t=50, b=40),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.2,
            xanchor="center",
            x=0.5,
            font=dict(size=11),
        ),
        **kwargs,
    )


def format_hover_cny(v: float) -> str:
    """Format a hover value as CNY."""
    return f"¥{v:,.2f}"


def make_hovertemplate(name: str) -> str:
    """Standard hovertemplate with CNY formatting."""
    return f"{name}: %{{y:$,.2f}}<extra></extra>"


def create_grouped_bar(
    df,
    x_col: str,
    bar_groups: list[tuple[str, str, str]],
    title: str,
    height: int = 400,
) -> go.Figure:
    """Create a grouped bar chart.

    Args:
        df: DataFrame with x_col and all value columns.
        x_col: Column name for X axis.
        bar_groups: List of (column, display_name, color).
        title: Chart title.
        height: Chart height.
    """
    fig = go.Figure()
    for col, name, color in bar_groups:
        if col in df.columns:
            fig.add_trace(
                go.Bar(
                    x=df[x_col],
                    y=df[col],
                    name=name,
                    marker_color=color,
                    hovertemplate=make_hovertemplate(name),
                )
            )
    fig.update_layout(
        **base_layout(title, height),
        barmode="group",
        bargap=0.15,
        bargroupgap=0.1,
    )
    return fig


def create_donut(
    labels: list[str],
    values: list[float],
    colors: list[str],
    title: str,
    hole: float = 0.5,
    height: int = 400,
) -> go.Figure:
    """Create a donut/pie chart."""
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            marker=dict(colors=colors),
            hole=hole,
            textinfo="label+percent",
            hovertemplate="%{label}: ¥%{value:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(**base_layout(title, height))
    return fig


def create_multi_line(
    df,
    x_col: str,
    series_defs: list[tuple[str, str, str, str]],
    hidden_set: set[str],
    enabled_sources: set[str],
    title: str,
    height: int = 450,
) -> go.Figure:
    """Create a multi-line chart with toggleable traces.

    Args:
        df: DataFrame with x_col and value columns.
        x_col: Column name for X axis.
        series_defs: List of (column, name, color, source). Source is one of
            'wechat', 'alipay', 'bank', 'all'.
        hidden_set: Set of series keys currently hidden.
        enabled_sources: Set of enabled data sources.
        title: Chart title.
        height: Chart height.
    """
    fig = go.Figure()
    for key, name, color, source in series_defs:
        if key not in df.columns:
            continue
        visible = True
        if key in hidden_set:
            visible = "legendonly"
        if source != "all" and source not in enabled_sources:
            visible = "legendonly"
        fig.add_trace(
            go.Scatter(
                x=df[x_col],
                y=df[key],
                name=name,
                line=dict(color=color, width=2.2),
                mode="lines+markers",
                marker=dict(size=4),
                visible=visible,
                hovertemplate=make_hovertemplate(name),
            )
        )
    fig.update_layout(**base_layout(title, height))
    return fig


def create_dual_axis_line(
    df,
    x_col: str,
    left_series: list[tuple[str, str, str]],
    right_series: list[tuple[str, str, str]],
    title: str,
    height: int = 400,
) -> go.Figure:
    """Create a dual-Y-axis line chart."""
    fig = go.Figure()
    for col, name, color in left_series:
        if col in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df[x_col],
                    y=df[col],
                    name=name,
                    line=dict(color=color, width=2.2),
                    mode="lines+markers",
                    marker=dict(size=4),
                    hovertemplate=make_hovertemplate(name),
                )
            )
    for col, name, color in right_series:
        if col in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df[x_col],
                    y=df[col],
                    name=name,
                    line=dict(color=color, width=2.2, dash="dash"),
                    mode="lines+markers",
                    marker=dict(size=4),
                    yaxis="y2",
                    hovertemplate=make_hovertemplate(name),
                )
            )
    layout = base_layout(title, height)
    layout.update(
        yaxis=dict(
            title="收入 (¥)",
            gridcolor=GRID_COLOR,
            zeroline=False,
        ),
        yaxis2=dict(
            title="缴税 (¥)",
            overlaying="y",
            side="right",
            gridcolor=GRID_COLOR,
            zeroline=False,
        ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.25,
            xanchor="center",
            x=0.5,
        ),
    )
    fig.update_layout(**layout)
    return fig


def create_simple_bars(
    df,
    x_col: str,
    bars: list[tuple[str, str, str]],
    title: str,
    height: int = 350,
) -> go.Figure:
    """Create a simple (non-grouped) bar chart with multiple traces."""
    fig = go.Figure()
    for col, name, color in bars:
        if col in df.columns:
            fig.add_trace(
                go.Bar(
                    x=df[x_col],
                    y=df[col],
                    name=name,
                    marker_color=color,
                    hovertemplate=make_hovertemplate(name),
                )
            )
    fig.update_layout(**base_layout(title, height))
    return fig
