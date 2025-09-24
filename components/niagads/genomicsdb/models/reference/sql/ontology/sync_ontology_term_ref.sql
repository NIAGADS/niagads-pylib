-- Trigger to sync relational rows to ontology:
-- If a row has an ontology_term_id, this creates a classified_as edge
-- from that row (treated as a vertex) to the ontology term.
--
-- Example query (Cypher):
--   MATCH (d:dataset)-[:classified_as]->(t:term {term_id:'GO:0006915'})
--   RETURN d.id, d.name;
--
-- This finds all datasets classified as the ontology term "apoptotic process".

CREATE OR REPLACE FUNCTION sync_classification()
RETURNS TRIGGER AS $$
DECLARE
    edge_type TEXT := TG_ARGV[0];  -- e.g. 'classified_as'
BEGIN
    IF NEW.ontology_term_id IS NOT NULL THEN
        EXECUTE format(
            'INSERT INTO %I (SOURCE, DESTINATION) VALUES ($1, $2)
             ON CONFLICT DO NOTHING',
            edge_type
        ) USING NEW.id, NEW.ontology_term_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
