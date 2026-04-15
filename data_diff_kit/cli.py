"""
CLI: command-line interface for Data Diff Kit.

Usage:
    python -m data_diff_kit.cli expected.csv actual.csv [options]
"""

import argparse
import sys

from .comparator import DataComparator


def main():
    parser = argparse.ArgumentParser(
        prog="data-diff-kit",
        description="Compare expected vs actual data outputs with smart format-aware diffing.",
    )
    parser.add_argument("expected", help="Path to expected output file (CSV, Excel, or JSON)")
    parser.add_argument("actual", help="Path to actual output file (CSV, Excel, or JSON)")
    parser.add_argument("--key", "-k", help="Column name to use as row key for alignment")
    parser.add_argument("--report", "-r", help="Path to write HTML accuracy report")
    parser.add_argument("--tolerance", "-t", type=float, default=0.0,
                        help="Numeric tolerance (e.g., 0.01 for 1%%)")
    parser.add_argument("--case-sensitive", action="store_true",
                        help="Treat casing differences as real mismatches")
    parser.add_argument("--no-date-norm", action="store_true",
                        help="Disable date format normalization")
    parser.add_argument("--no-currency-norm", action="store_true",
                        help="Disable currency symbol normalization")

    args = parser.parse_args()

    comparator = DataComparator(
        numeric_tolerance=args.tolerance,
        case_sensitive=args.case_sensitive,
        normalize_dates=not args.no_date_norm,
        normalize_currency=not args.no_currency_norm,
    )

    try:
        result = comparator.compare(args.expected, args.actual, key_column=args.key)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Print summary to terminal
    print(result.summary())
    print()

    # Show top mismatches
    diffs_df = result.diffs_to_dataframe()
    value_mismatches = diffs_df[diffs_df["diff_type"] == "value_mismatch"]
    if len(value_mismatches) > 0:
        print(f"Top value mismatches (showing up to 10):")
        print(value_mismatches.head(10).to_string(index=False))
        print()

    # Generate HTML report if requested
    if args.report:
        result.to_html(args.report)
        print(f"HTML report saved to: {args.report}")


if __name__ == "__main__":
    main()
