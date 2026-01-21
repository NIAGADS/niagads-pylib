RETURNS void AS $$
BEGIN
    CREATE PROPERTY GRAPH IF NOT EXISTS Ontology;
/* TODO: Multi-ontology / multi-version scoping: 
   Uses term_iri as stable identifier; ontology_id on vertices and edges 
   enables multi-ontology coexistence without duplication.
*/

    -- Vertex labels for ontology terms
    CREATE VERTEX LABELS (term, ontology, restriction);

    CREATE EDGE LABELS (
        is_a,                -- rdfs:subClassOf
        part_of,             -- frequently traversed in bio-ontologies
        equivalent_to,       -- owl:equivalentClass (optional but commonly useful)
        triple               -- generic predicate edge: use `predicate` property
    );
    
    -- Ontology term vertex with core properties
    -- Uses term_iri as stable identifier across multiple ontologies/versions
    CREATE (:term {
        ontology_term_id: INT NOT NULL UNIQUE,   -- Integer key, assigned from sequence (see below)
        term_iri: STRING NOT NULL UNIQUE,        -- Full URI (e.g., http://purl.obolibrary.org/obo/GO_0006915)
        term_id: STRING,                         -- CURIE form (e.g., GO:0006915)
        term: STRING,                            -- The term name/label
        label: STRING,                           -- Display-friendly label
        definition: STRING,                      -- Term definition
        synonyms: LIST,                          -- Array of synonym strings
        is_deprecated: BOOLEAN DEFAULT FALSE,
        is_placeholder: BOOLEAN DEFAULT FALSE,
        ontology_id: INTEGER,           -- References reference.externaldatabase; allows multi-ontology scoping
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

    -- Restriction/blank node vertex (for OWL restrictions)
    CREATE (:restriction {
        restriction_id: STRING,
        run_id: INTEGER NOT NULL
    });

    -- Ontology metadata vertex
    CREATE (:ontology {
        ontology_id: INTEGER,          -- References reference.externaldatabase (unique key)
        ontology: STRING,                       -- Ontology name/code
        version: STRING,                        -- Release/version identifier
        run_id: INTEGER NOT NULL                -- References admin.etlrun
    });

    -- NOTE
    -- `defined_in` was intentionally removed as a dedicated edge label.
    -- Model it (and other non-reasoned relationships) as `triple` edges:
    --   (:term)-[:triple {predicate: 'defined_in', ontology_id: ..., run_id: ...}]->(:ontology)
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
-- (SO_0000016, subClassOf, restriction_node)
-- (restriction_node, onProperty, part_of)
-- (restriction_node, someValuesFrom, SO_0001669)

