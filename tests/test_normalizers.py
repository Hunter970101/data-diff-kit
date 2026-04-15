"""Tests for the normalization functions."""

import pytest
from data_diff_kit.normalizers import (
    normalize_date,
    normalize_number,
    normalize_whitespace,
    normalize_case,
    ValueNormalizer,
)


class TestNormalizeDate:
    def test_iso_format(self):
        assert normalize_date("2024-01-15") == "2024-01-15"

    def test_us_format(self):
        assert normalize_date("01/15/2024") == "2024-01-15"

    def test_eu_format(self):
        assert normalize_date("15-01-2024") == "2024-01-15"

    def test_long_month(self):
        assert normalize_date("January 15, 2024") == "2024-01-15"

    def test_short_month(self):
        assert normalize_date("Jan 15, 2024") == "2024-01-15"

    def test_compact_format(self):
        assert normalize_date("20240115") == "2024-01-15"

    def test_not_a_date(self):
        assert normalize_date("hello world") is None

    def test_empty_string(self):
        assert normalize_date("") is None


class TestNormalizeNumber:
    def test_plain_integer(self):
        assert normalize_number("1500") == "1500"

    def test_with_thousands_separator(self):
        assert normalize_number("1,500") == "1500"

    def test_with_dollar_sign(self):
        assert normalize_number("$1,500.00") == "1500"

    def test_with_euro_sign(self):
        assert normalize_number("€6,300.00") == "6300"

    def test_decimal(self):
        assert normalize_number("128.02") == "128.02"

    def test_percentage(self):
        assert normalize_number("50%") == "0.5"

    def test_not_a_number(self):
        assert normalize_number("hello") is None

    def test_tolerance(self):
        # With tolerance, 1500 and 1501 should normalize close
        assert normalize_number("1500", tolerance=0.01) == "1500"

    def test_negative(self):
        assert normalize_number("-42.5") == "-42.5"


class TestNormalizeWhitespace:
    def test_extra_spaces(self):
        assert normalize_whitespace("  hello   world  ") == "hello world"

    def test_tabs_and_newlines(self):
        assert normalize_whitespace("hello\t\nworld") == "hello world"

    def test_already_clean(self):
        assert normalize_whitespace("hello world") == "hello world"


class TestNormalizeCase:
    def test_uppercase(self):
        assert normalize_case("APPROVED") == "approved"

    def test_mixed_case(self):
        assert normalize_case("Pending") == "pending"


class TestValueNormalizer:
    def test_dates_normalized(self):
        norm = ValueNormalizer()
        assert norm.normalize("2024-01-15") == norm.normalize("01/15/2024")

    def test_currency_normalized(self):
        norm = ValueNormalizer()
        assert norm.normalize("$1,500.00") == norm.normalize("1500")

    def test_case_normalized(self):
        norm = ValueNormalizer(case_sensitive=False)
        assert norm.normalize("Approved") == norm.normalize("approved")

    def test_case_sensitive(self):
        norm = ValueNormalizer(case_sensitive=True)
        assert norm.normalize("Approved") != norm.normalize("approved")

    def test_whitespace_normalized(self):
        norm = ValueNormalizer()
        assert norm.normalize("  Approved  ") == norm.normalize("Approved")

    def test_plain_string_passthrough(self):
        norm = ValueNormalizer()
        result = norm.normalize("Acme Corp")
        assert result == "acme corp"
