from typing import List
from niagads.api.common.models.annotations.associations import (
    GeneVariantAssociation,
    VariantAssociationSummary,
)
from niagads.api.common.models.records import Entity
from niagads.api.common.models.services.query import QueryDefinition
from niagads.api.genomicsdb.queries.records.associations import (
    GWAS_COMMON_FIELDS,
    GWAS_TRACK_CTE,
    association_trait_FILTERS,
)

GO_ASSOCIATION_CTE = """
    SELECT ga.source_id AS id, 
        json_agg(jsonb_build_object(
            'go_term_id', ot.source_id, 
            'go_term', ot.name, 'evidence', goa.evidence, 
            'ontology', CASE ontology.name
                WHEN 'molecular_function' THEN 'MF'
                WHEN 'cellular_component' THEN 'CC'
                WHEN 'biological_process' THEN 'BP'  
                END)
        ) AS go_annotation
    FROM CBIL.GeneAttributes ga,
    CBIL.GoAssociation goa,
    SREs.OntologyTerm ot,
    SRES.OntologyTerm ontology
    WHERE goa.gene_id = ga.gene_id
    AND go_term_id = ot.ontology_term_id
    AND ot.ancestor_term_id = ontology.ontology_term_id
    GROUP BY id 
"""

PATHWAY_CTE = """
    SELECT ga.source_id AS id, 
        json_agg(jsonb_build_object(
            'pathway', p.name, 
            'pathway_id', p.source_id, 
            'pathway_source', xdbr.id_type)) AS pathway_membership
    FROM CBIL.GeneAttributes ga,
    SREs.Pathway p,
    SREs.PathwayNode pn,
    SRes.ExternalDatabaseRelease xdbr
    WHERE p.pathway_id  = pn.pathway_id
    AND pn.row_id = ga.gene_id
    AND xdbr.external_database_release_id = p.external_database_release_id
    GROUP BY id
"""

GENE_RECORD_QUERY = f"""WITH goa AS ({GO_ASSOCIATION_CTE}),
        pathway AS ({PATHWAY_CTE})
        SELECT source_id AS id, 
        gene_symbol,
        annotation->>'name' AS gene_name,
        to_json(string_to_array(annotation->>'prev_symbol', '|') 
            || string_to_array(annotation->>'alias_symbol', '|')) AS synonyms,
        gene_type,
        jsonb_build_object(
            'chromosome', chromosome, 
            'start', location_start, 
            'end', location_end,
            'strand', CASE WHEN is_reversed THEN '-' ELSE '+' END
        ) AS location,
        CASE WHEN annotation IS NULL THEN NULL
        ELSE annotation->>'location' END AS cytogenic_location,
        annotation AS nomenclature,
        goa.go_annotation,
        pathway.pathway_membership
        FROM CBIL.GeneAttributes ga
        LEFT OUTER JOIN goa ON ga.source_id = goa.id
        LEFT OUTER JOIN pathway on ga.source_id = pathway.id
        WHERE ga.source_id = (SELECT gene_lookup(:id))
    """


GWAS_RESULTS_CTE = f"""
    SELECT 
    {GWAS_COMMON_FIELDS},
    CASE
        WHEN r.position::bigint < ga.location_start
        THEN 'upstream'
        WHEN r.position::bigint > ga.location_end
        THEN 'downstream'
        ELSE 'in gene'
    END AS relative_position
    FROM NIAGADS.VariantGWASTopHits r, Tracks t, CBIL.GeneAttributes ga
    WHERE ga.source_id = (SELECT gene_lookup(:id))
    AND ga.bin_index_100kb_flank @> r.bin_index
    AND int4range(ga.location_start - 100000, ga.location_end + 100000, '[]') @> r.position
    AND ga.chromosome = r.chromosome
    AND t.track_id = r.track 
    ORDER BY neg_log10_pvalue DESC
"""


GeneRecordQuery = QueryDefinition(
    query=GENE_RECORD_QUERY, bind_parameters=["id"], entity=Entity.GENE, fetch_one=True
)

GeneFunctionQuery = QueryDefinition(
    query=GENE_RECORD_QUERY,
    bind_parameters=["id"],
    json_field="go_annotation",
    fetch_one=True,
)

GenePathwayQuery = QueryDefinition(
    query=GENE_RECORD_QUERY,
    bind_parameters=["id"],
    json_field="pathway_membership",
    fetch_one=True,
)


def get_association_counts(
    result: List[GeneVariantAssociation],
) -> List[VariantAssociationSummary]:

    if len(result) == 0:  # FIXME: handle empty
        return []

    counts = {}
    ontology_terms = {}
    for r in result:
        # need to serialize to determine trait from phenotypes
        assoc = GeneVariantAssociation(**r)
        category = getattr(assoc, "trait_category", None)

        trait = getattr(assoc, "trait", None)
        if trait == "None":
            # might happen due to join or unexpected phenotype
            raise RuntimeError(
                f"Error getting count summary: NULL value returned for a trait. {assoc}"
            )
        trait_name = str(trait)

        # save the term so we can return the object in a JSON response
        ontology_terms[trait_name] = trait

        relative_position = getattr(assoc, "relative_position", None)
        counts.setdefault(category, {}).setdefault(trait_name, {})
        counts[category][trait_name][relative_position] = (
            counts[category][trait_name].get(relative_position, 0) + 1
        )

    summaries = []
    for category, traitDict in counts.items():
        for trait, numVariants in traitDict.items():
            numVariants.update({"total": sum(numVariants.values())})
            summaries.append(
                VariantAssociationSummary(
                    trait_category=category,
                    trait=ontology_terms[trait],
                    num_variants=numVariants,
                )
            )

    # Sort summaries by num_variants["total"] descending
    summaries.sort(key=lambda s: s.num_variants["total"], reverse=True)
    return summaries


GeneAssociationsQuery = QueryDefinition(
    counts_func=get_association_counts,
    bind_parameters=[
        "association_source",
        "association_source",
        "id",
        "association_trait",
        "association_trait",
        "association_trait",
        "association_trait",
    ],
    allow_filters=True,
    query=f"""WITH Tracks AS ({GWAS_TRACK_CTE}),
        Results AS ({GWAS_RESULTS_CTE})
        SELECT * FROM Results
        {association_trait_FILTERS}
    """,
)
