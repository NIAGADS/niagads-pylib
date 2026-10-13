CREATE MATERIALIZED VIEW Gene.KnownADGenes AS (
SELECT
    glm.gene_id,
    glm.rank < 3 AS high_confidence,
    ed.database_key AS data_source,
    ae.qualifiers->>'description' AS description,
    ae.annotation_evidence_id
FROM
    Gene.GeneListMembership glm
JOIN Reference.ExternalDatabase ed
    ON ed.external_database_id = glm.external_database_id
JOIN Admin.TableCatalog tc
    ON tc.name = 'genelistmembership'
JOIN Admin.SchemaCatalog sc
    ON sc.schema_id = tc.schema_id
    AND sc.name = 'gene'
JOIN Gene.AnnotationEvidence ae
    ON ae.table_id = tc.table_id
    AND ae.row_id = glm.gene_list_entry_id
    AND ae.external_database_id = glm.external_database_id
WHERE
    ed.database_key = 'ADSP-GVC'
);

CREATE INDEX idx_gene_knownadgenes_gene ON Gene.KnownADGenes(gene_id);
