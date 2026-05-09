def format_cny(n: float) -> str:
    """Format a number as CNY currency string."""
    if n >= 0:
        return f"¥{n:,.2f}"
    return f"-¥{abs(n):,.2f}"
