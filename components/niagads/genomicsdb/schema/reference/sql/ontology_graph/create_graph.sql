RETURNS void AS $$
BEGIN
    CREATE PROPERTY GRAPH IF NOT EXISTS Ontology;

    -- Vertex labels for ontology terms
    CREATE VERTEX LABELS (term, ontology, restriction);

    CREATE EDGE LABELS (
        is_a,                -- rdfs:subClassOf (term to term)
        part_of,             -- frequently traversed in bio-ontologies
        equivalent_to,       -- owl:equivalentClass (optional but commonly useful)
        has_restriction,     -- Links term to its OWL restriction constraints
        defined_in,          -- Links term to the ontology that defines it
        triple               -- generic predicate edge: use `predicate` property
    );
    
    -- Ontology term vertex with core properties
    -- Uses term_iri as stable identifier across multiple ontologies/versions
    -- Deduplicated: single term instance per unique term_iri
    -- Ontology scoping is handled via edges (defined_in, is_a, part_of, equivalent_to, triple)
    CREATE (:term {
        ontology_term_id: INT NOT NULL UNIQUE,   -- Integer key, assigned from sequence (see below)
        term_iri: STRING NOT NULL UNIQUE,        -- Full URI (e.g., http://purl.obolibrary.org/obo/GO_0006915)
        term_id: STRING NOT NULL UNIQUE,         -- CURIE form (e.g., GO:0006915)
        term: STRING NOT NULL,                            -- The term name/label
        label: STRING,                           -- Display-friendly label
        definition: STRING,                      -- Term definition
        synonyms: LIST,                          -- Array of synonym strings
        entity_type: STRING,                     -- entity type (e.g., class, property, individual)
        is_deprecated: BOOLEAN DEFAULT FALSE,
        run_id: INTEGER NOT NULL                 -- References admin.etlrun for versioning
    });

    

    -- Generic triple edge for predicates not covered by typed edge labels
    -- Allows flexible representation while keeping a small number of common relations as typed edges.
    -- Use this for annotation properties (synonym, xref, alt_id, consider, replaced_by, etc.),
    -- and for less frequently traversed object properties.
    CREATE (=triple {
        predicate: STRING NOT NULL,              -- Predicate IRI or code
        ontology_id: INTEGER,           -- Source ontology
        run_id: INTEGER NOT NULL                 -- Version/load snapshot
    })-[]->();

    -- Dedicated relationship edges (include provenance)
    CREATE (=is_a {
        ontology_id: INTEGER,
        run_id: INTEGER NOT NULL
    })-[]->();

    CREATE (=part_of {
        ontology_id: INTEGER,
        run_id: INTEGER NOT NULL
    })-[]->();

    CREATE (=equivalent_to {
        ontology_id: INTEGER,
        run_id: INTEGER NOT NULL
    })-[]->();

    CREATE (=defined_in {
        ontology_id: INTEGER,           -- Source ontology
        run_id: INTEGER NOT NULL
    })-[]->();

    CREATE (=has_restriction {
        ontology_id: INTEGER,           -- Source ontology
        run_id: INTEGER NOT NULL
    })-[]->();

    -- Restriction/blank node vertex (for OWL restrictions)
    -- A restriction is an anonymous blank node that serves as a container for restriction properties.
    -- Each restriction node's definition is the subgraph of outbound triple edges from it.
    -- The restriction itself carries only metadata (ontology scope and version).
    -- Example: a someValuesFrom restriction is defined by its outbound triple edges:
    --   (:restriction)-[:triple {predicate: 'owl:onProperty'}]->(:term {property})
    --   (:restriction)-[:triple {predicate: 'owl:someValuesFrom'}]->(:term {filler})
    CREATE (:restriction {
        restriction_id: STRING NOT NULL UNIQUE,  -- Blank node identifier
        ontology_id: INTEGER,                    -- Source ontology (scopes the restriction)
        run_id: INTEGER NOT NULL                 -- Version/load snapshot
    });

    -- Ontology metadata vertex
    CREATE (:ontology {
        ontology_id: INTEGER,          -- References reference.externaldatabase (unique key)
        ontology: STRING UNIQUE,                       -- Ontology name
        namespace: STRING UNIQUE,               -- ontology namespace or code
        version: STRING,                        -- Release/version identifier
        run_id: INTEGER NOT NULL                -- References admin.etlrun
    });

    -- NOTE on ontology tracking:
    -- Terms are deduplicated by term_iri (UNIQUE constraint on :term vertex).
    -- Use explicit `defined_in` edges to track which ontology defines each term:
    --   (:term)-[:defined_in {ontology_id: ..., run_id: ...}]->(:ontology)
    -- This maintains ontology_id scoping on edges while keeping vertices lean.
END;
$$ LANGUAGE plpgsql;


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