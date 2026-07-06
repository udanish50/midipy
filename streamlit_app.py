from __future__ import annotations

import io
import re
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
import streamlit as st
from midipy.midi_analysis import midiInfo
from midipy.midi_parser import parser, parser_segments
from midipy.midi_reader import readmidi


st.set_page_config(
    page_title="MidiPy Easy Dashboard",
    page_icon="🎵",
    layout="wide",
)

DEFAULT_UE_KEYS = [
    24, 25, 26, 27, 28, 30, 31, 32, 34, 35,
    37, 38, 39, 40, 41, 42, 43, 46, 47, 48,
    49, 51, 52, 53, 55, 59, 66, 67, 71, 78, 79,
]

AVAILABLE_METRICS = [
    "Total_Counts",
    "UE_Counts",
    "LF_Counts",
    "RF_Counts",
    "Avg_Velocity",
    "UE_Velocity",
    "LF_Velocity",
    "RF_Velocity",
    "Avg_Async",
    "UE_Async",
    "LF_Async",
    "RF_Async",
]


def parse_note_list(text: str) -> list[int]:
    """Convert comma/space-separated note values into a validated list."""
    pieces = [item for item in re.split(r"[\s,;]+", text.strip()) if item]
    if not pieces:
        raise ValueError("Enter at least one UE note value.")

    values: list[int] = []
    for piece in pieces:
        try:
            value = int(piece)
        except ValueError as exc:
            raise ValueError(f'"{piece}" is not a whole MIDI note number.') from exc

        if not 0 <= value <= 127:
            raise ValueError(f"MIDI note {value} is outside the allowed range 0–127.")

        if value not in values:
            values.append(value)

    return values


def safe_filename(original_name: str, used_names: set[str]) -> str:
    """Create a safe unique lowercase .mid filename for MidiPy."""
    stem = Path(original_name).stem
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_") or "midi_file"

    candidate = f"{stem}.mid"
    number = 2
    while candidate.lower() in used_names:
        candidate = f"{stem}_{number}.mid"
        number += 1

    used_names.add(candidate.lower())
    return candidate


def validate_and_save_uploads(uploaded_files, folder: Path):
    """Save only genuine, readable MIDI files into a clean temporary folder."""
    valid_names: list[str] = []
    skipped: list[tuple[str, str]] = []
    used_names: set[str] = set()

    for uploaded_file in uploaded_files:
        original_name = Path(uploaded_file.name).name
        data = uploaded_file.getvalue()
        destination: Path | None = None

        try:
            if original_name.startswith("."):
                raise ValueError("hidden file")

            if not data:
                raise ValueError("empty file (0 bytes)")

            if data[:4] != b"MThd":
                raise ValueError("not a Standard MIDI file; MThd header is missing")

            destination_name = safe_filename(original_name, used_names)
            destination = folder / destination_name
            destination.write_bytes(data)

            # Perform a deeper MidiPy validation before the batch analysis.
            midi = readmidi(str(destination))
            notes, _, bpms = midiInfo(midi, 0)

            if notes is None or len(notes) == 0:
                raise ValueError("no readable MIDI notes were found")

            if bpms is None or len(bpms) == 0:
                raise ValueError("no readable tempo information was found")

            valid_names.append(original_name)

        except Exception as error:
            if destination is not None and destination.exists():
                destination.unlink()
            skipped.append((original_name, str(error)))

    return valid_names, skipped


def average_segment_rows(segment_df: pd.DataFrame) -> pd.DataFrame:
    """Average each segment number across all uploaded MIDI files."""
    working = segment_df.copy()
    working["Segment_Number"] = (
        working["Name"]
        .str.extract(r"Segment\s+(\d+)", expand=False)
        .astype(int)
    )

    numeric_columns = [
        column
        for column in working.select_dtypes(include="number").columns
        if column != "Segment_Number"
    ]

    averaged = (
        working.groupby("Segment_Number", as_index=False)[numeric_columns]
        .mean()
    )
    averaged.insert(
        0,
        "Name",
        "Segment " + averaged["Segment_Number"].astype(str),
    )
    return averaged


def dataframe_to_excel_bytes(sheets: dict[str, pd.DataFrame]) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, dataframe in sheets.items():
            dataframe.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    return output.getvalue()


def dataframes_to_csv_zip(sheets: dict[str, pd.DataFrame]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, dataframe in sheets.items():
            archive.writestr(
                f"{name}.csv",
                dataframe.to_csv(index=False).encode("utf-8"),
            )
    return output.getvalue()


def show_count_chart(dataframe: pd.DataFrame, title: str) -> None:
    count_columns = [
        column
        for column in ["Total_Counts", "UE_Counts", "LF_Counts", "RF_Counts"]
        if column in dataframe.columns
    ]

    if not count_columns or "Name" not in dataframe.columns:
        return

    chart_data = dataframe[dataframe["Name"] != "TOTALS"].copy()
    if chart_data.empty:
        return

    for column in count_columns:
        chart_data[column] = pd.to_numeric(chart_data[column], errors="coerce")

    st.subheader(title)
    st.bar_chart(chart_data.set_index("Name")[count_columns])


# ---------------------------------------------------------------------
# Page heading
# ---------------------------------------------------------------------
st.title("🎵 MidiPy Easy Dashboard")
st.caption(
    "Upload MIDI files, choose the body-part note mappings, and download the results."
)

with st.expander("Very simple instructions", expanded=True):
    st.markdown(
        """
        1. Drag your `.mid` or `.midi` files into the upload box.
        2. Leave the settings unchanged unless you need different UE/LF/RF values.
        3. Click **Analyze MIDI files**.
        4. Preview the tables and download Excel or CSV results.
        """
    )

# ---------------------------------------------------------------------
# Sidebar settings
# ---------------------------------------------------------------------
with st.sidebar:
    st.header("Settings")

    ue_text = st.text_area(
        "Upper-extremity (UE) note values",
        value=", ".join(str(value) for value in DEFAULT_UE_KEYS),
        help="Enter whole MIDI note numbers separated by commas.",
        height=145,
    )

    left_foot_key = int(
        st.number_input(
            "Left-foot note value",
            min_value=0,
            max_value=127,
            value=44,
            step=1,
        )
    )

    right_foot_key = int(
        st.number_input(
            "Right-foot note value",
            min_value=0,
            max_value=127,
            value=36,
            step=1,
        )
    )

    st.divider()
    st.subheader("Analysis")

    run_whole = st.checkbox("Whole-file analysis", value=True)
    run_segments = st.checkbox("Segment analysis", value=True)

    number_of_segments = int(
        st.slider(
            "Number of segments",
            min_value=2,
            max_value=20,
            value=5,
            disabled=not run_segments,
        )
    )

    average_segments = st.checkbox(
        "Average matching segments across files",
        value=False,
        disabled=not run_segments,
    )

    with st.expander("Choose result columns"):
        selected_metrics = st.multiselect(
            "Metrics",
            options=AVAILABLE_METRICS,
            default=AVAILABLE_METRICS,
        )
        st.caption("Name is always included automatically.")

# ---------------------------------------------------------------------
# File upload and Analyze button
# ---------------------------------------------------------------------
uploaded_files = st.file_uploader(
    "Drop MIDI files here",
    type=["mid", "midi"],
    accept_multiple_files=True,
    help="You can select several files together.",
)

left, right = st.columns([1, 3])
with left:
    analyze_clicked = st.button(
        "Analyze MIDI files",
        type="primary",
        use_container_width=True,
        disabled=not uploaded_files,
    )
with right:
    if uploaded_files:
        st.write(f"**{len(uploaded_files)} file(s) selected**")
    else:
        st.info("Select at least one MIDI file to begin.")

if analyze_clicked:
    if not run_whole and not run_segments:
        st.error("Select Whole-file analysis, Segment analysis, or both.")
        st.stop()

    if not selected_metrics:
        st.error("Select at least one result metric.")
        st.stop()

    try:
        ue_keys = parse_note_list(ue_text)
    except ValueError as error:
        st.error(str(error))
        st.stop()

    overlap = sorted(set(ue_keys) & {left_foot_key, right_foot_key})
    if overlap:
        st.warning(
            "These values appear in both UE and foot settings: "
            + ", ".join(map(str, overlap))
        )

    with st.spinner("Checking and analyzing the MIDI files..."):
        try:
            with tempfile.TemporaryDirectory(prefix="midipy_dashboard_") as temporary:
                temporary_path = Path(temporary)
                midi_folder = temporary_path / "valid_midi"
                midi_folder.mkdir()

                valid_names, skipped_files = validate_and_save_uploads(
                    uploaded_files,
                    midi_folder,
                )

                if not valid_names:
                    st.session_state.pop("midipy_results", None)
                    st.error("None of the uploaded files could be analyzed.")
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

        except Exception as error:
            st.session_state.pop("midipy_results", None)
            st.error("MidiPy could not finish the analysis.")
            st.exception(error)

# ---------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------
results = st.session_state.get("midipy_results")

if results:
    valid_names = st.session_state.get("midipy_valid_names", [])
    skipped_files = st.session_state.get("midipy_skipped_files", [])

    st.success(f"Analysis finished for {len(valid_names)} valid MIDI file(s).")

    with st.expander("File-check details"):
        st.write("**Analyzed files**")
        for filename in valid_names:
            st.write(f"✓ {filename}")

        if skipped_files:
            st.write("**Skipped files**")
            st.dataframe(
                pd.DataFrame(skipped_files, columns=["File", "Reason"]),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.write("No files were skipped.")

    tab_names = list(results.keys())
    tabs = st.tabs(
        [
            name.replace("_", " ")
            for name in tab_names
        ]
    )

    for tab, name in zip(tabs, tab_names):
        with tab:
            dataframe = results[name]
            st.dataframe(
                dataframe,
                use_container_width=True,
                hide_index=True,
            )
            show_count_chart(dataframe, "Note-count overview")

    st.subheader("Download results")

    excel_bytes = dataframe_to_excel_bytes(results)
    csv_zip_bytes = dataframes_to_csv_zip(results)

    download_left, download_right = st.columns(2)

    with download_left:
        st.download_button(
            "Download Excel workbook",
            data=excel_bytes,
            file_name="MidiPy_Results.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            use_container_width=True,
        )

    with download_right:
        st.download_button(
            "Download CSV files",
            data=csv_zip_bytes,
            file_name="MidiPy_CSV_Results.zip",
            mime="application/zip",
            use_container_width=True,
        )
