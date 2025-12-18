"""
Extract and migrate GWAS summary statistics from legacy GenomicsDB to hipFG-compatible format.

Note this is meant to be a one-off; which is why SQL queries included hard-coded primary keys
that will not be valid for future instantiations of the database.

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
from niagads.sequence.chromosome import Human
from niagads.database.session import DatabaseSessionManager
from niagads.utils.list import qw
from niagads.utils.logging import (
    LOG_FORMAT_STR,
    FunctionContextLoggerWrapper,
    async_timed,
)
from niagads.utils.string import dict_to_info_string, xstr
from pydantic import BaseModel, field_validator, model_validator
from sqlalchemy import Row, RowMapping, text

LOG: Logger = FunctionContextLoggerWrapper(logger=logging.getLogger(__name__))
QUERY_YIELD = 500000
EXISTING_GWAS_FIELDS = qw(
    "variant_record_primary_key neg_log10_pvalue pvalue_display frequency allele restricted_stats chromosome position"
)
TARGET_FIELDS = qw(
    "chrom position variant_id ref alt pval OR z_score effect_size effect_size_se non_ref_af rsid QC_flags source_info neg_log10_pvalue display_info"
)

PVALUE_ONLY_TARGET_FIELDS = qw(
    "chrom position variant_id ref alt pval rsid QC_flags neg_log10_pvalue display_info"
)


RESTRICTED_STATS_MAP = {
    "effect": "effect_size",
    "std_err": "effect_size_se",
    "z_score": "z_score",
    "odds_ratio": "OR",
}


class VariantType(Enum):
    SNV = auto()
    MNV = auto()
    INDEL = auto()
    DEL = auto()
    INS = auto()
    SV = auto()


class Variant(BaseModel):
    chromosome: Human
    position: int
    ref: str
    alt: str
    test: str
    ref_snp_id: str = None
    variant_type: VariantType = None
    variant_id: str = None
    effect_sign_change: bool = False
    verified: bool = False

    @model_validator(mode="after")
    def resolve_structural_variant(self):
        l_ref = len(self.ref)
        l_alt = len(self.alt)

        if l_ref >= 50 or l_alt >= 50:
            self.variant_type = VariantType.SV

        return self

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
            variant_id=row["metaseq_id"],
            variant_type=VariantType(row["variant_class"]),
        )

    def test_is_ref(self):
        return self.test == self.ref

    def resolve_test_allele(self):
        if self.variant_id is None:
            raise ValueError(
                "Must resolve alleles (w/checks against genome) before resolving test allele."
            )

        # since variant ids have already been resolved
        if self.test_is_ref():
            self.test = self.alt
            self.effect_size_change = True

    def _get_alleles(self, swap=False):
        if swap:
            return [self.alt, self.ref]
        else:
            return [self.ref, self.alt]

    def _resolve_variant_id(self, swap: bool = False, skip_validation: bool = False):
        loc = [self.chromosome, self.position]

        if self.verified or skip_validation:
            if self.variant_type != VariantType.SV:
                self.variant_id = ":".join(
                    [str(x) for x in loc + self._get_alleles(swap)]
                )
                if len(self.variant_id) > 50:
                    raise NotImplementedError(
                        "Verified variant_id too long; use VRS to encode"
                    )
            else:  # SV
                raise NotImplementedError("SV use VRS to encode ID")

        else:  # not verified, verify against the genome
            raise NotImplementedError("Use VRS to do this")

    def verify_variant(self):
        if self.ref_snp_id is not None:
            # was mapped to dbSNP so verified
            self.verified = True
            self._resolve_variant_id()

        else:  # need to verify against genome
            try:
                self._resolve_variant_id()
                self.verified = True
            except:  # catch error not match genome
                # decide what do depending on variant type
                if self.variant_type == VariantType.SNV:
                    # if SNV, swap alleles and try again
                    try:
                        self._resolve_variant_id(swap=True)
                        self.verified = True
                    except:  # bypass validation and leave unverified
                        self._resolve_variant_id(skip_validation=True)

                else:  # not SNV, can't switch alleles, so bypass validation and leave unverified
                    self._resolve_variant_id(skip_validation=True)


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
            LOG.critical(row._mapping)  # DEBUG
            yield row._mapping  # should return a RowMapping (dict equivalent)


def standardize_stats(data: RowMapping, effect_sign_changed: bool = False):
    """
    Extracts and harmonizes GWAS statistics from a row, mapping restricted stats to standard output fields
    and non-restrcited stats to new field names

    Args:
        data (RowMapping): Input row containing GWAS summary statistics and restricted stats.
        effect_sign_changed (bool, optional): If True, flips effect size sign and adjusts frequency. Defaults to False.

    Returns:
        dict: Dictionary of mapped GWAS stats, including harmonized effect size, frequency, and unmapped source info.

    Note:
        If effect_sign_changed is True, effect_size is negated and frequency is set to 1 - frequency.
        Unmapped restricted stats are serialized to 'source_info'.
    """

    original_stats = data.get("restricted_stats", {}).copy()
    mapped_stats = {}
    for in_key, out_key in RESTRICTED_STATS_MAP.items():
        if in_key in original_stats:
            mapped_stats[out_key] = original_stats.pop(in_key)
        else:
            mapped_stats[out_key] = None
    mapped_stats["source_info"] = dict_to_info_string(original_stats)

    if effect_sign_changed:
        mapped_stats["non_ref_af"] = 1.0 - data["frequency"]
        try:
            mapped_stats["effect_size"] = -float(mapped_stats.get("effect_size"))
        except Exception:
            pass
    else:
        mapped_stats["non_ref_af"] = data["frequency"]

    mapped_stats["neg_log10_pvalue"] = data["neg_log10_pvalue"]
    mapped_stats["pval"] = "pvalue_display"
    return mapped_stats


def write_association(self, row, fh, pfh):
    # "chrom position variant_id ref alt pval OR z_score effect_size effect_size_se non_ref_af rsid QC_flags source_info neg_log10_pvalue info"
    variant: Variant = row["variant"]
    stats = row["stats"]
    flags = None
    if variant.effect_sign_change:
        flags = "EFFECT_STATS_SIGN_CHANGED"
    # TODO other flags
    values = [
        variant.chromosome,
        variant.position,
        variant.variant_id,
        variant.ref,
        variant.alt,
        stats["pval"],
        variant.ref_snp_id,
        flags,
        stats["neg_log10_pvalue"],
        None,  # display_info (later maybe annotation)
    ]
    print("\t".join([xstr(x, null_str="NULL") for x in values]), file=pfh)

    values = [
        variant.chromosome,
        variant.position,
        variant.variant_id,
        variant.ref,
        variant.alt,
        stats["pval"],
        stats["OR"],
        stats["z_score"],
        stats["effect_size"],
        stats["effect_size_se"],
        stats["non_ref_af"],
        variant.ref_snp_id,
        flags,
        stats["source_info"],
        stats["neg_log10_pvalue"],
        None,  # display_info (later maybe annotation)
    ]
    print("\t".join([xstr(x, null_str="NULL") for x in values]), file=fh)


# TODO transformation logic
def transform(data: RowMapping, is_lifted: bool):
    variant: Variant = Variant.from_row(data)
    variant.verify_variant()
    variant.resolve_test_allele()

    if is_lifted and not variant.verified:
        # if this was lifted over and can't be verified against the
        # genome, then no confidence so skip
        return None  # TODO: count/log skips

    standardize_statistics = standardize_stats(data, variant.effect_sign_change)
    return {"variant": variant, "stats": standardize_statistics}


# plus chromosome, position
# variant_gwas_id	protocol_app_node_id	variant_record_primary_key	bin_index	neg_log10_pvalue	pvalue_display	frequency	allele	restricted_stats
# 113176520	25	1:29937655:A:C:rs4949232	chr1.L1.B1.L2.B1.L3.B2.L4.B2.L5.B2.L6.B1.L7.B2.L8.B2.L9.B2.L10.B2.L11.B2.L12.B1.L13.B1	0.123551213121659	0.7524	0.868	C	{"effect": -0.0205, "std_err": 0.0651, "direction": "+++-++-+---", "frequency_se": 0.0119, "max_frequency": 0.9236, "min_frequency": 0.8497}


async def process_dataset(dataset_id: str, output_dir: str, session):
    LOG.info(f"Processing dataset: {dataset_id}")
    is_lifted = "_GRCh38_" in dataset_id
    file_prefix = os.path.join(output_dir, dataset_id.replace("_GRCh38_", "_"))
    file_name = f"{file_prefix}_restricted.txt"
    pvalue_file_name = f"{file_prefix}.txt"
    with open(file_name, "w") as fh, open(pvalue_file_name, "w") as pfh:
        print("\t".join(TARGET_FIELDS), file=fh)
        print("\t".join(PVALUE_ONLY_TARGET_FIELDS), file=pfh)
        async for row in retrieve_gwas_data(dataset_id, session):
            standardized_row = transform(row, is_lifted=is_lifted)
            if standardized_row is not None:
                write_association(standardized_row, fh, pfh)


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
    else:
        LOG.info(f"Found {len(ids)} datasets for {accession}: {ids}")
    return ids


def resolve_dataset_ids(session, accession, dataset):
    if accession is not None:
        return resolve_accession_datasets(accession, session)

    datasets = [d.upper() for d in dataset]
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

    LOG.info(f"Verified {len(ids)} datasets: {ids}")
    return ids


def run(args):

    db_session_manager = DatabaseSessionManager(
        connection_string=args.connection_string,
        pool_size=args.max_workers + 5,
        echo=args.debug,
    )

    with db_session_manager() as session:
        dataset_ids = resolve_dataset_ids(session, args.accession, args.dataset)

    if args.list_datasets_only:
        LOG.info("SUCCESS")
        return

    async def run_all():
        tasks = [
            asyncio.create_task(process_dataset(id, args.output_dir, session))
            for id in dataset_ids
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                LOG.error(f"Error processing dataset: {result}")

    asyncio.run(run_all())


def main():
    parser = argparse.ArgumentParser(
        description=(
            "extract GWAS summary statistics from legacy GenomicsDB database"
            "and save in format mimicing what is produced by hipFG"
        ),
        allow_abbrev=False,
    )
    parser.add_argument("--connection_string")
    parser.add_argument(
        "--seqrepo_service_url", default="http://localhost:5000/seqrepo"
    )
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
        help=(
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

    run(args)
    LOG.info("SUCCESS")


if __name__ == "__main__":
    main()
