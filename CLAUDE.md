# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Run the Streamlit dev server
uv run streamlit run src/finance_panel/app.py

# Or via module entry point
uv run python -m finance_panel

# Build wheel
uv build
```

There is no test suite or linter configured yet.

## Architecture

This is a personal finance visualization app built with Streamlit + Plotly + Pandas. It's a Python port of a TypeScript/React project ([finance-panel](https://github.com/user/finance-panel)), sharing the same JSON data format.

**Data flow:** JSON files in `data/` → `data_loader.py` parses into `FinanceState` (a dataclass in `types.py`) → stored in `st.session_state` → views build Pandas DataFrames from it → Plotly charts render via factory functions in `chart_utils.py`.

**Key design decisions:**

- **Multi-file data merging:** `load_all_data()` scans `data/wechat.json`, `data/alipay.json`, `data/tax.json`, plus all `*.json` files under `data/banks/`. Each is parsed independently, then `merge_states()` deep-merges them into one `FinanceState`. This avoids a monolithic data file and lets bank data live in separate files.
- **Monthly is the source of truth:** `compute_yearly_from_monthly()` derives yearly aggregates from monthly data, and these derived values take precedence over explicit `wechatByYear`/`alipayByYear` fields. During export (`state_to_disk_json()`), yearly totals that can be derived from monthly are omitted to avoid duplication.
- **Bank monthly data is additive:** Bank monthly data gets merged into `monthly_by_year.bank`, then during export it's deducted back out so the JSON roundtrips cleanly.
- **Session state** (`app.py:_init_session_state`) holds view mode, enabled sources, selected year/range, hidden chart series, and the loaded `FinanceState`. The sidebar and views read/write these keys. Only "wechat", "alipay", "bank" are valid source keys — views gate per-channel data behind `enabled_sources` membership.
- **Chart factory functions** (`chart_utils.py`) centralize Plotly theme colors, layout defaults (`base_layout()`), and common chart types (grouped bar, donut, multi-line with toggleable traces, dual-axis). Views should use these rather than building raw Plotly figures.
- **In-place editing** (`data_editor.py`) uses Streamlit's `st.data_editor` with collapsible `st.expander` sections for Alipay, WeChat, Bank, and Tax data. Bank rows are filtered by a year selector; saving replaces rows for that year.
- **Data directory** (`data/`) is gitignored — each developer maintains their own local copy of the JSON data files.

**File map (non-obvious relationships):**

| File | Role |
|------|------|
| `types.py` | All dataclasses: `FinanceState`, `MonthAgg`, `BankSpendRow`, `TaxYearAgg`, `YearMonthlyChannels`, `ChannelMonthly` |
| `data_loader.py` | JSON parsing, normalization, merging, export. Depends only on `types.py` |
| `app.py` | Streamlit entry point, session init, view routing. Imports all views and the sidebar |
| `components/sidebar.py` | Source toggles, view mode radio, year/range selectors, data reload + export buttons |
| `components/chart_utils.py` | Shared Plotly factories, color constants, layout defaults |
| `components/data_editor.py` | Collapsible editors for modifying data in-place |
| `views/annual.py` | Year-level aggregate charts (7 chart blocks) |
| `views/monthly.py` | Single-year 12-month breakdown (3 chart blocks) |
| `views/range_view.py` | Custom start/end month range (5 chart blocks) |
