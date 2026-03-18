"""
Sequence utility functions for nucleotide operations.
"""


def reverse_complement(seq):
    """
    Return the reverse complement of a nucleotide sequence.

    Args:
        seq (str): Input nucleotide sequence (A, C, G, T; case-insensitive).

    Returns:
        str: Reverse complement of the input sequence.
    """
    mapping = str.maketrans("ACGTacgt", "TGCAtgca")
    return seq.translate(mapping)[::-1]
