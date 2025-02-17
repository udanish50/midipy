
# Midipy

A Python package for MIDI data processing, analysis, and parsing.

## Overview

Midipy provides tools to read, analyze, and process MIDI files. This package decodes MIDI data, extracts musical features, and enables parsing of multiple MIDI files within a directory. It’s ideal for music data analysis, educational projects, and MIDI-related applications in Python.

## Features

- **Read MIDI files**: Parse and load MIDI files for analysis.
- **Analyze MIDI data**: Extract information such as note counts, velocities, and asynchrony.
- **Batch processing**: Process multiple MIDI files from a specified directory.
- **Segment-wise Analysis**: Perform analyses on specific segments within each MIDI file.

## Installation

To install the package, use:

```bash
pip install midipy
```

## Usage

### Importing and Using the `parser` Function

The main function to use in this package is the `parser` function, which parses all MIDI files in a specified directory and extracts relevant metrics. Below are the details on how to use this function.

### Parameters for `parser`

- **`source`**: (Required) The directory path containing MIDI files. Ensure that this directory contains only `.mid` files.
- **`metrics`**: (Optional) Specify `['all']` to include all available metrics or provide a list of specific metrics you want to display.
- **`output_format`**: (Optional) Choose `'excel'` or `'csv'` as the format for saving the output file.
- **`save_path`**: (Optional) Define the path and filename (without extension) for the output file. The default is `"Output"`.

### Segment-wise Analysis Using `parser_segments`

You can perform segment-wise analysis by using the `parser_segments` function. It divides each MIDI file into a specified number of segments and calculates metrics for each segment.

- **`num_segments`**: (Optional) Number of segments to divide each MIDI file into for analysis. Defaults to 10 if not specified.

### Available Metrics

When specifying metrics in the `metrics` parameter, use the following keywords to select specific data columns:

- **`'Total_Counts'`**: The total number of notes in each MIDI file.
- **`'UE_Counts'`**: Count of upper extremity (UE) notes, such as certain drum hits.
- **`'LF_Counts'`**: Count of left foot (LF) notes.
- **`'RF_Counts'`**: Count of right foot (RF) notes.
- **`'Avg_Velocity'`**: Average velocity of all notes, including a measure of the standard deviation (e.g., `45.37 (14.25)`).
- **`'UE_Velocity'`**: Average velocity of UE notes, with standard deviation.
- **`'LF_Velocity'`**: Average velocity of LF notes, with standard deviation.
- **`'RF_Velocity'`**: Average velocity of RF notes, with standard deviation.
- **`'Avg_Async'`**: Average asynchrony for all notes, showing the mean and standard deviation.
- **`'UE_Async'`**: Average asynchrony for UE notes, with standard deviation.
- **`'LF_Async'`**: Average asynchrony for LF notes, with standard deviation.
- **`'RF_Async'`**: Average asynchrony for RF notes, with standard deviation.

> **Note**: When selecting a subset of metrics, include `'Name'` in your `metrics` list if you want the session identifiers (e.g., "Patient 1 session 2") to appear in the DataFrame output.

### Example

The following example demonstrates how to parse MIDI files in a specified directory, select specific metrics, and save the output to an Excel file.

```python
import midipy
# Import the parser function from midipy
from midipy.midi_parser import parser

# Define the source directory and parse the MIDI files
df = parser(
    source="./P1",  # Replace with your directory containing MIDI files
    metrics=['Total_Counts', 'Avg_Velocity'],  # Specify the metrics you want
    output_format='excel',  # Choose 'excel' or 'csv' for output format
    save_path='MyMIDIOutput'  # Path and filename for the output (without extension)
)

# Display the parsed DataFrame
print(df)
```

### Segment-wise Analysis Example

The following example demonstrates how to perform segment-wise analysis on MIDI files, dividing each file into 10 segments.

```python
import midipy
# Import the parser_segments function from midipy
from midipy.midi_parser import parser_segments

# Define the source directory and parse the MIDI files segment-wise
def parser_segments(
    source, 
    metrics=['all'], 
    output_format='excel', 
    save_path='SegmentOutput', 
    num_segments=5,
    mean_segments=False   # <-- If you want averaged over segments 
)

# Display the segment-wise parsed DataFrame
print(df_segments)
```

In this example:
- **Directory**: The directory `./P1` contains the MIDI files to be parsed.
- **Metrics**: All available metrics are selected.
- **Output Format**: The data will be saved as an Excel file.
- **Number of Segments**: Each file is divided into 10 segments, allowing for detailed segment-wise analysis.

### Output Files

```python
# Install midipy (if not already installed)
# pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ midipy==0.1.4

import midipy
from midipy.midi_parser import parser
from midipy.midi_parser import parser_segments

# Example usage of `parser`
df = parser(source="./P1", metrics=['UE_Counts', 'RF_Async', 'UE_Async'], output_format='csv')
print(df)

# Example usage of `parser_segments` for segment-wise analysis
df2 = parser_segments(source="./P1", metrics=['all'], output_format='excel', num_segments=10)
print(df2)
```


- `parser` output: This file will contain the selected metrics for each session (entire MIDI file).
- `parser_segments` output: This file will include metrics for each segment within each session, offering finer-grained analysis.

With `midipy`, you can easily analyze MIDI files and extract meaningful musical features, whether for entire sessions or for specific segments within each file.
