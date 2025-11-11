RETURNS void AS $$
BEGIN
    CREATE GRAPH IF NOT EXISTS Ontology;

    CREATE VERTEX TYPE IF NOT EXISTS Reference.Ontology.Term (
        term_id VARCHAR(32) PRIMARY KEY,       -- e.g. GO:0006915
        term_iri VARCHAR(150),                      -- full uri
        term VARCHAR(512),                     -- the term
        label VARCHAR(512),                    -- a display term for applications
        definition TEXT,                       -- definitions can be long
        synonyms TEXT[],                       -- synonyms can be many / long
        is_deprecated BOOLEAN DEFAULT FALSE,
        is_placeholder BOOLEAN DEFAULT FALSE,  -- placeholder vertex
        --term_category VARCHAR(16) NOT NULL
        --    CHECK (term_category IN ('CLASS','PROPERTY','INDIVIDUAL'))

    );
    

    -- Generic restriction node
    CREATE VERTEX TYPE IF NOT EXISTS Reference.Ontology.restriction (
        restriction_id SERIAL PRIMARY KEY
    );



    CREATE EDGE TYPE IF NOT EXISTS Reference.Ontology.triple (
        predicate VARCHAR(32) NOT NULL         -- must point to a term_id
    ) SOURCE term DESTINATION term;

    CREATE VERTEX TYPE IF NOT EXISTS Reference.Ontology.externaldatabase_ref (
        externaldatabase_id INT PRIMARY KEY
    );

    -- Edge type for classification relationships (e.g. dataset classified as ontology term)
    CREATE EDGE TYPE IF NOT EXISTS Reference.Ontology.classified_as ()
    SOURCE dataset DESTINATION term;

    CREATE EDGE TYPE IF NOT EXISTS Reference.Ontology.defined_in ()
    SOURCE term DESTINATION externaldatabase_ref;
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

