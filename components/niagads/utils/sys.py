"""i/o and other system (e.g., subprocess) utils"""

import datetime
import gzip
import io
import logging
import os
import subprocess
from enum import auto
from pathlib import Path
from sys import exit, stderr
from typing import IO, Union

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
        cmd = ["mv", file + ".sorted", file]
        execute_cmd(cmd)
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
    sortedFile = generic_file_sort(file, header, overwrite)
    cmd = ["uniq", sortedFile, ">", sortedFile + ".uniq"]
    execute_cmd(cmd)

    if overwrite:
        cmd = ["mv", sortedFile + ".uniq", file]
        execute_cmd(cmd)
        return file
    else:
        return sortedFile + ".uniq"


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
            msg = f"EXECUTING: {" ".join(ascii_safe_cmd)}"
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
            f"Command failed with code {result.returncode}: {result.stderr.strip()}"
        )
    return result.stdout


def backup_file(fileName):
    """create a .bak version of a file"""
    cmd = ["cp", fileName, fileName + ".bak"]
    execute_cmd(cmd, shell=True)


def rename_file(oldFileName, targetFileName, backupExistingTarget=True):
    """
    _summary_

    Args:
        oldFileName (string): original file name
        targetFileName (string): new file name
        backupExistingTarget (bool, optional): if the target file exists, back up before renaming the old file. Defaults to True.
    """
    if backupExistingTarget and verify_path(targetFileName):
        backup_file(targetFileName)

    cmd = ["mv", oldFileName, targetFileName]
    execute_cmd(cmd, shell=True)


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


def create_dir(dirName):
    """
    check if directory exists in the path, if not create
    """
    try:
        os.stat(dirName)
    except OSError:
        os.mkdir(dirName)

    return dirName


def verify_path(fileName, isDir=False):
    """
    verify that a file exists
    if isDir is True, just verifies that the path
    exists
    """
    if isDir:
        return os.path.exists(fileName)
    else:
        return os.path.isfile(fileName)


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
