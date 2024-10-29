"""
midi_analysis.py

This module provides functions to analyze MIDI data, including:
- Extracting detailed information from MIDI tracks.
- Calculating tempo changes across tracks.
"""

# Import necessary libraries and functions
import numpy as np
from .midi_utils import decode_var_length

def midiInfo(midi, outputFormat=1, tracklist=None, verbose=0):
    """
    Extract detailed information from a MIDI structure, such as note timings and velocities.

    Parameters:
    - midi (dict): The parsed MIDI data structure.
    - outputFormat (int): Output format option (default is 1).
    - tracklist (list of int, optional): List of track numbers to analyze; defaults to all tracks.
    - verbose (int): Verbosity level for debugging (default is 0).

    Returns:
    - tuple: A tuple containing Notes (array), endtime (float or list), and tempo (list).
    """
    if tracklist is None:
        tracklist = list(range(len(midi['track'])))

    current_tempo = 500000  # Default tempo in microseconds per quarter note
    tempos, tempos_time = getTempoChanges(midi)

    # Default tempo settings if no tempo changes are detected
    if len(tempos) == 0:
        tempos = [current_tempo]
        tempos_time = [0]

    tempo = [t / 1000 for t in tempos]
    endtime = []  # Initialize endtime as an empty list
    Notes = np.zeros((0, 8))

    for tracknum in tracklist:
        cumtime = 0
        seconds = 0

        for msgNum, currMsg in enumerate(midi['track'][tracknum]['messages']):
            midimeta = currMsg['midimeta']
            deltatime = currMsg['deltatime']
            data = currMsg['data']
            msg_type = currMsg['type']
            chan = currMsg['chan']

            # Update cumulative time and seconds
            cumtime += deltatime
            seconds += deltatime * 1e-6 * current_tempo / midi['ticks_per_quarter_note']

            # Adjust current tempo if necessary
            idx = np.where(cumtime >= np.array(tempos_time))[0]
            if len(idx) > 0:
                current_tempo = tempos[idx[-1]]
            elif verbose:
                print('No tempos_time found?')

            # Note ON events
            if midimeta == 1 and msg_type == 144 and data[1] > 0:
                Notes = np.vstack((Notes, [tracknum, chan, data[0], data[1], seconds, 0, msgNum + 1, -1]))
            # Note OFF events
            elif midimeta == 1 and ((msg_type == 144 and data[1] == 0) or msg_type == 128):
                ind = np.where((Notes[:, 0] == tracknum) &
                               (Notes[:, 1] == chan) &
                               (Notes[:, 2] == data[0]) &
                               (Notes[:, 7] == -1))[0]

                if len(ind) == 0:
                    if verbose:
                        print(f'Warning: ending non-open note?')
                else:
                    if len(ind) > 1:
                        ind = ind[0]  # Take the first match
                    Notes[ind, 5] = seconds
                    Notes[ind, 7] = msgNum + 1
            # End of Track event
            elif midimeta == 0 and msg_type == 47:
                if not endtime:
                    endtime = seconds
                elif isinstance(endtime, float):
                    endtime = [endtime]
                endtime.append(seconds)

        # Set the end time for any unfinished notes
        nleft = np.sum(Notes[:, 7] == -1)
        if nleft > 0:
            Notes[Notes[:, 7] == -1, 5] = seconds

    # Sort Notes by start time (column 5)
    Notes = Notes[np.argsort(Notes[:, 4])]

    return Notes, endtime, tempo

def getTempoChanges(midi):
    """
    Identify and extract tempo change events from the MIDI data.

    Parameters:
    - midi (dict): The parsed MIDI data structure.

    Returns:
    - tuple: A tuple containing lists of tempos and corresponding time values.
    """
    tempos = []
    tempos_time = []
    for track in midi['track']:
        cumtime = 0
        for msg in track['messages']:
            cumtime += msg['deltatime']
            if msg['midimeta'] == 0 and msg['type'] == 81:  # Set Tempo event
                tempos_time.append(cumtime)
                d = msg['data']
                tempos.append(d[0] * 16**4 + d[1] * 16**2 + d[2])

    if len(tempos) == 0:
        tempos.append(500000)  # Default tempo in microseconds per quarter note
        tempos_time.append(0)

    return tempos, tempos_time

