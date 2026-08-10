# MeSH N-Triples Descriptor Extraction

Notes from discussion about extracting MeSH descriptors with `rdflib` and mapping them to the GenomicsDB `OntologyTerm` schema.

## Parse the N-Triples file

The source data is N-Triples, even though individual records may sometimes be displayed elsewhere as Turtle.

```python
from rdflib import Graph

graph = Graph()
graph.parse(mesh_file, format="nt")
```

## Identify descriptors

Identify descriptors from `rdf:type`, not from a `D...` identifier. MeSH descriptor instances may use concrete descriptor types rather than only the `meshv:Descriptor` superclass.

```python
from rdflib import Namespace, RDF

MESHV = Namespace("http://id.nlm.nih.gov/mesh/vocab#")

DESCRIPTOR_TYPES = {
    MESHV.Descriptor,
    MESHV.TopicalDescriptor,
    MESHV.GeographicalDescriptor,
    MESHV.PublicationType,
    MESHV.CheckTag,
}

descriptors = {
    subject
    for descriptor_type in DESCRIPTOR_TYPES
    for subject in graph.subjects(RDF.type, descriptor_type)
}
```

## `OntologyTerm` field mapping

Target schema: `components/niagads/database/genomicsdb/schema/reference/ontology.py`.

| `OntologyTerm` field | MeSH source |
|---|---|
| `term_iri` | Descriptor subject IRI |
| `source_id` / `curie` | `meshv:identifier` |
| `term` | Descriptor `rdfs:label` |
| `label` | Optional; the descriptor `rdfs:label` already supplies `term` |
| `definition` | `meshv:scopeNote` on the preferred concept |
| `namespace` | Constant MeSH namespace |
| `synonyms` | Non-preferred terms within the preferred concept |
| `is_deprecated` | Derived from `meshv:active` |
| `entity_type` | `EntityTypeIRI.CLASS` for storage in the current schema |

Properties such as `meshv:broaderDescriptor`, `meshv:treeNumber`, `meshv:allowableQualifier`, `meshv:concept`, and `meshv:preferredConcept` are relationships and should remain in the ontology graph rather than being flattened into `OntologyTerm` fields.

## Accurate descriptor synonyms

Not every concept or term attached to a descriptor is a synonym of that descriptor. A descriptor groups concepts useful for retrieval, and those concepts may be broader, narrower, or related.

MeSH states that terms *within a single concept* are strictly synonymous. Therefore, strict descriptor synonyms come from the descriptor's preferred concept:

```text
descriptor -> meshv:preferredConcept -> meshv:term -> term resource
term resource -> rdfs:label -> synonym text
```

The concept's `meshv:preferredTerm` is the canonical descriptor term and should be excluded from the synonym list. A term resource's `meshv:altLabel` represents a lexical permutation or variant; it can be included when useful for search, but is distinct from selecting synonymous terms.

```python
from rdflib import RDFS

def descriptor_synonyms(graph, descriptor):
    preferred_concept = graph.value(descriptor, MESHV.preferredConcept)
    if preferred_concept is None:
        return []

    preferred_term = graph.value(preferred_concept, MESHV.preferredTerm)
    synonyms = set()

    for term_node in graph.objects(preferred_concept, MESHV.term):
        if term_node == preferred_term:
            continue

        for label in graph.objects(term_node, RDFS.label):
            if label.language in (None, "en"):
                synonyms.add(str(label))

    return sorted(synonyms, key=str.casefold)
```

If the data does not repeat `meshv:preferredTerm` objects under the more general `meshv:term` predicate, the exclusion still remains valid; only nodes explicitly reached through `meshv:term` are synonym candidates.

## Minimal descriptor extraction

```python
from niagads.common.reference.ontologies.types import EntityTypeIRI

def extract_descriptor(graph, descriptor):
    identifier = graph.value(descriptor, MESHV.identifier)
    term = graph.value(descriptor, RDFS.label)
    active = graph.value(descriptor, MESHV.active)
    preferred_concept = graph.value(descriptor, MESHV.preferredConcept)

    return {
        "term_iri": str(descriptor),
        "curie": str(identifier),
        "term": str(term),
        "definition": (
            str(graph.value(preferred_concept, MESHV.scopeNote))
            if preferred_concept is not None
            and graph.value(preferred_concept, MESHV.scopeNote) is not None
            else None
        ),
        "namespace": "MESH",
        "synonyms": descriptor_synonyms(graph, descriptor) or None,
        "is_deprecated": active is not None and not bool(active.toPython()),
        "entity_type": str(EntityTypeIRI.CLASS),
    }
```

## References

- [MeSH RDF descriptors](https://hhs.github.io/meshrdf/descriptors)
- [MeSH RDF concepts](https://hhs.github.io/meshrdf/concepts)
- [MeSH RDF terms](https://hhs.github.io/meshrdf/terms)
