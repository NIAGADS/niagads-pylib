from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound
from niagads.genomicsdb.schema.gene.annotation import PathwayMembership
from niagads.genomicsdb.schema.gene.gene_models import Gene, GeneIdentifierType
from niagads.genomicsdb.schema.reference.pathway import Pathway
from niagads.etl.plugins.parameters import ResumeCheckpoint
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.genomicsdb.schema.admin.pipeline import ETLOperation

async def pathway_load(plugin: AbstractBasePlugin, session: AsyncSession, transformed: List, gene_id_type: GeneIdentifierType):
    """
    Helper function to load pathway data into the database.

    Args:
        plugin: The plugin instance calling this function.
        session: The database session.
        transformed: List of transformed pathway annotations.
        gene_id_type: The type of gene identifier to use for resolving genes.

    Returns:
        ResumeCheckpoint: The checkpoint for resuming the ETL process.
    """
    plugin.logger.debug(f"Starting load with {len(transformed)} records.")

    external_database_id = await plugin._params.resolve_xdbref(session)
    pathway_count = 0
    membership_count = 0
    checkpoint = None

    try:
        for record in transformed:
            # Set checkpoint
            checkpoint = ResumeCheckpoint(full_record=record)

            # Load pathway and get its primary key
            try:
                pathway_pk = await Pathway.find_primary_key(
                    filters={"source_id": record.pathway_id}
                )
            except NoResultFound:
                pathway = Pathway(
                    source_id=record.pathway_id,
                    pathway_name=record.pathway_name,
                    external_database_id=external_database_id,
                    run_id=plugin._run_id,
                )
                pathway_pk = await pathway.submit(session)
                pathway_count += 1

            plugin.update_transaction_count(ETLOperation.INSERT, Pathway.table_name(), pathway_count)

            # Lookup the gene and get its primary key
            gene_pk = await Gene.resolve_identifier(
                session, id=record.id, gene_identifier_type=gene_id_type
            )

            # Load the gene<->pathway membership
            await PathwayMembership(
                gene_id=gene_pk,
                pathway_id=pathway_pk,
                run_id=plugin._run_id,
                external_database_id=external_database_id,
            ).submit(session)
            membership_count += 1

        plugin.update_transaction_count(ETLOperation.INSERT, PathwayMembership.table_name(), membership_count)

    finally:
        return checkpoint