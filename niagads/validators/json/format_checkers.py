''' Format Checkers are validators that assert 
that the value corresponds to an expected format 
built-in to Draft 7 are the following: https://json-schema.org/draft-07/json-schema-release-notes#formats

below are additional format checkers required by NIAGADS projects

# see https://lat.sk/2017/03/custom-json-schema-type-validator-format-python/
for more information
'''

from jsonschema import FormatChecker
from ...utils.string import matches
from ...utils import RegularExpressions as RE

JSONSchemaFormatChecker = FormatChecker()

@JSONSchemaFormatChecker.checks('pubmed_id', AssertionError)
def pubmed_id(value):
   assert matches(RE.PUBMED_ID, str(value))
   return True

@JSONSchemaFormatChecker.checks('doi', AssertionError)
def doi(value):
    assert matches(RE.DOI, str(value))
    return True

@JSONSchemaFormatChecker.checks('md5sum', AssertionError)
def md5sum(value):
    assert matches(RE.MD5SUM, str(value))
    return True