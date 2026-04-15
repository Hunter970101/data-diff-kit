# Data Diff Kit

**[▶ Live Demo](https://data-diff-kit-hjt4f4jzi2b6el7fn2zwk6.streamlit.app/)** — try it in your browser, no install needed.

A Python toolkit for comparing expected vs. actual data outputs, with intelligent differentiation between **real value errors** and **format-only differences**.

## The Problem

When validating data pipelines, model outputs, or ETL results, raw field-by-field comparison produces noisy reports flooded with false positives — a date stored as `2024-01-15` vs `01/15/2024` isn't a real error, but a naive diff flags it as one.

**Data Diff Kit** solves this by classifying every mismatch into:

- **Value Mismatch** — the data is actually wrong (e.g., amount `1500` vs `1800`)
- **Format Difference** — same value, different representation (e.g., `$1,500.00` vs `1500`)
- **Match** — fields are identical

## Features

- Compare CSV, Excel, or JSON data files side by side
- Smart format-aware diffing: normalizes dates, numbers, currency, whitespace, and casing before comparison
- Configurable tolerance for numeric comparisons
- Structured accuracy report with per-field breakdown
- Visual heatmap showing error distribution across fields
- CLI interface for quick use
- Clean Python API for integration

## Quick Start

### Install

```bash
pip install -r requirements.txt
```

### Run with sample data

```bash
python -m data_diff_kit.cli sample_data/expected.csv sample_data/actual.csv --report output_report.html
```

### Use as a library

```python
from data_diff_kit.comparator import DataComparator

comparator = DataComparator()
result = comparator.compare("expected.csv", "actual.csv")

print(f"Overall Accuracy: {result.accuracy:.1%}")
print(f"Value Mismatches: {result.value_mismatch_count}")
print(f"Format-Only Diffs: {result.format_diff_count}")

# Generate visual report
result.to_html("report.html")
```

## Accuracy Report

The generated report includes:

- **Summary stats** — overall accuracy, total comparisons, mismatch counts
- **Per-field breakdown** — which fields have the most errors
- **Difference detail table** — every mismatch with row/column location, expected vs actual values, and classification
- **Heatmap visualization** — spot error patterns at a glance

## Project Structure

```
data-diff-kit/
├── data_diff_kit/
│   ├── __init__.py
│   ├── comparator.py      # Core comparison engine
│   ├── normalizers.py      # Format normalization functions
│   ├── report.py           # Report generation & visualization
│   └── cli.py              # Command-line interface
├── tests/
│   ├── test_comparator.py
│   └── test_normalizers.py
├── sample_data/
│   ├── expected.csv
│   └── actual.csv
├── requirements.txt
└── README.md
```

## Configuration

```python
comparator = DataComparator(
    numeric_tolerance=0.01,       # Allow 1% difference for numeric fields
    case_sensitive=False,          # Ignore casing differences
    normalize_dates=True,          # Treat different date formats as equal
    normalize_whitespace=True,     # Strip extra spaces
    normalize_currency=True,       # Remove currency symbols for comparison
)
```

## License

MIT
