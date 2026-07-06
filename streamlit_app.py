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
    for group_metrics in METRIC_GROUPS.values()
    for metric in group_metrics
]

COUNT_METRICS = [
    "Total_Counts",
    "UE_Counts",
    "LF_Counts",
    "RF_Counts",
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
    "UE_Counts": "Notes matching the upper-extremity mapping.",
    "LF_Counts": "Notes matching the left-foot mapping.",
    "RF_Counts": "Notes matching the right-foot mapping.",
    "Avg_Velocity": "Mean note velocity with standard deviation.",
    "UE_Velocity": "Upper-extremity mean velocity with standard deviation.",
    "LF_Velocity": "Left-foot mean velocity with standard deviation.",
    "RF_Velocity": "Right-foot mean velocity with standard deviation.",
    "Avg_Async": "Mean overall timing asynchrony with standard deviation.",
    "UE_Async": "Upper-extremity timing asynchrony.",
    "LF_Async": "Left-foot timing asynchrony.",
    "RF_Async": "Right-foot timing asynchrony.",
}

METRIC_CATEGORY = {
    metric: group
    for group, metrics in METRIC_GROUPS.items()
    for metric in metrics
}

if "analysis_cycle" not in st.session_state:
    st.session_state["analysis_cycle"] = 0

analysis_cycle = int(st.session_state["analysis_cycle"])


# =============================================================================
# LIGHT, ACCESSIBLE VISUAL SYSTEM
# =============================================================================

st.markdown(
    """
    <style>
    :root {
        --mp-blue: #3157d5;
        --mp-blue-dark: #2443aa;
        --mp-blue-soft: #eef3ff;
        --mp-green: #16744a;
        --mp-green-soft: #edf8f2;
        --mp-amber: #875500;
        --mp-amber-soft: #fff7e6;
        --mp-red: #b42318;
        --mp-ink: #172033;
        --mp-muted: #59667c;
        --mp-border: #dfe5ef;
        --mp-page: #f6f8fc;
        --mp-white: #ffffff;
        --mp-shadow: 0 8px 24px rgba(32, 48, 88, 0.065);
    }

    html {
        scroll-behavior: smooth;
        color-scheme: light !important;
    }

    body,
    .stApp,
    [data-testid="stAppViewContainer"] {
        background: var(--mp-page) !important;
        color: var(--mp-ink) !important;
    }

    [data-testid="stHeader"] {
        background: rgba(246, 248, 252, 0.94) !important;
        border-bottom: 1px solid var(--mp-border);
        backdrop-filter: blur(12px);
    }

    [data-testid="stSidebar"],
    [data-testid="collapsedControl"] {
        display: none !important;
    }

    .block-container {
        max-width: 1180px;
        padding-top: 1.25rem;
        padding-bottom: 6.5rem;
    }

    h1, h2, h3 {
        color: var(--mp-ink);
        letter-spacing: -0.025em;
    }

    p, li, label {
        line-height: 1.5;
    }

    .mp-brand {
        margin: 0;
        font-size: clamp(1.7rem, 4vw, 2.35rem);
        line-height: 1.08;
    }

    .mp-subtitle {
        margin: 0.35rem 0 0;
        color: var(--mp-muted);
        font-size: 0.98rem;
    }

    .mp-stepper {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        align-items: center;
        gap: 0;
        margin: 1.15rem 0 1.25rem;
        padding: 0.85rem 1rem;
        border: 1px solid var(--mp-border);
        border-radius: 14px;
        background: var(--mp-white);
        box-shadow: var(--mp-shadow);
    }

    .mp-step {
        position: relative;
        display: flex;
        align-items: center;
        gap: 0.55rem;
        min-width: 0;
        color: #8a94a7;
        font-size: 0.88rem;
        font-weight: 700;
    }

    .mp-step:not(:last-child)::after {
        content: "";
        position: absolute;
        left: calc(50% + 1.5rem);
        right: 0.75rem;
        top: 50%;
        height: 2px;
        background: #dfe5ef;
        transform: translateY(-50%);
        z-index: 0;
    }

    .mp-step.completed:not(:last-child)::after {
        background: #7da28e;
    }

    .mp-step-badge {
        position: relative;
        z-index: 1;
        display: grid;
        width: 1.8rem;
        height: 1.8rem;
        flex: 0 0 1.8rem;
        place-items: center;
        border: 2px solid #cfd6e2;
        border-radius: 50%;
        background: var(--mp-white);
        color: #7a8598;
        font-size: 0.78rem;
        font-weight: 800;
    }

    .mp-step.current {
        color: var(--mp-blue-dark);
    }

    .mp-step.current .mp-step-badge {
        border-color: var(--mp-blue);
        background: var(--mp-blue);
        color: white;
        box-shadow: 0 0 0 4px rgba(49, 87, 213, 0.12);
    }

    .mp-step.completed {
        color: #355c47;
    }

    .mp-step.completed .mp-step-badge {
        border-color: var(--mp-green);
        background: var(--mp-green-soft);
        color: var(--mp-green);
    }

    .mp-section-head {
        margin: 1.35rem 0 0.65rem;
    }

    .mp-section-head h2 {
        margin: 0;
        font-size: 1.28rem;
    }

    .mp-section-head p {
        margin: 0.25rem 0 0;
        color: var(--mp-muted);
        font-size: 0.93rem;
    }

    .mp-status-strip {
        display: flex;
        flex-wrap: wrap;
        gap: 0.65rem 1rem;
        align-items: center;
        margin-top: 0.65rem;
        padding: 0.72rem 0.85rem;
        border: 1px solid var(--mp-border);
        border-radius: 11px;
        background: #fafbfe;
        color: var(--mp-ink);
        font-size: 0.9rem;
    }

    .mp-status-item {
        display: inline-flex;
        gap: 0.38rem;
        align-items: center;
    }

    .mp-success-text {
        color: var(--mp-green);
        font-weight: 700;
    }

    .mp-warning-text {
        color: var(--mp-amber);
        font-weight: 700;
    }

    .mp-neutral-text {
        color: var(--mp-muted);
    }

    .mp-overlap {
        margin-top: 0.55rem;
        padding: 0.7rem 0.8rem;
        border: 1px solid #efc46f;
        border-radius: 10px;
        background: var(--mp-amber-soft);
        color: #6d4700;
        font-size: 0.9rem;
    }

    .mp-overlap strong {
        color: #5c3c00;
    }

    .mp-completion {
        padding: 0.85rem 1rem;
        border: 1px solid #b8dec9;
        border-radius: 12px;
        background: var(--mp-green-soft);
        color: #24593a;
    }

    .mp-completion strong {
        color: #17482e;
    }

    .mp-privacy {
        margin-top: 0.65rem;
        color: var(--mp-muted);
        font-size: 0.82rem;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--mp-border) !important;
        border-radius: 14px !important;
        background: var(--mp-white) !important;
        box-shadow: var(--mp-shadow);
    }

    div[data-testid="stFileUploaderDropzone"] {
        min-height: 150px;
        border: 2px dashed #aebce2 !important;
        border-radius: 13px !important;
        background: #f8faff !important;
    }

    div[data-testid="stFileUploaderDropzone"]:hover {
        border-color: var(--mp-blue) !important;
        background: var(--mp-blue-soft) !important;
    }

    div.stButton > button,
    div.stDownloadButton > button,
    [data-testid="stFormSubmitButton"] > button {
        min-height: 44px;
        border-radius: 10px;
        font-weight: 750;
    }

    div.stButton > button:focus-visible,
    div.stDownloadButton > button:focus-visible,
    input:focus-visible,
    textarea:focus-visible,
    [role="button"]:focus-visible {
        outline: 3px solid rgba(49, 87, 213, 0.3) !important;
        outline-offset: 2px;
    }

    button[kind="primary"] {
        border-color: var(--mp-blue) !important;
        background: var(--mp-blue) !important;
    }

    button[kind="primary"]:hover {
        border-color: var(--mp-blue-dark) !important;
        background: var(--mp-blue-dark) !important;
    }

    [data-testid="stMetric"] {
        min-height: 105px;
        padding: 0.9rem;
        border: 1px solid var(--mp-border);
        border-radius: 12px;
        background: var(--mp-white);
        box-shadow: var(--mp-shadow);
    }

    [data-testid="stMetricLabel"] {
        color: var(--mp-muted);
    }

    [data-baseweb="tab-list"] {
        gap: 0.3rem;
        padding: 0.2rem;
        border-radius: 10px;
        background: #edf1f7;
    }

    [data-baseweb="tab"] {
        min-height: 42px;
        border-radius: 8px;
    }

    [aria-selected="true"][data-baseweb="tab"] {
        background: var(--mp-white);
        color: var(--mp-ink);
        box-shadow: 0 2px 8px rgba(32, 48, 88, 0.08);
    }

    [data-testid="stDataFrame"] {
        border: 1px solid var(--mp-border);
        border-radius: 11px;
        overflow: hidden;
    }

    .st-key-sticky_action_bar {
        border-top: 1px solid var(--mp-border);
        background: rgba(255, 255, 255, 0.97);
        box-shadow: 0 -8px 28px rgba(32, 48, 88, 0.10);
        backdrop-filter: blur(12px);
    }

    .st-key-sticky_action_bar > div {
        max-width: 1180px;
        margin: 0 auto;
        padding: 0.55rem 1rem;
    }

    .mp-action-summary {
        padding-top: 0.55rem;
        color: var(--mp-muted);
        font-size: 0.9rem;
    }

    .mp-footer {
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid var(--mp-border);
        color: var(--mp-muted);
        font-size: 0.8rem;
        text-align: center;
    }

    @media (max-width: 760px) {
        .block-container {
            padding: 0.8rem 0.8rem 7rem;
        }

        .mp-stepper {
            grid-template-columns: 1fr 1fr;
            gap: 0.75rem;
        }

        .mp-step::after {
            display: none;
        }

        .mp-step-label {
            white-space: normal;
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
            scroll-behavior: auto !important;
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def safe_filename(original_name: str, used_names: set[str]) -> str:
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
    rows: list[dict[str, Any]] = []
    ready_count = 0
    total_size = 0

    for uploaded_file in uploaded_files or []:
        original_name = Path(uploaded_file.name).name
        data = uploaded_file.getvalue()
        size = len(data)
        total_size += size

        if original_name.startswith("."):
            status = "⚠ Needs attention"
            detail = "Hidden system file"
        elif size == 0:
            status = "✕ Invalid"
            detail = "Empty file"
        elif data[:4] != b"MThd":
            status = "✕ Invalid"
            detail = "Standard MIDI header is missing"
        else:
            status = "✓ Ready"
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

            destination = folder / safe_filename(original_name, used_names)
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


def average_segment_rows(segment_df: pd.DataFrame) -> pd.DataFrame:
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

            header_fill = PatternFill(fill_type="solid", fgColor="3157D5")
            header_font = Font(color="FFFFFF", bold=True)

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


def display_dataframe(dataframe: pd.DataFrame) -> None:
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


def result_summary(dataframe: pd.DataFrame) -> dict[str, float | None]:
    data = dataframe.copy()

    if "Name" in data.columns:
        totals_rows = data[data["Name"].astype(str).str.upper().eq("TOTALS")]
        non_total_rows = data[~data["Name"].astype(str).str.upper().eq("TOTALS")]
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
            numeric = pd.to_numeric(non_total_rows[column], errors="coerce")
            summary[key] = float(numeric.sum()) if numeric.notna().any() else None

    return summary


def chartable_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
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
        "Metric",
        options=available,
        index=available.index(default_metric),
        format_func=lambda metric: METRIC_LABELS.get(metric, metric),
        key=f"chart_metric_{result_name}_{analysis_cycle}",
        help=(
            "When a cell contains a mean and standard deviation, "
            "the chart uses the mean."
        ),
    )

    chart_df = chartable_dataframe(dataframe)
    chart_df = chart_df[
        ~chart_df["Name"].astype(str).str.upper().eq("TOTALS")
    ].copy()
    chart_df = chart_df.dropna(subset=[selected_metric])

    if chart_df.empty:
        st.info("The selected metric has no chartable values.")
        return

    metric_title = METRIC_LABELS.get(selected_metric, selected_metric)

    try:
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
                .str.replace(r"\s*Segment\s+\d+\s*$", "", regex=True)
                .str.strip()
            )
            chart_df.loc[chart_df["Session"].eq(""), "Session"] = "Average"

            segment_chart = (
                chart_df[["Segment", "Session", selected_metric]]
                .dropna(subset=["Segment", selected_metric])
                .rename(columns={selected_metric: "Value"})
            )
            segment_chart["Segment"] = segment_chart["Segment"].astype(int)
            segment_chart["Value"] = pd.to_numeric(
                segment_chart["Value"],
                errors="coerce",
            )
            segment_chart = segment_chart.dropna(subset=["Value"])

            if not segment_chart.empty:
                st.vega_lite_chart(
                    segment_chart,
                    {
                        "mark": {
                            "type": "line",
                            "point": True,
                            "tooltip": True,
                        },
                        "encoding": {
                            "x": {
                                "field": "Segment",
                                "type": "quantitative",
                                "title": "Segment",
                                "axis": {"tickMinStep": 1},
                            },
                            "y": {
                                "field": "Value",
                                "type": "quantitative",
                                "title": metric_title,
                                "scale": {"zero": False},
                            },
                            "color": {
                                "field": "Session",
                                "type": "nominal",
                                "title": "Session",
                            },
                            "tooltip": [
                                {
                                    "field": "Session",
                                    "type": "nominal",
                                    "title": "Session",
                                },
                                {
                                    "field": "Segment",
                                    "type": "quantitative",
                                    "title": "Segment",
                                },
                                {
                                    "field": "Value",
                                    "type": "quantitative",
                                    "title": metric_title,
                                },
                            ],
                        },
                    },
                    width="stretch",
                    height=390,
                    key=f"segment_chart_{selected_metric}_{analysis_cycle}",
                )
                return

        whole_chart = (
            chart_df[["Name", selected_metric]]
            .rename(columns={"Name": "Session", selected_metric: "Value"})
        )
        whole_chart["Value"] = pd.to_numeric(
            whole_chart["Value"],
            errors="coerce",
        )
        whole_chart = whole_chart.dropna(subset=["Value"])

        st.vega_lite_chart(
            whole_chart,
            {
                "mark": {
                    "type": "bar",
                    "cornerRadiusTopLeft": 5,
                    "cornerRadiusTopRight": 5,
                    "tooltip": True,
                },
                "encoding": {
                    "x": {
                        "field": "Session",
                        "type": "nominal",
                        "title": "Session",
                        "sort": None,
                        "axis": {
                            "labelAngle": -35,
                            "labelLimit": 180,
                        },
                    },
                    "y": {
                        "field": "Value",
                        "type": "quantitative",
                        "title": metric_title,
                    },
                    "tooltip": [
                        {
                            "field": "Session",
                            "type": "nominal",
                            "title": "Session",
                        },
                        {
                            "field": "Value",
                            "type": "quantitative",
                            "title": metric_title,
                        },
                    ],
                },
            },
            width="stretch",
            height=390,
            key=f"whole_chart_{selected_metric}_{analysis_cycle}",
        )

    except Exception as chart_error:
        st.warning(
            "The chart could not be displayed, but tables and downloads remain available."
        )
        with st.expander("Chart diagnostic details"):
            st.code(str(chart_error))


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


def start_new_analysis() -> None:
    clear_analysis_state()
    st.session_state["analysis_cycle"] = (
        int(st.session_state.get("analysis_cycle", 0)) + 1
    )
    st.rerun()


@st.dialog("Start a new analysis?")
def confirm_new_analysis() -> None:
    st.write(
        "This will remove the current uploads, settings, and displayed results."
    )
    confirm_column, cancel_column = st.columns(2)

    with confirm_column:
        if st.button(
            "Start new analysis",
            type="primary",
            use_container_width=True,
            key=f"confirm_reset_{analysis_cycle}",
        ):
            start_new_analysis()

    with cancel_column:
        if st.button(
            "Keep current analysis",
            use_container_width=True,
            key=f"cancel_reset_{analysis_cycle}",
        ):
            st.rerun()


upload_key = f"midi_upload_{analysis_cycle}"
existing_uploads = st.session_state.get(upload_key, [])
existing_results = st.session_state.get("midipy_results")

title_column, help_column, reset_column = st.columns(
    [6, 1.15, 1.45],
    vertical_alignment="center",
)

with title_column:
    st.markdown(
        """
        <h1 class="mp-brand">MidiPy Analysis Studio</h1>
        <p class="mp-subtitle">
            Validate MIDI files, configure mappings, analyze performance, and export results.
        </p>
        """,
        unsafe_allow_html=True,
    )

with help_column:
    with st.popover(
        "Help",
        use_container_width=True,
    ):
        st.markdown(
            """
            **Workflow**

            1. Upload one or more `.mid` or `.midi` files.
            2. Confirm the body-part mappings.
            3. Choose the analysis scope and results.
            4. Analyze, review, and export.

            **Terminology**

            - **UE:** upper extremity
            - **LF:** left foot
            - **RF:** right foot
            - **Velocity:** MIDI performance intensity
            - **Asynchrony:** timing difference from the quantized beat
            """
        )

with reset_column:
    if st.button(
        "New analysis",
        use_container_width=True,
        key=f"new_analysis_top_{analysis_cycle}",
    ):
        if existing_uploads or existing_results:
            confirm_new_analysis()
        else:
            start_new_analysis()

if existing_results:
    current_stage = 4
elif existing_uploads:
    current_stage = 2
else:
    current_stage = 1

step_labels = ["Upload", "Configure", "Analyze", "Review"]
step_html = []

for index, label in enumerate(step_labels, start=1):
    if index < current_stage:
        state_class = "completed"
        badge = "✓"
    elif index == current_stage:
        state_class = "current"
        badge = str(index)
    else:
        state_class = "upcoming"
        badge = str(index)

    step_html.append(
        f"""
        <div class="mp-step {state_class}">
            <span class="mp-step-badge">{badge}</span>
            <span class="mp-step-label">{label}</span>
        </div>
        """
    )

st.markdown(
    '<div class="mp-stepper">' + "".join(step_html) + "</div>",
    unsafe_allow_html=True,
)


st.markdown(
    """
    <div class="mp-section-head">
        <h2>1. Upload MIDI files</h2>
        <p>Add all sessions that belong to this analysis.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.container(border=True):
    uploaded_files = st.file_uploader(
        "Drag and drop MIDI files or browse",
        type=["mid", "midi"],
        accept_multiple_files=True,
        key=upload_key,
        help="Supported formats: MID and MIDI. Maximum size is controlled by the host.",
    )

    precheck_rows, ready_count, total_size = precheck_uploads(uploaded_files)
    attention_count = len(precheck_rows) - ready_count

    if uploaded_files:
        ready_text = (
            f'<span class="mp-success-text">✓ {ready_count} ready</span>'
            if ready_count
            else '<span class="mp-warning-text">No ready files</span>'
        )
        attention_text = (
            f'<span class="mp-warning-text">⚠ {attention_count} need attention</span>'
            if attention_count
            else '<span class="mp-neutral-text">No file problems detected</span>'
        )

        st.markdown(
            f"""
            <div class="mp-status-strip">
                <span class="mp-status-item">{ready_text}</span>
                <span class="mp-status-item">{attention_text}</span>
                <span class="mp-status-item mp-neutral-text">
                    {human_file_size(total_size)} total
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander(
            f"View file details · {len(uploaded_files)} selected",
            expanded=attention_count > 0,
        ):
            st.dataframe(
                pd.DataFrame(precheck_rows),
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.caption("No files selected · Supported formats: MID and MIDI")

    st.markdown(
        """
        <div class="mp-privacy">
            Privacy: files are copied to a temporary workspace during analysis and
            removed afterward. Use de-identified files and follow institutional rules.
        </div>
        """,
        unsafe_allow_html=True,
    )


st.markdown(
    """
    <div class="mp-section-head">
        <h2>2. Configure the analysis</h2>
        <p>Defaults are prepared. Change only what is required for this dataset.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

mapping_column, scope_column = st.columns(
    [1.08, 0.92],
    gap="medium",
)

with mapping_column:
    with st.container(border=True):
        st.subheader("Body-part mapping")
        st.caption("Choose note numbers instead of editing an encoded text string.")

        ue_keys = st.multiselect(
            "Upper-extremity MIDI notes",
            options=list(range(128)),
            default=DEFAULT_UE_KEYS,
            key=f"ue_notes_{analysis_cycle}",
            help=(
                "Search for a note number, select it, or remove an existing chip. "
                "MIDI note values range from 0 to 127."
            ),
            placeholder="Search and select MIDI note values",
        )

        st.caption(f"{len(ue_keys)} upper-extremity notes selected")

        foot_left, foot_right = st.columns(2)

        with foot_left:
            left_foot_key = int(
                st.number_input(
                    "Left foot",
                    min_value=0,
                    max_value=127,
                    value=44,
                    step=1,
                    key=f"left_foot_{analysis_cycle}",
                    help="One MIDI note value from 0 to 127.",
                )
            )

        with foot_right:
            right_foot_key = int(
                st.number_input(
                    "Right foot",
                    min_value=0,
                    max_value=127,
                    value=36,
                    step=1,
                    key=f"right_foot_{analysis_cycle}",
                    help="One MIDI note value from 0 to 127.",
                )
            )

        overlap_messages: list[str] = []

        ue_foot_overlap = sorted(
            set(ue_keys) & {left_foot_key, right_foot_key}
        )
        if ue_foot_overlap:
            overlap_messages.append(
                "UE and foot mapping: "
                + ", ".join(map(str, ue_foot_overlap))
            )

        if left_foot_key == right_foot_key:
            overlap_messages.append(
                f"Left foot and right foot both use note {left_foot_key}"
            )

        if overlap_messages:
            st.markdown(
                """
                <div class="mp-overlap">
                    <strong>⚠ Mapping overlap</strong><br>
                    {}
                </div>
                """.format("<br>".join(overlap_messages)),
                unsafe_allow_html=True,
            )
        else:
            st.success("Mappings are distinct.")

with scope_column:
    with st.container(border=True):
        st.subheader("Analysis scope")
        st.caption("Select the level of detail needed for this task.")

        analysis_mode = st.segmented_control(
            "Analysis type",
            options=[
                "Whole files + segments",
                "Whole files only",
                "Segments only",
            ],
            default="Whole files + segments",
            selection_mode="single",
            required=True,
            key=f"analysis_mode_{analysis_cycle}",
            help=(
                "Whole-file results summarize complete sessions. "
                "Segment results show changes across time."
            ),
        )

        run_whole = analysis_mode in {
            "Whole files + segments",
            "Whole files only",
        }
        run_segments = analysis_mode in {
            "Whole files + segments",
            "Segments only",
        }

        if analysis_mode == "Whole files + segments":
            st.caption("Recommended: summary and time-based detail.")
        elif analysis_mode == "Whole files only":
            st.caption("Fastest option: one result row per session.")
        else:
            st.caption("Time-based detail without whole-session summaries.")

        if run_segments:
            with st.container(border=True):
                st.markdown("**Segment settings**")

                number_of_segments = int(
                    st.slider(
                        "Number of segments",
                        min_value=2,
                        max_value=20,
                        value=5,
                        key=f"segment_count_{analysis_cycle}",
                        help="Each MIDI file is divided into equal-duration segments.",
                    )
                )

                average_segments = st.checkbox(
                    "Average matching segments across files",
                    value=False,
                    key=f"average_segments_{analysis_cycle}",
                    help=(
                        "All Segment 1 rows are averaged together, then all Segment 2 "
                        "rows, and so on."
                    ),
                )
        else:
            number_of_segments = 5
            average_segments = False


preset_key = f"result_preset_{analysis_cycle}"
current_preset = st.session_state.get(preset_key, "Complete report")

with st.expander(
    f"Results to include · {current_preset}",
    expanded=False,
):
    result_preset = st.segmented_control(
        "Result detail",
        options=[
            "Complete report",
            "Counts only",
            "Custom",
        ],
        default="Complete report",
        selection_mode="single",
        required=True,
        key=preset_key,
    )

    if result_preset == "Complete report":
        selected_metrics = AVAILABLE_METRICS.copy()
        st.info(
            "Includes note counts, velocity, and asynchrony measures."
        )

    elif result_preset == "Counts only":
        selected_metrics = COUNT_METRICS.copy()
        st.info(
            "Includes total, upper-extremity, left-foot, and right-foot counts."
        )

    else:
        metric_rows = []
        for metric in AVAILABLE_METRICS:
            metric_rows.append(
                {
                    "Include": True,
                    "Category": METRIC_CATEGORY[metric],
                    "Measure": METRIC_LABELS[metric],
                    "Description": METRIC_HELP[metric],
                }
            )

        metric_editor = pd.DataFrame(
            metric_rows,
            index=AVAILABLE_METRICS,
        )

        edited_metrics = st.data_editor(
            metric_editor,
            use_container_width=True,
            hide_index=True,
            disabled=["Category", "Measure", "Description"],
            key=f"custom_metrics_{analysis_cycle}",
            column_config={
                "Include": st.column_config.CheckboxColumn(
                    "Include",
                    help="Select the measures to include in the output.",
                    default=True,
                    width="small",
                ),
                "Category": st.column_config.TextColumn(
                    "Category",
                    width="small",
                ),
                "Measure": st.column_config.TextColumn(
                    "Measure",
                    width="medium",
                ),
                "Description": st.column_config.TextColumn(
                    "Description",
                    width="large",
                ),
            },
        )

        selected_metrics = edited_metrics.index[
            edited_metrics["Include"].fillna(False)
        ].tolist()

        st.caption(
            f"{len(selected_metrics)} of {len(AVAILABLE_METRICS)} measures selected"
        )


current_settings = {
    "ue_keys": sorted(ue_keys),
    "left_foot_key": left_foot_key,
    "right_foot_key": right_foot_key,
    "analysis_mode": analysis_mode,
    "number_of_segments": number_of_segments,
    "average_segments": average_segments,
    "selected_metrics": selected_metrics,
}

current_upload_signature = upload_signature(uploaded_files)
current_settings_signature = settings_signature(current_settings)

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

results_are_stale = bool(results) and not results_are_current

if results_are_stale:
    st.warning(
        "Files or settings changed after the displayed results were created. "
        "Refresh the analysis to update them."
    )


analysis_disabled = (
    not uploaded_files
    or ready_count == 0
    or not selected_metrics
    or not ue_keys
)

action_label = (
    "Refresh analysis"
    if results_are_stale
    else "Analyze MIDI files"
)

with st.bottom():
    with st.container(key="sticky_action_bar"):
        summary_column, action_column = st.columns(
            [5, 2],
            vertical_alignment="center",
        )

        with summary_column:
            if not uploaded_files:
                action_summary = "Upload MIDI files to begin."
            elif ready_count == 0:
                action_summary = "No valid MIDI file is ready."
            else:
                action_summary = (
                    f"{ready_count} file(s) ready · "
                    f"{len(selected_metrics)} result measure(s) selected"
                )

            st.markdown(
                f'<div class="mp-action-summary">{action_summary}</div>',
                unsafe_allow_html=True,
            )

        with action_column:
            submitted = st.button(
                action_label,
                type="primary",
                use_container_width=True,
                disabled=analysis_disabled,
                key=f"analyze_{analysis_cycle}",
            )


if submitted:
    with st.status(
        "Analyzing MIDI files…",
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
                        "None of the selected files passed complete MIDI validation."
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

                new_results: dict[str, pd.DataFrame] = {}

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
                    new_results["Whole_File_Results"] = whole_df

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

                    new_results["Segment_Results"] = segment_df

                st.session_state["midipy_results"] = new_results
                st.session_state["midipy_valid_names"] = valid_names
                st.session_state["midipy_skipped_files"] = skipped_files
                st.session_state[
                    "midipy_analysis_signature"
                ] = current_upload_signature
                st.session_state[
                    "midipy_analysis_settings_signature"
                ] = current_settings_signature
                st.session_state["midipy_last_settings"] = current_settings

                analysis_status.update(
                    label=(
                        f"Analysis complete — {len(valid_names)} file(s) processed."
                    ),
                    state="complete",
                    expanded=False,
                )

            st.rerun()

        except Exception as error:
            clear_analysis_state()
            analysis_status.update(
                label="The analysis could not be completed.",
                state="error",
                expanded=True,
            )

            st.error(
                "MidiPy encountered a problem while processing the files."
            )

            st.markdown(
                """
                - Confirm that the files are genuine Standard MIDI files.
                - Remove empty or damaged files.
                - Confirm that all mappings use values from 0 to 127.
                """
            )

            with st.expander("Technical details for support"):
                st.code(str(error))


results = st.session_state.get("midipy_results")
results_are_current = (
    bool(results)
    and st.session_state.get("midipy_analysis_signature")
        == current_upload_signature
    and st.session_state.get("midipy_analysis_settings_signature")
        == current_settings_signature
)

if results and results_are_current:
    valid_names = st.session_state.get("midipy_valid_names", [])
    skipped_files = st.session_state.get("midipy_skipped_files", [])

    st.markdown(
        """
        <div class="mp-section-head">
            <h2>4. Review results</h2>
            <p>Review the overview first, then inspect detailed tables and file quality.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    excel_bytes = dataframe_to_excel_bytes(results)
    csv_zip_bytes = dataframes_to_csv_zip(results)

    completion_column, excel_column, csv_column = st.columns(
        [5, 1.55, 1.55],
        vertical_alignment="center",
    )

    with completion_column:
        skipped_text = (
            f" · {len(skipped_files)} skipped"
            if skipped_files
            else ""
        )
        st.markdown(
            f"""
            <div class="mp-completion">
                <strong>✓ Analysis completed</strong><br>
                {len(valid_names)} file(s) processed{skipped_text}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with excel_column:
        st.download_button(
            "Download Excel",
            data=excel_bytes,
            file_name="MidiPy_Results.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            use_container_width=True,
        )

    with csv_column:
        st.download_button(
            "Download CSV",
            data=csv_zip_bytes,
            file_name="MidiPy_CSV_Results.zip",
            mime="application/zip",
            use_container_width=True,
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
            f"{int(summary['total']):,}"
            if summary["total"] is not None
            else "—",
        )
        summary_columns[2].metric(
            "UE notes",
            f"{int(summary['ue']):,}"
            if summary["ue"] is not None
            else "—",
        )
        summary_columns[3].metric(
            "LF notes",
            f"{int(summary['lf']):,}"
            if summary["lf"] is not None
            else "—",
        )
        summary_columns[4].metric(
            "RF notes",
            f"{int(summary['rf']):,}"
            if summary["rf"] is not None
            else "—",
        )
    else:
        summary_columns = st.columns(3)
        summary_columns[0].metric("Files analyzed", len(valid_names))
        summary_columns[1].metric(
            "Segment rows",
            len(results.get("Segment_Results", [])),
        )
        summary_columns[2].metric("Files skipped", len(skipped_files))

    overview_tab, tables_tab, quality_tab = st.tabs(
        [
            "Overview",
            "Detailed tables",
            "File quality",
        ]
    )

    with overview_tab:
        result_options = list(results.keys())

        selected_result_name = st.segmented_control(
            "Result set",
            options=result_options,
            default=result_options[0],
            selection_mode="single",
            required=True,
            format_func=lambda name: (
                "Whole-file results"
                if name == "Whole_File_Results"
                else "Segment results"
            ),
            key=f"result_set_{analysis_cycle}",
        )

        render_result_chart(
            results[selected_result_name],
            selected_result_name,
        )

        st.caption(
            "Velocity and asynchrony charts use the mean shown before "
            "the standard deviation."
        )

    with tables_tab:
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
                    f"{len(dataframe):,} row(s) × "
                    f"{len(dataframe.columns):,} column(s)"
                )

    with quality_tab:
        quality_left, quality_right = st.columns(2)

        with quality_left:
            st.markdown("**Successfully analyzed**")
            for filename in valid_names:
                st.write(f"✓ {filename}")

        with quality_right:
            st.markdown("**Skipped during validation**")
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
            "The temporary analysis workspace is removed after processing."
        )


st.markdown(
    """
    <div class="mp-footer">
        MidiPy Analysis Studio · Guided, accessible, and error-tolerant MIDI analysis
    </div>
    """,
    unsafe_allow_html=True,
)
