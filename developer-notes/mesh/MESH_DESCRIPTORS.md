# MeSH topical descriptors

This guide explains the relationships among the main MeSH entities and how topical descriptors are represented in this project.

## Brief Overview

MeSH uses a three-level structure:

```text
Descriptor
    ├── Preferred Concept
    │     ├── preferred Term
    │     └── synonymous Terms
    └── Concept
          ├── preferred Term
          └── synonymous Terms
```

A **descriptor** is a MeSH subject heading. It contains one or more **concepts**, one of which is designated the **preferred concept**.

A **concept** represents a distinct meaning within the descriptor. Each concept contains one or more **terms** that are synonymous expressions of that concept. One of those terms is designated the preferred term.

NLM describes this explicitly as the MeSH **Descriptor → Concept → Term** structure.

## MeSH entities and their relationships

### Topical descriptor

A **topical descriptor** is a MeSH subject heading used to represent a biomedical topic for indexing and retrieval.

Descriptors have persistent identifiers such as `D066331` and corresponding MeSH URIs.

A descriptor may contain a single concept or a group of related concepts. NLM notes that a descriptor is often broader than a single concept and may therefore represent a class of concepts.

### Concept

A **concept** represents a particular meaning within a descriptor.

NLM defines a concept as the common meaning shared by synonymous terms. Concepts have their own persistent `M...` identifiers. Terms that share the same concept are synonymous; concepts grouped under the same descriptor are *not necessarily synonymous* with one another.

Concepts may also carry information such as a **scope note**. Scope notes belong to concepts rather than descriptors because a descriptor can contain multiple concepts with different meanings.

### Preferred concept

When a descriptor contains multiple concepts, one is designated the **preferred concept**.

The preferred concept is the concept selected by MeSH as the primary representation of the descriptor. It may be a broader concept encompassing narrower concepts or one among several distinct concepts.

### Term

A **term** is a word or phrase used to express a concept.

A concept may contain multiple terms. Terms within the same concept are synonymous because they represent the same meaning. Terms generally have their own persistent `T...` identifiers.

### Preferred term

Each concept has a **preferred term**, which is the preferred lexical expression for that concept.

The preferred term names the concept but is still a term, not a separate concept or descriptor. NLM identifies the concept name as the same term designated as the concept's preferred term.

### To Summarize

The MeSH entities should not be treated as interchangeable:

```
Descriptor != Concept != Term
```

* A **descriptor** is the subject-heading entity and may contain multiple concepts.
* A **concept** represents a distinct meaning within that descriptor.
* The **preferred concept** is the descriptor's primary concept.
* A **term** is a lexical expression of a concept.
* A **preferred term** is the preferred lexical expression of that concept.
* Terms belonging to the same concept are synonymous; different concepts within the same descriptor are not necessarily synonyms.

## Representing a descriptor as an `OntologyTerm`

For this project, topical descriptors are the primary MeSH entities loaded as `OntologyTerm` records:

```text
namespace   = MeSH_descriptor
term        = descriptor label
label       = descriptor label
term_iri    = descriptor MeSH URI
source_id   = MESH_<descriptor ID>
entity_type = EntityTypeIRI.CLASS
```

`EntityTypeIRI.CLASS` is a project modeling choice for representing descriptors as ontology-level searchable entities.

The preferred concept's scope note is the most direct explanation of the descriptor's meaning:

```text
OntologyTerm.definition = preferred_concept.scope_note
```

Lexical information associated with the preferred concept and its terms are treated as synonyms:

```text
OntologyTerm.synonyms =
    preferred concept label
    + preferred term label, alternate labels, abbreviation
    + active related-term labels, alternate labels, abbreviations
```

Duplicate synonyms are removed case-insensitively. The descriptor's own label is not duplicated in the final synonym list.

This mapping intentionally simplifies the native MeSH structure for indexing and retrieval.

## Example source descriptor JSON

*Placeholder: insert an example descriptor JSON here.*

```json
{
  "TODO": "Example MeSH topical descriptor JSON will be provided later"
}
```

## Example transformed ontology term

*Placeholder: insert the corresponding transformed **`OntologyTerm`** JSON here.*

```json
{
  "TODO": "Example transformed ontology term JSON will be provided later"
}
```

## Official documentation

* [Introduction to MeSH in XML Format](https://www.nlm.nih.gov/mesh/xmlmesh.html) — NLM's explanation of the Descriptor → Concept → Term model.
* [MeSH XML Data Elements](https://www.nlm.nih.gov/mesh/xml_data_elements.html) — definitions of MeSH XML elements and attributes.
* [MeSH RDF](https://id.nlm.nih.gov/mesh/) — NLM's RDF representation and documentation.
