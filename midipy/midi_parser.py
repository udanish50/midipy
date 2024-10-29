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

def parsemidi(source):
    """
    Parse multiple MIDI files in a specified directory and extract relevant note and timing information.

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
        # Parse patient and session numbers from filename
        numbers = re.findall(r'\d+', filename)
        if len(numbers) < 2:
            raise ValueError(f'Filename {filename} does not contain enough numeric parts to extract patient and session numbers.')
        
        patient = str(numbers[0])
        session = str(numbers[1])
        sessions.append(f'Patient {patient} session {session}')
        
        # Load MIDI file and extract information
        midi = readmidi(os.path.join(source, filename))
        Notes, _, bpms = midiInfo(midi, 0)
        bpms = bpms[0]
        
        # Convert seconds to ticks
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

