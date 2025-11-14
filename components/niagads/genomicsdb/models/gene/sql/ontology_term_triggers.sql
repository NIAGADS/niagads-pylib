-- Trigger to sync gene_type classification with ontology graph
-- This will keep the classified_as edge in sync with gene_type changes

CREATE OR REPLACE FUNCTION GENE.sync_gene_type_classification()
RETURNS TRIGGER AS $$
BEGIN
    -- Use the provided ontology sync function, passing the edge type
    PERFORM Reference.ontology_sync_classification('classified_as');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sync_gene_type_classification
AFTER INSERT OR UPDATE OR DELETE ON gene.model
FOR EACH ROW
EXECUTE FUNCTION GENE.sync_gene_type_classification();
