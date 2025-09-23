-- validate_triple_predicate_trigger.sql
--
-- This PL/pgSQL trigger function validates that the predicate term in a triple
-- exists and is of kind 'property'. It raises an exception if the predicate term
-- does not exist or is not a property, ensuring data integrity for the triple table.
-- The commented trigger example shows how to attach this function to the triple table.

CREATE OR REPLACE FUNCTION validate_triple_predicate()
RETURNS TRIGGER AS $$
DECLARE
    kind TEXT;
BEGIN
    SELECT term_kind INTO kind FROM term WHERE term_id = NEW.predicate;

    IF kind IS NULL THEN
        RAISE EXCEPTION 'Predicate term % does not exist', NEW.predicate;
    ELSIF kind <> 'property' THEN
        RAISE EXCEPTION 'Predicate term % must have term_kind=property, found %',
            NEW.predicate, kind;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

/*REATE TRIGGER trg_validate_triple_predicate
BEFORE INSERT OR UPDATE ON triple
FOR EACH ROW
EXECUTE FUNCTION validate_triple_predicate();
*/
