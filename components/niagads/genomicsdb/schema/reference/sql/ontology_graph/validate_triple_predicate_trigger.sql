-- Trigger to validate ontology edges:
-- Ensures that every triple predicate refers to an existing term_id
-- and that the referenced term has term_category='property'.

CREATE OR REPLACE FUNCTION Reference.ontology_validate_triple_predicate()
RETURNS TRIGGER AS $$
DECLARE
    category TEXT;
BEGIN
    SELECT term_category INTO category FROM reference.ontology.term WHERE term_id = NEW.predicate;

    IF category IS NULL THEN
        RAISE EXCEPTION 'Predicate term % does not exist', NEW.predicate;
    ELSIF category <> 'property' THEN
        RAISE EXCEPTION 'Predicate term % must have term_category=property, found %',
            NEW.predicate, category;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


/*REATE TRIGGER trg_validate_triple_predicate
BEFORE INSERT OR UPDATE ON Reference.Ontology.triple
FOR EACH ROW
EXECUTE FUNCTION Reference.ontology_validate_triple_predicate();
*/
