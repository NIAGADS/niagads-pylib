RETURNS void AS $$
BEGIN
    CREATE GRAPH IF NOT EXISTS Ontology;

    CREATE VERTEX TYPE IF NOT EXISTS Reference.Ontology.term (
        term_id VARCHAR(32) PRIMARY KEY,       -- e.g. GO:0006915
        uri VARCHAR(150),                      -- full uri
        term VARCHAR(512),                     -- the term
        label VARCHAR(512),                    -- a display term for applications
        definition TEXT,                       -- definitions can be long
        synonyms TEXT[],                       -- synonyms can be many / long
        is_obsolete BOOLEAN DEFAULT FALSE,
        replaced_by VARCHAR(32),
        term_category VARCHAR(16) NOT NULL
            CHECK (term_category IN ('class','property','individual'))
    );

    CREATE EDGE TYPE IF NOT EXISTS Reference.Ontology.triple (
        predicate VARCHAR(32) NOT NULL         -- must point to a term_id
    ) SOURCE term DESTINATION term;

    CREATE VERTEX TYPE IF NOT EXISTS Reference.Ontology.externaldatabase_ref (
        externaldatabase_id INT PRIMARY KEY
    );

    CREATE EDGE TYPE IF NOT EXISTS Reference.Ontology.defined_in ()
    SOURCE term DESTINATION externaldatabase_ref;
END;
$$ LANGUAGE plpgsql;


