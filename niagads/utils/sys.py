""" i/o and other system (e.g., subprocess) utils"""
import os
import gzip
import datetime
import requests
import logging

from sys import stderr, exit
from urllib.parse import urlencode
from subprocess import check_output, CalledProcessError

from .dict import print_dict
from .string import ascii_safe_str

def print_args(args, pretty=True):
    ''' print argparse args '''
    return print_dict(vars(args), pretty)


def get_opener(fileName=None, compressed=False, binary=True):
    ''' check if compressed files are expected and return
    appropriate opener for a file'''

    if compressed or (fileName is not None and fileName.endswith('.gz')):
        if binary:
            return gzip.GzipFile
        return gzip.open
    return open


def execute_cmd(cmd, cwd=None, printCmdOnly=False, verbose=True, shell=False):
    '''
    execute a shell command
    cmd = command as array of strings
    cwd = working directory for the command
    printCmdOnly = prints the command w/out executing
    shell = execute in a shell (e.g., necessary for commands like gzip)
    '''
    if verbose or printCmdOnly:
        asciiSafeCmd = [ascii_safe_str(c) for c in cmd]
        warning("EXECUTING: ", ' '.join(asciiSafeCmd), flush=True)
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


# ================================

class ExitOnExceptionHandler(logging.FileHandler):
    """
    logging exception handler that catches ERRORS and CRITICAL
    level logging and exits 
    see https://stackoverflow.com/a/48201163
    """
    def emit(self, record):
        super().emit(record)
        if record.levelno in (logging.ERROR, logging.CRITICAL):
            raise SystemExit(-1)

