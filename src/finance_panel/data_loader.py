"""Data engine: loads, parses, merges, and exports finance JSON files.

Equivalent to the TypeScript financeDataFile.ts.
"""

from __future__ import annotations

import json
import math
import uuid
from pathlib import Path
from typing import Any

from finance_panel.types import (
    BankSpendRow,
    ChannelMonthly,
    FinanceState,
    MonthAgg,
    TaxYearAgg,
    YearMonthlyChannels,
)


def _new_id() -> str:
    return str(uuid.uuid4())


def _num(v: Any, fallback: float = 0.0) -> float:
    """Parse a value as a non-negative number. Handles comma-separated strings."""
    if isinstance(v, (int, float)) and math.isfinite(v):
        return float(v)
    if isinstance(v, str) and v.strip():
        cleaned = v.replace(",", "")
        try:
            n = float(cleaned)
            if math.isfinite(n):
                return n
        except ValueError:
            pass
    return fallback


def _normalize_wechat_by_year(raw: Any) -> dict[str, MonthAgg]:
    """Parse a year-keyed object of {income, expense}."""
    if raw is None or not isinstance(raw, dict):
        return {}
    out: dict[str, MonthAgg] = {}
    for y, v in raw.items():
        if not isinstance(v, dict):
            continue
        out[str(y)] = MonthAgg(
            income=max(0.0, _num(v.get("income"))),
            expense=max(0.0, _num(v.get("expense"))),
        )
    return out


def _normalize_month_key(m: str) -> int | None:
    """Validate that a key is a month number 1-12."""
    try:
        n = int(str(m).strip())
    except ValueError:
        return None
    if n < 1 or n > 12:
        return None
    return n


def _normalize_month_channel_map(raw: Any) -> dict[str, MonthAgg]:
    """Parse a single channel's month-keyed {income, expense} map."""
    if raw is None or not isinstance(raw, dict):
        return {}
    out: dict[str, MonthAgg] = {}
    for mk, v in raw.items():
        mo = _normalize_month_key(mk)
        if mo is None or not isinstance(v, dict):
            continue
        out[str(mo)] = MonthAgg(
            income=max(0.0, _num(v.get("income"))),
            expense=max(0.0, _num(v.get("expense"))),
        )
    return out


def normalize_year_monthly_block(raw: Any) -> YearMonthlyChannels:
    """Parse one year's {wechat, alipay, bank} channel block."""
    if raw is None or not isinstance(raw, dict):
        return YearMonthlyChannels()
    return YearMonthlyChannels(
        wechat=ChannelMonthly(months=_normalize_month_channel_map(raw.get("wechat"))),
        alipay=ChannelMonthly(months=_normalize_month_channel_map(raw.get("alipay"))),
        bank=ChannelMonthly(months=_normalize_month_channel_map(raw.get("bank"))),
    )


def normalize_monthly_by_year(raw: Any) -> dict[str, YearMonthlyChannels]:
    """Parse the entire monthlyByYear tree."""
    if raw is None or not isinstance(raw, dict):
        return {}
    out: dict[str, YearMonthlyChannels] = {}
    for year, v in raw.items():
        y = str(year).strip()
        if not y:
            continue
        out[y] = normalize_year_monthly_block(v)
    return out


def _bank_from_entry(e: dict[str, Any]) -> BankSpendRow | None:
    """Parse a single bank entry from on-disk format."""
    label = str(e.get("label", "")).strip()
    if not label:
        return None
    year = _num(e.get("year"), float("nan"))
    if not math.isfinite(year) or year < 1990 or year > 2100:
        return None

    income = 0.0
    expense = 0.0
    monthly: dict[str, MonthAgg] | None = None

    if "monthly" in e and isinstance(e["monthly"], dict):
        monthly = {}
        for m, v in e["monthly"].items():
            mo = _normalize_month_key(m)
            if mo is None or not isinstance(v, dict):
                continue
            m_income = max(0.0, _num(v.get("income")))
            m_expense = max(0.0, _num(v.get("expense")))
            income += m_income
            expense += m_expense
            monthly[str(mo)] = MonthAgg(income=m_income, expense=m_expense)
    else:
        income = max(0.0, _num(e.get("income")))
        expense_raw = _num(e.get("expense")) if "expense" in e else _num(e.get("amount"))
        expense = max(0.0, expense_raw)

    row_id = str(e.get("id", "")).strip() or _new_id()
    return BankSpendRow(
        id=row_id,
        label=label,
        year=int(year),
        amount=round(expense, 2),
        income=round(income, 2),
        monthly=monthly,
    )


def _normalize_banks(raw: Any) -> list[BankSpendRow]:
    """Parse a banks array."""
    if not isinstance(raw, list):
        return []
    rows: list[BankSpendRow] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        row = _bank_from_entry(item)
        if row:
            rows.append(row)
    return rows


def _normalize_tax_by_year(raw: Any) -> dict[str, TaxYearAgg]:
    """Parse taxByYear data."""
    if raw is None or not isinstance(raw, dict):
        return {}
    out: dict[str, TaxYearAgg] = {}
    for y, v in raw.items():
        if not isinstance(v, dict):
            continue
        out[str(y)] = TaxYearAgg(
            income=max(0.0, _num(v.get("income"))),
            tax_paid=max(0.0, _num(v.get("taxPaid"))),
            tax_refund=max(0.0, _num(v.get("taxRefund"))),
        )
    return out


def compute_yearly_from_monthly(
    monthly_by_year: dict[str, YearMonthlyChannels],
) -> tuple[dict[str, MonthAgg], dict[str, MonthAgg]]:
    """Compute yearly WeChat and Alipay aggregates from monthly data."""
    wechat_by_year: dict[str, MonthAgg] = {}
    alipay_by_year: dict[str, MonthAgg] = {}

    for year, channels in monthly_by_year.items():
        w_income = sum(m.income for m in channels.wechat.months.values())
        w_expense = sum(m.expense for m in channels.wechat.months.values())
        a_income = sum(m.income for m in channels.alipay.months.values())
        a_expense = sum(m.expense for m in channels.alipay.months.values())

        if w_income > 0 or w_expense > 0:
            wechat_by_year[year] = MonthAgg(
                income=round(w_income, 2),
                expense=round(w_expense, 2),
            )
        if a_income > 0 or a_expense > 0:
            alipay_by_year[year] = MonthAgg(
                income=round(a_income, 2),
                expense=round(a_expense, 2),
            )

    return wechat_by_year, alipay_by_year


def _normalize_legacy_bank_rows(raw: list[Any]) -> list[BankSpendRow]:
    """Parse legacy bankRows field for backward compatibility."""
    rows: list[BankSpendRow] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label", "")).strip()
        year = _num(item.get("year"), float("nan"))
        if not math.isfinite(year) or year < 1990 or year > 2100:
            continue
        income = max(0.0, _num(item.get("income")))
        amount = max(0.0, _num(item.get("amount")))
        row_id = str(item.get("id", "")).strip() or _new_id()
        rows.append(
            BankSpendRow(
                id=row_id,
                label=label,
                year=int(year),
                amount=amount,
                income=income,
            )
        )
    return rows


def parse_json_text(text: str) -> tuple[bool, FinanceState | None, list[str], str | None]:
    """Parse a single JSON file text into a FinanceState.

    Returns (ok, state, warnings, error).
    """
    warnings: list[str] = []

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return False, None, [], "JSON 格式无效，无法解析"

    if data is None or not isinstance(data, dict):
        return False, None, [], "根节点必须是 JSON 对象"

    if data.get("version") != 1:
        return False, None, [], "缺少或错误的 version 字段，需要 version: 1"

    if "alipayByYear" in data and not isinstance(data["alipayByYear"], dict):
        return False, None, [], "alipayByYear 必须是对象"

    if "monthlyByYear" in data and not isinstance(data["monthlyByYear"], dict):
        return False, None, [], "monthlyByYear 必须是对象"

    monthly_by_year = normalize_monthly_by_year(data.get("monthlyByYear"))

    # Merge bank monthly data into monthly_by_year
    if isinstance(data.get("banks"), list):
        for b in data["banks"]:
            if isinstance(b, dict) and isinstance(b.get("monthly"), dict):
                year = str(b["year"])
                if year not in monthly_by_year:
                    monthly_by_year[year] = YearMonthlyChannels()
                bank_monthly = monthly_by_year[year].bank.months
                for m, v in b["monthly"].items():
                    mo = _normalize_month_key(m)
                    if mo is None or not isinstance(v, dict):
                        continue
                    m_key = str(mo)
                    cur = bank_monthly.get(m_key, MonthAgg())
                    bank_monthly[m_key] = MonthAgg(
                        income=round(cur.income + max(0.0, _num(v.get("income"))), 2),
                        expense=round(cur.expense + max(0.0, _num(v.get("expense"))), 2),
                    )

    computed_wechat, computed_alipay = compute_yearly_from_monthly(monthly_by_year)

    # Monthly-derived totals take precedence
    wechat_by_year = {**_normalize_wechat_by_year(data.get("wechatByYear")), **computed_wechat}
    alipay_by_year = {**_normalize_wechat_by_year(data.get("alipayByYear")), **computed_alipay}
    tax_by_year = _normalize_tax_by_year(data.get("taxByYear"))
    bank_rows = _normalize_banks(data.get("banks"))

    if (
        not wechat_by_year
        and data.get("wechatByYear") is not None
        and isinstance(data["wechatByYear"], dict)
    ):
        warnings.append("wechatByYear 存在但未解析出任何年份，请检查键名与 income/expense 是否为数字")

    if "banks" in data and not isinstance(data["banks"], list):
        return False, None, [], "banks 必须是数组"

    if isinstance(data.get("banks"), list) and data["banks"] and not bank_rows:
        warnings.append("banks 数组非空但未解析出有效行，请检查每行是否包含 year、label、income、expense")

    if not bank_rows and isinstance(data.get("bankRows"), list):
        bank_rows = _normalize_legacy_bank_rows(data["bankRows"])
        if bank_rows:
            warnings.append("已兼容旧字段 bankRows，建议改为使用 banks 并采用 expense 表示支出")

    if (
        not wechat_by_year
        and not alipay_by_year
        and not monthly_by_year
        and not bank_rows
        and not warnings
    ):
        warnings.append("数据为空：可在 JSON 中填写 wechatByYear、alipayByYear、monthlyByYear 与 banks")

    last_wechat_import_at = None
    if isinstance(data.get("lastWechatImportAt"), str) and data["lastWechatImportAt"].strip():
        last_wechat_import_at = data["lastWechatImportAt"].strip()

    state = FinanceState(
        version=1,
        wechat_by_year=wechat_by_year,
        alipay_by_year=alipay_by_year,
        bank_rows=bank_rows,
        monthly_by_year=monthly_by_year,
        tax_by_year=tax_by_year,
        last_wechat_import_at=last_wechat_import_at,
    )
    return True, state, warnings, None


def merge_states(states: list[FinanceState]) -> FinanceState:
    """Deep-merge multiple FinanceState objects."""
    merged = FinanceState()
    all_warnings: list[str] = []

    for s in states:
        merged.wechat_by_year.update(s.wechat_by_year)
        merged.alipay_by_year.update(s.alipay_by_year)
        merged.tax_by_year.update(s.tax_by_year)
        merged.bank_rows.extend(s.bank_rows)

        if s.last_wechat_import_at:
            merged.last_wechat_import_at = s.last_wechat_import_at

        for year, channels in s.monthly_by_year.items():
            if year not in merged.monthly_by_year:
                merged.monthly_by_year[year] = YearMonthlyChannels()
            merged.monthly_by_year[year].wechat.months.update(channels.wechat.months)
            merged.monthly_by_year[year].alipay.months.update(channels.alipay.months)
            merged.monthly_by_year[year].bank.months.update(channels.bank.months)

    return merged


def load_all_data(data_dir: str | Path) -> tuple[FinanceState | None, list[str]]:
    """Load all JSON files from the data directory.

    Scans data/ for wechat.json, alipay.json, tax.json, and all *.json
    under data/banks/. No hardcoded bank list needed.

    Returns (state, warnings).
    """
    data_path = Path(data_dir)
    if not data_path.exists():
        return None, [f"数据目录不存在: {data_dir}"]

    states: list[FinanceState] = []
    all_warnings: list[str] = []

    # Core files
    core_files = ["wechat.json", "alipay.json", "tax.json"]
    for filename in core_files:
        filepath = data_path / filename
        if filepath.is_file():
            ok, state, warnings, error = parse_json_text(filepath.read_text(encoding="utf-8"))
            if ok and state:
                states.append(state)
                all_warnings.extend(warnings)
            elif error:
                all_warnings.append(f"{filename}: {error}")

    # Bank files
    banks_dir = data_path / "banks"
    if banks_dir.is_dir():
        for filepath in sorted(banks_dir.glob("*.json")):
            ok, state, warnings, error = parse_json_text(filepath.read_text(encoding="utf-8"))
            if ok and state:
                states.append(state)
                all_warnings.extend(warnings)
            elif error:
                all_warnings.append(f"banks/{filepath.name}: {error}")

    if not states:
        return None, all_warnings

    merged = merge_states(states)
    return merged, all_warnings


def state_to_disk_json(state: FinanceState) -> str:
    """Export current state as a merged FinanceDataFileV1 JSON string.

    Omits yearly aggregates that can be derived from monthlyByYear,
    and deducts bank monthly data from the aggregated monthlyByYear.bank.
    """
    computed_wechat, computed_alipay = compute_yearly_from_monthly(state.monthly_by_year)

    # Filter out yearly totals that can be derived from monthly data
    wechat_by_year: dict[str, dict[str, float]] = {}
    for y, v in state.wechat_by_year.items():
        if y not in computed_wechat:
            wechat_by_year[y] = {"income": v.income, "expense": v.expense}

    alipay_by_year: dict[str, dict[str, float]] = {}
    for y, v in state.alipay_by_year.items():
        if y not in computed_alipay:
            alipay_by_year[y] = {"income": v.income, "expense": v.expense}

    # Deduct bank monthly data from aggregated bank monthly
    monthly_by_year: dict[str, dict[str, dict[str, dict[str, float]]]] = {}
    for y, channels in state.monthly_by_year.items():
        filtered_bank = dict(channels.bank.months)

        for row in state.bank_rows:
            if str(row.year) == y and row.monthly:
                for m, v in row.monthly.items():
                    if m in filtered_bank:
                        cur = filtered_bank[m]
                        new_income = max(0.0, cur.income - v.income)
                        new_expense = max(0.0, cur.expense - v.expense)
                        if new_income == 0 and new_expense == 0:
                            del filtered_bank[m]
                        else:
                            filtered_bank[m] = MonthAgg(income=new_income, expense=new_expense)

        monthly_by_year[y] = {
            "wechat": {m: {"income": v.income, "expense": v.expense} for m, v in channels.wechat.months.items()},
            "alipay": {m: {"income": v.income, "expense": v.expense} for m, v in channels.alipay.months.items()},
            "bank": {m: {"income": v.income, "expense": v.expense} for m, v in filtered_bank.items()},
        }

    banks = []
    for r in state.bank_rows:
        entry: dict[str, Any] = {"label": r.label, "year": r.year, "id": r.id}
        if r.monthly:
            entry["monthly"] = {m: {"income": v.income, "expense": v.expense} for m, v in r.monthly.items()}
        else:
            entry["income"] = r.income
            entry["expense"] = r.amount
        banks.append(entry)

    file_data: dict[str, Any] = {
        "version": 1,
        "wechatByYear": wechat_by_year,
        "alipayByYear": alipay_by_year,
        "monthlyByYear": monthly_by_year,
        "banks": banks,
        "taxByYear": {y: {"income": v.income, "taxPaid": v.tax_paid, "taxRefund": v.tax_refund} for y, v in state.tax_by_year.items()},
    }
    if state.last_wechat_import_at:
        file_data["lastWechatImportAt"] = state.last_wechat_import_at

    return json.dumps(file_data, ensure_ascii=False, indent=2) + "\n"
