"""
This module provides helpers for parsing, validating, and manipulating NIAGADS
BED/BED-like files.

Note: These will actually work for any file (e.g., VCF)
that is 1) tab-delimited, 2) first two columns are chromosome, position, and
3) has at most one header line (no # prefix assumed)
"""

from niagads.utils.sys import execute_cmd, get_parent_directory


def chromosomes_are_prefixed(file_name: str) -> bool:
    """
    Check if the chromosome column in a tab-delimited file is prefixed with 'chr'.

    Assumes the first column contains chromosome names and inspects the second
    line (first data row) to determine if the value starts with 'chr'.

    Args:
        file_name (str): Path to the file to check.

    Returns:
        bool: True if the chromosome column is prefixed with 'chr', False otherwise.
    """
    return (
        execute_cmd(
            f"awk 'NR==2{{print ($1 ~ /^chr/)}}' {file_name}", shell=True
        ).strip()
        == "1"
    )
    
    
# TODO: debug -> this fails somewhere for large files, causing (when overwrite = True) an empty file
# need to figure out why


def bed_file_sort(file_name: str, header: bool, overwrite: bool = False):
    """
    Sort a tab-delimited file by chromosome and position.

    Args:
        file_name (str): Path to the file to sort.
        header (bool): Whether the file contains a header line.
        overwrite (bool, optional): If True, overwrite the original file with
            the sorted output.
    """
    sorted_file_name = file_name + ".sorted"
    header_clause = "NR==1{print;next} " if header else ""

    working_directory = get_parent_directory(file_name)
    strip_chr = 'sub(/^chr/, "", c); ' if chromosomes_are_prefixed(file_name) else ""

    cmd = (
        "awk '"
        + header_clause
        + "{c=$1; "
        + strip_chr
        + ' if(c=="X")c=23; else if(c=="Y")c=24; else if(c=="M"||c=="MT")c=25;'
        + ' print c "\\t" $0}\' '
        + file_name
        + " | sort -T "
        + working_directory
        + " -k1,1n -k3,3n | cut -f2- > "
        + sorted_file_name
    )

    # Run the command and check for errors
    result = execute_cmd(cmd, shell=True)
    if not result.endswith("0"):
        raise RuntimeError(f"bed_file_sort failed: {cmd}\nOutput: {result}")

    if overwrite:
        execute_cmd("mv " + sorted_file_name + " " + file_name, shell=True)
