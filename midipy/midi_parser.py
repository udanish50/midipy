"""
midi_parser.py

This module provides a function to parse multiple MIDI files from a specified directory.
"""

# Import necessary libraries and functions
import os
import re
import numpy as np
import pandas as pd
from .midi_reader import readmidi
from .midi_analysis import midiInfo
import warnings


# Ignore warnings
warnings.filterwarnings("ignore")

def parsemidi(source):
    """
    Parse multiple MIDI files in a specified directory and extract relevant note and timing information.
    If filename does not contain at least two numbers, it will simply use the filename as the "Name" field.
    
    Parameters:
    - source (str): Directory path containing the MIDI files.

    Returns:
    - pd.DataFrame: A DataFrame containing parsed data for each MIDI file.
    """
    # Check if the source directory exists
    if not os.path.isdir(source):
        raise ValueError('The specified directory does not exist.')

    # Get the list of MIDI files
    all_files = [f for f in os.listdir(source) if f.endswith('.mid')]
    num_files = len(all_files)

    if num_files == 0:
        raise ValueError('No MIDI files found in the specified directory.')

    # Initialize lists and arrays to store output data
    sessions = []
    
    # Velocities
    avg_velocity = np.zeros(num_files)
    ue_velocity = np.zeros(num_files)
    lf_velocity = np.zeros(num_files)
    rf_velocity = np.zeros(num_files)
    
    # Velocity standard deviations
    savg_velocity = np.zeros(num_files)
    sue_velocity = np.zeros(num_files)
    slf_velocity = np.zeros(num_files)
    srf_velocity = np.zeros(num_files)
    
    # Asynchrony
    avg_asynchrony = np.zeros(num_files)
    ue_asynchrony = np.zeros(num_files)
    lf_asynchrony = np.zeros(num_files)
    rf_asynchrony = np.zeros(num_files)
    
    # Asynchrony standard deviations
    savg_asynchrony = np.zeros(num_files)
    sue_asynchrony = np.zeros(num_files)
    slf_asynchrony = np.zeros(num_files)
    srf_asynchrony = np.zeros(num_files)
    
    # Counts
    total_counts = np.zeros(num_files + 1)
    ue_counts = np.zeros(num_files + 1)
    lf_counts = np.zeros(num_files + 1)
    rf_counts = np.zeros(num_files + 1)
    
    # Lists for table
    avg_velocity_list = []
    ue_velocity_list = []
    lf_velocity_list = []
    rf_velocity_list = []
    
    avg_asynchrony_list = []
    ue_asynchrony_list = []
    lf_asynchrony_list = []
    rf_asynchrony_list = []
    
    for i, filename in enumerate(all_files):
        # Attempt to parse patient and session numbers from filename
        numbers = re.findall(r'\d+', filename)
        if len(numbers) >= 2:
            patient = str(numbers[0])
            session = str(numbers[1])
            sessions.append(f'Patient {patient} session {session}')
        else:
            # Fallback: just use the raw filename as the name
            sessions.append(filename)

        # Load MIDI file and extract information
        midi = readmidi(os.path.join(source, filename))
        Notes, _, bpms = midiInfo(midi, 0)
        bpms = bpms[0]
        
        # Convert seconds to milliseconds (as in your original code)
        Notes[:, 4] *= 1000
        Notes[:, 5] *= 1000

        # Extremity Separation
        ue = np.isin(Notes[:, 2], [38, 40, 43, 51, 53, 59])
        lf = Notes[:, 2] == 44
        rf = Notes[:, 2] == 36

        # Note counts
        total_counts[i] = Notes.shape[0]
        ue_counts[i] = np.sum(ue)
        lf_counts[i] = np.sum(lf)
        rf_counts[i] = np.sum(rf)

        # Velocity calculations
        avg_velocity[i] = np.mean(Notes[:, 3])
        ue_velocity[i] = np.mean(Notes[ue, 3])
        lf_velocity[i] = np.mean(Notes[lf, 3])
        rf_velocity[i] = np.mean(Notes[rf, 3])

        # Velocity standard deviations
        savg_velocity[i] = np.std(Notes[:, 3])
        sue_velocity[i] = np.std(Notes[ue, 3])
        slf_velocity[i] = np.std(Notes[lf, 3])
        srf_velocity[i] = np.std(Notes[rf, 3])
        
        # Asynchrony
        min_ioi = bpms / 4
        threshold = min_ioi / 2
        ue_as = []
        lf_as = []
        rf_as = []
        
        for j in range(int(total_counts[i])):
            nn = Notes[j, 2]  # Trigger code for each note
            t1 = Notes[j, 4]  # Timestamp for each note
            intquantize = bpms * round(t1 / bpms)
            asynchrony = t1 - intquantize
            if abs(asynchrony) <= threshold:
                if nn in [38, 40, 43, 51, 53, 59]:
                    ue_as.append(asynchrony)
                elif nn == 44:
                    lf_as.append(asynchrony)
                elif nn == 36:
                    rf_as.append(asynchrony)
        
        # Means and cumulative values
        means = [np.mean(ue_as), np.mean(lf_as), np.mean(rf_as)]
        cumulative = ue_as + lf_as + rf_as
        
        ue_asynchrony[i] = means[0]
        lf_asynchrony[i] = means[1]
        rf_asynchrony[i] = means[2]
        avg_asynchrony[i] = np.mean(cumulative)
        
        # Standard deviations for asynchrony
        savg_asynchrony[i] = np.std(cumulative)
        sue_asynchrony[i] = np.std(ue_as)
        slf_asynchrony[i] = np.std(lf_as)
        srf_asynchrony[i] = np.std(rf_as)
        
        # Store results for table
        avg_velocity_list.append(f'{avg_velocity[i]:.2f} ({savg_velocity[i]:.2f})')
        ue_velocity_list.append(f'{ue_velocity[i]:.2f} ({sue_velocity[i]:.2f})')
        lf_velocity_list.append(f'{lf_velocity[i]:.2f} ({slf_velocity[i]:.2f})')
        rf_velocity_list.append(f'{rf_velocity[i]:.2f} ({srf_velocity[i]:.2f})')
        avg_asynchrony_list.append(f'{avg_asynchrony[i]:.2f} ({savg_asynchrony[i]:.2f})')
        ue_asynchrony_list.append(f'{ue_asynchrony[i]:.2f} ({sue_asynchrony[i]:.2f})')
        lf_asynchrony_list.append(f'{lf_asynchrony[i]:.2f} ({slf_asynchrony[i]:.2f})')
        rf_asynchrony_list.append(f'{rf_asynchrony[i]:.2f} ({srf_asynchrony[i]:.2f})')

    # Populate final table
    sessions.append('TOTALS')
    name_col = sessions
    
    # Cumulative totals
    total_counts[-1] = np.sum(total_counts[:-1])
    ue_counts[-1] = np.sum(ue_counts[:-1])
    lf_counts[-1] = np.sum(lf_counts[:-1])
    rf_counts[-1] = np.sum(rf_counts[:-1])
    avg_velocity_list.append(f'{np.mean(avg_velocity):.2f} ({np.mean(savg_velocity):.2f})')
    ue_velocity_list.append(f'{np.mean(ue_velocity):.2f} ({np.mean(sue_velocity):.2f})')
    lf_velocity_list.append(f'{np.mean(lf_velocity):.2f} ({np.mean(slf_velocity):.2f})')
    rf_velocity_list.append(f'{np.mean(rf_velocity):.2f} ({np.mean(srf_velocity):.2f})')
    avg_asynchrony_list.append(f'{np.mean(avg_asynchrony):.2f} ({np.mean(savg_asynchrony):.2f})')
    ue_asynchrony_list.append(f'{np.mean(ue_asynchrony):.2f} ({np.mean(sue_asynchrony):.2f})')
    lf_asynchrony_list.append(f'{np.mean(lf_asynchrony):.2f} ({np.mean(slf_asynchrony):.2f})')
    rf_asynchrony_list.append(f'{np.mean(rf_asynchrony):.2f} ({np.mean(srf_asynchrony):.2f})')
    
    # Create final DataFrame
    participant_table = pd.DataFrame({
        'Name': name_col,
        'Total_Counts': total_counts,
        'UE_Counts': ue_counts,
        'LF_Counts': lf_counts,
        'RF_Counts': rf_counts,
        'Avg_Velocity': avg_velocity_list,
        'UE_Velocity': ue_velocity_list,
        'LF_Velocity': lf_velocity_list,
        'RF_Velocity': rf_velocity_list,
        'Avg_Async': avg_asynchrony_list,
        'UE_Async': ue_asynchrony_list,
        'LF_Async': lf_asynchrony_list,
        'RF_Async': rf_asynchrony_list
    })
    
    # Save the table to an Excel file
    participant_table.to_excel("Output.xlsx", index=False)

    return participant_table


def parser(source, metrics=['all'], output_format='excel', save_path='Output'):
    """
    Similar parser function but does not throw error if filename format is not standard.
    """
    if not os.path.isdir(source):
        raise ValueError('The specified directory does not exist.')

    all_files = [f for f in os.listdir(source) if f.endswith('.mid')]
    num_files = len(all_files)
    if num_files == 0:
        raise ValueError('No MIDI files found in the specified directory.')

    sessions = []
    avg_velocity, ue_velocity, lf_velocity, rf_velocity = np.zeros(num_files), np.zeros(num_files), np.zeros(num_files), np.zeros(num_files)
    savg_velocity, sue_velocity, slf_velocity, srf_velocity = np.zeros(num_files), np.zeros(num_files), np.zeros(num_files), np.zeros(num_files)
    avg_asynchrony, ue_asynchrony, lf_asynchrony, rf_asynchrony = np.zeros(num_files), np.zeros(num_files), np.zeros(num_files), np.zeros(num_files)
    savg_asynchrony, sue_asynchrony, slf_asynchrony, srf_asynchrony = np.zeros(num_files), np.zeros(num_files), np.zeros(num_files), np.zeros(num_files)
    total_counts, ue_counts, lf_counts, rf_counts = np.zeros(num_files), np.zeros(num_files), np.zeros(num_files), np.zeros(num_files)

    avg_velocity_list, ue_velocity_list, lf_velocity_list, rf_velocity_list = [], [], [], []
    avg_asynchrony_list, ue_asynchrony_list, lf_asynchrony_list, rf_asynchrony_list = [], [], [], []

    for i, filename in enumerate(all_files):
        # Relaxed filename parsing
        numbers = re.findall(r'\d+', filename)
        if len(numbers) >= 2:
            patient, session = str(numbers[0]), str(numbers[1])
            sessions.append(f'Patient {patient} session {session}')
        else:
            # Fallback
            sessions.append(filename)

        midi = readmidi(os.path.join(source, filename))
        Notes, _, bpms = midiInfo(midi, 0)
        bpms = bpms[0]

        # Convert to ms
        Notes[:, 4] *= 1000
        Notes[:, 5] *= 1000

        ue = np.isin(Notes[:, 2], [38, 40, 43, 51, 53, 59])
        lf = Notes[:, 2] == 44
        rf = Notes[:, 2] == 36

        total_counts[i], ue_counts[i], lf_counts[i], rf_counts[i] = (
            Notes.shape[0],
            np.sum(ue),
            np.sum(lf),
            np.sum(rf)
        )
        avg_velocity[i], ue_velocity[i], lf_velocity[i], rf_velocity[i] = (
            np.mean(Notes[:, 3]),
            np.mean(Notes[ue, 3]),
            np.mean(Notes[lf, 3]),
            np.mean(Notes[rf, 3])
        )
        savg_velocity[i], sue_velocity[i], slf_velocity[i], srf_velocity[i] = (
            np.std(Notes[:, 3]),
            np.std(Notes[ue, 3]),
            np.std(Notes[lf, 3]),
            np.std(Notes[rf, 3])
        )

        min_ioi, threshold = bpms / 4, bpms / 8
        ue_as, lf_as, rf_as = [], [], []
        for j in range(int(total_counts[i])):
            nn, t1 = Notes[j, 2], Notes[j, 4]
            intquantize = bpms * round(t1 / bpms)
            asynchrony = t1 - intquantize
            if abs(asynchrony) <= threshold:
                if nn in [38, 40, 43, 51, 53, 59]:
                    ue_as.append(asynchrony)
                elif nn == 44:
                    lf_as.append(asynchrony)
                elif nn == 36:
                    rf_as.append(asynchrony)

        ue_asynchrony[i], lf_asynchrony[i], rf_asynchrony[i] = (
            np.mean(ue_as) if len(ue_as) > 0 else 0,
            np.mean(lf_as) if len(lf_as) > 0 else 0,
            np.mean(rf_as) if len(rf_as) > 0 else 0
        )
        avg_asynchrony[i] = np.mean(ue_as + lf_as + rf_as) if (len(ue_as) + len(lf_as) + len(rf_as)) > 0 else 0
        savg_asynchrony[i], sue_asynchrony[i], slf_asynchrony[i], srf_asynchrony[i] = (
            np.std(ue_as + lf_as + rf_as),
            np.std(ue_as),
            np.std(lf_as),
            np.std(rf_as)
        )

        avg_velocity_list.append(f'{avg_velocity[i]:.2f} ({savg_velocity[i]:.2f})')
        ue_velocity_list.append(f'{ue_velocity[i]:.2f} ({sue_velocity[i]:.2f})')
        lf_velocity_list.append(f'{lf_velocity[i]:.2f} ({slf_velocity[i]:.2f})')
        rf_velocity_list.append(f'{rf_velocity[i]:.2f} ({srf_velocity[i]:.2f})')
        avg_asynchrony_list.append(f'{avg_asynchrony[i]:.2f} ({savg_asynchrony[i]:.2f})')
        ue_asynchrony_list.append(f'{ue_asynchrony[i]:.2f} ({sue_asynchrony[i]:.2f})')
        lf_asynchrony_list.append(f'{lf_asynchrony[i]:.2f} ({slf_asynchrony[i]:.2f})')
        rf_asynchrony_list.append(f'{rf_asynchrony[i]:.2f} ({srf_asynchrony[i]:.2f})')

    # Append TOTALS row
    sessions.append('TOTALS')
    total_counts = np.append(total_counts, np.sum(total_counts))
    ue_counts = np.append(ue_counts, np.sum(ue_counts))
    lf_counts = np.append(lf_counts, np.sum(lf_counts))
    rf_counts = np.append(rf_counts, np.sum(rf_counts))
    avg_velocity_list.append(f'{np.mean(avg_velocity):.2f} ({np.mean(savg_velocity):.2f})')
    ue_velocity_list.append(f'{np.mean(ue_velocity):.2f} ({np.mean(sue_velocity):.2f})')
    lf_velocity_list.append(f'{np.mean(lf_velocity):.2f} ({np.mean(slf_velocity):.2f})')
    rf_velocity_list.append(f'{np.mean(rf_velocity):.2f} ({np.mean(srf_velocity):.2f})')
    avg_asynchrony_list.append(f'{np.mean(avg_asynchrony):.2f} ({np.mean(savg_asynchrony):.2f})')
    ue_asynchrony_list.append(f'{np.mean(ue_asynchrony):.2f} ({np.mean(sue_asynchrony):.2f})')
    lf_asynchrony_list.append(f'{np.mean(lf_asynchrony):.2f} ({np.mean(slf_asynchrony):.2f})')
    rf_asynchrony_list.append(f'{np.mean(rf_asynchrony):.2f} ({np.mean(srf_asynchrony):.2f})')

    participant_table = pd.DataFrame({
        'Name': sessions,
        'Total_Counts': total_counts,
        'UE_Counts': ue_counts,
        'LF_Counts': lf_counts,
        'RF_Counts': rf_counts,
        'Avg_Velocity': avg_velocity_list,
        'UE_Velocity': ue_velocity_list,
        'LF_Velocity': lf_velocity_list,
        'RF_Velocity': rf_velocity_list,
        'Avg_Async': avg_asynchrony_list,
        'UE_Async': ue_asynchrony_list,
        'LF_Async': lf_asynchrony_list,
        'RF_Async': rf_asynchrony_list
    })

    # Filter columns if specific metrics are requested
    if metrics != ['all']:
        if not isinstance(metrics, list):
            raise ValueError('Metrics should be a list of column names, e.g., ["Total_Counts"], or ["all"].')
        try:
            participant_table = participant_table[['Name'] + metrics]
        except KeyError as e:
            raise KeyError(f"Some of the specified metrics {metrics} are not in the DataFrame columns. "
                           f"Available columns: {list(participant_table.columns)}")

    # Save the output
    if output_format == 'csv':
        participant_table.to_csv(f"{save_path}.csv", index=False)
    else:
        participant_table.to_excel(f"{save_path}.xlsx", index=False)

    return participant_table

def parser_segments(
    source, 
    metrics=['all'], 
    output_format='excel', 
    save_path='SegmentOutput', 
    num_segments=5,
    mean_segments=False   # <-- New parameter
):
    """
    Parse multiple MIDI files and compute segment-wise metrics.
    If filename does not contain at least two numbers, it will
    fallback to the plain filename as Name.

    Parameters
    ----------
    source : str
        Directory path containing the MIDI files.
    metrics : list, optional
        Which metrics (columns) to keep in the final output; ['all'] means keep all.
    output_format : {'excel', 'csv'}, optional
        Format to save the final output. Defaults to 'excel'.
    save_path : str, optional
        The base name for the output file. Defaults to 'SegmentOutput'.
    num_segments : int, optional
        Number of segments to divide each file's total duration into.
    mean_segments : bool, optional
        If False (default), returns a row for each file's segments (original behavior).
        If True, returns one row per segment index, averaging all files' metrics.
    """


    if not os.path.isdir(source):
        raise ValueError('The specified directory does not exist.')

    if num_segments <= 0 or not isinstance(num_segments, int):
        raise ValueError('Number of segments must be a positive integer.')

    all_files = [f for f in os.listdir(source) if f.endswith('.mid')]
    num_files = len(all_files)
    if num_files == 0:
        raise ValueError('No MIDI files found in the specified directory.')

    segment_data = []

    for i, filename in enumerate(all_files):
        # Relaxed filename parsing
        numbers = re.findall(r'\d+', filename)
        if len(numbers) >= 2:
            patient, session = str(numbers[0]), str(numbers[1])
            name_prefix = f'Patient {patient} session {session}'
        else:
            name_prefix = filename  # Fallback if format doesn't match

        midi = readmidi(os.path.join(source, filename))
        Notes, _, bpms = midiInfo(midi, 0)
        bpms = bpms[0]

        # Convert times to milliseconds
        Notes[:, 4] *= 1000
        Notes[:, 5] *= 1000

        # Calculate the total duration
        overall_start = Notes[:, 4].min()
        overall_end = Notes[:, 5].max()
        total_duration = overall_end - overall_start

        # Segment size
        segment_duration = total_duration / num_segments

        for seg_index in range(num_segments):
            segment_start = overall_start + seg_index * segment_duration
            segment_end = segment_start + segment_duration

            segment_notes = Notes[
                (Notes[:, 4] >= segment_start) & (Notes[:, 4] < segment_end)
            ]

            segment_ue = np.isin(segment_notes[:, 2], [38, 40, 43, 51, 53, 59])
            segment_lf = (segment_notes[:, 2] == 44)
            segment_rf = (segment_notes[:, 2] == 36)

           # if len(segment_notes) > 0:
           #     avg_vel = np.mean(segment_notes[:, 3])
           #     avg_async = np.mean(segment_notes[:, 5] - segment_notes[:, 4])
           # else:
           #     avg_vel = 0
           #     avg_async = 0

           # Compute average velocity
            if len(segment_notes) > 0:
                avg_vel = np.mean(segment_notes[:, 3])
            else:
                avg_vel = 0

            # Compute asynchronies just as in parsemidi()
            min_ioi   = bpms / 4
            threshold = min_ioi / 2

            async_values   = []
            ue_async_vals  = []
            lf_async_vals  = []
            rf_async_vals  = []

            for note in segment_notes:
                nn = note[2]
                t1 = note[4]
                intquantize = bpms * round(t1 / bpms)
                asynchrony   = t1 - intquantize
                if abs(asynchrony) <= threshold:
                    async_values.append(asynchrony)
                    if   nn in [38,40,43,51,53,59]: ue_async_vals.append(asynchrony)
                    elif nn == 44:                  lf_async_vals.append(asynchrony)
                    elif nn == 36:                  rf_async_vals.append(asynchrony)

            avg_async      = np.mean(async_values)  if async_values  else 0
            ue_async_mean  = np.mean(ue_async_vals) if ue_async_vals  else 0
            lf_async_mean  = np.mean(lf_async_vals) if lf_async_vals  else 0
            rf_async_mean  = np.mean(rf_async_vals) if rf_async_vals  else 0

            segment_data.append({
                'Name': f'{name_prefix} Segment {seg_index + 1}',
                'Total_Counts': len(segment_notes),
                'UE_Counts': np.sum(segment_ue),
                'LF_Counts': np.sum(segment_lf),
                'RF_Counts': np.sum(segment_rf),
                'Avg_Velocity': avg_vel,
                'UE_Velocity': np.mean(segment_notes[segment_ue, 3]) if np.sum(segment_ue) > 0 else 0,
                'LF_Velocity': np.mean(segment_notes[segment_lf, 3]) if np.sum(segment_lf) > 0 else 0,
                'RF_Velocity': np.mean(segment_notes[segment_rf, 3]) if np.sum(segment_rf) > 0 else 0,
                #'Avg_Async': avg_async,
                #'UE_Async': (np.mean(segment_notes[segment_ue, 5] - segment_notes[segment_ue, 4])
                #             if np.sum(segment_ue) > 0 else 0),
                #'LF_Async': (np.mean(segment_notes[segment_lf, 5] - segment_notes[segment_lf, 4])
                #             if np.sum(segment_lf) > 0 else 0),
                #'RF_Async': (np.mean(segment_notes[segment_rf, 5] - segment_notes[segment_rf, 4])
                #             if np.sum(segment_rf) > 0 else 0),
                'Avg_Async': avg_async,
                'UE_Async': ue_async_mean,
                'LF_Async': lf_async_mean,
                'RF_Async': rf_async_mean,
            })

    # Create DataFrame for segment-wise metrics
    segment_df = pd.DataFrame(segment_data)

    # ----------------------------------------------------------
    # A) If mean_segments=True, average each segment across files
    # ----------------------------------------------------------
    if mean_segments:
        # 1) Extract segment number from Name (assuming "Segment X")
        seg_num_series = segment_df['Name'].str.extract(r'Segment\s+(\d+)')[0]
        seg_num_series = seg_num_series.astype(int, errors='ignore')
        
        # 2) In case "Segment_Number" already exists, drop it to avoid the pandas error
        if 'Segment_Number' in segment_df.columns:
            segment_df.drop(columns=['Segment_Number'], inplace=True)

        segment_df['Segment_Number'] = seg_num_series

        # 4) Identify numeric columns (e.g., velocities, counts)
        numeric_cols = segment_df.select_dtypes(include=[np.number]).columns

        # 5) Group by Segment_Number and compute the mean of numeric columns
        #    Using as_index=False so we don't run into duplicate column issues
        df_agg = segment_df.groupby('Segment_Number', as_index=False)[numeric_cols].mean()

        # 6) Rebuild a Name that says "Segment X" for the aggregated row
        df_agg['Name'] = 'Segment ' + df_agg['Segment_Number'].astype(str)
        
        # 7) Move 'Name' to the front if desired (minimal changes though)
        #    We'll just place it left-most, then keep the rest as is
        col_order = ['Name', 'Segment_Number'] + [col for col in df_agg.columns 
                                                  if col not in ['Name', 'Segment_Number']]
        df_agg = df_agg[col_order]

        # 8) Overwrite the main DataFrame with the aggregated data
        segment_df = df_agg

    # ------------------------------------------------------------
    # B) Filter columns if specific metrics are requested
    # ------------------------------------------------------------
    if metrics != ['all']:
        if not isinstance(metrics, list):
            raise ValueError('Metrics should be a list of column names, e.g., ["Total_Counts"], or ["all"].')
        try:
            # Always include 'Name' in the final output
            keep_cols = ['Name'] + metrics
            segment_df = segment_df[keep_cols]
        except KeyError as e:
            raise KeyError(
                f"Some of the specified metrics {metrics} are not in the DataFrame columns. "
                f"Available columns: {list(segment_df.columns)}"
            )

    # ------------------------------------------------------------
    # C) Save the output
    # ------------------------------------------------------------
    if output_format == 'csv':
        segment_df.to_csv(f"{save_path}.csv", index=False)
    else:
        segment_df.to_excel(f"{save_path}.xlsx", index=False)

    return segment_df
