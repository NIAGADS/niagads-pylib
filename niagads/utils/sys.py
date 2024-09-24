""" i/o and other system (e.g., subprocess) utils"""
import os
import gzip
import datetime
import requests
import logging

from typing import IO
from sys import stderr, exit
from urllib.parse import urlencode
from subprocess import check_output, CalledProcessError

from .enums import ClassProperties
from .dict import print_dict
from .string import ascii_safe_str
from .exceptions import RestrictedValueError

LOGGER = logging.getLogger(__name__)

def file_chunker(buffer: IO, chunkSize:int):
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


        
def file_line_count(fileName: str, eol: str='\n', header=False) -> int:
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
            
    with open(fileName, 'rb') as fh:
        generator = __count_generator(fh.raw.read)
        # count each eol
        count = sum(buffer.count(bytes(eol, encoding='utf-8')) for buffer in generator)
        return count if header else count + 1


def is_xlsx(fileName: str) -> bool:
    """ 
    tests if a file is an EXCEL (xlsx) file 
    from : https://stackoverflow.com/a/60494584
    """
    with open(fileName, 'rb') as f:         
        first_four_bytes = f.read()[:4]     
        return first_four_bytes == b'PK\x03\x04' 


def generic_file_sort(file: str, header=True, overwrite=True):
    """ sorts file; returns sorted file name """
    if not header:
        cmd = ["sort", file, ">", file + ".sorted"]
    else:
        cmd = ["(", "head", "-n", 2, file, "&&", "tail", "-n", "+3", file, "|", "sort", ")", ">", file + ".sorted"]
        
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
    ''' return numbr items in a generator '''
    return len(list(generator))


def get_class_properties(instance, property):
    """given a class instance (or class Type itself), prints properties 
    (methods [or non-dunder methods (__methodName__)], members, or everything)
    useful when using a class important from a poorly documented package
    
    Args:
        instance (instantiated class object): class to investigate; can also pass the class itself
        entity (str or ClassProperties enum value, optional): one of ClassProperties
    """
    if ClassProperties.has_value(property):
        lookup = ClassProperties[property.upper()]
        if lookup == ClassProperties.METHODS:
            # ignore class-level properties (defined outside of init)
            # after https://www.askpython.com/python/examples/find-all-methods-of-class
            methods = [attribute for attribute in dir(instance) if callable(getattr(instance, attribute))]
            return [ m for m in methods if not m.startswith('__') and not m.endswith('__') ]

        if property == ClassProperties.MEMBERS:
            # only works if class is instantiated
            if type(instance) == type: # the class Type itself was passed
                raise ValueError("Can only get members from an instantiated class")
            else:
                return list(vars(instance).keys())
            
    else:
        raise RestrictedValueError("property", property, ClassProperties)


def print_args(args, pretty=True):
    ''' print argparse args '''
    return print_dict(vars(args), pretty)


def get_opener(fileName=None, compressed=False, binary=False):
    ''' check if compressed files are expected and return
    appropriate opener for a file'''

    if compressed or (fileName is not None and fileName.endswith('gz')):
        if binary or (fileName is not None and is_binary_file(fileName)):
            return gzip.GzipFile
        return gzip.open
    return open


def is_binary_file(fileName):
    """
    tests if the file is binary
    adapted from https://stackoverflow.com/a/7392391

    Args:
        fileName (string): file name (full path)
    """
    textchars = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)) - {0x7f})
    is_binary_string = lambda bytes: bool(bytes.translate(None, textchars))
    return is_binary_string(open(fileName, 'rb').read(1024))


def execute_cmd(cmd, cwd=None, printCmdOnly=False, verbose=True, shell=False):
    '''
    execute a shell command
    cmd = command as array of strings
    cwd = working directory for the command
    printCmdOnly = prints the command w/out executing
    shell = execute in a shell (e.g., necessary for commands like gzip)
    '''
    if verbose or printCmdOnly:
        if not isinstance(cmd, str):
            asciiSafeCmd = [ascii_safe_str(c) for c in cmd]
            cmd = ' '.join(asciiSafeCmd)
        warning("EXECUTING: " + cmd)
        if printCmdOnly: return
    try:
        if shell:
            output = check_output(cmd, cwd=cwd, shell=True)
        else:
            output = check_output(cmd, cwd=cwd)
        warning(output)
    except CalledProcessError as e:
        die(e)


def gzip_file(filename, removeOriginal):
    '''
    gzip a file
    '''
    with open(filename) as f_in, gzip.open(filename + '.gz', 'wb') as f_out:
        f_out.writelines(f_in)
    if removeOriginal:
        os.remove(filename)
        
        
def warning(*objs, **kwargs):
    '''
    print log messages to stderr
    '''
    fh = stderr
    flush = False
    if kwargs:
        if 'file' in kwargs: fh = kwargs['file']
        if 'flush' in kwargs: flush = kwargs['flush']

    print('[' + str(datetime.datetime.now()) + ']\t', *objs, file=fh)
    if flush:
        fh.flush()


def create_dir(dirName):
    '''
    check if directory exists in the path, if not create
    '''
    try:
        os.stat(dirName)
    except OSError:
        os.mkdir(dirName)

    return dirName


def verify_path(fileName, isDir=False):
    '''
    verify that a file exists
    if isDir is True, just verifies that the path
    exists
    '''
    if isDir:
        return os.path.exists(fileName)
    else:
        return os.path.isfile(fileName)
        

def die(message):
    '''
    mimics Perl's die function
    '''
    warning(message)
    exit(1)


def make_request(requestUrl, params, returnSuccess=True):
    """
    make request and catch errors; return flag indicating 
    if successful even in case of error if returnSuccess == True
    
    Args:
        requestUrl (string): url + endpoint
        params (obj): {key:value} for parameters
        returnSuccess (bool, optional): return success flag even in case of error. Defaults to False.

    Returns:
        None or flag indicating success
    """

    ''' make a request and catch errors 
        return True if call is successful and returnSuccess=True
    '''
    requestUrl += "?" + urlencode(params)
    try:
        response = requests.get(requestUrl)
        response.raise_for_status()      
        if returnSuccess:
            return True       
        return response.json()
    except Exception as err:
        if returnSuccess:
            return False
        return {"message": "ERROR: " + err.args[0]}

# ------------------------------------------------------------------------------------------------------------
class FakeSecHead(object):
    '''
    puts a fake section into a properties file file so that ConfigParser can
    be used to retrieve info / necessary for gus.config (GenomicsDB admin config) files

    workaround for the INI-style headings required by ConfigParser
    see https://stackoverflow.com/questions/2819696/parsing-properties-file-in-python
    
    Required for Python versions < 3 only; for 3+ see db.postgres.postgres_dbi.load_database_config for solution
    '''
    def __init__(self, fp):
        self.fp = fp
        self.sechead = '[section]\n'

    def readline(self):
        if self.sechead:
            try: 
                return self.sechead
            finally: 
                self.sechead = None
        else: 
            return self.fp.readline()