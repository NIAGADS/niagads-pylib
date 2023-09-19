from collections import OrderedDict
from ..utils.list import qw

# NOTE in Python 3.7+ all dicts are inherently ordered dicts, so this 
# overhead would not be necessary
ANNOTATION_PROPERTIES = OrderedDict({
    'definition': qw('IAO_0000115 definition def'),
    'preferred_term': ['IAO_0000111'],
    'is_obsolete':['ObsoleteClass', 'ObsoleteProperty'],
    'is_deprecated':  ['deprecated'],
    'comment': ['comment'],
    'synonym': qw('IAO_0000118 alternative_term Synonym hasBroadSynonym hasExactSynonym hasNarrowSynonym hasRelatedSynonym OBI_9991119 OBI_9991118'),
    'db_ref': qw('dbref seeAlso hasDbXref')
})

def annotation_property_types():
    pTypes = list(ANNOTATION_PROPERTIES.keys())
    pTypes.remove('db_ref')
    pTypes.remove('synonym')
    return pTypes

ORDERED_PROPERTY_LABELS = ['id', 'iri', 'term'] + annotation_property_types()