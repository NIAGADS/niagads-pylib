""" XML Validators (using Relax NG schemas) and Parsers """
from lxml.etree import parse as parseXML, RelaxNG, ParseError
import logging

class XMLParser(object):
    def __init__(self, rngSchemaFileName=None, verbose=False, debug=False):
        self._debug: bool = debug
        self._verbose = verbose
        self.logger = logging.getLogger(__name__)
        self.__validator = self.__load_validator(rngSchemaFileName)
    
    def __load_validator(self, rngSchemaFileName):
        if rngSchemaFileName is None:
            return None
        schemaXML = parseXML(rngSchemaFileName)
        return RelaxNG(schemaXML)
    
    def parse(self, xmlFileName):
        """ if the XML is valid, returns the parsed XML else fails """
        xml = parseXML(xmlFileName)
        if self.__validator is not None:
            isValid = self.__validator.validate(xml) # should automatially log the errors
            if isValid:
                return xml
            else:
                raise ParseError("Invalid XML: %s; see log" % xmlFileName)
        

