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
from niagads.bed.utils import bed_file_sort
from niagads.common.core import ComponentBaseMixin

from niagads.exceptions.core import ValidationError
from niagads.genomics.features.region.core import GenomicRegion
from niagads.genomics.features.variant.annotators import GA4GHVRSService
from niagads.genomics.features.variant.models import Variant as _BaseVariant
from niagads.genomics.features.variant.types import VariantClass
from niagads.genomics.sequence.assembly import Assembly, HumanGenome
from niagads.database.session import DatabaseSessionManager
from niagads.utils.list import qw
from niagads.utils.logging import ExitOnExceptionHandler, async_timed
from niagads.utils.string import dict_to_info_string, xstr
from sqlalchemy import Row, RowMapping, bindparam, text


QUERY_YIELD = 5000
EXISTING_GWAS_FIELDS = qw(
    "variant_record_primary_key neg_log10_pvalue pvalue_display frequency allele restricted_stats chromosome position"
)
TARGET_FIELDS = qw(
    "chrom position variant_id ref alt pval OR z_score effect_size effect_size_se non_ref_af rsid source_info QC_flags"
)

PVALUE_ONLY_TARGET_FIELDS = qw("chrom position variant_id ref alt pval rsid QC_flags")


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
        positional_id = row["variant_id"]
        chrm, position, ref, alt = positional_id.split(":")

        start = int(position) - 1
        location: GenomicRegion = GenomicRegion(
            chromosome=HumanGenome(chrm), start=start, end=start + len(ref)
        )

        variant_class = row["variant_class"]
        if variant_class in ["INS", "DEL", "INDEL"] and max(len(ref), len(alt)) < 50:
            variant_class = f"SHORT_{variant_class}"

        return cls(
            location=location,
            ref=ref,
            alt=alt,
            ref_snp_id=row["ref_snp_id"],
            test=row["allele"],
            positional_id=positional_id,
            variant_class=VariantClass(variant_class),
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
        query_yield: int,
        test: bool = False,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(debug=debug, verbose=verbose)
        self._seqrepo_service_url = seqrepo_service_url
        self._dataset = dataset
        self._accession = accession
        self._output_dir = output_dir
        self._invalid_skips = 0
        self._test = test
        self._max_workers = max_workers
        self._connection_string = connection_string
        self._query_yield = query_yield

        self.logger.info(f"Initializing Data Migrator using: {connection_string}")

        self._session_manager = DatabaseSessionManager(
            connection_string=connection_string, echo=debug, pool_size=2
        )

    @async_timed
    async def retrieve_gwas_data(
        self, dataset_id: str, session
    ) -> AsyncGenerator[RowMapping, None]:

        self.logger.info(
            f"DATASET {dataset_id}: Retrieving data for dataset {dataset_id} from the database."
        )
        # extracting by chromosome to reduce sorting overhead
        sql = f"""
            SELECT {','.join(EXISTING_GWAS_FIELDS)}, 
            props.details->>'metaseq_id' AS variant_id,
            props.details->>'ref_snp_id' AS ref_snp_id,
            props.details->>'variant_class_abbrev' AS variant_class
            FROM Results.VariantGWAS r,
            get_variant_display_details(r.variant_record_primary_key) as props
            WHERE protocol_app_node_id = :id
        """

        if self._test:
            sql += f" LIMIT {self._query_yield}"

        await session.execute(
            text("SET statement_timeout = 86400000")
        )  # 24 hours in ms
        try:
            result = await session.stream(
                text(sql).execution_options(yield_per=self._query_yield),
                {"id": dataset_id},
            )
            row: Row
            async for row in result:
                # self.logger.info(f"{row}")  # DEBUG speed
                yield row._mapping
        except Exception as err:
            self.logger.error("Error during db streaming", exc_info="True")
            raise

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

        if mapped_stats["effect_size"] is None:  # if effect is not present, try beta
            mapped_stats["effect_size"] = original_stats.get("beta", None)

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
        # "chrom position variant_id ref alt pval OR z_score effect_size effect_size_se non_ref_af rsid source_info QC_flags"
        # self.logger.info(f"writing {variant}")  # DEBUG speed
        try:
            flags = []
            if variant.effect_sign_change:
                flags.append("EFFECT_STATS_SIGN_CHANGED")
                if self._verbose:
                    self.logger.debug(
                        f"EFFECT_STATS_SIGN_CHANGED: {variant.positional_id}"
                    )
            if variant.unverified:
                flags.append("UNVERIFIED")
                if self._verbose:
                    self.logger.debug(f"UNVERIFIED: {variant.positional_id}")

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
            ]
            pfh.write("\t".join([xstr(x, null_str="NULL") for x in values]) + "\n")

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
                stats["source_info"],
                ",".join(flags) if flags else None,
            ]
            fh.write("\t".join([xstr(x, null_str="NULL") for x in values]) + "\n")
            # print("\t".join([xstr(x, null_str="NULL") for x in values]), file=fh)
        except Exception as err:
            self.logger.exception("Error writing association", exc_info=True)
            raise

    def verify_variant(
        self, variant: Variant, vrs_service: GA4GHVRSService
    ) -> AlleleValidationStatus:

        # if mapped to ref_snp; verified
        if variant.ref_snp_id is not None:
            return AlleleValidationStatus.VALID

        else:  # verify against genome
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
    def transform(
        self, data: RowMapping, is_lifted: bool, vrs_service: GA4GHVRSService
    ):
        try:
            variant: Variant = Variant.from_row(data)
            validation_status = self.verify_variant(variant, vrs_service)

            if validation_status == AlleleValidationStatus.INVALID:
                if is_lifted:
                    # if this was lifted over and can't be verified against the
                    # genome, then no confidence so skip
                    try:
                        self.logger.warning(
                            f"SKIPPING {variant.positional_id} - invalid liftover"
                        )
                    except:
                        self.logger.info(data)
                        raise
                    return None, None
                else:
                    variant.unverified = True

            if validation_status == AlleleValidationStatus.VALID_IF_SWAPPED:
                if variant.variant_class == VariantClass.SNV:
                    if self._verbose:
                        msg = "Swapping Alleles for {variant.positional_id}"

                    variant.swap_alleles()
                    if self._verbose:
                        self.logger.debug(f"{msg} - {variant.positional_id}")

                else:
                    # otherwise INDEL -> keep direction
                    variant.unverified = True

            # this is where effect sign change gets flagged
            variant.resolve_test_allele()

            if self._verbose:
                self.logger.debug(data)

            standardize_statistics = self.standardize_stats(
                data, variant.effect_sign_change
            )
            return variant, standardize_statistics
        except Exception as err:
            self.logger.exception("Error transforming variant", exc_info=True)
            raise

    # plus chromosome, position
    # variant_gwas_id	protocol_app_node_id	variant_record_primary_key	bin_index	neg_log10_pvalue	pvalue_display	frequency	allele	restricted_stats
    # 113176520	25	1:29937655:A:C:rs4949232	chr1.L1.B1.L2.B1.L3.B2.L4.B2.L5.B2.L6.B1.L7.B2.L8.B2.L9.B2.L10.B2.L11.B2.L12.B1.L13.B1	0.123551213121659	0.7524	0.868	C	{"effect": -0.0205, "std_err": 0.0651, "direction": "+++-++-+---", "frequency_se": 0.0119, "max_frequency": 0.9236, "min_frequency": 0.8497}

    async def process_dataset(self, dataset_id: str, output_dir: str):
        self.logger.info(f"DATASET {dataset_id}: Processing dataset: {dataset_id}")
        source_id = dataset_id["source_id"]
        is_lifted = "_GRCh38_" in source_id

        if is_lifted:
            if not source_id.endswith("GRCh38"):
                source_id = source_id.replace("GRCh38_", "") + "_GRCh38"

        file_prefix = os.path.join(output_dir, source_id)

        file_name = f"{file_prefix}.txt"
        pvalue_file_name = f"{file_prefix}_pvalue.txt"

        vrs_service: GA4GHVRSService = GA4GHVRSService(
            assembly=Assembly.GRCh38, seqrepo_service_url=self._seqrepo_service_url
        )
        # not ideal, but hope solves dropped connection issue
        session_manager = DatabaseSessionManager(
            connection_string=self._connection_string,
            echo=self._debug,
            pool_size=2,
            max_connection_lifetime=86400,  # 24hrs
        )
        try:
            with open(file_name, "w") as fh, open(pvalue_file_name, "w") as pfh:

                print("\t".join(TARGET_FIELDS), file=fh)
                print("\t".join(PVALUE_ONLY_TARGET_FIELDS), file=pfh)

                async with session_manager.session_ctx() as session:
                    async for row in self.retrieve_gwas_data(
                        dataset_id["protocol_app_node_id"], session
                    ):

                        variant, standardized_stats = self.transform(
                            row, is_lifted, vrs_service
                        )

                        if variant is not None:
                            self.write_association(variant, standardized_stats, fh, pfh)

            self.logger.info(f"DATASET {dataset_id}: Sorting {dataset_id} files.")
            bed_file_sort(file_name, header=True, overwrite=not self._debug)
            bed_file_sort(pvalue_file_name, header=True, overwrite=not self._debug)
        except Exception as err:

            self.logger.info(
                f"DATASET {dataset_id}: Unexpected Error during processing"
            )
            raise err
        finally:
            await session_manager.close()

    async def resolve_accession_datasets(self, accession: str, session):
        sql = """SELECT source_id FROM Study.ProtocolAppNode
            WHERE external_database_release_id = 19
            AND subtype_id = 49841
            AND source_id LIKE :accession
        """
        result = await session.execute(text(sql), {"accession": accession + "%"})
        ids = [row[0] for row in result.fetchall()]
        if not ids:
            raise ValueError(f"ACCESSION {accession}:No datasets found for accession.")
        else:
            self.logger.info(f"ACCESSION {accession}: Found {len(ids)} datasets: {ids}")
        return ids

    async def resolve_dataset_ids(self, session, accession, datasets):
        if accession is not None:
            dataset_ids = await self.resolve_accession_datasets(accession, session)
        else:
            dataset_ids = datasets

        sql = """SELECT source_id, protocol_app_node_id::int FROM Study.ProtocolAppNode
            WHERE external_database_release_id = 19
            AND subtype_id = 49841
            AND source_id IN :ids
        """
        result = await session.execute(
            text(sql).bindparams(bindparam("ids", expanding=True)),
            {"ids": tuple(dataset_ids)},
        )
        ids = [row._mapping for row in result]
        if not ids:
            raise ValueError(f"No datasets found for ids: {dataset_ids}.")
        if len(ids) != len(dataset_ids):
            unmatched = set(dataset_ids) - set([id["source_id"] for id in ids])
            raise ValueError(
                f"The following dataset IDs were not found: {sorted(unmatched)}"
            )

        self.logger.info(f"ACCESSION {accession}: Verified {len(ids)} datasets: {ids}")
        return ids

    async def run(self, list_datasets_only: bool = False):
        async with self._session_manager.session_ctx() as session:
            dataset_ids = await self.resolve_dataset_ids(
                session, self._accession, self._dataset
            )

            if list_datasets_only:
                self.logger.info("SUCCESS")
                return

        semaphore = asyncio.Semaphore(self._max_workers)

        async def limited_process_dataset(dataset_id, output_dir):
            async with semaphore:
                await self.process_dataset(dataset_id, output_dir)

        tasks = [
            asyncio.create_task(limited_process_dataset(id, self._output_dir))
            for id in dataset_ids
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                self.logger.exception(
                    f"Error processing dataset: {result}", exc_info=result
                )

        if self._test:
            self.logger.info("DONE WITH TEST")
        else:
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
    parser.add_argument("--max_workers", type=int, default=5)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--query_yield", type=int, default=QUERY_YIELD)
    parser.add_argument(
        "--list_datasets_only",
        action="store_true",
        help=(
            "List GWAS summary statistics accessions. "
            "If an accession number is provided with the `--accession`"
            "flag, then list datasets corresponding to that accession."
        ),
    )
    parser.add_argument(
        "--log_file",
        help="log file name (saved to output directory)",
        default="gwas-migration.log",
    )

    args = parser.parse_args()

    logging.basicConfig(
        handlers=[
            ExitOnExceptionHandler(
                filename=os.path.join(args.output_dir, args.log_file),
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
        query_yield=args.query_yield,
        test=args.test,
        max_workers=args.max_workers,
        debug=args.debug,
        verbose=args.verbose,
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
