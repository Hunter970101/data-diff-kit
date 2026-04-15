"""
Normalizers: functions that strip formatting noise so that comparison
focuses on actual data values rather than cosmetic differences.

Each normalizer takes a raw string and returns a canonical form.
If two raw strings normalize to the same canonical form, the difference
is classified as "format-only" rather than a true value mismatch.
"""

import re
from datetime import datetime
from typing import Optional

# ---------------------------------------------------------------------------
# Date normalization
# ---------------------------------------------------------------------------

_DATE_FORMATS = [
    "%Y-%m-%d",          # 2024-01-15
    "%d/%m/%Y",          # 15/01/2024
    "%m/%d/%Y",          # 01/15/2024
    "%Y/%m/%d",          # 2024/01/15
    "%d-%m-%Y",          # 15-01-2024
    "%m-%d-%Y",          # 01-15-2024
    "%b %d, %Y",         # Jan 15, 2024
    "%B %d, %Y",         # January 15, 2024
    "%d %b %Y",          # 15 Jan 2024
    "%d %B %Y",          # 15 January 2024
    "%Y%m%d",            # 20240115
]


def normalize_date(value: str) -> Optional[str]:
    """Try to parse a date string and return ISO format (YYYY-MM-DD).

    Returns None if the value doesn't look like a date.
    """
    value = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(value, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Numeric / currency normalization
# ---------------------------------------------------------------------------

_CURRENCY_SYMBOLS = re.compile(r"[$€£¥₹￥]")
_THOUSANDS_SEP = re.compile(r"(?<=\d),(?=\d{3})")


def normalize_number(value: str, tolerance: float = 0.0) -> Optional[str]:
    """Strip currency symbols and thousands separators, return a canonical
    numeric string.  Returns None if the value isn't numeric.

    When tolerance > 0, the returned string is rounded so that values within
    tolerance compare as equal.
    """
    cleaned = _CURRENCY_SYMBOLS.sub("", value)
    cleaned = _THOUSANDS_SEP.sub("", cleaned)
    cleaned = cleaned.strip().replace(" ", "")

    # Handle percentage
    is_pct = cleaned.endswith("%")
    if is_pct:
        cleaned = cleaned[:-1]

    try:
        num = float(cleaned)
    except ValueError:
        return None

    if is_pct:
        num = num / 100.0

    if tolerance > 0:
        # Bucket the number by tolerance so values within range compare equal
        num = round(num / tolerance) * tolerance

    # Normalize to remove trailing zeros: 1500.0 -> "1500", 1.50 -> "1.5"
    return f"{num:g}"


# ---------------------------------------------------------------------------
# Whitespace normalization
# ---------------------------------------------------------------------------

def normalize_whitespace(value: str) -> str:
    """Collapse all whitespace to single spaces and strip."""
    return " ".join(value.split())


# ---------------------------------------------------------------------------
# Case normalization
# ---------------------------------------------------------------------------

def normalize_case(value: str) -> str:
    """Lowercase for case-insensitive comparison."""
    return value.lower()


# ---------------------------------------------------------------------------
# Combined normalizer
# ---------------------------------------------------------------------------

class ValueNormalizer:
    """Applies a chain of normalizations based on configuration."""

    def __init__(
        self,
        normalize_dates: bool = True,
        normalize_numbers: bool = True,
        normalize_currency: bool = True,
        normalize_ws: bool = True,
        case_sensitive: bool = False,
        numeric_tolerance: float = 0.0,
    ):
        self.normalize_dates = normalize_dates
        self.normalize_numbers = normalize_numbers
        self.normalize_currency = normalize_currency
        self.normalize_ws = normalize_ws
        self.case_sensitive = case_sensitive
        self.numeric_tolerance = numeric_tolerance

    def normalize(self, value: str) -> str:
        """Return a canonical representation of *value*.

        The order matters: we try date first (most specific pattern),
        then numeric, then fall through to generic string normalization.
        """
        if not isinstance(value, str):
            value = str(value) if value is not None else ""

        # Try date
        if self.normalize_dates:
            date_result = normalize_date(value)
            if date_result is not None:
                return date_result

        # Try numeric / currency
        if self.normalize_numbers or self.normalize_currency:
            num_result = normalize_number(value, self.numeric_tolerance)
            if num_result is not None:
                return num_result

        # Generic string cleanup
        result = value
        if self.normalize_ws:
            result = normalize_whitespace(result)
        if not self.case_sensitive:
            result = normalize_case(result)

        return result
