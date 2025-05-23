# Midipy

A Python package for MIDI data processing, analysis, and parsing.

## Overview

Midipy provides tools to read, analyze, and process MIDI files. This package decodes MIDI data, extracts musical features, and enables parsing of multiple MIDI files within a directory. It’s ideal for music data analysis, educational projects, and MIDI-related applications in Python.

## Features

* **Read MIDI files**: Parse and load MIDI files for analysis.
* **Analyze MIDI data**: Extract information such as note counts, velocities, and asynchrony.
* **Batch processing**: Process multiple MIDI files from a specified directory.
* **Segment-wise Analysis**: Perform analyses on specific segments within each MIDI file.

## Installation

To install the package, use:

```bash
pip install midipy
```

## Usage

### Importing and Using the `parser` Function

The main function to use in this package is the `parser` function, which parses all MIDI files in a specified directory and extracts relevant metrics. Below are the details on how to use this function.

### Parameters for `parser`

* **`source`**: (Required) The directory path containing MIDI files. Ensure that this directory contains only `.mid` files.
* **`metrics`**: (Optional) Specify `['all']` to include all available metrics or provide a list of specific metrics you want to display.
* **`output_format`**: (Optional) Choose `'excel'` or `'csv'` as the format for saving the output file.
* **`save_path`**: (Optional) Define the path and filename (without extension) for the output file. The default is `"Output"`.
* **`ue_keys`**: (Optional) List of MIDI note values to treat as upper extremity. Defaults to `[38, 40, 43, 51, 53, 59]`.
* **`lf_key`**: (Optional) Single MIDI note value for left foot. Defaults to `44`.
* **`rf_key`**: (Optional) Single MIDI note value for right foot. Defaults to `36`.

### Segment-wise Analysis Using `parser_segments`

You can perform segment-wise analysis by using the `parser_segments` function. It divides each MIDI file into a specified number of segments and calculates metrics for each segment.

* **`source`**: (Required) Directory path containing MIDI files.
* **`metrics`**: (Optional) See above.
* **`output_format`**: (Optional) `'excel'` or `'csv`.
* **`save_path`**: (Optional) Base name for output file. Defaults to `'SegmentOutput'`.
* **`num_segments`**: (Optional) Number of segments to divide each MIDI file into for analysis. Defaults to `10`.
* **`mean_segments`**: (Optional) If `True`, averages each segment index across all files. Defaults to `False`.
* **`ue_keys`**, **`lf_key`**, **`rf_key`**: Same as in `parser`—override default extremity note values.

### Available Metrics

When specifying metrics in the `metrics` parameter, use the following keywords to select specific data columns:

* **`'Total_Counts'`**: The total number of notes in each MIDI file.
* **`'UE_Counts'`**: Count of upper extremity (UE) notes, such as certain drum hits.
* **`'LF_Counts'`**: Count of left foot (LF) notes.
* **`'RF_Counts'`**: Count of right foot (RF) notes.
* **`'Avg_Velocity'`**: Average velocity of all notes, including a measure of the standard deviation (e.g., `45.37 (14.25)`).
* **`'UE_Velocity'`**: Average velocity of UE notes, with standard deviation.
* **`'LF_Velocity'`**: Average velocity of LF notes, with standard deviation.
* **`'RF_Velocity'`**: Average velocity of RF notes, with standard deviation.
* **`'Avg_Async'`**: Average asynchrony for all notes, showing the mean and standard deviation.
* **`'UE_Async'`**: Average asynchrony for UE notes, with standard deviation.
* **`'LF_Async'`**: Average asynchrony for LF notes, with standard deviation.
* **`'RF_Async'`**: Average asynchrony for RF notes, with standard deviation.

> **Note**: When selecting a subset of metrics, include `'Name'` in your `metrics` list if you want the session identifiers (e.g., "Patient 1 session 2") to appear in the DataFrame output.

### Example

The following example demonstrates how to parse MIDI files in a specified directory, select specific metrics, and save the output to an Excel file.

```python
import midipy
from midipy.midi_parser import parser

# Default usage with optional overrides:
df_default = parser(
    source="./P1",
    metrics=['Total_Counts', 'Avg_Velocity'],
    output_format='excel',
    save_path='MyMIDIOutput'
)

# Customizing extremity keys:
df_custom = parser(
    source="./P1",
    ue_keys=[36, 38, 40],
    lf_key=37,
    rf_key=39,
    metrics=['UE_Counts', 'RF_Async'],
    output_format='csv'
)

print(df_default)
print(df_custom)
```

### Segment-wise Analysis Example

```python
import midipy
from midipy.midi_parser import parser_segments

# Default segment-wise analysis:
df_segments = parser_segments(
    source="./P1",
    num_segments=10
)

# Segment analysis with custom keys and averaging:
df_mean_segments = parser_segments(
    source="./P1",
    num_segments=5,
    mean_segments=True,
    ue_keys=[36, 38, 40],
    lf_key=37,
    rf_key=39
)

print(df_segments)
print(df_mean_segments)
```

In these examples:

* **Directory**: The directory `./P1` contains the MIDI files to be parsed.
* **Metrics** and **Overrides**: Demonstrates both default and custom extremity-key settings.

### Output Files

* `parser` output: Contains selected metrics for each session (entire MIDI file).
* `parser_segments` output: Contains metrics for each segment within each session, offering finer-grained analysis.

