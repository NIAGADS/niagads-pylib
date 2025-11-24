"""
Extract and migrate GWAS summary statistics from legacy GenomicsDB to hipFG-compatible format.

Note this is meant to be a one-off; which is why SQL queries included hard-coded primary keys
that will not be valid for future instantiations of the database.

# TODO: extract statistics correction logic into variant parsers
# TODO: extract primary key generators
"""

import argparse
import asyncio
from enum import Enum, auto
import logging
import os
from logging import Logger
from typing import AsyncGenerator, Optional

from niagads.arg_parser.core import comma_separated_list
from niagads.assembly.core import Human
from niagads.database.session import DatabaseSessionManager
from niagads.utils.list import qw
from niagads.utils.logging import (
    LOG_FORMAT_STR,
    FunctionContextLoggerWrapper,
    async_timed,
)
from pydantic import BaseModel, field_validator, model_validator
from sqlalchemy import Row, RowMapping, text

LOG: Logger = FunctionContextLoggerWrapper(logger=logging.getLogger(__name__))
QUERY_YIELD = 500000
EXISTING_GWAS_FIELDS = qw(
    "variant_record_primary_key neg_log10_pvalue pvalue_display frequency allele restricted_stats chromosome position"
)
TARGET_FIELDS = qw(
    "chrom position variant_id ref alt pval neg_log10_pvalue OR z_score effect_size effect_size_se non_ref_af rsid QC_flags source_info"
)


class VariantType(Enum):
    SNV = auto()
    MNV = auto()
    INDEL = auto()
    SV = auto()


class Variant(BaseModel):
    chromosome: Human
    position: int
    ref: str
    alt: str
    test: str
    ref_snp_id: Optional[str] = None
    variant_type: Optional[VariantType] = None

    @field_validator(variant_type, mode="after")
    def resolve_variant_type(self):
        if self.variant_type is not None:
            return VariantType(self.variant_type)

        l_ref = len(self.ref)
        l_alt = len(self.alt)

        if l_ref >= 50 or l_alt >= 50:
            return VariantType.SV

        if l_ref != l_alt:
            return VariantType.INDEL

        return VariantType.SNV

    @classmethod
    def from_row(cls, row):
        chrm, position, ref, alt = row["metaseq_id"].split(":")

        return cls(
            chromosome=Human(chrm),
            position=position,
            ref=ref,
            alt=alt,
            ref_snp_id=row["ref_snp_id"],
            test=row["allele"],
        )

    def has_rsid(self):
        return self.ref_snp_id is not None

    def test_is_alt(self):
        return self.test == self.alt

    def is_sv(self):
        return self.variant_type == VariantType.SV


@async_timed
async def retrieve_gwas_data(
    dataset_id: str, session
) -> AsyncGenerator[RowMapping, None]:

    # extracting by chromosome to reduce sorting overhead
    sql = f"""
        SELECT {','.join(EXISTING_GWAS_FIELDS)}, 
        props.details->>'metaseq_id' AS variant_id,
        props.details->>'ref_snp_id' AS ref_snp_id 
        FROM Results.VariantGWAS r,
        get_variant_display_details(r.variant_record_primary_key) as props
        WHERE protocol_app_node_id = :id
        AND chromosome = :chr
        ORDER BY position ASC
    """

    chromosomes = Human.list()
    for chrm in chromosomes:
        LOG.debug(f"Retrieving data for {dataset_id}: {chrm}")
        result = await session.execute(
            text(sql).execution_options(stream_results=True, yield_per=QUERY_YIELD),
            {"id": dataset_id, "chr": chrm},
        )
        row: Row
        async for row in result:
            yield row._mapping  # should return a RowMapping (dict equivalent)


def write_association(variant: Variant, data: RowMapping, fh, pvfh):
    pass


# TODO transformation logic
def transform(data: RowMapping, fh, pvfh, is_lifted: bool):
    variant = Variant.from_row(data)
    if is_lifted and variant.is_sv():
        return
    if variant.has_rsid() and variant.test_is_alt():
        write_association(variant, data, fh, pvfh)
    if not variant.test_is_alt():
        pass


# plus chromosome, position
# variant_gwas_id	protocol_app_node_id	variant_record_primary_key	bin_index	neg_log10_pvalue	pvalue_display	frequency	allele	restricted_stats
# 113176520	25	1:29937655:A:C:rs4949232	chr1.L1.B1.L2.B1.L3.B2.L4.B2.L5.B2.L6.B1.L7.B2.L8.B2.L9.B2.L10.B2.L11.B2.L12.B1.L13.B1	0.123551213121659	0.7524	0.868	C	{"effect": -0.0205, "std_err": 0.0651, "direction": "+++-++-+---", "frequency_se": 0.0119, "max_frequency": 0.9236, "min_frequency": 0.8497}


async def process_dataset(dataset_id: str, session):
    LOG.info(f"Processing dataset: {dataset_id}")
    is_lifted = "_GRCh38_" in dataset_id
    file_prefix = os.path.join(args.output_dir, dataset_id.replace("_GRCh38_", "_"))
    file_name = f"{file_prefix}_restricted.txt"
    pvalue_file_name = f"{file_prefix}.txt"
    with open(file_name, "w") as fh, open(pvalue_file_name, "w") as pfh:
        async for row in retrieve_gwas_data(dataset_id, session):
            transform(row, fh, pfh, is_lifted=is_lifted)


def resolve_accession_datasets(accession: str, session):
    sql = """SELECT source_id FROM Study.ProtocolAppNode
        WHERE external_database_release_id = 19
        AND subtype_id = 49841
        AND source_id LIKE :accession
    """
    result = session.execute(text(sql), {"accession": accession + "%"})
    ids = [row[0] for row in result.fetchall()]
    if not ids:
        raise ValueError(f"No datasets found for accession: {accession}")
    return ids


def resolve_dataset_ids(session):
    if args.accession is not None:
        return resolve_accession_datasets(args.accession, session)

    datasets = [d.upper() for d in args.dataset]
    sql = """SELECT source_id FROM Study.ProtocolAppNode
        WHERE external_database_release_id = 19
        AND subtype_id = 49841
        AND source_id IN :ids
    """
    result = session.execute(text(sql), {"ids": tuple(datasets)})
    ids = [row[0] for row in result.fetchall()]
    if not ids:
        raise ValueError(f"No datasets found for ids: {datasets}.")
    if len(ids) != len(datasets):
        unmatched = set(datasets) - set(ids)
        raise ValueError(
            f"The following dataset IDs were not found: {sorted(unmatched)}"
        )
    return ids


def run():

    db_session_manager = DatabaseSessionManager(
        connection_string=args.connection_string,
        pool_size=args.max_workers + 5,
        echo=args.debug,
    )

    with db_session_manager() as session:
        dataset_ids = resolve_dataset_ids(args.datasets, session)

    async def run_all():
        tasks = [
            asyncio.create_task(process_dataset(id, session)) for id in dataset_ids
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                LOG.error(f"Error processing dataset: {result}")

    asyncio.run(run_all())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "extract GWAS summary statistics from legacy GenomicsDB database"
            "and save in format mimicing what is produced by hipFG"
        ),
        allow_abbrev=False,
    )
    parser.add_argument("--connection_string")
    parser.add_argument(
        "--dataset", type=comma_separated_list, help="one or more dataset IDs"
    )
    parser.add_argument("--accession")
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--max_workers", type=int, default=20)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument(
        "--list_datasets_only",
        action="store_true",
        description=(
            "List GWAS summary statistics accessions. "
            "If an accession number is provided with the `--accession`"
            "flag, then list datasets corresponding to that accession."
        ),
    )
    args = parser.parse_args()

    if args.dataset and args.accession:
        raise ValueError(
            "Please specify either a list of datasets or a list of accessions."
        )

    logging.basicConfig(
        format=LOG_FORMAT_STR,
        level=logging.DEBUG if args.debug else logging.INFO,
    )

    run()
