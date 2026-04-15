"""
Comparator: the core engine that compares two datasets field-by-field
and classifies each difference.
"""

import pandas as pd
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .normalizers import ValueNormalizer


# ---------------------------------------------------------------------------
# Result data classes
# ---------------------------------------------------------------------------

@dataclass
class CellDiff:
    """A single cell-level difference."""
    row: int
    column: str
    expected: str
    actual: str
    diff_type: str  # "value_mismatch" | "format_diff"


@dataclass
class FieldStats:
    """Accuracy stats for one column."""
    column: str
    total: int
    matches: int
    format_diffs: int
    value_mismatches: int

    @property
    def accuracy(self) -> float:
        return self.matches / self.total if self.total > 0 else 1.0

    @property
    def strict_accuracy(self) -> float:
        """Accuracy counting format diffs as errors too."""
        return self.matches / self.total if self.total > 0 else 1.0

    @property
    def lenient_accuracy(self) -> float:
        """Accuracy treating format diffs as acceptable."""
        return (self.matches + self.format_diffs) / self.total if self.total > 0 else 1.0


@dataclass
class ComparisonResult:
    """Full comparison result with stats, diffs, and reporting helpers."""
    total_cells: int = 0
    match_count: int = 0
    format_diff_count: int = 0
    value_mismatch_count: int = 0
    diffs: list = field(default_factory=list)
    field_stats: dict = field(default_factory=dict)
    expected_df: Optional[pd.DataFrame] = None
    actual_df: Optional[pd.DataFrame] = None

    @property
    def accuracy(self) -> float:
        """Lenient accuracy (format diffs = OK)."""
        good = self.match_count + self.format_diff_count
        return good / self.total_cells if self.total_cells > 0 else 1.0

    @property
    def strict_accuracy(self) -> float:
        """Strict accuracy (format diffs = error)."""
        return self.match_count / self.total_cells if self.total_cells > 0 else 1.0

    def summary(self) -> str:
        lines = [
            "=" * 50,
            "  DATA DIFF KIT — Comparison Summary",
            "=" * 50,
            f"  Total cells compared : {self.total_cells}",
            f"  Exact matches        : {self.match_count}",
            f"  Format-only diffs    : {self.format_diff_count}",
            f"  Value mismatches     : {self.value_mismatch_count}",
            "-" * 50,
            f"  Lenient accuracy     : {self.accuracy:.1%}",
            f"  Strict accuracy      : {self.strict_accuracy:.1%}",
            "=" * 50,
        ]
        return "\n".join(lines)

    def diffs_to_dataframe(self) -> pd.DataFrame:
        if not self.diffs:
            return pd.DataFrame(columns=["row", "column", "expected", "actual", "diff_type"])
        return pd.DataFrame([
            {
                "row": d.row,
                "column": d.column,
                "expected": d.expected,
                "actual": d.actual,
                "diff_type": d.diff_type,
            }
            for d in self.diffs
        ])

    def to_html(self, path: str):
        """Generate an HTML accuracy report (delegates to report module)."""
        from .report import generate_html_report
        generate_html_report(self, path)


# ---------------------------------------------------------------------------
# File loaders
# ---------------------------------------------------------------------------

def _load_file(path: str) -> pd.DataFrame:
    """Load CSV, Excel, or JSON into a DataFrame."""
    p = Path(path)
    suffix = p.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(p, dtype=str, keep_default_na=False)
    elif suffix in (".xlsx", ".xls"):
        return pd.read_excel(p, dtype=str, keep_default_na=False)
    elif suffix == ".json":
        return pd.read_json(p, dtype=str)
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Use .csv, .xlsx, or .json")


# ---------------------------------------------------------------------------
# Comparator
# ---------------------------------------------------------------------------

class DataComparator:
    """Compare two tabular datasets with format-aware diffing."""

    def __init__(
        self,
        numeric_tolerance: float = 0.0,
        case_sensitive: bool = False,
        normalize_dates: bool = True,
        normalize_whitespace: bool = True,
        normalize_currency: bool = True,
    ):
        self.normalizer = ValueNormalizer(
            normalize_dates=normalize_dates,
            normalize_numbers=True,
            normalize_currency=normalize_currency,
            normalize_ws=normalize_whitespace,
            case_sensitive=case_sensitive,
            numeric_tolerance=numeric_tolerance,
        )

    def compare(
        self,
        expected: str | pd.DataFrame,
        actual: str | pd.DataFrame,
        key_column: Optional[str] = None,
    ) -> ComparisonResult:
        """Compare expected vs actual data.

        Args:
            expected: file path or DataFrame with expected values
            actual: file path or DataFrame with actual values
            key_column: optional column to align rows by (like a primary key)

        Returns:
            ComparisonResult with full diff details
        """
        # Load data
        df_exp = _load_file(expected) if isinstance(expected, str) else expected.copy()
        df_act = _load_file(actual) if isinstance(actual, str) else actual.copy()

        # Align by key if provided
        if key_column:
            df_exp = df_exp.set_index(key_column).sort_index()
            df_act = df_act.set_index(key_column).sort_index()

        # Use shared columns only
        shared_cols = [c for c in df_exp.columns if c in df_act.columns]
        if not shared_cols:
            raise ValueError("No overlapping columns found between expected and actual data.")

        df_exp = df_exp[shared_cols].reset_index(drop=True)
        df_act = df_act[shared_cols].reset_index(drop=True)

        # Ensure same row count (compare up to the shorter)
        n_rows = min(len(df_exp), len(df_act))
        df_exp = df_exp.iloc[:n_rows]
        df_act = df_act.iloc[:n_rows]

        # Initialize result
        result = ComparisonResult(
            expected_df=df_exp,
            actual_df=df_act,
        )

        # Field-level stats
        for col in shared_cols:
            result.field_stats[col] = FieldStats(
                column=col, total=0, matches=0, format_diffs=0, value_mismatches=0
            )

        # Cell-by-cell comparison
        for row_idx in range(n_rows):
            for col in shared_cols:
                exp_val = str(df_exp.at[row_idx, col])
                act_val = str(df_act.at[row_idx, col])

                result.total_cells += 1
                result.field_stats[col].total += 1

                if exp_val == act_val:
                    # Exact match
                    result.match_count += 1
                    result.field_stats[col].matches += 1
                elif self.normalizer.normalize(exp_val) == self.normalizer.normalize(act_val):
                    # Format-only difference
                    result.format_diff_count += 1
                    result.field_stats[col].format_diffs += 1
                    result.diffs.append(CellDiff(
                        row=row_idx,
                        column=col,
                        expected=exp_val,
                        actual=act_val,
                        diff_type="format_diff",
                    ))
                else:
                    # Real value mismatch
                    result.value_mismatch_count += 1
                    result.field_stats[col].value_mismatches += 1
                    result.diffs.append(CellDiff(
                        row=row_idx,
                        column=col,
                        expected=exp_val,
                        actual=act_val,
                        diff_type="value_mismatch",
                    ))

        return result
