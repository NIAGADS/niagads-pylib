from collections import OrderedDict
from ..utils.list import qw

# NOTE in Python 3.7+ all dicts are inherently ordered dicts, so this 
# overhead would not be necessary
ANNOTATION_PROPERTIES = OrderedDict({
    'definition': qw('IAO_0000115 definition def'),
    'synonym': qw('IAO_0000118 alternative_term Synonym hasBroadSynonym hasExactSynonym hasNarrowSynonym hasRelatedSynonym OBI_9991119 OBI_9991118'),
    'preferred_term': ['IAO_0000111'],
    'is_obsolete':['ObsoleteClass', 'ObsoleteProperty'],
    'is_deprecated':  ['deprecated'],
    'db_ref':qw('dbref seeAlso hasDbXref'),
    'comment': ['comment']
})

ANNOTATION_PROPERTY_TYPES = list(ANNOTATION_PROPERTIES.keys())

ORDERED_PROPERTY_LABELS = ['id', 'iri', 'term'] + ANNOTATION_PROPERTY_TYPES