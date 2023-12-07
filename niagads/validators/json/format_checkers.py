from jsonschema import FormatChecker
# see https://lat.sk/2017/03/custom-json-schema-type-validator-format-python/
FORMAT_CHECKER = FormatChecker()

@FORMAT_CHECKER.checks('even', AssertionError)
def even_number(value):
    assert value % 2 == 0
    return True

@FORMAT_CHECKER.checks('pubmed_id', AssertionError)
# handle both numeric and string check
def pubmed_id(value):

        if isinstance(value, int):
            
        assert value % 2 == 0
        return True
