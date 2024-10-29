"""
midi_reader.py

This module provides functions for reading and parsing MIDI files.
It relies on helper functions from midi_utils.py for handling specific MIDI processing tasks.
"""

# Import necessary functions from midi_utils
from .midi_utils import decode_int, decode_var_length, midi_msg_type, channel_voice_msg_len

def readmidi(filename, rawbytes=False):
    """
    Reads and parses a MIDI file, extracting header and track information.

    Parameters:
    - filename (str): Path to the MIDI file.
    - rawbytes (bool): Whether to include raw byte data in the output dictionary.

    Returns:
    - dict: A dictionary containing parsed MIDI data.
    """
    # Open the file in binary read mode
    with open(filename, 'rb') as f:
        A = f.read()

    # Initialize the MIDI structure to store parsed data
    midi = {}
    if rawbytes:
        midi['rawbytes_all'] = A

    # Ensure the file starts with 'MThd', indicating a valid MIDI header
    if A[:4] != b'MThd':
        raise ValueError('File does not begin with header ID (MThd)')

    # Parse header information
    header_len = decode_int(A[4:8])
    if header_len != 6:
        raise ValueError('Header length != 6 bytes')

    format = decode_int(A[8:10])
    if format not in [0, 1, 2]:
        raise ValueError('Format does not equal 0, 1, or 2')
    midi['format'] = format

    num_tracks = decode_int(A[10:12])
    if format == 0 and num_tracks != 1:
        raise ValueError('File is format 0, but num_tracks != 1')

    time_unit = decode_int(A[12:14])
    if time_unit & 0x8000 == 0:
        midi['ticks_per_quarter_note'] = time_unit
    else:
        raise ValueError('Header: SMPTE time format found - not currently supported')

    if rawbytes:
        midi['rawbytes_header'] = A[:14]

    # Read each track's data
    ctr = 14
    track_rawbytes = []
    midi['track'] = []  # Initialize the 'track' key as a list

    for i in range(num_tracks):
        if A[ctr:ctr+4] != b'MTrk':
            raise ValueError(f'Track {i+1} does not begin with track ID=MTrk')
        ctr += 4

        track_len = decode_int(A[ctr:ctr+4])
        ctr += 4

        track_rawbytes.append(A[(ctr-8):(ctr+track_len)])
        
        track_dict = {}  # Create a new dictionary for each track
        if rawbytes:
            track_dict['rawbytes_header'] = A[ctr-8:ctr]
        
        midi['track'].append(track_dict)  # Append the track dictionary to the list
        
        ctr += track_len

    # Parse each track's messages
    for i in range(num_tracks):
        track = track_rawbytes[i]
        if rawbytes:
            midi['track'][i]['rawbytes'] = track
        
        msgCtr = 0
        ctr = 8  # Skip the first 8 bytes (MTrk and length)
        last_byte = None
        midi['track'][i]['messages'] = []  # Initialize the 'messages' key as a list

        while ctr < len(track):
            currMsg = {'used_running_mode': 0}
            ctr_start_msg = ctr
            deltatime, ctr = decode_var_length(track, ctr)

            if track[ctr] == 255:  # Meta event
                msg_type = track[ctr + 1]
                ctr += 2
                data_len, ctr = decode_var_length(track, ctr)
                thedata = track[ctr:ctr + data_len]
                ctr += data_len
                chan = None
                midimeta = 0
                type = msg_type  # Ensure type is set for meta events
            else:  # MIDI event
                midimeta = 1
                if track[ctr] < 128:  # Running status
                    currMsg['used_running_mode'] = 1
                    if last_byte is None:
                        raise ValueError("Running mode used but no previous MIDI command byte found.")
                    B = last_byte
                    nB = track[ctr]
                else:
                    B = track[ctr]
                    nB = track[ctr + 1]
                    ctr += 1
                    last_byte = B

                Hn = B >> 4
                Ln = B & 0x0F
                msg_type = midi_msg_type(B, nB)

                if msg_type == 'channel_mode':
                    type = (Hn << 4) + (nB - 120 + 1)
                    thedata = track[ctr:ctr + 2]
                    chan = Ln
                    ctr += 2
                elif msg_type == 'channel_voice':
                    type = (Hn << 4)
                    length = channel_voice_msg_len(type)
                    thedata = track[ctr:ctr + length]
                    chan = Ln
                    ctr += length
                elif msg_type == 'sysex':
                    length, ctr = decode_var_length(track, ctr)
                    type = B
                    thedata = track[ctr:ctr + length]
                    chan = None
                    ctr += length
                elif msg_type == 'sys_realtime':
                    type = B
                    thedata = []
                    chan = None
            
            # Update the current message dictionary with parsed data
            currMsg.update({
                'deltatime': deltatime,
                'midimeta': midimeta,
                'type': type,
                'data': thedata,
                'chan': chan
            })

            if rawbytes:
                currMsg['rawbytes'] = track[ctr_start_msg:ctr]

            # Append the current message to the track's message list
            midi['track'][i]['messages'].append(currMsg)
            msgCtr += 1

    return midi
