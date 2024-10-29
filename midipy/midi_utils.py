"""
midi_utils.py

This module contains utility functions to assist with MIDI file processing, such as
decoding integers from bytes, interpreting variable-length values, and determining MIDI message types.
"""

# Import necessary packages
import numpy as np

def decode_int(bytes_data):
    """
    Decode a list of bytes into an integer.

    Parameters:
    - bytes_data (list of int): The list of bytes to decode.

    Returns:
    - int: The decoded integer value.
    """
    value = 0
    for i in range(len(bytes_data)):
        value += (bytes_data[len(bytes_data) - i - 1] << (8 * i))
    return value

def decode_var_length(bytes_data, ptr):
    """
    Decode a variable-length value from a byte list, commonly used in MIDI files.

    Parameters:
    - bytes_data (list of int): The list of bytes to decode.
    - ptr (int): The initial pointer position in the byte list.

    Returns:
    - tuple: A tuple containing the decoded value and the updated pointer position.
    """
    value = 0
    keepgoing = True
    while keepgoing:
        byte = bytes_data[ptr]
        ptr += 1
        if byte < 128:
            keepgoing = False
        value = (value << 7) + (byte & 0x7F)
    return value, ptr

def midi_msg_type(B, nB):
    """
    Determine the type of a MIDI message based on the status byte.

    Parameters:
    - B (int): The first byte of the message (status byte).
    - nB (int): The second byte of the message.

    Returns:
    - str: A string representing the message type ('channel_mode', 'channel_voice', 'sysex', 'sys_realtime').

    Raises:
    - ValueError: If the message type is invalid.
    """
    Hn = B >> 4  # High nibble (upper 4 bits)
    Ln = B & 0x0F  # Low nibble (lower 4 bits)
    if Hn == 11 and 120 <= nB <= 127:
        return 'channel_mode'
    elif 8 <= Hn <= 14:
        return 'channel_voice'
    elif Hn == 15 and 0 <= Ln <= 7:
        return 'sysex'
    elif Hn == 15 and 8 <= Ln <= 15:
        return 'sys_realtime'
    else:
        raise ValueError('Invalid MIDI message type')

def channel_voice_msg_len(type):
    """
    Return the length of channel voice messages based on the type.

    Parameters:
    - type (int): The MIDI message type.

    Returns:
    - int: The length of the message in bytes.

    Raises:
    - ValueError: If the message type is invalid.
    """
    if type in [128, 144, 160, 176, 224]:
        return 2  # Messages with two data bytes
    elif type in [192, 208]:
        return 1  # Messages with one data byte
    else:
        raise ValueError('Invalid channel voice message type')

