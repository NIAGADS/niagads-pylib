"""i/o and other system (e.g., subprocess) utils"""

import datetime
import gzip
import io
import logging
import os
import shutil
import subprocess
from enum import auto
from pathlib import Path
from sys import exit, stderr
from typing import IO, Union
from glob import glob

from niagads.enums.core import CaseInsensitiveEnum
from niagads.utils.dict import print_dict
from niagads.utils.string import ascii_safe_str

LOGGER = logging.getLogger(__name__)


class ClassProperties(CaseInsensitiveEnum):
    """enum for functions that extract info about a class -- methods or members?"""

    METHODS = auto()
    MEMBERS = auto()


def file_chunker(buffer: IO, chunkSize: int):
    """
    Read n-line chunks from filehandle. Returns sequence of n lines, or None at EOF.
    from https://stackoverflow.com/a/22610745

    buffer is the file handler; may be of type TextIOWrapper or BufferedReader (binary)

    example usage:

    with open(filename) as fh:
        chunkCounter = 0
        for chunk in file_chunker(fh, 20):
            chunkCounter = chunkCounter + 1
            print("Chunk: " + str(chunkCounter))
            for line in chunk:
                print(line)
    """

    while buffer:
        chunk = [buffer.readline() for _ in range(chunkSize)]

        if not any(chunk):  # detect termination at end-of-file (list of ['', '',...] )
            chunk = None

        yield chunk


def file_line_count(fileName: str, eol: str = "\n", header=False) -> int:
    """
    get file_size as count of number of lines
    if header = True, does not count header line
    adapted from: https://pynative.com/python-count-number-of-lines-in-file/

    Args:
        fileName (str): name of the file
        eol (str): EOL indicator, defaults to newline
        header (bool, optional): file includes a header line

    Returns
        the number of lines in the file
    """

    def __count_generator(reader):
        b = reader(1024 * 1024)
        while b:
            yield b
            b = reader(1024 * 1024)

    with open(fileName, "rb") as fh:
        generator = __count_generator(fh.raw.read)
        # count each eol
        count = sum(buffer.count(bytes(eol, encoding="utf-8")) for buffer in generator)
        return count if header else count + 1


def is_xlsx(fileName: str) -> bool:
    """
    tests if a file is an EXCEL (xlsx) file
    from : https://stackoverflow.com/a/60494584
    """
    with open(fileName, "rb") as f:
        first_four_bytes = f.read()[:4]
        return first_four_bytes == b"PK\x03\x04"


def generic_file_sort(file: str, header=True, overwrite=True):
    """sorts file; returns sorted file name"""
    if not header:
        cmd = ["sort", file, ">", file + ".sorted"]
    else:
        cmd = [
            "(",
            "head",
            "-n",
            2,
            file,
            "&&",
            "tail",
            "-n",
            "+3",
            file,
            "|",
            "sort",
            ")",
            ">",
            file + ".sorted",
        ]

    execute_cmd(cmd)

    if overwrite:
        shutil.move(f"{file}.sorted", file)
        return file
    else:
        return file + ".sorted"


def remove_duplicate_lines(file: str, header=True, overwrite=True):
    """remove duplicate lines from a file

    Args:
        file (str): file name
        header (boolean, optional): file contains header? Defaults to True
        overwrite (boolean, optional): overwrite file? Defaults to True

    Returns:
        cleaned file name
    """
    sorted_file = generic_file_sort(file, header, overwrite)
    uniq_file_name = f"{sorted_file}.uniq"
    cmd = ["uniq", sorted_file, ">", uniq_file_name]
    execute_cmd(cmd)

    if overwrite:
        shutil.move(uniq_file_name, file)
        return file
    else:
        return uniq_file_name


def generator_size(generator):
    """return numbr items in a generator"""
    return len(list(generator))


def get_class_properties(instance, property):
    """given a class instance (or class Type itself), prints properties
    (methods [or non-dunder methods (__methodName__)], members, or everything)
    useful when using a class important from a poorly documented package

    Args:
        instance (instantiated class object): class to investigate; can also pass the class itself
        entity (str or ClassProperties enum value, optional): one of ClassProperties
    """
    from niagads.exceptions.core import RestrictedValueError

    if ClassProperties.has_value(property):
        lookup = ClassProperties[property.upper()]
        if lookup == ClassProperties.METHODS:
            # ignore class-level properties (defined outside of init)
            # after https://www.askpython.com/python/examples/find-all-methods-of-class
            methods = [
                attribute
                for attribute in dir(instance)
                if callable(getattr(instance, attribute))
            ]
            return [
                m for m in methods if not m.startswith("__") and not m.endswith("__")
            ]

        if property == ClassProperties.MEMBERS:
            # only works if class is instantiated
            if type(instance) == type:  # the class Type itself was passed
                raise ValueError("Can only get members from an instantiated class")
            else:
                return list(vars(instance).keys())

    else:
        raise RestrictedValueError("property", property, ClassProperties)


def print_args(args, pretty=True):
    """print argparse args"""
    return print_dict(vars(args), pretty)


def open_file(path: str, binary: bool = False) -> io.IOBase:
    """
    Open a file with support for compressed (.gz) files.

    Args:
        path (str): Path to the file.
        binary (bool): Whether to open the file in binary mode.

    Returns:
        io.IOBase: File object.
    """
    if path.endswith(".gz"):
        mode = "rb" if binary else "rt"
        return gzip.open(path, mode, encoding=None if binary else "utf-8")
    mode = "rb" if binary else "r"
    return open(path, mode, encoding=None if binary else "utf-8")


def is_binary_file(fileName):
    """
    tests if the file is binary
    adapted from https://stackoverflow.com/a/7392391

    Args:
        fileName (string): file name (full path)
    """
    textchars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7F})
    is_binary_string = lambda bytes: bool(bytes.translate(None, textchars))
    return is_binary_string(open(fileName, "rb").read(1024))


def get_parent_directory(file_name: str):
    """
    Return the parent directory of a file as a string.
    If the file is in the current directory, return the current working directory.

    Args:
        file_name (str): The file path for which to get the parent directory.

    Returns:
        str: The parent directory as a string, or the current working directory if the parent is empty.
    """
    parent = str(Path(file_name).parent)
    return parent if parent else os.getcwd()


def execute_cmd(
    cmd: Union[str, list],
    cwd: str = None,
    print_cmd_only: bool = False,
    verbose: bool = False,
    shell: bool = False,
    logger: logging.Logger = None,
):
    """
    Execute a shell command and return its standard output as a string.

    Args:
        cmd (str | list): The command to execute, as a string or list of arguments.
        cwd (str, optional): Working directory for the command.
        print_cmd_only (bool, optional): If True, print the command and do not execute.
        verbose (bool, optional): If True, print/log the command before execution.
        shell (bool, optional): If True, execute the command in a shell.
        logger (logging.Logger, optional): Logger to use for command output (if provided).

    Returns:
        str: The standard output from the command.

    Raises:
        RuntimeError: If the command returns a non-zero exit code or execution fails.
    """
    if verbose or print_cmd_only:
        if not isinstance(cmd, str):
            ascii_safe_cmd = [ascii_safe_str(c) for c in cmd]
            msg = f"EXECUTING: {' '.join(ascii_safe_cmd)}"
        else:
            msg = cmd
        if logger is not None:
            logger.info(msg)
        else:
            print(msg)
        if print_cmd_only:
            return None

    if shell:
        if isinstance(cmd, list):
            cmd = " ".join(cmd)

    result = subprocess.run(cmd, cwd=cwd, shell=shell, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed with code {result.returncode} - \n STDOUT:"
            f"{result.stdout.strip()} \n STDERR: {result.stderr.strip()}"
        )
    return result.stdout.strip()


def backup_file(target_file):
    """create a .bak version of a file"""
    shutil.copy(target_file, f"{target_file}.bak")


def remove_path(target_path: str):
    if verify_path(target_path):
        if os.path.isdir(target_path):
            shutil.rmtree(target_path)
        else:
            os.remove(target_path)


def rename_file(
    source_file, target_file, backup_source: bool = False, overwrite: bool = False
):
    """
    rename a file

    Args:
        source_file (string): original file name
        target_file (string): new file name
        backup_source (bool, optional): back up before renaming the source file.
            Defaults to False.
        overwrite (bool, optional): if the target file exists, overwrite.
            Defaults to False.

    Returns
        bool indicating success
    """
    logger = logging.getLogger(__name__)

    if not verify_path(source_file):
        raise ValueError(
            f"Cannot rename source file {source_file} - file does not exist."
        )

    if os.path.isdir(source_file):
        raise NotImplementedError(
            f"{source_file} is a directory. This utility function is for file operations only."
        )

    target_exists = verify_path(target_file)
    if target_exists:
        if not overwrite:
            logger.warning(
                f"Target file {target_file}.  To overwrite, set `overwrite` to `True`."
            )
            return False
        else:
            logger.warning(f"Target file {target_file}.  Overwriting.")

    if backup_source:
        backup_file(source_file)

    shutil.move(source_file, target_file)


def gzip_file(filename, removeOriginal):
    """
    gzip a file
    """
    with open(filename) as f_in, gzip.open(filename + ".gz", "wb") as f_out:
        f_out.writelines(f_in)
    if removeOriginal:
        os.remove(filename)


def warning(*objs, **kwargs):
    """
    print log messages to stderr
    """
    fh = stderr
    flush = False
    if kwargs:
        if "file" in kwargs:
            fh = kwargs["file"]
        if "flush" in kwargs:
            flush = kwargs["flush"]

    print("[" + str(datetime.datetime.now()) + "]\t", *objs, file=fh)
    if flush:
        fh.flush()


def create_dir(directory_name):
    """
    check if directory exists in the path, if not create
    """
    try:
        os.stat(directory_name)
    except OSError:
        os.mkdir(directory_name)

    return directory_name


def verify_path(target_path):
    """
    verify that a file or directory exists
    """
    if os.path.isdir(target_path):
        return os.path.exists(target_path)
    else:
        return os.path.isfile(target_path)


def get_files_by_pattern(path: str, pattern: str, recursive: bool = False) -> list:
    """
    Get a list of all files in a path that match a given pattern.

    Uses glob pattern matching. Supports wildcards like *, ?, and [seq].

    Args:
        path (str): Directory path to search.
        pattern (str): Glob pattern to match (e.g., '*.txt', '*.csv').
        recursive (bool, optional): If True, recursively search subdirectories.
            Defaults to False.

    Returns:
        list: List of file paths matching the pattern, sorted alphabetically.
    """

    if recursive:
        pattern = f"**/{pattern}"

    full_pattern = os.path.join(path, pattern)
    matches = glob(full_pattern, recursive=recursive)
    return sorted([m for m in matches if os.path.isfile(m)])


def die(message):
    """
    mimics Perl's die function
    """
    warning(message)
    exit(1)


# ------------------------------------------------------------------------------------------------------------
class FakeSecHead(object):
    """
    puts a fake section into a properties file file so that ConfigParser can
    be used to retrieve info / necessary for gus.config (GenomicsDB admin config) files

    workaround for the INI-style headings required by ConfigParser
    see https://stackoverflow.com/questions/2819696/parsing-properties-file-in-python

    Required for Python versions < 3 only; for 3+ see db.postgres.postgres_dbi.load_database_config for solution
    """

    def __init__(self, fp):
        self.fp = fp
        self.sechead = "[section]\n"

    def readline(self):
        if self.sechead:
            try:
                return self.sechead
            finally:
                self.sechead = None
        else:
            return self.fp.readline()
