import logging
import json

from os.path import basename

from . import annotation_property_types, ANNOTATION_PROPERTIES, REGEX_PATTERNS, OBSOLETE_RELATIONSHIPS
from ..utils.list import array_in_string, list_to_string
from ..utils.string import is_balanced, regex_extract

class OntologyTerm:
    def __init__(self, iri, debug=False):
        self.logger = logging.getLogger(__name__)
        self.__debug = debug
        
        self.__iri = iri
        self.__id = basename(iri).replace(':', '_')
        self.__term = None
        self.__annotationProperties = {}
        self.__subclassOf = None
        self.__synonyms = None
        self.__dbRefs = None
        self.__includeComments = False
        self.__propTypes = annotation_property_types()
        
        
    def set_is_obsolete(self):
        self.__annotationProperties['is_obsolete'] = True
        
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
        """takes is_a relationships; finds obsolete flags and removes,
        setting the term to obsolete when required
        
        then assigns the remaning relationships to the term

        Args:
            relationships (str list): list of relationships in str format
        """
        for r in relationships:
            if array_in_string(r, OBSOLETE_RELATIONSHIPS):
                self.set_is_obsolete()
                relationships.remove(r)
        self.__subclassOf = relationships
        
    def get_db_refs(self, asStr=False):
        if self.__dbRefs is None:
            return None      
        return '//'.join(self.__dbRefs) if asStr else self.__dbRefs
        
    def get_synonyms(self, asStr=False):
        if self.__synonyms is None:
            return None   
        return '//'.join(self.__synonyms) if asStr else self.__synonyms
        
    def is_a(self, parse=False, asStr=False):
        if self.__subclassOf is None:
            return None  
        if parse:
            relationships = [parse_subclass_relationship(r) for r in self.__subclassOf]
            return '//'.join([json.dumps(r) for r in relationships]) if asStr else relationships
        return '//'.join(self.__subclassOf) if asStr else self.__subclassOf
        
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
        for prop in self.__propTypes:
            if not self.__includeComments and prop == 'comment':
                continue
            if prop in self.__annotationProperties:
                annotation = True if prop == 'is_obsolete' \
                    else '//'.join(self.__annotationProperties[prop])     
                values.append(annotation)
            else:
                values.append(None)
    
        return list_to_string(values, nullStr='NULL', delim='\t')
    
        
    def set_annotation_property(self, prop, value):
        """set annotation property; incls clean and validating property IRIs

        Args:
            prop (str): field/property to add
            value (str): value to assign to the property
        """
        # some comments & definitions have newlines or tabs in them
        # so clean it up; see https://stackoverflow.com/a/10711166
        value = ' '.join(value.split())
    
        if prop == 'label':
            self.set_term(value)
            
        else:
            propType = self.__get_annotation_type(prop)
            if propType is not None:
                if propType == 'db_ref': 
                    self.add_db_ref(value)
                elif propType == 'synonym':
                    self.add_synonym(value)
                elif propType == 'is_obsolete':
                    self.set_is_obsolete()
                else:
                    value = [value] # make everything a list
                    if propType in self.__annotationProperties:
                        self.__annotationProperties[propType] = self.__annotationProperties[propType] + value
                    else:
                        self.__annotationProperties[propType] = value
                
    
    def __get_annotation_type(self, property):
        """get property mapping for iri (e.g., multiple synonym fields -> synonym property)

        Args:
            property (str): field or property name

        Returns:
            string indicating mapped type (e.g., multiple synonym fields -> synonym property)
        """
        for annotType, properties in ANNOTATION_PROPERTIES.items():
            if property in properties:
                return annotType
        
        return None


# -- functions for parsing is_a relationships


def __phrase_type(relStr):
    if '(' in relStr or ')' in relStr:
        if is_balanced(relStr): # () are balanced
            return 'QUALIFIER'
        else: # it's been split due to nested logic
            return 'BROKEN_QUALIFIER'
    else: # a class
        return 'CLASS'
    

def __parse_qualifier(relStr):
    qualifier = regex_extract(REGEX_PATTERNS.qualifier, relStr)
    namespace, iri, qual = qualifier.split('.')
    phrase = regex_extract(REGEX_PATTERNS.outermost, relStr)
    return '.'.join([iri, qual]), phrase
    
    
def parse_subclass_relationship(relStr, piece="full"):
    """parses subclass relationships (owlready2 format) and returns an array of elements that can be joined into a phrase
    or further parsed (e.g., to map the IRIs to terms)
    
    Examples:
       
    Args:
        relStr (str): the string to be parsed; expects is_a relationship from 'owlready2' package
        piece (str): for debugging purposes; can use to log breakdown
  
    Returns:
        dict representation of the relationship
    """
    relationships = relStr.split(' ')
    
    if len(relationships) == 1:
        relation = relationships[0]
        pType = __phrase_type(relation)
        if pType == 'CLASS':
            namespace, iri = relation.split('.')
            return iri
        elif pType == 'QUALIFIER':
            qualifier, innerRels = __parse_qualifier(relation)
            return { qualifier: parse_subclass_relationship(innerRels, "inner") }
        else:
            raise NotImplementedError("Issue parsing relationship - case not caught: " + relStr)
            
    else:
        if relationships[1] in ['&', '|']:
            # valid a | b or a & b
            if __phrase_type(relationships[0]) != 'BROKEN_QUALIFIER':
                # re- split again on first occurrence of logical operator
                # trim spaces
                operator = relationships[1]
                relationships = [x.strip() for x in relStr.split(operator, 1)] 
                
                # recursively process left & right side of operation
                return { 'AND' if operator == '&' else 'OR': 
                            [parse_subclass_relationship(relationships[0], "left"),
                            parse_subclass_relationship(relationships[1], "right")]
                        }
            
            else: # logical operation is nested, splitting broke the qualifier
                qualifier, innerRels = __parse_qualifier(relStr)
                return {qualifier: parse_subclass_relationship(innerRels, "inner")}
