"""
Report: generates visual HTML accuracy reports with charts and heatmaps.
"""

import io
import base64
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd


def _fig_to_base64(fig) -> str:
    """Convert a matplotlib figure to a base64-encoded PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="#1a1a2e")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _make_accuracy_chart(field_stats: dict) -> str:
    """Bar chart of per-field lenient accuracy."""
    cols = list(field_stats.keys())
    accuracies = [field_stats[c].lenient_accuracy * 100 for c in cols]

    fig, ax = plt.subplots(figsize=(max(6, len(cols) * 0.8), 4))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#1a1a2e")

    colors = ["#06d6a0" if a >= 95 else "#ffd166" if a >= 80 else "#ef476f" for a in accuracies]
    bars = ax.bar(cols, accuracies, color=colors, edgecolor="none", width=0.6)

    ax.set_ylim(0, 105)
    ax.set_ylabel("Accuracy %", color="#e0e0e0", fontsize=11)
    ax.set_title("Per-Field Accuracy", color="#e0e0e0", fontsize=13, fontweight="bold")
    ax.tick_params(colors="#e0e0e0", labelsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#333")
    ax.spines["bottom"].set_color("#333")

    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    return _fig_to_base64(fig)


def _make_heatmap(result) -> str:
    """Heatmap of mismatch counts by field × diff type."""
    data = {
        "Field": [],
        "Value Mismatches": [],
        "Format Diffs": [],
    }
    for col, stats in result.field_stats.items():
        data["Field"].append(col)
        data["Value Mismatches"].append(stats.value_mismatches)
        data["Format Diffs"].append(stats.format_diffs)

    df = pd.DataFrame(data).set_index("Field")

    fig, ax = plt.subplots(figsize=(6, max(3, len(df) * 0.5)))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#1a1a2e")

    sns.heatmap(
        df, annot=True, fmt="d", cmap="YlOrRd", linewidths=0.5,
        linecolor="#333", ax=ax, cbar_kws={"shrink": 0.8}
    )
    ax.set_title("Error Distribution Heatmap", color="#e0e0e0", fontsize=13, fontweight="bold")
    ax.tick_params(colors="#e0e0e0", labelsize=10)

    plt.tight_layout()
    return _fig_to_base64(fig)


def _make_diff_type_pie(result) -> str:
    """Pie chart showing match / format diff / value mismatch proportions."""
    labels = ["Exact Match", "Format Diff", "Value Mismatch"]
    sizes = [result.match_count, result.format_diff_count, result.value_mismatch_count]
    colors = ["#06d6a0", "#ffd166", "#ef476f"]

    # Filter out zeros
    filtered = [(l, s, c) for l, s, c in zip(labels, sizes, colors) if s > 0]
    if not filtered:
        return ""
    labels, sizes, colors = zip(*filtered)

    fig, ax = plt.subplots(figsize=(5, 4))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#1a1a2e")

    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=colors, autopct="%1.1f%%",
        textprops={"color": "#e0e0e0", "fontsize": 10},
        wedgeprops={"edgecolor": "#1a1a2e", "linewidth": 2},
    )
    for t in autotexts:
        t.set_fontweight("bold")

    ax.set_title("Difference Breakdown", color="#e0e0e0", fontsize=13, fontweight="bold")
    plt.tight_layout()
    return _fig_to_base64(fig)


# ---------------------------------------------------------------------------
# HTML report
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Data Diff Kit — Accuracy Report</title>
<style>
  :root {{
    --bg: #0f0f1a;
    --card: #1a1a2e;
    --border: #2a2a4a;
    --text: #e0e0e0;
    --muted: #8888aa;
    --green: #06d6a0;
    --yellow: #ffd166;
    --red: #ef476f;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'Segoe UI', system-ui, sans-serif;
    padding: 2rem;
    line-height: 1.6;
  }}
  h1 {{
    font-size: 1.8rem;
    margin-bottom: 0.5rem;
    background: linear-gradient(135deg, var(--green), #118ab2);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }}
  .subtitle {{ color: var(--muted); margin-bottom: 2rem; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
  .stat-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.2rem;
  }}
  .stat-card .label {{ font-size: 0.85rem; color: var(--muted); }}
  .stat-card .value {{ font-size: 1.8rem; font-weight: 700; margin-top: 0.3rem; }}
  .green {{ color: var(--green); }}
  .yellow {{ color: var(--yellow); }}
  .red {{ color: var(--red); }}
  .chart-row {{ display: flex; flex-wrap: wrap; gap: 1.5rem; margin-bottom: 2rem; }}
  .chart-row img {{ border-radius: 12px; max-width: 100%; }}
  table {{
    width: 100%;
    border-collapse: collapse;
    background: var(--card);
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 2rem;
  }}
  th, td {{ padding: 0.7rem 1rem; text-align: left; border-bottom: 1px solid var(--border); font-size: 0.9rem; }}
  th {{ background: #16163a; color: var(--muted); font-weight: 600; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.5px; }}
  .tag {{
    display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600;
  }}
  .tag.value_mismatch {{ background: rgba(239,71,111,0.2); color: var(--red); }}
  .tag.format_diff {{ background: rgba(255,209,102,0.2); color: var(--yellow); }}
</style>
</head>
<body>

<h1>Data Diff Kit</h1>
<p class="subtitle">Accuracy Report — {total_rows} rows × {total_cols} columns</p>

<div class="grid">
  <div class="stat-card">
    <div class="label">Total Cells</div>
    <div class="value">{total_cells}</div>
  </div>
  <div class="stat-card">
    <div class="label">Exact Matches</div>
    <div class="value green">{match_count}</div>
  </div>
  <div class="stat-card">
    <div class="label">Format Diffs</div>
    <div class="value yellow">{format_diff_count}</div>
  </div>
  <div class="stat-card">
    <div class="label">Value Mismatches</div>
    <div class="value red">{value_mismatch_count}</div>
  </div>
  <div class="stat-card">
    <div class="label">Lenient Accuracy</div>
    <div class="value green">{lenient_accuracy}</div>
  </div>
  <div class="stat-card">
    <div class="label">Strict Accuracy</div>
    <div class="value">{strict_accuracy}</div>
  </div>
</div>

<div class="chart-row">
  <img src="data:image/png;base64,{pie_chart}" alt="Breakdown" />
  <img src="data:image/png;base64,{accuracy_chart}" alt="Per-field accuracy" />
</div>

<h2 style="margin-bottom:1rem;">Error Heatmap</h2>
<div style="margin-bottom:2rem;">
  <img src="data:image/png;base64,{heatmap}" alt="Heatmap" style="border-radius:12px;" />
</div>

<h2 style="margin-bottom:1rem;">Difference Details</h2>
{diff_table}

</body>
</html>
"""


def generate_html_report(result, path: str):
    """Write a self-contained HTML report to *path*."""

    # Build diff table
    diffs_df = result.diffs_to_dataframe()
    if len(diffs_df) > 0:
        rows_html = []
        for _, r in diffs_df.iterrows():
            tag_class = r["diff_type"]
            tag_label = "VALUE MISMATCH" if r["diff_type"] == "value_mismatch" else "FORMAT DIFF"
            rows_html.append(
                f"<tr><td>{r['row']}</td><td>{r['column']}</td>"
                f"<td>{r['expected']}</td><td>{r['actual']}</td>"
                f'<td><span class="tag {tag_class}">{tag_label}</span></td></tr>'
            )
        diff_table = (
            "<table><thead><tr><th>Row</th><th>Column</th><th>Expected</th>"
            "<th>Actual</th><th>Type</th></tr></thead><tbody>"
            + "\n".join(rows_html)
            + "</tbody></table>"
        )
    else:
        diff_table = '<p style="color:var(--green);">No differences found!</p>'

    # Generate charts
    pie_chart = _make_diff_type_pie(result)
    accuracy_chart = _make_accuracy_chart(result.field_stats)
    heatmap = _make_heatmap(result)

    n_rows = len(result.expected_df) if result.expected_df is not None else 0
    n_cols = len(result.field_stats)

    html = _HTML_TEMPLATE.format(
        total_rows=n_rows,
        total_cols=n_cols,
        total_cells=result.total_cells,
        match_count=result.match_count,
        format_diff_count=result.format_diff_count,
        value_mismatch_count=result.value_mismatch_count,
        lenient_accuracy=f"{result.accuracy:.1%}",
        strict_accuracy=f"{result.strict_accuracy:.1%}",
        pie_chart=pie_chart,
        accuracy_chart=accuracy_chart,
        heatmap=heatmap,
        diff_table=diff_table,
    )

    Path(path).write_text(html, encoding="utf-8")
