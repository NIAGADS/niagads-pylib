""" i/o and other system (e.g., subprocess) utils"""
import os
import gzip
import datetime
import requests
import logging

from sys import stderr, exit
from urllib.parse import urlencode
from subprocess import check_output, CalledProcessError

from .enums import CLASS_PROPERTIES
from .dict import print_dict
from .string import ascii_safe_str
from .exceptions import RestrictedValueError


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
        entity (str or CLASS_PROPERTIES enum value, optional): one of CLASS_PROPERTIES
    """
    if CLASS_PROPERTIES.has_value(property):
        lookup = CLASS_PROPERTIES[property.upper()]
        if lookup == CLASS_PROPERTIES.METHODS:
            # ignore class-level properties (defined outside of init)
            # after https://www.askpython.com/python/examples/find-all-methods-of-class
            methods = [attribute for attribute in dir(instance) if callable(getattr(instance, attribute))]
            return [ m for m in methods if not m.startswith('__') and not m.endswith('__') ]

        if property == CLASS_PROPERTIES.MEMBERS:
            # only works if class is instantiated
            if type(instance) == type: # the class Type itself was passed
                raise ValueError("Can only get members from an instantiated class")
            else:
                return list(vars(instance).keys())
            
    else:
        raise RestrictedValueError("property", property, CLASS_PROPERTIES)


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

