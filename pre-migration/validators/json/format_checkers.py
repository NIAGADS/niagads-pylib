''' Format Checkers are validators that assert 
that the value corresponds to an expected format 
built-in to Draft 7 are the following: https://json-schema.org/draft-07/json-schema-release-notes#formats

below are additional format checkers required by NIAGADS projects

# see https://lat.sk/2017/03/custom-json-schema-type-validator-format-python/
for more information
'''

from jsonschema import FormatChecker
from ...utils.string import matches
from ...utils import RegularExpressions as RE, RegexFlag

JSONSchemaFormatChecker = FormatChecker()

@JSONSchemaFormatChecker.checks('pubmed_id', AssertionError)
def pubmed_id(value):
    """
    expects PMID:34650042 or 34650042 (8 digit number)
    """
    if value is None: 
        return True
    
    assert matches(RE.PUBMED_ID, str(value))
    return True

@JSONSchemaFormatChecker.checks('doi', AssertionError)
def doi(value: str):
    """
    expects DOI or url that contains DOI, e.g., 10.1038/s41467-021-26271-2
    """
    if value is None:
        return True
    
    assert matches(RE.DOI, str(value), flags=RegexFlag.IGNORECASE)
    return True


@JSONSchemaFormatChecker.checks('md5sum', AssertionError)
def md5sum(value: str):
    if value is None:
        return True
    
    assert matches(RE.MD5SUM, str(value))
    return True


@JSONSchemaFormatChecker.checks('file_size', AssertionError)
def file_size(value: str):
    """
    expects file size in K,M,G bytes, e.g., 1.1K, 10M, 2.5 G
    """
    if value is None:
        return True
    
    matches(RE.FILE_SIZE, str(value), flags=RegexFlag.IGNORECASE)
    return True


@JSONSchemaFormatChecker.checks('info_string', AssertionError)
def info_string(value: str):
    """
    expects string of key=value pairs delimited by semi-colons
    """
    if value is None:
        return True
    
    pairs = str(value).split(';')
    for p in pairs:
        assert matches(RE.KEY_VALUE_PAIR, p)
    return True

