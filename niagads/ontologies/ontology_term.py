import logging
from os.path import basename

from . import annotation_property_types, ANNOTATION_PROPERTIES, REGEX_PATTERNS
from ..utils.list import list_to_string
from ..utils.string import is_balanced, regex_extract, regex_replace

class OntologyTerm:
    def __init__(self, iri, debug=False):
        self.logger = logging.getLogger(__name__)
        self.__debug = debug
        
        self.__iri = iri
        self.__id = basename(iri).replace(':', '_')
        self.__term = None
        self.__annotationProperties = {}
        self.__subclass_of = None
        self.__synonyms = None
        self.__dbRefs = None
        self.__includeComments = False # TODO: flag to include comments in output
       
    def include_comments(self, includeComments=True):
        self.__includeComments = includeComments
     
    def debug(self, debug=True):
        self.__debug = debug   
        
    def add_db_ref(self, value):
        value = value.replace(': ', ':')
        if self.__dbRefs is None:
            self.__dbRefs = [value]
        else:
            self.__dbRefs.append(value)
       
            
    def add_synonym(self, value):
        if self.__synonyms is None:
            self.__synonyms = [value]
        else:
            self.__synonyms.append(value)
            
        
    def set_is_a(self, relationships):
        self.__subclass_of = relationships
        
    def get_db_refs(self, asStr=False):
        if self.__dbRefs is None:
            return None      
        return '//'.join(self.__dbRefs) if asStr else self.__dbRefs
        
    def get_synonyms(self, asStr=False):
        if self.__synonyms is None:
            return None   
        return '//'.join(self.__synonyms) if asStr else self.__synonyms
        
    def is_a(self, parse=False, asStr=False):
        if self.__subclass_of is None:
            return None  
        if parse:
            relationships = [parse_subclass_relationship(r) for r in self.__subclass_of]
            return '//'.join([' '.join(r) for r in relationships]) if asStr else relationships
        return '//'.join(self.__subclass_of) if asStr else self.__subclass_of
        
    def get_id(self):
        return self.__id
    
    def get_iri(self):
        return self.__iri
    
    def get_term(self):
        return self.__term
    
    def set_term(self, term):
        self.__term = term
        
    def get_annotation_properties(self):
        return self.__annotationProperties
            
    def in_namespace(self, namespace: str):
        if self.__id.startswith(namespace + '_'):
            return True
        else:
            return False
        
        
    def __str__(self):
        """str() wrapper

        Returns:
            tab delimited string of term and its annotations
        """
        values = [self.__id, self.__iri, self.__term]
        for prop in annotation_property_types():
            annotation = '//'.join(self.__annotationProperties[prop]) \
                if prop in self.__annotationProperties else None
            values.append(annotation)
    
        return list_to_string(values, nullStr='', delim='\t')
    
        
    def set_annotation_property(self, prop, value):
        if prop == 'label':
            self.set_term(value)
        else:
            propType = self.valid_annotation_property(prop, returnType=True)
            
            if propType == 'db_ref': 
                self.add_db_ref(value)
            if propType == 'synonym':
                self.add_synonym(value)
            else:    
                value = [value] # make everything a list
                if propType in self.__annotationProperties:
                    self.__annotationProperties[propType] = self.__annotationProperties[propType] + value
                else:
                    self.__annotationProperties[propType] = value
                
    
    def valid_annotation_property(self, property, returnType=False):
        for annotType, properties in ANNOTATION_PROPERTIES.items():
            if property in properties:
                return annotType if returnType else True
        
        # if can't be mapped:    
        if not returnType:
            return False
        else:
            raise KeyError('Annotation property: ' + property + ' not in reserved types.')


# -- functions for parsing is_a relationships


def __phrase_type(relStr):
    if regex_extract(REGEX_PATTERNS.logic, relStr) is not None:
        return 'LOGIC' # & or |
    if '(' in relStr or ')' in relStr:
        if is_balanced(relStr): # () are balanced
            return 'QUALIFIER'
        else: # it's been split due to nested logic
            return 'BROKEN_QUALIFIER'
    else: # a class
        return 'CLASS'
    

def __parse_qualifier(relStr):
    qualifier = regex_extract(REGEX_PATTERNS.qualifier, relStr)
    phrase = regex_extract(REGEX_PATTERNS.outermost, relStr)
    return qualifier, phrase
    
    
def parse_subclass_relationship(relStr, prefix=None):
    """parses subclass relationships (owlready2 format) and returns an array of elements that can be joined into a phrase
    or further parsed (e.g., to map the IRIs to terms)
    
    Examples:
        obo.CL_0000542 -> ['CL_0000542']
        obo.CL_0000542 & obo.RO_0001000.some(obo.CL_0000542 | obo.BFO_0000050.value(obo.NCBITaxon_9606)) -> ['CL_0000542', '&', 'RO_0001000', 'some', '(', 'CL_0000542', '|', 'BFO_0000050', 'value', '(', 'NCBITaxon_9606', ')', ')']
        obo.RO_0001000.some(obo.CL_0000542 | obo.BFO_0000050.value(obo.NCBITaxon_9606)) -> ['RO_0001000', 'some', '(', 'CL_0000542', '|', 'BFO_0000050', 'value', '(', 'NCBITaxon_9606', ')', ')']
        obo.RO_0001000.some(obo.CL_0000542 | obo.BFO_0000050.value(obo.NCBITaxon_9606)) & obo.CL_0000542 -> ['RO_0001000', 'some', '(', 'CL_0000542', '|', 'BFO_0000050', 'value', '(', 'NCBITaxon_9606', ')', ')']
        obo.BFO_0000050.value(obo.NCBITaxon_9606) -> ['BFO_0000050', 'value', '(', 'NCBITaxon_9606', ')']


    Args:
        relStr (str): the string to be parsed; expects is_a relationship from 'owlready2' package
        prefix (str list, optional): prefix; used for recursion or to add a prefix to the result. Defaults to None.

    Returns:
        _type_: _description_
    """
    # if you set the default value of the translation parameter to [], 
    # it does not garbage collect correctly and subsequent calls to
    # parse_subclass_relationship (e.g., in a loop) will get 
    # concatenated
    # so, we set it to None and change it to [] after the function is
    # called
    result = [] if prefix is None else prefix
    if isinstance(result, str):
        result = [result]

    relationships = relStr.split(' ')
    for index, r in enumerate(relationships):
        phraseType = __phrase_type(r)
        if phraseType == 'LOGIC':
            result.append(r)
            
        elif phraseType == 'CLASS':
            namespace, iri = r.split('.')
            result.append(iri)
            
        elif 'QUALIFIER' in phraseType:
            qualifiedRelationship = ' '.join(relationships[index:]) if phraseType == 'BROKEN_QUALIFIER' else r
            qualifier, newRelStr = __parse_qualifier(qualifiedRelationship)
            namespace, iri, qual = qualifier.split('.')
            result += [iri, qual, '(']
            result = parse_subclass_relationship(newRelStr, result) + [')']
            break

    return result
