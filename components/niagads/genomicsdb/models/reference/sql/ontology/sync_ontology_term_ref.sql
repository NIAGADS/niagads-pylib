-- sync_ontology_term_ref.sql
--
-- This PL/pgSQL trigger function synchronizes ontology term references for a given table.
-- It inserts a stub vertex into the reference table and, if an ontology_term_id is present,
-- creates an edge between the source and ontology term. The function is parameterized by
-- the reference table name and edge type, allowing flexible use for different schemas.

CREATE OR REPLACE FUNCTION sync_ontology_term_ref()
RETURNS TRIGGER AS $$
DECLARE
    ref_table TEXT := TG_ARGV[0];  -- e.g. 'dataset_ref'
    edge_type TEXT := TG_ARGV[1];  -- e.g. 'has_type'
BEGIN
    -- insert stub vertex
    EXECUTE format(
        'INSERT INTO %I (dataset_id) VALUES ($1) ON CONFLICT DO NOTHING',
        ref_table
    ) USING NEW.id;

    -- create edge if ontology_term_id present
    IF NEW.ontology_term_id IS NOT NULL THEN
        EXECUTE format(
            'INSERT INTO %I (SOURCE, DESTINATION) VALUES ($1, $2) ON CONFLICT DO NOTHING',
            edge_type
        ) USING NEW.id, NEW.ontology_term_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
