-- Trigger to keep ontology provenance in sync:
-- Whenever a new row is inserted into the externaldatabase table,
-- ensure a corresponding vertex is created in externaldatabase_ref.
--
-- Example:
--   INSERT INTO externaldatabase (id, name, version, source_file)
--   VALUES (101, 'Gene Ontology', '2025-09-01', 'go.obo');
--   -- Automatically creates vertex: (externaldatabase_ref { externaldatabase_id: 101 })

CREATE OR REPLACE FUNCTION reference.ontology_insert_externaldatabase_ref()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO reference.ontology.externaldatabase_ref (externaldatabase_id)
    VALUES (NEW.id)
    ON CONFLICT (externaldatabase_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

/*
CREATE TRIGGER trg_insert_externaldatabase_ref
AFTER INSERT ON reference.externaldatabase
FOR EACH ROW
EXECUTE FUNCTION Reference.ontology_insert_externaldatabase_ref();
*/