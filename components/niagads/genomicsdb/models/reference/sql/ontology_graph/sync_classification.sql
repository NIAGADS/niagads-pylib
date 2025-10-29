-- Trigger to sync relational rows to ontology across lifecycle:
--  - INSERT: create a classified_as edge if ontology_term_id is set
--  - UPDATE: update the edge if ontology_term_id changes
--  - DELETE: remove the edge when the row is deleted
--
-- Example query (Cypher):
--   MATCH (d:dataset)-[:classified_as]->(t:term {term_id:'GO:0006915'})
--   RETURN d.id, d.name;

-- for use case see `gene/sql/ontology_term_triggers`

-- Note: edge_types must be passed in fully qualified, on inserts: 
-- INSERT INTO reference.ontology.classified_as (from_vertex, to_vertex) VALUES ('GO:0008150', 'GO:0009987');


CREATE OR REPLACE FUNCTION Reference.ontology_sync_classification()
RETURNS TRIGGER AS $$
DECLARE
    edge_type TEXT := TG_ARGV[0];  -- e.g. 'classified_as'
    term_to_check VARCHAR(32);
BEGIN
    -- Figure out which ontology_term_id to validate
    term_to_check := COALESCE(NEW.ontology_term_id, OLD.ontology_term_id);

    -- Safety check: ensure ontology_term_id points to an existing term
    IF term_to_check IS NOT NULL THEN
        PERFORM 1 FROM reference.ontology.term WHERE term_id = term_to_check;
        IF NOT FOUND THEN
            RAISE EXCEPTION
                'Invalid ontology_term_id: % (must exist in term table)',
                term_to_check;
        END IF;
    END IF;

    -- Handle INSERT
    IF TG_OP = 'INSERT' AND NEW.ontology_term_id IS NOT NULL THEN
        EXECUTE format(
            'INSERT INTO %I (SOURCE, DESTINATION) VALUES ($1, $2)
             ON CONFLICT DO NOTHING',
            edge_type
        ) USING NEW.id, NEW.ontology_term_id;
    END IF;

    -- Handle UPDATE
    IF TG_OP = 'UPDATE' AND OLD.ontology_term_id IS DISTINCT FROM NEW.ontology_term_id THEN
        -- Delete old edge
        IF OLD.ontology_term_id IS NOT NULL THEN
            EXECUTE format(
                'DELETE FROM %I WHERE SOURCE = $1 AND DESTINATION = $2',
                edge_type
            ) USING OLD.id, OLD.ontology_term_id;
        END IF;

        -- Insert new edge
        IF NEW.ontology_term_id IS NOT NULL THEN
            EXECUTE format(
                'INSERT INTO %I (SOURCE, DESTINATION) VALUES ($1, $2)
                 ON CONFLICT DO NOTHING',
                edge_type
            ) USING NEW.id, NEW.ontology_term_id;
        END IF;
    END IF;

    -- Handle DELETE
    IF TG_OP = 'DELETE' AND OLD.ontology_term_id IS NOT NULL THEN
        EXECUTE format(
            'DELETE FROM %I WHERE SOURCE = $1 AND DESTINATION = $2',
            edge_type
        ) USING OLD.id, OLD.ontology_term_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
