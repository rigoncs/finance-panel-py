from dataclasses import dataclass, field


@dataclass
class MonthAgg:
    income: float = 0.0
    expense: float = 0.0


@dataclass
class ChannelMonthly:
    months: dict[str, MonthAgg] = field(default_factory=dict)


@dataclass
class YearMonthlyChannels:
    wechat: ChannelMonthly = field(default_factory=ChannelMonthly)
    alipay: ChannelMonthly = field(default_factory=ChannelMonthly)
    bank: ChannelMonthly = field(default_factory=ChannelMonthly)


@dataclass
class BankSpendRow:
    id: str
    label: str
    year: int
    amount: float = 0.0
    income: float = 0.0
    monthly: dict[str, MonthAgg] | None = None


@dataclass
class TaxYearAgg:
    income: float = 0.0
    tax_paid: float = 0.0
    tax_refund: float = 0.0


@dataclass
class FinanceState:
    version: int = 1
    wechat_by_year: dict[str, MonthAgg] = field(default_factory=dict)
    alipay_by_year: dict[str, MonthAgg] = field(default_factory=dict)
    bank_rows: list[BankSpendRow] = field(default_factory=list)
    monthly_by_year: dict[str, YearMonthlyChannels] = field(default_factory=dict)
    tax_by_year: dict[str, TaxYearAgg] = field(default_factory=dict)
    last_wechat_import_at: str | None = None
