"""
common tasks that involve regular expressions
plus, wrappers for Python regular expression package re
so there is no need to import re in addition to using these 
utilities
"""
import re

def regex_replace(pattern, replacement, value, **kwargs):
    """
    wrapper for `re.sub`
    
    Args:
        pattern (str): regular expression pattern to match
        replacement (str):string to substitute for pattern
        value (str): original string
        **kwargs (optional): optional keyword arguments expected by `re.sub`:
            `count`: maximum number of patterns to be replaced
            `flags`: (e.g., IGNORECASE) 
                see https://docs.python.org/3/library/re.html#re.RegexFlag; 
                can import from `niagads.utils.RegexFlag`
                Defaults to NOFLAG (0).

    Returns:
        updated string
    """
    return re.sub(pattern, replacement, value, **kwargs)


def regex_extract(pattern, value, firstMatchOnly=True, **kwargs):
    """
    wrapper for `re.search`
    
    Args:
        pattern (str): regular expression pattern to match
        value (str): string to search
        **kwargs (optional): optional keyword arguments expected by `re.search`:
            `flags`: (e.g., IGNORECASE) 
                see https://docs.python.org/3/library/re.html#re.RegexFlag; 
                can import from `niagads.utils.RegexFlag`
                Defaults to NOFLAG (0).

    Returns:
        string containing first match if firstMatchOnly, else list of all pattern matches
    """
    if firstMatchOnly:
        result = re.search(pattern, value, **kwargs) 

        if result is not None:
            try:
                return result.group(1) 
            except:
                return result.group()
        return None
    
    else:
        result = re.findall(pattern, value, **kwargs)
        return None if len(result) == 0 else result


def matches(pattern, value, **kwargs):
    """
    checks if string contains a pattern
    
    Args:
        pattern (str): regular expression pattern to match
        value (str): string to search
        **kwargs (optional): optional keyword arguments expected by `re.search`:
            `flags`: (e.g., IGNORECASE) 
                see https://docs.python.org/3/library/re.html#re.RegexFlag; 
                can import from `niagads.utils.RegexFlag`
                Defaults to NOFLAG (0).

    Returns:
        True if match is found
    """
    result = re.search(pattern, value, **kwargs)
    return result is not None


def regex_split(pattern, value, **kwargs):
    """
    wrapper for `re.split`
    
    Args:
        pattern (str): regular expression pattern to match
        value (str): string to search
        **kwargs (optional): optional keyword arguments expected by `re.split`:
            `maxsplit`: if maxsplit is non-zero than at most, maxsplit splits will be done
            `flags`: (e.g., IGNORECASE) 
                see https://docs.python.org/3/library/re.html#re.RegexFlag; 
                can import from `niagads.utils.RegexFlag`
                Defaults to NOFLAG (0).

    """
    return re.split(pattern, value, **kwargs)
