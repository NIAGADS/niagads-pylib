import logging
from os.path import basename

from . import ANNOTATION_PROPERTY_TYPES, ANNOTATION_PROPERTIES
from ..utils.list import list_to_string

class OntologyTerm:
    def __init__(self, iri, debug=False):
        self.logger = logging.getLogger(__name__)
        self.__debug = debug
        
        self.__iri = iri
        self.__id = basename(iri).replace(':', '_')
        self.__term = None
        self.__annotation_properties = {}
        self.__parents = []
        self.__includeComments = False
       
    def include_comments(self, includeComments=True):
        self.__includeComments = includeComments
     
    def debug(self, debug=True):
        self.__debug = debug   
        
    def add_parent(self, parentId):
        self.__parents.append(parentId)
        
    def get_parents(self, asStr=False):
        if self.__parents is None:
            return None
        
        return '//'.join(self.__parents) if asStr else self.__parents
        
    def get_id(self):
        return self.__id
    
    def get_iri(self):
        return self.__iri
    
    def get_term(self):
        return self.__term
    
    def set_term(self, term):
        self.__term = term
        
    def get_annotation_properties(self):
        return self.__annotation_properties
        
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
        for prop in ANNOTATION_PROPERTY_TYPES:
            annotation = '//'.join(self.__annotation_properties[prop]) \
                if prop in self.__annotation_properties else None
            values.append(annotation)
    
        values.append(self.get_parents(asStr=True))
        return list_to_string(values, nullStr='', delim='\t')
    

        
    def set_annotation_property(self, prop, value):
        if prop == 'label':
            self.set_term(value)
        else:
            propType = self.valid_annotation_property(prop, returnType=True)
            if propType == 'dbref': 
                value = value.replace(': ', ':')
            value = [value] # make everything a list
            if propType in self.__annotation_properties:
                self.__annotation_properties[propType] = self.__annotation_properties[propType] + value
            else:
                self.__annotation_properties[propType] = value
                
    
    def valid_annotation_property(self, property, returnType=False):
        for annotType, properties in ANNOTATION_PROPERTIES.items():
            if property in properties:
                return annotType if returnType else True
        
        # if can't be mapped:    
        if not returnType:
            return False
        else:
            raise KeyError('Annotation property: ' + property + ' not in reserved types.')
