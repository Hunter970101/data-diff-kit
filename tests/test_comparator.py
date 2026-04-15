"""Tests for the DataComparator."""

import pytest
import pandas as pd
from data_diff_kit.comparator import DataComparator


@pytest.fixture
def sample_expected():
    return pd.DataFrame({
        "id": ["001", "002", "003"],
        "name": ["Acme Corp", "Global Trading", "Tech Ltd"],
        "date": ["2024-01-15", "2024-02-20", "2024-03-10"],
        "amount": ["1500.00", "3200.50", "8750.00"],
        "status": ["Approved", "Pending", "Approved"],
    })


@pytest.fixture
def sample_actual():
    return pd.DataFrame({
        "id": ["001", "002", "003"],
        "name": ["Acme Corp", "global trading", "Tech Ltd"],
        "date": ["01/15/2024", "2024-02-20", "March 10, 2024"],
        "amount": ["$1,500.00", "3200.50", "9000.00"],
        "status": ["Approved", "pending", "Rejected"],
    })


class TestDataComparator:
    def test_basic_comparison(self, sample_expected, sample_actual):
        comp = DataComparator()
        result = comp.compare(sample_expected, sample_actual)

        assert result.total_cells == 15  # 3 rows × 5 cols
        assert result.value_mismatch_count > 0
        assert result.format_diff_count > 0

    def test_exact_match(self):
        df = pd.DataFrame({"a": ["1", "2"], "b": ["x", "y"]})
        comp = DataComparator()
        result = comp.compare(df, df.copy())

        assert result.accuracy == 1.0
        assert result.value_mismatch_count == 0
        assert result.format_diff_count == 0

    def test_format_diffs_detected(self, sample_expected, sample_actual):
        comp = DataComparator()
        result = comp.compare(sample_expected, sample_actual)

        format_diffs = [d for d in result.diffs if d.diff_type == "format_diff"]
        # "global trading" vs "Global Trading" -> format diff (case)
        # "01/15/2024" vs "2024-01-15" -> format diff (date)
        # "$1,500.00" vs "1500.00" -> format diff (currency)
        # "pending" vs "Pending" -> format diff (case)
        # "March 10, 2024" vs "2024-03-10" -> format diff (date)
        assert len(format_diffs) >= 4

    def test_value_mismatches_detected(self, sample_expected, sample_actual):
        comp = DataComparator()
        result = comp.compare(sample_expected, sample_actual)

        value_mismatches = [d for d in result.diffs if d.diff_type == "value_mismatch"]
        # "9000.00" vs "8750.00" -> value mismatch
        # "Rejected" vs "Approved" -> value mismatch
        assert len(value_mismatches) >= 2

    def test_lenient_vs_strict_accuracy(self, sample_expected, sample_actual):
        comp = DataComparator()
        result = comp.compare(sample_expected, sample_actual)

        # Lenient should be >= strict because format diffs are forgiven
        assert result.accuracy >= result.strict_accuracy

    def test_field_stats_populated(self, sample_expected, sample_actual):
        comp = DataComparator()
        result = comp.compare(sample_expected, sample_actual)

        assert "name" in result.field_stats
        assert "amount" in result.field_stats
        assert result.field_stats["name"].total == 3

    def test_summary_string(self, sample_expected, sample_actual):
        comp = DataComparator()
        result = comp.compare(sample_expected, sample_actual)

        summary = result.summary()
        assert "Total cells compared" in summary
        assert "Lenient accuracy" in summary

    def test_numeric_tolerance(self):
        df_exp = pd.DataFrame({"val": ["100.00"]})
        df_act = pd.DataFrame({"val": ["100.50"]})

        # Without tolerance -> mismatch
        comp = DataComparator(numeric_tolerance=0.0)
        result = comp.compare(df_exp, df_act)
        assert result.value_mismatch_count == 1

        # With tolerance -> format diff
        comp = DataComparator(numeric_tolerance=1.0)
        result = comp.compare(df_exp, df_act)
        assert result.value_mismatch_count == 0

    def test_diffs_to_dataframe(self, sample_expected, sample_actual):
        comp = DataComparator()
        result = comp.compare(sample_expected, sample_actual)
        diffs_df = result.diffs_to_dataframe()

        assert isinstance(diffs_df, pd.DataFrame)
        assert "row" in diffs_df.columns
        assert "diff_type" in diffs_df.columns
