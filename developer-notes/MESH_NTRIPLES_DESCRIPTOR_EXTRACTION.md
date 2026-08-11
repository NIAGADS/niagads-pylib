# MeSH N-Triples Descriptor Extraction

Top-level design notes for using `rdflib` to parse MeSH TopicalDescriptors,
Concepts, Terms, and their relationships into source-shaped records.

The important boundary: the RDF parser should traverse the RDF graph and
preserve the result as MeSH-shaped data. It should not translate directly into
the GenomicsDB `OntologyTerm` schema, but it also should not make consumers
re-traverse RDF to use the result. If downstream code needs the graph to resolve
concepts, terms, labels, or relationship details, the data has been identified
but not really parsed.

Schema translation belongs in an ETL plugin, because the same parsed MeSH record
may be useful for ontology loading, search-index construction, QA reports, graph
analysis, or other source-specific workflows.

This should follow the same parser/plugin split as:

- `components/niagads/rdf_parsers/owl.py`
- `bases/niagads/genomicsdb_etl/plugins/reference/ontology/owl.py`

## Parse the N-Triples file

The MeSH RDF download is N-Triples. Use `rdflib.Graph.parse(..., format="nt")`,
or a shared `NTriplesParser` base class.

```python
from rdflib import Graph

graph = Graph()
graph.parse(mesh_file, format="nt")
```

## Parser responsibility

A `MeSHParser` should expose methods that yield parsed, source-oriented records,
for example:

- `extract_descriptors()`
- `extract_concepts()`
- `extract_terms()`

Those records should use MeSH vocabulary semantics and stable scalar/list
fields, not `OntologyTerm` field names. A downstream plugin can then decide how
to flatten or normalize them.

The parser owns graph traversal. The ETL plugin should receive hydrated records
and transform them. It should not need to call `graph.objects(...)`, resolve term
IRIs, or chase `meshv:preferredConcept` itself.

## Descriptor identity

Identify descriptors from `rdf:type`, not from a `D...` identifier. MeSH
descriptor instances may use concrete descriptor types rather than only the
`meshv:Descriptor` superclass.

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

If the immediate goal is TopicalDescriptors only, start with
`meshv:TopicalDescriptor`. Keep the descriptor type in the emitted record so the
same extraction model can support other descriptor classes later.

## Reasonable intermediate structures

The parser output can be plain dictionaries or small dataclasses/Pydantic models.
The key is that they represent MeSH RDF, not GenomicsDB storage.

Example parsed descriptor record:

```python
{
    "iri": "http://id.nlm.nih.gov/mesh/D000544",
    "identifier": "D000544",
    "descriptor_type": "TopicalDescriptor",
    "label": "Alzheimer Disease",
    "active": True,
    "preferred_concept": {
        "iri": "http://id.nlm.nih.gov/mesh/M000...",
        "identifier": "M000...",
        "label": "Alzheimer Disease",
        "scope_note": "...",
        "preferred_term": {
            "iri": "http://id.nlm.nih.gov/mesh/T...",
            "identifier": "T...",
            "label": "Alzheimer Disease",
            "alt_labels": [],
            "active": True,
        },
        "terms": [
            {
                "iri": "http://id.nlm.nih.gov/mesh/T...",
                "identifier": "T...",
                "label": "Alzheimer Dementia",
                "alt_labels": ["Dementia, Alzheimer"],
                "active": True,
            },
        ],
    },
    "concepts": [
        {
            "iri": "http://id.nlm.nih.gov/mesh/M000...",
            "identifier": "M000...",
            "label": "...",
            "scope_note": "...",
            "preferred_term": {...},
            "terms": [{...}],
            "broader_concepts": [{...}],
            "narrower_concepts": [{...}],
            "related_concepts": [{...}],
        },
    ],
    "tree_numbers": ["C10.228.140.380.100"],
    "broader_descriptors": [
        {
            "iri": "http://id.nlm.nih.gov/mesh/D...",
            "identifier": "D...",
            "label": "...",
        },
    ],
    "allowable_qualifiers": [
        {
            "iri": "http://id.nlm.nih.gov/mesh/Q...",
            "identifier": "Q...",
            "label": "...",
        },
    ],
}
```

Example concept record:

```python
{
    "iri": "http://id.nlm.nih.gov/mesh/M000...",
    "identifier": "M000...",
    "label": "Alzheimer Disease",
    "preferred_term": {
        "iri": "http://id.nlm.nih.gov/mesh/T...",
        "identifier": "T...",
        "label": "Alzheimer Disease",
        "alt_labels": [],
        "active": True,
    },
    "terms": [
        {
            "iri": "http://id.nlm.nih.gov/mesh/T...",
            "identifier": "T...",
            "label": "Alzheimer Dementia",
            "alt_labels": ["Dementia, Alzheimer"],
            "active": True,
        },
    ],
    "scope_note": "...",
    "broader_concepts": [
        {
            "iri": "http://id.nlm.nih.gov/mesh/M...",
            "identifier": "M...",
            "label": "...",
        },
    ],
    "narrower_concepts": [{...}],
    "related_concepts": [{...}],
}
```

Example term record:

```python
{
    "iri": "http://id.nlm.nih.gov/mesh/T...",
    "identifier": "T...",
    "label": "Alzheimer Dementia",
    "alt_labels": ["Dementia, Alzheimer"],
    "active": True,
}
```

Relationship lists can use compact records to avoid recursively embedding the
entire graph forever. A compact relationship record should still include enough
parsed information for consumers to work without RDF traversal: at minimum IRI,
identifier, label, and relationship type when applicable.

## Concepts and synonyms

Do not treat every concept attached to a descriptor as a descriptor synonym. A
MeSH descriptor groups concepts useful for retrieval; those concepts may be
broader, narrower, or related. Strict synonymy applies to terms within a single
concept.

A parser may expose lower-level helpers internally, but public parser output
should already include the terms for a concept. It should not decide which labels
become `OntologyTerm.synonyms`; that choice belongs in the ETL plugin.

For an ontology-term loader, a reasonable transform policy would be:

- canonical term: descriptor `rdfs:label`
- source id: descriptor `meshv:identifier`
- definition: preferred concept `meshv:scopeNote`
- strict synonyms: non-preferred term labels from the preferred concept
- search variants: optional term `meshv:altLabel` values, if the loader wants
  lexical variants in its search surface
- relationships: broader descriptors, tree numbers, allowable qualifiers,
  descriptor-concept links, and concept-concept links should be read from parsed
  relationship fields, not rediscovered from RDF

That policy is intentionally ETL-side, not parser-side.

## ETL responsibility

A MeSH ontology ETL plugin can consume parser records and map them to:

- `OntologyTerm` rows for descriptor-level terms
- ontology graph triples for descriptor and concept relationships
- optional chunk text and embeddings for RAG/search use cases

The plugin should not need the `rdflib.Graph`. It should be able to operate on
the yielded descriptor/concept/term records alone.

The plugin is the right place to know about:

- `OntologyTerm.source_id`
- `OntologyTerm.term_iri`
- `OntologyTerm.entity_type`
- `external_database_id`
- run metadata
- duplicate/update policy
- which synonym or variant labels are appropriate for the target table

## References

- [MeSH RDF descriptors](https://hhs.github.io/meshrdf/descriptors)
- [MeSH RDF concepts](https://hhs.github.io/meshrdf/concepts)
- [MeSH RDF terms](https://hhs.github.io/meshrdf/terms)
