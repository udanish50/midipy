from __future__ import annotations

import hashlib
import io
import json
import math
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from midipy.midi_analysis import midiInfo
from midipy.midi_parser import parser, parser_segments
from midipy.midi_reader import readmidi
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


# =============================================================================
# APP CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="MidiPy Analysis Studio",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DEFAULT_UE_KEYS = [
    24, 25, 26, 27, 28, 30, 31, 32, 34, 35,
    37, 38, 39, 40, 41, 42, 43, 46, 47, 48,
    49, 51, 52, 53, 55, 59, 66, 67, 71, 78, 79,
]

METRIC_GROUPS = {
    "Note counts": [
        "Total_Counts",
        "UE_Counts",
        "LF_Counts",
        "RF_Counts",
    ],
    "Velocity": [
        "Avg_Velocity",
        "UE_Velocity",
        "LF_Velocity",
        "RF_Velocity",
    ],
    "Asynchrony": [
        "Avg_Async",
        "UE_Async",
        "LF_Async",
        "RF_Async",
    ],
}

AVAILABLE_METRICS = [
    metric
    for metrics in METRIC_GROUPS.values()
    for metric in metrics
]

METRIC_LABELS = {
    "Name": "Session",
    "Total_Counts": "Total notes",
    "UE_Counts": "Upper-extremity notes",
    "LF_Counts": "Left-foot notes",
    "RF_Counts": "Right-foot notes",
    "Avg_Velocity": "Overall velocity",
    "UE_Velocity": "Upper-extremity velocity",
    "LF_Velocity": "Left-foot velocity",
    "RF_Velocity": "Right-foot velocity",
    "Avg_Async": "Overall asynchrony",
    "UE_Async": "Upper-extremity asynchrony",
    "LF_Async": "Left-foot asynchrony",
    "RF_Async": "Right-foot asynchrony",
    "Segment_Number": "Segment",
}

METRIC_HELP = {
    "Total_Counts": "Total number of MIDI notes detected.",
    "UE_Counts": "Notes whose MIDI values match the upper-extremity mapping.",
    "LF_Counts": "Notes whose MIDI value matches the left-foot mapping.",
    "RF_Counts": "Notes whose MIDI value matches the right-foot mapping.",
    "Avg_Velocity": "Mean note velocity with standard deviation in parentheses.",
    "UE_Velocity": "Upper-extremity mean velocity with standard deviation.",
    "LF_Velocity": "Left-foot mean velocity with standard deviation.",
    "RF_Velocity": "Right-foot mean velocity with standard deviation.",
    "Avg_Async": "Mean overall timing asynchrony with standard deviation.",
    "UE_Async": "Upper-extremity timing asynchrony.",
    "LF_Async": "Left-foot timing asynchrony.",
    "RF_Async": "Right-foot timing asynchrony.",
}

COUNT_METRICS = [
    "Total_Counts",
    "UE_Counts",
    "LF_Counts",
    "RF_Counts",
]


# =============================================================================
# VISUAL SYSTEM
# =============================================================================

st.markdown(
    """
    <style>
    :root {
        --mp-primary: #3659e3;
        --mp-primary-dark: #253da8;
        --mp-accent: #11a8a0;
        --mp-success: #16794b;
        --mp-warning: #9a5b00;
        --mp-danger: #b42318;
        --mp-surface-soft: color-mix(in srgb, var(--secondary-background-color) 72%, transparent);
        --mp-border: color-mix(in srgb, var(--text-color) 16%, transparent);
        --mp-shadow: 0 12px 32px rgba(20, 34, 74, 0.08);
        --mp-radius: 18px;
    }

    html {
        scroll-behavior: smooth;
    }

    .stApp {
        background:
            radial-gradient(circle at 88% 2%, rgba(54, 89, 227, 0.10), transparent 25rem),
            radial-gradient(circle at 8% 28%, rgba(17, 168, 160, 0.08), transparent 24rem),
            var(--background-color);
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    [data-testid="stToolbar"] {
        right: 1rem;
    }

    .block-container {
        max-width: 1240px;
        padding-top: 2.4rem;
        padding-bottom: 4rem;
    }

    [data-testid="stSidebar"] {
        border-right: 1px solid var(--mp-border);
    }

    h1, h2, h3 {
        letter-spacing: -0.025em;
    }

    h1 {
        line-height: 1.08;
    }

    p, li, label {
        line-height: 1.55;
    }

    .mp-hero {
        position: relative;
        overflow: hidden;
        padding: 2rem 2.1rem;
        margin-bottom: 1.2rem;
        border: 1px solid rgba(255, 255, 255, 0.18);
        border-radius: 24px;
        background:
            linear-gradient(125deg, rgba(25, 42, 102, 0.98), rgba(54, 89, 227, 0.93) 58%, rgba(17, 168, 160, 0.88));
        box-shadow: 0 18px 50px rgba(31, 54, 140, 0.24);
        color: white;
    }

    .mp-hero::after {
        content: "";
        position: absolute;
        width: 19rem;
        height: 19rem;
        right: -7rem;
        top: -8rem;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.10);
    }

    .mp-eyebrow {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        padding: 0.34rem 0.7rem;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.15);
        border: 1px solid rgba(255, 255, 255, 0.22);
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }

    .mp-hero h1 {
        margin: 0.85rem 0 0.45rem;
        color: white;
        font-size: clamp(2rem, 5vw, 3.25rem);
    }

    .mp-hero p {
        max-width: 48rem;
        margin: 0;
        color: rgba(255, 255, 255, 0.88);
        font-size: 1.03rem;
    }

    .mp-stepper {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.65rem;
        margin: 1rem 0 1.45rem;
    }

    .mp-step {
        min-height: 74px;
        padding: 0.85rem 0.9rem;
        border: 1px solid var(--mp-border);
        border-radius: 14px;
        background: var(--background-color);
        box-shadow: 0 5px 18px rgba(20, 34, 74, 0.04);
    }

    .mp-step-number {
        display: inline-grid;
        width: 1.65rem;
        height: 1.65rem;
        place-items: center;
        margin-right: 0.35rem;
        border-radius: 50%;
        background: rgba(54, 89, 227, 0.12);
        color: var(--mp-primary);
        font-size: 0.78rem;
        font-weight: 800;
    }

    .mp-step strong {
        font-size: 0.91rem;
    }

    .mp-step small {
        display: block;
        margin-top: 0.35rem;
        color: color-mix(in srgb, var(--text-color) 70%, transparent);
        line-height: 1.35;
    }

    .mp-section-heading {
        margin: 1.6rem 0 0.75rem;
    }

    .mp-section-heading h2 {
        margin: 0;
        font-size: 1.45rem;
    }

    .mp-section-heading p {
        margin: 0.25rem 0 0;
        color: color-mix(in srgb, var(--text-color) 68%, transparent);
    }

    .mp-status-card {
        padding: 0.95rem 1rem;
        border: 1px solid var(--mp-border);
        border-radius: 14px;
        background: var(--background-color);
    }

    .mp-status-card strong {
        display: block;
        margin-bottom: 0.25rem;
    }

    .mp-good {
        border-left: 4px solid var(--mp-success);
    }

    .mp-warn {
        border-left: 4px solid var(--mp-warning);
    }

    .mp-muted {
        color: color-mix(in srgb, var(--text-color) 66%, transparent);
        font-size: 0.9rem;
    }

    .mp-callout {
        padding: 0.9rem 1rem;
        border: 1px solid rgba(54, 89, 227, 0.20);
        border-radius: 14px;
        background: rgba(54, 89, 227, 0.06);
    }

    .mp-footer {
        margin-top: 2.2rem;
        padding-top: 1rem;
        border-top: 1px solid var(--mp-border);
        color: color-mix(in srgb, var(--text-color) 62%, transparent);
        font-size: 0.83rem;
        text-align: center;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--mp-border);
        border-radius: var(--mp-radius);
        box-shadow: var(--mp-shadow);
        background: color-mix(in srgb, var(--background-color) 94%, transparent);
    }

    div[data-testid="stFileUploaderDropzone"] {
        min-height: 168px;
        border: 2px dashed color-mix(in srgb, var(--mp-primary) 45%, var(--mp-border));
        border-radius: 18px;
        background: rgba(54, 89, 227, 0.035);
        transition: border-color 160ms ease, background 160ms ease, transform 160ms ease;
    }

    div[data-testid="stFileUploaderDropzone"]:hover {
        border-color: var(--mp-primary);
        background: rgba(54, 89, 227, 0.07);
        transform: translateY(-1px);
    }

    div.stButton > button,
    div.stDownloadButton > button,
    [data-testid="stFormSubmitButton"] > button {
        min-height: 46px;
        border-radius: 12px;
        font-weight: 750;
        transition: transform 150ms ease, box-shadow 150ms ease, border-color 150ms ease;
    }

    div.stButton > button:hover,
    div.stDownloadButton > button:hover,
    [data-testid="stFormSubmitButton"] > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 8px 18px rgba(37, 61, 168, 0.14);
    }

    div.stButton > button:focus-visible,
    div.stDownloadButton > button:focus-visible,
    [data-testid="stFormSubmitButton"] > button:focus-visible,
    input:focus-visible,
    textarea:focus-visible {
        outline: 3px solid rgba(54, 89, 227, 0.32) !important;
        outline-offset: 2px;
    }

    button[kind="primary"] {
        border-color: var(--mp-primary) !important;
        background: linear-gradient(135deg, var(--mp-primary), var(--mp-primary-dark)) !important;
    }

    [data-testid="stMetric"] {
        min-height: 112px;
        padding: 1rem;
        border: 1px solid var(--mp-border);
        border-radius: 15px;
        background: var(--background-color);
        box-shadow: 0 7px 20px rgba(20, 34, 74, 0.05);
    }

    [data-testid="stMetricLabel"] {
        color: color-mix(in srgb, var(--text-color) 66%, transparent);
    }

    [data-testid="stMetricValue"] {
        font-size: clamp(1.45rem, 4vw, 2rem);
    }

    [data-baseweb="tab-list"] {
        gap: 0.35rem;
        padding: 0.25rem;
        border-radius: 12px;
        background: var(--mp-surface-soft);
    }

    [data-baseweb="tab"] {
        min-height: 42px;
        border-radius: 9px;
        padding-inline: 1rem;
    }

    [aria-selected="true"][data-baseweb="tab"] {
        background: var(--background-color);
        box-shadow: 0 3px 12px rgba(20, 34, 74, 0.08);
    }

    [data-testid="stDataFrame"] {
        border: 1px solid var(--mp-border);
        border-radius: 14px;
        overflow: hidden;
    }

    @media (max-width: 780px) {
        .block-container {
            padding-top: 1rem;
            padding-inline: 0.9rem;
        }

        .mp-hero {
            padding: 1.45rem;
            border-radius: 18px;
        }

        .mp-stepper {
            grid-template-columns: 1fr 1fr;
        }
    }

    @media (max-width: 480px) {
        .mp-stepper {
            grid-template-columns: 1fr;
        }
    }

    @media (prefers-reduced-motion: reduce) {
        html {
            scroll-behavior: auto;
        }

        *,
        *::before,
        *::after {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# DATA AND VALIDATION HELPERS
# =============================================================================

def parse_note_list(text: str) -> list[int]:
    """Convert comma, semicolon, or whitespace-separated values into MIDI notes."""
    pieces = [item for item in re.split(r"[\s,;]+", text.strip()) if item]
    if not pieces:
        raise ValueError("Enter at least one upper-extremity MIDI note value.")

    values: list[int] = []
    for piece in pieces:
        try:
            value = int(piece)
        except ValueError as exc:
            raise ValueError(
                f'"{piece}" is not a whole MIDI note number.'
            ) from exc

        if not 0 <= value <= 127:
            raise ValueError(
                f"MIDI note {value} is outside the valid range of 0 to 127."
            )

        if value not in values:
            values.append(value)

    return values


def safe_filename(original_name: str, used_names: set[str]) -> str:
    """Create a unique lowercase .mid filename for MidiPy."""
    stem = Path(original_name).stem
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_") or "midi_file"

    candidate = f"{stem}.mid"
    number = 2
    while candidate.lower() in used_names:
        candidate = f"{stem}_{number}.mid"
        number += 1

    used_names.add(candidate.lower())
    return candidate


def human_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024**2:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / 1024**2:.1f} MB"


def precheck_uploads(uploaded_files) -> tuple[list[dict[str, Any]], int, int]:
    """Perform a quick non-destructive check before the user starts analysis."""
    rows: list[dict[str, Any]] = []
    ready_count = 0
    total_size = 0

    for uploaded_file in uploaded_files or []:
        original_name = Path(uploaded_file.name).name
        data = uploaded_file.getvalue()
        size = len(data)
        total_size += size

        if original_name.startswith("."):
            status = "Needs attention"
            detail = "Hidden system file"
        elif size == 0:
            status = "Needs attention"
            detail = "Empty file"
        elif data[:4] != b"MThd":
            status = "Needs attention"
            detail = "Standard MIDI header is missing"
        else:
            status = "Ready"
            detail = "Basic file check passed"
            ready_count += 1

        rows.append(
            {
                "File": original_name,
                "Size": human_file_size(size),
                "Status": status,
                "Details": detail,
            }
        )

    return rows, ready_count, total_size


def validate_and_save_uploads(uploaded_files, folder: Path):
    """Save only genuine, MidiPy-readable files into a clean temporary folder."""
    valid_names: list[str] = []
    skipped: list[tuple[str, str]] = []
    used_names: set[str] = set()

    for uploaded_file in uploaded_files:
        original_name = Path(uploaded_file.name).name
        data = uploaded_file.getvalue()
        destination: Path | None = None

        try:
            if original_name.startswith("."):
                raise ValueError("Hidden system file")

            if not data:
                raise ValueError("The file is empty")

            if data[:4] != b"MThd":
                raise ValueError("The Standard MIDI MThd header is missing")

            destination_name = safe_filename(original_name, used_names)
            destination = folder / destination_name
            destination.write_bytes(data)

            midi = readmidi(str(destination))
            notes, _, tempos = midiInfo(midi, 0)

            if notes is None or len(notes) == 0:
                raise ValueError("No readable MIDI notes were found")

            if tempos is None or len(tempos) == 0:
                raise ValueError("No readable tempo information was found")

            valid_names.append(original_name)

        except Exception as error:
            if destination is not None and destination.exists():
                destination.unlink()
            skipped.append((original_name, str(error)))

    return valid_names, skipped


def upload_signature(uploaded_files) -> str:
    """Create a stable signature so stale results are never shown as current."""
    digest = hashlib.sha256()
    for uploaded_file in uploaded_files or []:
        data = uploaded_file.getvalue()
        digest.update(Path(uploaded_file.name).name.encode("utf-8", errors="ignore"))
        digest.update(str(len(data)).encode("ascii"))
        digest.update(hashlib.sha256(data).digest())
    return digest.hexdigest()


def settings_signature(settings: dict[str, Any]) -> str:
    payload = json.dumps(settings, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def mean_from_metric(value: Any) -> float | None:
    """Extract the leading mean from a value such as '45.37 (14.25)'."""
    if value is None:
        return None

    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return float(value)

    match = re.search(r"[-+]?\d*\.?\d+", str(value))
    if not match:
        return None

    try:
        return float(match.group())
    except ValueError:
        return None


def display_dataframe(dataframe: pd.DataFrame) -> None:
    """Display a result table with human-readable column headings."""
    display_df = dataframe.rename(columns=METRIC_LABELS)

    column_config: dict[str, Any] = {}
    for source_name, display_name in METRIC_LABELS.items():
        if source_name not in dataframe.columns:
            continue

        help_text = METRIC_HELP.get(source_name)
        source_series = dataframe[source_name]

        if source_name in COUNT_METRICS or source_name == "Segment_Number":
            column_config[display_name] = st.column_config.NumberColumn(
                display_name,
                help=help_text,
                format="%.0f",
            )
        elif pd.api.types.is_numeric_dtype(source_series):
            column_config[display_name] = st.column_config.NumberColumn(
                display_name,
                help=help_text,
                format="%.2f",
            )
        else:
            column_config[display_name] = st.column_config.TextColumn(
                display_name,
                help=help_text,
            )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
    )


def average_segment_rows(segment_df: pd.DataFrame) -> pd.DataFrame:
    """Average each segment index across files without using MidiPy's fragile path."""
    if "Name" not in segment_df.columns:
        return segment_df

    working = segment_df.copy()
    working["Segment_Number"] = pd.to_numeric(
        working["Name"]
        .astype(str)
        .str.extract(r"Segment\s+(\d+)", expand=False),
        errors="coerce",
    )
    working = working.dropna(subset=["Segment_Number"])

    if working.empty:
        return segment_df

    working["Segment_Number"] = working["Segment_Number"].astype(int)
    numeric_columns = [
        column
        for column in working.select_dtypes(include="number").columns
        if column != "Segment_Number"
    ]

    if not numeric_columns:
        return segment_df

    averaged = (
        working.groupby("Segment_Number", as_index=False)[numeric_columns]
        .mean()
        .sort_values("Segment_Number")
    )
    averaged.insert(
        0,
        "Name",
        "Segment " + averaged["Segment_Number"].astype(str),
    )

    ordered_columns = ["Name"] + [
        column
        for column in segment_df.columns
        if column != "Name" and column in averaged.columns
    ]
    if "Segment_Number" not in ordered_columns:
        ordered_columns.append("Segment_Number")

    return averaged[ordered_columns]


def dataframe_to_excel_bytes(sheets: dict[str, pd.DataFrame]) -> bytes:
    """Build a formatted workbook suitable for nontechnical users."""
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, dataframe in sheets.items():
            export_df = dataframe.rename(columns=METRIC_LABELS)
            export_df.to_excel(
                writer,
                sheet_name=sheet_name[:31],
                index=False,
            )

            worksheet = writer.book[sheet_name[:31]]
            worksheet.freeze_panes = "A2"
            worksheet.auto_filter.ref = worksheet.dimensions

            header_fill = PatternFill(
                fill_type="solid",
                fgColor="3659E3",
            )
            header_font = Font(
                color="FFFFFF",
                bold=True,
            )

            for cell in worksheet[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(
                    vertical="center",
                    wrap_text=True,
                )

            worksheet.row_dimensions[1].height = 28

            for column_index, column_cells in enumerate(
                worksheet.iter_cols(),
                start=1,
            ):
                maximum = max(
                    len(str(cell.value)) if cell.value is not None else 0
                    for cell in column_cells
                )
                worksheet.column_dimensions[
                    get_column_letter(column_index)
                ].width = min(max(maximum + 3, 12), 42)

    return output.getvalue()


def dataframes_to_csv_zip(sheets: dict[str, pd.DataFrame]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(
        output,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        for name, dataframe in sheets.items():
            export_df = dataframe.rename(columns=METRIC_LABELS)
            archive.writestr(
                f"{name}.csv",
                export_df.to_csv(index=False).encode("utf-8"),
            )
    return output.getvalue()


def result_summary(dataframe: pd.DataFrame) -> dict[str, float | None]:
    """Create meaningful high-level values from whole-file results."""
    data = dataframe.copy()

    if "Name" in data.columns:
        totals_rows = data[
            data["Name"].astype(str).str.upper().eq("TOTALS")
        ]
        non_total_rows = data[
            ~data["Name"].astype(str).str.upper().eq("TOTALS")
        ]
    else:
        totals_rows = pd.DataFrame()
        non_total_rows = data

    summary: dict[str, float | None] = {
        "files": float(len(non_total_rows)),
        "total": None,
        "ue": None,
        "lf": None,
        "rf": None,
    }

    for key, column in [
        ("total", "Total_Counts"),
        ("ue", "UE_Counts"),
        ("lf", "LF_Counts"),
        ("rf", "RF_Counts"),
    ]:
        if column not in data.columns:
            continue

        if not totals_rows.empty:
            summary[key] = mean_from_metric(totals_rows.iloc[0][column])
        else:
            numeric = pd.to_numeric(
                non_total_rows[column],
                errors="coerce",
            )
            summary[key] = float(numeric.sum()) if numeric.notna().any() else None

    return summary


def chartable_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Convert display-formatted result fields into chartable mean values."""
    output = dataframe.copy()

    for column in output.columns:
        if column == "Name":
            continue
        output[column] = output[column].map(mean_from_metric)

    return output


def render_result_chart(
    dataframe: pd.DataFrame,
    result_name: str,
) -> None:
    available = [
        metric
        for metric in AVAILABLE_METRICS
        if metric in dataframe.columns
    ]

    if not available or "Name" not in dataframe.columns:
        st.info("No chart-compatible result columns are available.")
        return

    default_metric = (
        "Total_Counts"
        if "Total_Counts" in available
        else available[0]
    )

    selected_metric = st.selectbox(
        "Metric to visualize",
        options=available,
        index=available.index(default_metric),
        format_func=lambda metric: METRIC_LABELS.get(metric, metric),
        key=f"chart_metric_{result_name}",
        help="The chart uses the mean value when a table cell contains mean and standard deviation.",
    )

    chart_df = chartable_dataframe(dataframe)
    chart_df = chart_df[
        ~chart_df["Name"].astype(str).str.upper().eq("TOTALS")
    ].copy()
    chart_df = chart_df.dropna(subset=[selected_metric])

    if chart_df.empty:
        st.info("The selected metric has no chartable values.")
        return

    if result_name == "Segment_Results":
        chart_df["Segment"] = pd.to_numeric(
            chart_df["Name"]
            .astype(str)
            .str.extract(r"Segment\s+(\d+)", expand=False),
            errors="coerce",
        )
        chart_df["Session"] = (
            chart_df["Name"]
            .astype(str)
            .str.replace(
                r"\s*Segment\s+\d+\s*$",
                "",
                regex=True,
            )
        )

        if chart_df["Segment"].notna().all():
            pivot = chart_df.pivot_table(
                index="Segment",
                columns="Session",
                values=selected_metric,
                aggfunc="mean",
            ).sort_index()
            st.line_chart(pivot)
            return

    simple_chart = chart_df[["Name", selected_metric]].set_index("Name")
    st.bar_chart(simple_chart)


def clear_analysis_state() -> None:
    for key in [
        "midipy_results",
        "midipy_valid_names",
        "midipy_skipped_files",
        "midipy_analysis_signature",
        "midipy_analysis_settings_signature",
        "midipy_last_settings",
    ]:
        st.session_state.pop(key, None)


# =============================================================================
# SIDEBAR: SUPPORTING, NON-CRITICAL CONTENT
# =============================================================================

with st.sidebar:
    st.header("MidiPy help")
    st.markdown(
        """
        **Recommended workflow**

        1. Upload one or more MIDI files.
        2. Review the automatic file check.
        3. Confirm the body-part mappings.
        4. Run the analysis.
        5. Review and export results.
        """
    )

    st.divider()

    st.subheader("Terminology")
    st.markdown(
        """
        **UE** — upper extremity  
        **LF** — left foot  
        **RF** — right foot  
        **Velocity** — MIDI performance intensity  
        **Asynchrony** — timing difference from the quantized beat
        """
    )

    st.divider()

    st.subheader("Privacy")
    st.caption(
        "This hosted app temporarily processes uploaded files to create results. "
        "Use de-identified research files and follow institutional data-handling rules."
    )

    if st.button(
        "Start a new analysis",
        use_container_width=True,
        help="Clears displayed results and returns the dashboard to a fresh state.",
    ):
        clear_analysis_state()
        st.rerun()


# =============================================================================
# HERO AND WORKFLOW
# =============================================================================

st.markdown(
    """
    <section class="mp-hero" aria-labelledby="midipy-title">
        <span class="mp-eyebrow">Human-centred MIDI analysis</span>
        <h1 id="midipy-title">MidiPy Analysis Studio</h1>
        <p>
            A guided workspace for validating MIDI files, configuring body-part
            mappings, reviewing performance measures, and exporting clear results.
        </p>
    </section>

    <div class="mp-stepper" aria-label="Analysis workflow">
        <div class="mp-step">
            <span class="mp-step-number">1</span><strong>Upload</strong>
            <small>Add one or more Standard MIDI files.</small>
        </div>
        <div class="mp-step">
            <span class="mp-step-number">2</span><strong>Configure</strong>
            <small>Confirm note mappings and analysis options.</small>
        </div>
        <div class="mp-step">
            <span class="mp-step-number">3</span><strong>Analyze</strong>
            <small>Validate and process the files securely.</small>
        </div>
        <div class="mp-step">
            <span class="mp-step-number">4</span><strong>Review</strong>
            <small>Inspect, visualize, and export the results.</small>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# STEP 1: UPLOAD
# =============================================================================

st.markdown(
    """
    <div class="mp-section-heading">
        <h2>1. Upload MIDI files</h2>
        <p>Select all sessions that should be included in this analysis.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.container(border=True):
    uploaded_files = st.file_uploader(
        "MIDI files",
        type=["mid", "midi"],
        accept_multiple_files=True,
        help="Supported extensions: .mid and .midi. Multiple files can be selected together.",
    )

    precheck_rows, ready_count, total_size = precheck_uploads(uploaded_files)
    attention_count = len(precheck_rows) - ready_count

    if uploaded_files:
        status_left, status_middle, status_right = st.columns(3)

        with status_left:
            st.metric("Files selected", len(uploaded_files))

        with status_middle:
            st.metric("Ready after basic check", ready_count)

        with status_right:
            st.metric("Combined size", human_file_size(total_size))

        if attention_count:
            st.warning(
                f"{attention_count} file(s) need attention and will be skipped "
                "unless replaced."
            )
        else:
            st.success(
                "All selected files passed the basic MIDI header check."
            )

        with st.expander(
            "Review selected files",
            expanded=attention_count > 0,
        ):
            st.dataframe(
                pd.DataFrame(precheck_rows),
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.info(
            "No files have been selected. Use the upload area above to begin."
        )


# =============================================================================
# STEP 2: CONFIGURE
# =============================================================================

st.markdown(
    """
    <div class="mp-section-heading">
        <h2>2. Configure the analysis</h2>
        <p>Defaults are already prepared. Change them only when your MIDI mapping requires it.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.container(border=True):
    st.subheader("Body-part note mapping")

    ue_text = st.text_area(
        "Upper-extremity (UE) MIDI note values",
        value=", ".join(str(value) for value in DEFAULT_UE_KEYS),
        help=(
            "Enter whole MIDI note numbers from 0 to 127. "
            "Separate values with commas, spaces, or semicolons."
        ),
        height=118,
    )

    mapping_left, mapping_right = st.columns(2)

    with mapping_left:
        left_foot_key = int(
            st.number_input(
                "Left-foot (LF) MIDI note value",
                min_value=0,
                max_value=127,
                value=44,
                step=1,
                help="One MIDI note number from 0 to 127.",
            )
        )

    with mapping_right:
        right_foot_key = int(
            st.number_input(
                "Right-foot (RF) MIDI note value",
                min_value=0,
                max_value=127,
                value=36,
                step=1,
                help="One MIDI note number from 0 to 127.",
            )
        )

    st.divider()
    st.subheader("Analysis scope")

    analysis_mode = st.radio(
        "Choose what to analyze",
        options=[
            "Whole files and segments",
            "Whole files only",
            "Segments only",
        ],
        index=0,
        horizontal=True,
        help=(
            "Whole-file results summarize each complete session. "
            "Segment results show changes across time."
        ),
    )

    run_whole = analysis_mode in {
        "Whole files and segments",
        "Whole files only",
    }
    run_segments = analysis_mode in {
        "Whole files and segments",
        "Segments only",
    }

    segment_left, segment_right = st.columns(2)

    with segment_left:
        number_of_segments = int(
            st.slider(
                "Number of segments",
                min_value=2,
                max_value=20,
                value=5,
                disabled=not run_segments,
                help="Each MIDI file is divided into equal-duration segments.",
            )
        )

    with segment_right:
        average_segments = st.checkbox(
            "Average matching segments across files",
            value=False,
            disabled=not run_segments,
            help=(
                "For example, all Segment 1 rows are averaged together, "
                "then all Segment 2 rows, and so on."
            ),
        )

    with st.expander("Advanced result options"):
        metric_preset = st.radio(
            "Result detail",
            options=[
                "Complete report",
                "Counts only",
                "Choose columns",
            ],
            index=0,
            horizontal=True,
        )

        if metric_preset == "Complete report":
            selected_metrics = AVAILABLE_METRICS.copy()
            st.caption("All count, velocity, and asynchrony measures will be included.")

        elif metric_preset == "Counts only":
            selected_metrics = COUNT_METRICS.copy()
            st.caption("Only total, UE, LF, and RF note counts will be included.")

        else:
            selected_metrics = st.multiselect(
                "Columns to include",
                options=AVAILABLE_METRICS,
                default=AVAILABLE_METRICS,
                format_func=lambda metric: METRIC_LABELS.get(metric, metric),
                help="The session name is included automatically.",
            )

    submitted = st.button(
        "Analyze MIDI files",
        type="primary",
        use_container_width=True,
        disabled=not uploaded_files or ready_count == 0,
        key="analyze_midi_files",
    )


# =============================================================================
# STEP 3: ANALYZE
# =============================================================================

current_settings = {
    "ue_text": ue_text,
    "left_foot_key": left_foot_key,
    "right_foot_key": right_foot_key,
    "analysis_mode": analysis_mode,
    "number_of_segments": number_of_segments,
    "average_segments": average_segments,
    "selected_metrics": selected_metrics,
}

current_upload_signature = upload_signature(uploaded_files)
current_settings_signature = settings_signature(current_settings)

if submitted:
    if not selected_metrics:
        st.error(
            "Select at least one result column before running the analysis."
        )
        st.stop()

    try:
        ue_keys = parse_note_list(ue_text)
    except ValueError as error:
        st.error(str(error))
        st.stop()

    overlap = sorted(
        set(ue_keys) & {left_foot_key, right_foot_key}
    )
    if overlap:
        st.warning(
            "Mapping overlap detected: "
            + ", ".join(map(str, overlap))
            + ". These values appear in both UE and foot mappings. "
              "Confirm that this is intentional."
        )

    with st.status(
        "Preparing the analysis…",
        expanded=True,
    ) as analysis_status:
        try:
            analysis_status.write(
                "Creating a clean temporary workspace."
            )

            with tempfile.TemporaryDirectory(
                prefix="midipy_dashboard_"
            ) as temporary:
                temporary_path = Path(temporary)
                midi_folder = temporary_path / "validated_midi"
                midi_folder.mkdir()

                analysis_status.write(
                    "Validating MIDI headers, note data, and tempo information."
                )
                valid_names, skipped_files = validate_and_save_uploads(
                    uploaded_files,
                    midi_folder,
                )

                if not valid_names:
                    clear_analysis_state()
                    analysis_status.update(
                        label="No usable MIDI files were found.",
                        state="error",
                        expanded=True,
                    )
                    st.error(
                        "None of the selected files passed the complete MIDI validation."
                    )
                    if skipped_files:
                        st.dataframe(
                            pd.DataFrame(
                                skipped_files,
                                columns=["File", "Reason"],
                            ),
                            use_container_width=True,
                            hide_index=True,
                        )
                    st.stop()

                metrics_argument = (
                    ["all"]
                    if set(selected_metrics) == set(AVAILABLE_METRICS)
                    else selected_metrics
                )

                results: dict[str, pd.DataFrame] = {}

                if run_whole:
                    analysis_status.write(
                        f"Computing whole-file measures for {len(valid_names)} file(s)."
                    )
                    whole_df = parser(
                        source=str(midi_folder),
                        metrics=metrics_argument,
                        output_format="csv",
                        save_path=str(temporary_path / "whole_results"),
                        ue_keys=ue_keys,
                        lf_key=left_foot_key,
                        rf_key=right_foot_key,
                    )
                    results["Whole_File_Results"] = whole_df

                if run_segments:
                    analysis_status.write(
                        f"Computing {number_of_segments} segment(s) per file."
                    )
                    segment_df = parser_segments(
                        source=str(midi_folder),
                        metrics=metrics_argument,
                        output_format="csv",
                        save_path=str(temporary_path / "segment_results"),
                        num_segments=number_of_segments,
                        mean_segments=False,
                        ue_keys=ue_keys,
                        lf_key=left_foot_key,
                        rf_key=right_foot_key,
                    )

                    if average_segments:
                        segment_df = average_segment_rows(segment_df)

                    results["Segment_Results"] = segment_df

                st.session_state["midipy_results"] = results
                st.session_state["midipy_valid_names"] = valid_names
                st.session_state["midipy_skipped_files"] = skipped_files
                st.session_state[
                    "midipy_analysis_signature"
                ] = current_upload_signature
                st.session_state[
                    "midipy_analysis_settings_signature"
                ] = current_settings_signature
                st.session_state[
                    "midipy_last_settings"
                ] = current_settings

                analysis_status.update(
                    label=(
                        f"Analysis complete — {len(valid_names)} file(s) processed."
                    ),
                    state="complete",
                    expanded=False,
                )

        except Exception as error:
            clear_analysis_state()
            analysis_status.update(
                label="The analysis could not be completed.",
                state="error",
                expanded=True,
            )
            st.error(
                "MidiPy encountered a problem while processing the files. "
                "Review the guidance below and try again."
            )
            st.markdown(
                """
                - Confirm that the files are genuine Standard MIDI files.
                - Remove empty or damaged files.
                - Confirm that the UE, LF, and RF mappings contain values from 0 to 127.
                """
            )
            with st.expander("Technical details for support"):
                st.code(str(error))


# =============================================================================
# STEP 4: REVIEW RESULTS
# =============================================================================

results = st.session_state.get("midipy_results")
stored_upload_signature = st.session_state.get(
    "midipy_analysis_signature"
)
stored_settings_signature = st.session_state.get(
    "midipy_analysis_settings_signature"
)

results_are_current = (
    bool(results)
    and stored_upload_signature == current_upload_signature
    and stored_settings_signature == current_settings_signature
)

if results and not results_are_current:
    st.warning(
        "The files or settings have changed since the displayed results were created. "
        "Run the analysis again to refresh the results."
    )

if results and results_are_current:
    valid_names = st.session_state.get(
        "midipy_valid_names",
        [],
    )
    skipped_files = st.session_state.get(
        "midipy_skipped_files",
        [],
    )

    st.markdown(
        """
        <div class="mp-section-heading">
            <h2>4. Review and export results</h2>
            <p>Start with the overview, then inspect detailed tables and charts.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    whole_dataframe = results.get("Whole_File_Results")
    if whole_dataframe is not None:
        summary = result_summary(whole_dataframe)

        summary_columns = st.columns(5)
        summary_columns[0].metric(
            "Files analyzed",
            int(summary["files"] or len(valid_names)),
        )
        summary_columns[1].metric(
            "Total notes",
            f"{int(summary['total']):,}" if summary["total"] is not None else "—",
        )
        summary_columns[2].metric(
            "UE notes",
            f"{int(summary['ue']):,}" if summary["ue"] is not None else "—",
        )
        summary_columns[3].metric(
            "LF notes",
            f"{int(summary['lf']):,}" if summary["lf"] is not None else "—",
        )
        summary_columns[4].metric(
            "RF notes",
            f"{int(summary['rf']):,}" if summary["rf"] is not None else "—",
        )
    else:
        summary_columns = st.columns(3)
        summary_columns[0].metric(
            "Files analyzed",
            len(valid_names),
        )
        summary_columns[1].metric(
            "Segment rows",
            len(results.get("Segment_Results", [])),
        )
        summary_columns[2].metric(
            "Files skipped",
            len(skipped_files),
        )

    overview_tab, data_tab, quality_tab, export_tab = st.tabs(
        [
            "Overview",
            "Detailed data",
            "File quality",
            "Export",
        ]
    )

    with overview_tab:
        st.subheader("Visual overview")

        result_options = list(results.keys())
        selected_result_name = st.radio(
            "Result set",
            options=result_options,
            horizontal=True,
            format_func=lambda name: (
                "Whole-file results"
                if name == "Whole_File_Results"
                else "Segment results"
            ),
        )

        render_result_chart(
            results[selected_result_name],
            selected_result_name,
        )

        st.caption(
            "Velocity and asynchrony charts use the mean value shown before "
            "the standard deviation in parentheses."
        )

    with data_tab:
        st.subheader("Result tables")

        for result_name, dataframe in results.items():
            label = (
                "Whole-file results"
                if result_name == "Whole_File_Results"
                else "Segment results"
            )

            with st.expander(
                label,
                expanded=len(results) == 1,
            ):
                display_dataframe(dataframe)
                st.caption(
                    f"{len(dataframe):,} row(s) × {len(dataframe.columns):,} column(s)"
                )

    with quality_tab:
        st.subheader("Processing record")

        quality_left, quality_right = st.columns(2)

        with quality_left:
            st.markdown("**Successfully analyzed**")
            if valid_names:
                for filename in valid_names:
                    st.write(f"✓ {filename}")
            else:
                st.write("No files were recorded.")

        with quality_right:
            st.markdown("**Skipped during complete validation**")
            if skipped_files:
                st.dataframe(
                    pd.DataFrame(
                        skipped_files,
                        columns=["File", "Reason"],
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.write("✓ No files were skipped.")

        st.info(
            "Files are copied into a temporary workspace for analysis. "
            "The temporary workspace is removed after processing."
        )

    with export_tab:
        st.subheader("Download the completed analysis")
        st.write(
            "Choose Excel for a formatted workbook or CSV for use in other software."
        )

        excel_bytes = dataframe_to_excel_bytes(results)
        csv_zip_bytes = dataframes_to_csv_zip(results)

        export_left, export_right = st.columns(2)

        with export_left:
            with st.container(border=True):
                st.markdown("### Excel workbook")
                st.caption(
                    "Formatted headings, frozen header rows, filters, and adjusted column widths."
                )
                st.download_button(
                    "Download Excel results",
                    data=excel_bytes,
                    file_name="MidiPy_Results.xlsx",
                    mime=(
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    ),
                    use_container_width=True,
                )

        with export_right:
            with st.container(border=True):
                st.markdown("### CSV package")
                st.caption(
                    "A ZIP file containing a separate CSV file for each result table."
                )
                st.download_button(
                    "Download CSV results",
                    data=csv_zip_bytes,
                    file_name="MidiPy_CSV_Results.zip",
                    mime="application/zip",
                    use_container_width=True,
                )

        st.caption(
            "Downloaded files use descriptive column names while preserving the original values."
        )

elif not results:
    st.markdown(
        """
        <div class="mp-section-heading">
            <h2>3. Run the analysis</h2>
            <p>After files and settings are ready, use the Analyze MIDI files button above.</p>
        </div>
        <div class="mp-callout">
            Results will appear here as soon as processing is complete. The dashboard
            will provide summary cards, interactive charts, detailed tables, a file-quality
            record, and Excel/CSV downloads.
        </div>
        """,
        unsafe_allow_html=True,
    )


st.markdown(
    """
    <div class="mp-footer">
        MidiPy Analysis Studio · Designed for clear, guided, and error-tolerant MIDI analysis
    </div>
    """,
    unsafe_allow_html=True,
)
