""" i/o and other system (e.g., subprocess) utils"""

import sys
import os
import gzip
import datetime
import requests
import json

from urllib.parse import urlencode
from types import SimpleNamespace
from subprocess import check_output, CalledProcessError

def ascii_safe_str(obj):
    ''' here and not in string_utils to avoid circular imports '''
    try: return str(obj)
    except UnicodeEncodeError:
        return obj.encode('ascii', 'ignore').decode('ascii')
    return ""


def print_dict(dictObj, pretty=True):
    ''' pretty print a dict / JSON object 
    here and not in dict_utils to avoid circular import '''
    if isinstance(dictObj, SimpleNamespace):
        return dictObj.__repr__()
    return json.dumps(dictObj, indent=4, sort_keys=True) if pretty else json.dumps(dictObj)


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
    fh = sys.stderr
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
    sys.exit(1)


def make_request(endpoint, params, returnSuccess=False):
    ''' make a request and catch errors 
        return True if call is successful and returnSuccess=True
    '''
    requestUrl = endpoint + "?" + urlencode(requestParams)
    try:
        response = requests.get(requestUrl)
        response.raise_for_status()      
        if returnSuccess:
            return True       
        return response.json()
    except requests.exceptions.HTTPError as err:
        if returnSuccess:
            return False
        return {"message": "ERROR: " + err.args[0]}
