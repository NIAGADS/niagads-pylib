RETURNS void AS $$
BEGIN
    CREATE GRAPH IF NOT EXISTS Ontology;

    CREATE VERTEX TYPE IF NOT EXISTS Reference.Ontology.term (
        term_id VARCHAR(32) PRIMARY KEY,       -- e.g. GO:0006915
        term_iri VARCHAR(150),                      -- full uri
        term VARCHAR(512),                     -- the term
        label VARCHAR(512),                    -- a display term for applications
        definition TEXT,                       -- definitions can be long
        synonyms TEXT[],                       -- synonyms can be many / long
        is_deprecated BOOLEAN DEFAULT FALSE,
        is_placeholder BOOLEAN DEFAULT FALSE,  -- placeholder vertex
        run_id INTEGER NOT NULL -- references admin.etltask run_id
    );
    

    CREATE EDGE TYPE IF NOT EXISTS Reference.Ontology.triple (
        predicate VARCHAR(32) NOT NULL,         -- must point to a term_id
        run_id INTEGER NOT NULL -- references admin.etltask run_id
    ) SOURCE term DESTINATION term;

    -- restriction blind node (BNode)
    -- TODO: Instantiate when ETL Plugin adapted to handle restrictions 
    /* CREATE VERTEX TYPE IF NOT EXISTS Reference.Ontology.restriction (
        restriction_id SERIAL PRIMARY KEY,
        run_id INTEGER NOT NULL -- references admin.etltask run_id
    );*/

    -- link to source ontology metadata in Reference.ExternalDatabase
    CREATE VERTEX TYPE IF NOT EXISTS Reference.Ontology.ontology (
        ontology_id INTEGER PRIMARY KEY, -- references reference.externaldatabase 
        run_id INTEGER NOT NULL -- references admin.etltask run_id
    );

    CREATE EDGE TYPE IF NOT EXISTS Reference.Ontology.defined_in (
        run_id INTEGER NOT NULL -- references admin.etltask run_id
    ) SOURCE term DESTINATION ontology;
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

