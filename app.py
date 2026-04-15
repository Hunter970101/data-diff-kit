"""
Data Diff Kit — Streamlit Frontend
Upload two files, compare them, and see the accuracy report interactively.
"""

import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from data_diff_kit.comparator import DataComparator

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Data Diff Kit",
    page_icon="🔍",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Custom styling
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .stMetric {
        background: #1a1a2e;
        border: 1px solid #2a2a4a;
        border-radius: 12px;
        padding: 16px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🔍 Data Diff Kit")
st.markdown("Upload **expected** and **actual** data files to compare them. "
            "The tool intelligently separates **real value errors** from **format-only differences** "
            "(date formats, currency symbols, casing, whitespace).")

st.divider()

# ---------------------------------------------------------------------------
# Sidebar — settings
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Settings")

    numeric_tolerance = st.slider(
        "Numeric tolerance",
        min_value=0.0, max_value=10.0, value=0.0, step=0.01,
        help="Allow small numeric differences. E.g., 0.01 means 100.00 and 100.01 are treated as equal."
    )
    case_sensitive = st.checkbox("Case sensitive", value=False,
                                 help="If checked, 'Approved' vs 'approved' is a real mismatch.")
    normalize_dates = st.checkbox("Normalize dates", value=True,
                                  help="Treat different date formats as the same (e.g., 2024-01-15 vs 01/15/2024).")
    normalize_currency = st.checkbox("Normalize currency", value=True,
                                     help="Strip currency symbols and thousands separators (e.g., $1,500.00 vs 1500).")

    st.divider()
    st.markdown("**Supported formats:** CSV, Excel (.xlsx)")

# ---------------------------------------------------------------------------
# File upload
# ---------------------------------------------------------------------------
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📄 Expected Output")
    expected_file = st.file_uploader("Upload expected file", type=["csv", "xlsx"],
                                      key="expected", label_visibility="collapsed")

with col_right:
    st.subheader("📄 Actual Output")
    actual_file = st.file_uploader("Upload actual file", type=["csv", "xlsx"],
                                    key="actual", label_visibility="collapsed")

# ---------------------------------------------------------------------------
# Load files into DataFrames
# ---------------------------------------------------------------------------
def load_upload(uploaded_file) -> pd.DataFrame:
    """Read an uploaded file into a DataFrame."""
    if uploaded_file.name.endswith(".csv"):
        return pd.read_csv(uploaded_file, dtype=str, keep_default_na=False)
    else:
        return pd.read_excel(uploaded_file, dtype=str, keep_default_na=False)


# ---------------------------------------------------------------------------
# Run comparison
# ---------------------------------------------------------------------------
if expected_file and actual_file:
    df_expected = load_upload(expected_file)
    df_actual = load_upload(actual_file)

    # Preview the data
    with st.expander("👀 Preview uploaded data", expanded=False):
        prev_left, prev_right = st.columns(2)
        with prev_left:
            st.caption("Expected")
            st.dataframe(df_expected, use_container_width=True, height=200)
        with prev_right:
            st.caption("Actual")
            st.dataframe(df_actual, use_container_width=True, height=200)

    # Compare
    comparator = DataComparator(
        numeric_tolerance=numeric_tolerance,
        case_sensitive=case_sensitive,
        normalize_dates=normalize_dates,
        normalize_currency=normalize_currency,
    )
    result = comparator.compare(df_expected, df_actual)

    st.divider()

    # -------------------------------------------------------------------
    # Summary metrics
    # -------------------------------------------------------------------
    st.subheader("📊 Summary")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Cells", f"{result.total_cells}")
    m2.metric("Exact Matches", f"{result.match_count}", delta=None)
    m3.metric("Format Diffs", f"{result.format_diff_count}")
    m4.metric("Value Mismatches", f"{result.value_mismatch_count}")
    m5.metric("Lenient Accuracy", f"{result.accuracy:.1%}")

    st.divider()

    # -------------------------------------------------------------------
    # Charts
    # -------------------------------------------------------------------
    st.subheader("📈 Visualizations")

    chart_left, chart_right = st.columns(2)

    # Pie chart — diff type breakdown
    with chart_left:
        labels = []
        sizes = []
        colors = []
        for label, size, color in [
            ("Exact Match", result.match_count, "#06d6a0"),
            ("Format Diff", result.format_diff_count, "#ffd166"),
            ("Value Mismatch", result.value_mismatch_count, "#ef476f"),
        ]:
            if size > 0:
                labels.append(label)
                sizes.append(size)
                colors.append(color)

        if sizes:
            fig_pie, ax_pie = plt.subplots(figsize=(5, 4))
            fig_pie.patch.set_facecolor("none")
            ax_pie.set_facecolor("none")
            wedges, texts, autotexts = ax_pie.pie(
                sizes, labels=labels, colors=colors, autopct="%1.1f%%",
                textprops={"color": "#e0e0e0", "fontsize": 10},
                wedgeprops={"edgecolor": "#0e1117", "linewidth": 2},
            )
            for t in autotexts:
                t.set_fontweight("bold")
            ax_pie.set_title("Difference Breakdown", color="#e0e0e0", fontsize=13, fontweight="bold")
            st.pyplot(fig_pie)
            plt.close(fig_pie)

    # Bar chart — per-field accuracy
    with chart_right:
        cols = list(result.field_stats.keys())
        accuracies = [result.field_stats[c].lenient_accuracy * 100 for c in cols]

        fig_bar, ax_bar = plt.subplots(figsize=(max(5, len(cols) * 0.7), 4))
        fig_bar.patch.set_facecolor("none")
        ax_bar.set_facecolor("none")

        bar_colors = ["#06d6a0" if a >= 95 else "#ffd166" if a >= 80 else "#ef476f" for a in accuracies]
        ax_bar.bar(cols, accuracies, color=bar_colors, width=0.6)
        ax_bar.set_ylim(0, 105)
        ax_bar.set_ylabel("Accuracy %", color="#e0e0e0")
        ax_bar.set_title("Per-Field Accuracy", color="#e0e0e0", fontsize=13, fontweight="bold")
        ax_bar.tick_params(colors="#e0e0e0", labelsize=9)
        ax_bar.spines["top"].set_visible(False)
        ax_bar.spines["right"].set_visible(False)
        ax_bar.spines["left"].set_color("#333")
        ax_bar.spines["bottom"].set_color("#333")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        st.pyplot(fig_bar)
        plt.close(fig_bar)

    # Heatmap
    heatmap_data = {
        "Field": [],
        "Value Mismatches": [],
        "Format Diffs": [],
    }
    for col, stats in result.field_stats.items():
        heatmap_data["Field"].append(col)
        heatmap_data["Value Mismatches"].append(stats.value_mismatches)
        heatmap_data["Format Diffs"].append(stats.format_diffs)

    heatmap_df = pd.DataFrame(heatmap_data).set_index("Field")

    if heatmap_df.values.sum() > 0:
        st.subheader("🗺️ Error Heatmap")
        fig_heat, ax_heat = plt.subplots(figsize=(6, max(3, len(heatmap_df) * 0.45)))
        fig_heat.patch.set_facecolor("none")
        ax_heat.set_facecolor("none")
        sns.heatmap(
            heatmap_df, annot=True, fmt="d", cmap="YlOrRd",
            linewidths=0.5, linecolor="#333", ax=ax_heat,
            cbar_kws={"shrink": 0.8}
        )
        ax_heat.set_title("Error Distribution", color="#e0e0e0", fontsize=13, fontweight="bold")
        ax_heat.tick_params(colors="#e0e0e0", labelsize=10)
        plt.tight_layout()
        st.pyplot(fig_heat)
        plt.close(fig_heat)

    st.divider()

    # -------------------------------------------------------------------
    # Diff detail table
    # -------------------------------------------------------------------
    st.subheader("🔎 Difference Details")

    diffs_df = result.diffs_to_dataframe()

    if len(diffs_df) > 0:
        # Filter controls
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            type_filter = st.selectbox("Filter by type", ["All", "value_mismatch", "format_diff"])
        with filter_col2:
            col_filter = st.selectbox("Filter by column", ["All"] + list(diffs_df["column"].unique()))

        filtered = diffs_df.copy()
        if type_filter != "All":
            filtered = filtered[filtered["diff_type"] == type_filter]
        if col_filter != "All":
            filtered = filtered[filtered["column"] == col_filter]

        # Color-code the diff type
        def highlight_type(val):
            if val == "value_mismatch":
                return "background-color: rgba(239,71,111,0.3); color: #ef476f; font-weight: bold"
            elif val == "format_diff":
                return "background-color: rgba(255,209,102,0.3); color: #ffd166; font-weight: bold"
            return ""

        styled = filtered.style.applymap(highlight_type, subset=["diff_type"])
        st.dataframe(styled, use_container_width=True, height=400)

        st.caption(f"Showing {len(filtered)} of {len(diffs_df)} differences")
    else:
        st.success("No differences found! The datasets match perfectly. 🎉")

else:
    # No files uploaded yet — show instructions
    st.info("👆 Upload both files to start comparing. You can use the sample files in the `sample_data/` folder to try it out.")
