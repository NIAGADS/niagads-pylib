RETURNS void AS $$
BEGIN
    CREATE GRAPH IF NOT EXISTS ontology;

    CREATE VERTEX TYPE IF NOT EXISTS term (
        term_id TEXT PRIMARY KEY,
        label TEXT,
        namespace TEXT,
        definition TEXT,
        synonyms TEXT[],
        is_obsolete BOOLEAN DEFAULT FALSE,
        replaced_by TEXT,
        term_kind TEXT NOT NULL
            CHECK (term_kind IN ('class','property','individual'))
    );

    CREATE EDGE TYPE IF NOT EXISTS triple (
        predicate TEXT NOT NULL
    ) SOURCE term DESTINATION term;

    CREATE VERTEX TYPE IF NOT EXISTS externaldatabase_ref (
        externaldatabase_id INT PRIMARY KEY
    );

    CREATE EDGE TYPE IF NOT EXISTS defined_in ()
    SOURCE term DESTINATION externaldatabase_ref;
END;
$$ LANGUAGE plpgsql
