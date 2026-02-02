-- Apache AGE graph schema initialization for ontology relationships

-- Create the ontology graph using documented function
SELECT ag_catalog.create_graph('ontology_graph');

-- Create vertex labels using documented function
SELECT ag_catalog.create_vlabel('ontology_graph', 'term');
SELECT ag_catalog.create_vlabel('ontology_graph', 'ontology');
SELECT ag_catalog.create_vlabel('ontology_graph', 'restriction');

-- Create edge labels using documented function
SELECT ag_catalog.create_elabel('ontology_graph', 'is_a');
SELECT ag_catalog.create_elabel('ontology_graph', 'part_of');
SELECT ag_catalog.create_elabel('ontology_graph', 'equivalent_to');
SELECT ag_catalog.create_elabel('ontology_graph', 'has_restriction');
SELECT ag_catalog.create_elabel('ontology_graph', 'defined_in');
SELECT ag_catalog.create_elabel('ontology_graph', 'triple');

-- Create unique indexes on unique properties
CREATE UNIQUE INDEX idx_og_ontology_term_id
ON ag_catalog."ontology_graph_term" ((properties->>'ontology_term_id'));

CREATE UNIQUE INDEX idx_og_restriction_id
ON ag_catalog."ontology_graph_restriction" ((properties->>'restriction_id'));

CREATE UNIQUE INDEX idx_og_ontology_id
ON ag_catalog."ontology_graph_ontology" ((properties->>'ontology_id'));

CREATE INDEX idx_og_triple_predicate
ON ag_catalog."ontology_graph_triple" ((properties->>'predicate'));

-- XXX: not sure that this is needed
--CREATE UNIQUE INDEX idx_triple_spo_uniq
--ON ag_catalog."ontology_graph_triple" (start_id, end_id, (properties->>'predicate'), (properties->>'ontology_id'));


-- example Triple
/*
(s)-[:triple {p: <predicate>}]->(o)

-- insert
SELECT * FROM cypher('ontology_graph', $$
  MATCH (s {id: $sid}), (o {id: $oid})
  CREATE (s)-[:triple {predicate: $pred}]->(o)
$$, $${"sid": 1, "oid": 2, "pred": "is_a"}$$);

-- select through
SELECT * FROM cypher('ontology_graph', $$
  MATCH (s)-[r:triple]->(o)
  WHERE r.predicate = $pred
  RETURN s, r, o
$$, $${"pred":"is_a"}$$);
*/

-- Example RESTRICTION usage:
/*
<owl:Class rdf:about="http://purl.obolibrary.org/obo/SO_0000016">
<rdfs:subClassOf rdf:resource="http://purl.obolibrary.org/obo/SO_0001660"/>
<rdfs:subClassOf>
    <owl:Restriction>
        <owl:onProperty rdf:resource="http://purl.obolibrary.org/obo/so#part_of"/>
        <owl:someValuesFrom rdf:resource="http://purl.obolibrary.org/obo/SO_0001669"/>
    </owl:Restriction>
</rdfs:subClassOf>
</owl:Class>
*/

-- Graph representation:
-- (:term {term_iri: SO_0000016})-[:is_a]->(:term {term_iri: SO_0001660})
-- (:term {term_iri: SO_0000016})-[:has_restriction]->(:restriction {restriction_id: '_blank1'})
--
-- Restriction subgraph (defined by its outbound edges):
-- (:restriction {restriction_id: '_blank1'})-[:triple {predicate: 'http://www.w3.org/2002/07/owl#onProperty', ontology_id, run_id}]->(:term {term_iri: so#part_of})
-- (:restriction {restriction_id: '_blank1'})-[:triple {predicate: 'http://www.w3.org/2002/07/owl#someValuesFrom', ontology_id, run_id}]->(:term {term_iri: SO_0001669})
--
-- NOTE: If the restriction uses a named edge type (e.g., part_of), use that instead of triple:
-- (:restriction {restriction_id: '_blank1'})-[:part_of {ontology_id, run_id}]->(:term {target_iri})
--
-- Interpretation: SO_0000016 (BREUR_motif) is a subclass of SO_0001660 and is constrained by
-- a restriction: instances must have at least one part_of relationship to SO_0001669 (RNApol_II_core_promoter).

/*
-- Find all terms with part_of relationships to SO_0001669
-- including through restrictions of any structure

MATCH (target:term {term_iri: 'http://purl.obolibrary.org/obo/SO_0001669'})

-- Direct part_of edges
MATCH (source:term)-[:part_of {ontology_id, run_id}]->(target)

UNION

-- Through restrictions: find restrictions that have ANY outbound edge to this target
MATCH (source:term)-[:has_restriction]->(r:restriction),
(r)-[]->(target)

RETURN DISTINCT source.term_iri, source.term

*/

/*
--POSSIBLE NLP QUERY PATTERN; note that example does not reflect current relational table schema

-- User queries "neurons"
WITH query_embedding AS (
SELECT embedding_vector('neurons') AS vec
),
semantic_matches AS (
-- Find similar terms via vector search
SELECT term_id, term_iri, label, similarity
FROM ontologyterm
ORDER BY embedding <-> query_embedding.vec
LIMIT 10
),
expanded_matches AS (
-- For each match, traverse AGE to find related terms
MATCH (t:term {term_iri: semantic_matches.term_iri})-[:derived_from|:part_of|:equivalent_to*..3]->(related:term)
RETURN semantic_matches.term_iri, related.term_iri, related.label
)
SELECT DISTINCT d.sample_id, d.cell_type
FROM genomic_data d
WHERE d.cell_type_term_id IN (
SELECT term_id FROM semantic_matches
UNION
SELECT term_id FROM ontologyterm WHERE term_iri IN (expanded_matches.term_iri)
);
*/