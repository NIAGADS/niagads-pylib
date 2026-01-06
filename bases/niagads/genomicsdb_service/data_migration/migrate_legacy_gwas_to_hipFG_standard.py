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
from typing import AsyncGenerator

from niagads.arg_parser.core import comma_separated_list
from niagads.common.core import ComponentBaseMixin

from niagads.genomics.features.region.core import GenomicRegion
from niagads.genomics.features.variant.annotators import GA4GHVRSService
from niagads.genomics.features.variant.models import Variant as _BaseVariant
from niagads.genomics.features.variant.types import VariantClass
from niagads.genomics.sequence.assembly import Assembly, HumanGenome
from niagads.database.session import DatabaseSessionManager
from niagads.utils.list import qw
from niagads.utils.logging import ExitOnExceptionHandler, async_timed
from niagads.utils.string import dict_to_info_string, xstr
from pydantic import ValidationError
from sqlalchemy import Row, RowMapping, text


QUERY_YIELD = 500000
EXISTING_GWAS_FIELDS = qw(
    "variant_record_primary_key neg_log10_pvalue pvalue_display frequency allele restricted_stats chromosome position"
)
TARGET_FIELDS = qw(
    "chrom position variant_id ref alt pval OR z_score effect_size effect_size_se non_ref_af rsid QC_flags source_info neg_log10_pvalue"
)

PVALUE_ONLY_TARGET_FIELDS = qw(
    "chrom position variant_id ref alt pval rsid QC_flags neg_log10_pvalue"
)


RESTRICTED_STATS_MAP = {
    "effect": "effect_size",
    "std_err": "effect_size_se",
    "z_score": "z_score",
    "odds_ratio": "OR",
}


class AlleleValidationStatus(Enum):
    VALID = auto()
    INVALID = auto()
    VALID_IF_SWAPPED = auto()


class Variant(_BaseVariant):
    test: str
    effect_sign_change: bool = False
    unverified: bool = False

    @classmethod
    def from_row(cls, row: dict[str, str]):
        positional_id = row["metaseq_id"]
        chrm, position, ref, alt = positional_id.split(":")

        start = int(position) - 1
        location: GenomicRegion = GenomicRegion(
            chromosome=HumanGenome(chrm), start=start, end=start + len(ref)
        )

        return cls(
            location=location,
            ref=ref,
            alt=alt,
            ref_snp_id=row["ref_snp_id"],
            test=row["allele"],
            positional_id=positional_id,
            variant_class=VariantClass(row["variant_class"]),
        )

    def resolve_test_allele(self):
        # if test allele is the ref, make it the alt and
        # indicate that statistical correction needs to be made
        if self.test == self.ref:
            self.test = self.alt
            self.effect_sign_change = True

    def swap_alleles(self):
        self.positional_id = self._alt_positional_id()

        ref_swap = self.alt
        self.alt = self.ref
        self.ref = ref_swap

    def _alt_positional_id(self):
        return f"{self.location.chromosome.value}:{self.location.start + 1}:{self.alt}:{self.ref}"


class GWASDataMigrator(ComponentBaseMixin):
    def __init__(
        self,
        connection_string: str,
        seqrepo_service_url: str,
        dataset: str,
        accession: str,
        output_dir: str,
        max_workers: int,
        test: bool = False,
        debug: bool = False,
    ):
        super().__init__(debug=debug, verbose=False)
        self._seqrepo_service_url = seqrepo_service_url
        self._dataset = dataset
        self._accession = accession
        self._output_dir = output_dir
        self._invalid_skips = 0
        self._test = test

        self.logger.info(f"Initializing Data Migrator using: {connection_string}")

        self._session_manager = DatabaseSessionManager(
            connection_string=connection_string,
            pool_size=max_workers + 5,
            echo=debug,
        )

    @async_timed
    async def retrieve_gwas_data(
        self, dataset_id: str, session
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

        if self._test:
            sql += " LIMIT 100"

        chromosomes = HumanGenome.list()
        for chrm in chromosomes:
            self.logger.debug(f"Retrieving data for {dataset_id}: {chrm}")
            result = await session.execute(
                text(sql).execution_options(stream_results=True, yield_per=QUERY_YIELD),
                {"id": dataset_id, "chr": chrm},
            )
            row: Row
            async for row in result:
                self.logger.critical(row._mapping)  # DEBUG
                yield row._mapping  # should return a RowMapping (dict equivalent)

    def standardize_stats(self, data: RowMapping, effect_sign_changed: bool = False):
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
            try:
                mapped_stats["non_ref_af"] = 1.0 - float(data["frequency"])
            except Exception:
                mapped_stats["non_ref_af"] = None
            try:
                mapped_stats["effect_size"] = -float(mapped_stats.get("effect_size"))
            except Exception:
                pass
        else:
            mapped_stats["non_ref_af"] = data["frequency"]

        mapped_stats["neg_log10_pvalue"] = data["neg_log10_pvalue"]
        mapped_stats["pval"] = data["pvalue_display"]
        return mapped_stats

    def write_association(self, variant: Variant, stats, fh, pfh):
        # "chrom position variant_id ref alt pval OR z_score effect_size effect_size_se non_ref_af rsid QC_flags source_info neg_log10_pvalue info"
        flags = []
        if variant.effect_sign_change:
            flags.append("EFFECT_STATS_SIGN_CHANGED")
            self.logger.warning(f"EFFECT_STATS_SIGN_CHANGED: {variant.positional_id}")
        if variant.unverified:
            flags.append("UNVERIFIED")
            self.logger.warning(f"UNVERIFIED: {variant.positional_id}")

        # TODO other flags
        values = [
            variant.location.chromosome.value,
            variant.location.start + 1,  # location are 0-based
            variant.positional_id,
            variant.ref,
            variant.alt,
            stats["pval"],
            variant.ref_snp_id,
            ",".join(flags) if flags else None,
            stats["neg_log10_pvalue"],
        ]
        print("\t".join([xstr(x, null_str="NULL") for x in values]), file=pfh)

        values = [
            variant.location.chromosome.value,
            variant.location.start + 1,
            variant.positional_id,
            variant.ref,
            variant.alt,
            stats["pval"],
            stats["OR"],
            stats["z_score"],
            stats["effect_size"],
            stats["effect_size_se"],
            stats["non_ref_af"],
            variant.ref_snp_id,
            ",".join(flags) if flags else None,
            stats["source_info"],
            stats["neg_log10_pvalue"],
        ]
        print("\t".join([xstr(x, null_str="NULL") for x in values]), file=fh)

    def verify_variant(
        self, variant: Variant, seqrepo_service_url: str, allow_swap: bool = True
    ) -> AlleleValidationStatus:

        # if mapped to ref_snp; verified
        if variant.ref_snp_id is not None:
            return AlleleValidationStatus.VALID

        else:  # verify against genome
            vrs_service: GA4GHVRSService = GA4GHVRSService(
                assembly=Assembly.GRCh38, seqrepo_service_url=seqrepo_service_url
            )
            try:
                vrs_service.validate_sequence(variant.location, variant.ref)
                return AlleleValidationStatus.VALID
            except ValidationError:
                try:
                    vrs_service.validate_sequence(variant.location, variant.alt)
                    return AlleleValidationStatus.VALID_IF_SWAPPED
                except ValidationError:
                    return AlleleValidationStatus.INVALID

    # TODO transformation logic
    def transform(self, data: RowMapping, is_lifted: bool):
        variant: Variant = Variant.from_row(data)
        validation_status = self.verify_variant(variant)

        if validation_status == AlleleValidationStatus.INVALID:
            if is_lifted:
                # if this was lifted over and can't be verified against the
                # genome, then no confidence so skip
                self.logger.warning(
                    f"SKIPPING - INVALID_LIFTOVER {variant.positional_id}"
                )
                return None, None
            else:
                variant.unverified = True

        if validation_status == AlleleValidationStatus.VALID_IF_SWAPPED:
            if variant.variant_class == VariantClass.SNV:
                variant.swap_alleles()
            else:
                # otherwise INDEL -> keep direction
                variant.unverified = True

        # this is where effect sign change gets flagged
        variant.resolve_test_allele()

        standardize_statistics = self.standardize_stats(
            data, variant.effect_sign_change
        )
        return variant, standardize_statistics

    # plus chromosome, position
    # variant_gwas_id	protocol_app_node_id	variant_record_primary_key	bin_index	neg_log10_pvalue	pvalue_display	frequency	allele	restricted_stats
    # 113176520	25	1:29937655:A:C:rs4949232	chr1.L1.B1.L2.B1.L3.B2.L4.B2.L5.B2.L6.B1.L7.B2.L8.B2.L9.B2.L10.B2.L11.B2.L12.B1.L13.B1	0.123551213121659	0.7524	0.868	C	{"effect": -0.0205, "std_err": 0.0651, "direction": "+++-++-+---", "frequency_se": 0.0119, "max_frequency": 0.9236, "min_frequency": 0.8497}

    async def process_dataset(self, dataset_id: str, output_dir: str, session):
        self.logger.info(f"Processing dataset: {dataset_id}")
        is_lifted = "_GRCh38_" in dataset_id
        file_prefix = os.path.join(output_dir, dataset_id.replace("_GRCh38_", "_"))
        file_name = f"{file_prefix}_restricted.txt"
        pvalue_file_name = f"{file_prefix}.txt"
        with open(file_name, "w") as fh, open(pvalue_file_name, "w") as pfh:
            print("\t".join(TARGET_FIELDS), file=fh)
            print("\t".join(PVALUE_ONLY_TARGET_FIELDS), file=pfh)
            async for row in self.retrieve_gwas_data(dataset_id, session):
                variant, standardized_stats = self.transform(row, is_lifted=is_lifted)
                if variant is not None:
                    self.write_association(variant, standardized_stats, fh, pfh)

    def resolve_accession_datasets(self, accession: str, session):
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
            self.logger.info(f"Found {len(ids)} datasets for {accession}: {ids}")
        return ids

    def resolve_dataset_ids(self, session, accession, dataset):
        self.logger.info(f"")
        if accession is not None:
            return self.resolve_accession_datasets(accession, session)

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

        self.logger.info(f"Verified {len(ids)} datasets: {ids}")
        return ids

    async def run(self, list_datasets_only: bool = False):
        async with self._session_manager() as session:
            dataset_ids = self.resolve_dataset_ids(
                session, self._accession, self._dataset
            )

            if list_datasets_only:
                self.logger.info("SUCCESS")
                return

            async def run_all():
                tasks = [
                    asyncio.create_task(
                        self.process_dataset(id, self._output_dir, session)
                    )
                    for id in dataset_ids
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception):
                        self.logger.error(f"Error processing dataset: {result}")

            asyncio.run(run_all())

        self.logger.info("SUCCESS")


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
    parser.add_argument("--test", action="store_true")
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

    logging.basicConfig(
        handlers=[
            ExitOnExceptionHandler(
                filename=os.path.join(args.output_dir, "gwas-migration.log"),
                mode="w",
                encoding="utf-8",
            )
        ],
        level=logging.DEBUG if args.debug else logging.INFO,
    )

    if (args.dataset and args.accession) or (not args.dataset and not args.accession):
        raise ValueError(
            "Please specify either a list of datasets or a list of accessions."
        )

    migrator = GWASDataMigrator(
        connection_string=args.connection_string,
        seqrepo_service_url=args.seqrepo_service_url,
        dataset=args.dataset,
        accession=args.accession,
        output_dir=args.output_dir,
        test=args.test,
        max_workers=args.max_workers,
        debug=args.debug,
    )

    try:

        async def run():
            await migrator.run(list_datasets_only=args.list_datasets_only)

        asyncio.run(run())
        migrator.logger.info("SUCCESS")
    except Exception as err:
        migrator.logger.info("FAIL")
        migrator.logger.critical(f"Exception occurred: {err}", exc_info=True)


if __name__ == "__main__":
    main()
