"""
TrackJSONLoader Plugin
- Loads Track records from TrackRecord-compliant JSON files into the Track table.
"""

import json
from typing import Any, Dict, Iterator, List, Optional, Set

from niagads.arg_parser.core import comma_separated_list
from niagads.common.reference.ontologies.models import OntologyTerm
from niagads.common.track.models.record import TrackRecord
from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.dataset.track import Track
from niagads.database.genomicsdb.schema.reference.ontology import OntologyTerm as DBOntologyTerm
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import PathValidatorMixin
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.genomicsdb_etl.plugins.dataset.base import (
    TrackLoaderBase,
    TrackLoaderBaseParams,
)
from niagads.utils.sys import read_open_ctx
from pydantic import Field, field_validator


class TrackJSONLoaderParams(TrackLoaderBaseParams, PathValidatorMixin):
    """Parameters for TrackJSONLoader plugin."""

    file: str = Field(
        ...,
        description="comma-separated list of one or more "
        "TrackRecord-compliant JSON file(s) to load",
        # json_schema_extra={"type":comma_separated_list}
    )

    dataset_type_curie: str = Field(
        description="ontology term CURIE for the dataset type; if not specified, will use track's feature_type",
    )



@PluginRegistry.register(
    metadata=PluginMetadata(
        version="1.0",
        description=f"Loads TrackRecord-compliant JSON file(s) into {Track.table_name()}.",
        affected_tables=[Track],
        load_strategy=ETLLoadStrategy.BULK,
        operation=ETLOperation.INSERT,
        is_large_dataset=False,
        parameter_model=TrackJSONLoaderParams,
    )
)
class TrackJSONLoader(TrackLoaderBase):
    """
    ETL plugin for loading Track records from TrackRecord-compliant JSON files.

    Supports loading from single or multiple JSON files. Each file should contain
    either a single TrackRecord object or an array of TrackRecord objects.

    Preprocessing validates ontology terms and extracts them to a tab-delimited file.
    """

    _params: TrackJSONLoaderParams

    def __init__(
        self,
        params: Dict[str, Any],
        name: Optional[str] = None,
        log_path: str = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(params, name, log_path, debug, verbose)
        self._dataset_type_id: int = None
        self._ontology_terms: Set[tuple] = set()  # (term, curie) pairs

    async def on_run_start(self, session):
        """Initialize dataset type and prepare for ETL run."""
        await super().on_run_start(session)
        if self.is_etl_run:
            self._dataset_type_id = await DBOntologyTerm.find_primary_key(
                session, curie=self._params.dataset_type_curie
            )

    async def preprocess(self) -> None:
        """
        Preprocess: Extract and validate ontology terms from all tracks.

        Iterates through all track JSON files and extracts all ontology terms
        from track records and nested models. Writes terms to a tab-delimited
        file for validation.
        """
        self.logger.info("Preprocessing: Extracting ontology terms from tracks...")

        file_paths = self._params.file.split(',')
        term_count = 0

        # Extract terms from all files
        for file_path in file_paths:
            records = self._load_json_file(file_path)
            if not isinstance(records, list):
                records = [records]

            for record_data in records:
                track_record = TrackRecord(**record_data)
                terms = self._extract_ontology_terms(track_record)
                self._ontology_terms.update(terms)
                term_count += len(terms)

        # Write terms to file
        preprocess_output = self._get_preprocess_output_file()
        self._write_ontology_terms_file(preprocess_output, self._ontology_terms)

        self.logger.info(
            f"Preprocessing complete: Extracted {len(self._ontology_terms)} "
            f"unique ontology terms (from {term_count} total references) "
            f"to {preprocess_output}"
        )

    def _load_json_file(self, file_path: str) -> Any:
        """Load JSON file and return parsed content."""
        with read_open_ctx(file_path) as fh:
            content = json.load(fh)
        self.logger.debug(f"Loaded JSON from {file_path}")
        return content

    def _extract_ontology_terms(self, track: TrackRecord) -> Set[tuple]:
        """
        Extract all ontology terms from a TrackRecord and nested models.

        Returns set of (term, curie) tuples from all nested OntologyTerm objects.
        """
        terms: Set[tuple] = set()

        # Extract from participant_phenotypes
        if track.participant_phenotypes:
            pheno_terms = track.participant_phenotypes.get_ontology_terms()
            for term in pheno_terms:
                if term:
                    terms.add((term.term, term.curie))

        # Extract from study_diagnosis phenotype counts
        if track.study_diagnosis:
            for pheno_count in track.study_diagnosis:
                if pheno_count.phenotype:
                    terms.add((pheno_count.phenotype.term, pheno_count.phenotype.curie))

        # Extract from biosample_characteristics
        if track.biosample_characteristics:
            bio_char = track.biosample_characteristics
            # Extract from list fields
            for field in ["biosample", "biomarker", "tissue"]:
                field_value = getattr(bio_char, field, None)
                if field_value and isinstance(field_value, list):
                    for term in field_value:
                        if term:
                            terms.add((term.term, term.curie))
            # Extract from single OntologyTerm fields
            if bio_char.life_stage:
                terms.add((bio_char.life_stage.term, bio_char.life_stage.curie))

        # Extract from experimental_design
        if track.experimental_design:
            if track.experimental_design.covariates:
                for term in track.experimental_design.covariates:
                    if term:
                        terms.add((term.term, term.curie))

        return terms

    def _get_preprocess_output_file(self) -> str:
        """Generate output file path for preprocessing results."""
        return f"{self._name}_ontology_terms.txt"

    def _write_ontology_terms_file(
        self, output_file: str, terms: Set[tuple]
    ) -> None:
        """Write ontology terms to tab-delimited file."""
        with open(output_file, "w") as f:
            f.write("term\tcurie\n")
            for term, curie in sorted(terms):
                f.write(f"{term}\t{curie}\n")

    def extract(self) -> Iterator[TrackRecord]:
        """
        Extract TrackRecord objects from JSON file(s).

        Yields individual TrackRecord objects, handling both single records
        and arrays of records per file.
        """
        total_records = 0

        for file_path in self._params.file.split(','):
            self.logger.info(f"Extracting records from {file_path}")
            try:
                records_data = self._load_json_file(file_path)

                # Handle both single record and array of records
                if not isinstance(records_data, list):
                    records_data = [records_data]

                for record_data in records_data:
                    try:
                        track_record = TrackRecord(**record_data)
                        total_records += 1
                        if self._verbose:
                            self.logger.debug(
                                f"Extracted record: {track_record.id}"
                            )
                        yield track_record
                    except Exception as err:
                        self.logger.error(
                            f"Failed to parse record from {file_path}: {err}"
                        )
                        raise

            except Exception as err:
                self.logger.error(f"Failed to extract from {file_path}: {err}")
                raise

        self.logger.info(f"Extracted {total_records} track records from {len(self._params.file)} file(s)")

    async def transform(self, records: list[TrackRecord]) -> list[TrackRecord]:
        """
        Transform TrackRecord objects (pass-through).

        Args:
            records: List of TrackRecord objects from extract.

        Returns:
            List of TrackRecord objects unchanged.
        """
        return records

    async def load(self, session, records: list[TrackRecord]):
        """
        Load Track records into database.

        Args:
            session: Async SQLAlchemy session.
            records: List of TrackRecord objects to load.

        Returns:
            ResumeCheckpoint for resuming ETL operations.
        """
        tracks: list[Track] = []

        # Create Track records
        for record in records:
            track_data = record.model_dump(exclude=["id"], exclude_none=True)
            track_data["source_id"] = record.id
            track_data["run_id"] = self.run_id
            track_data["external_database_id"] = self.external_database_id
            track_data["is_filer_track"] = False

            if self._dataset_type_id is not None:
                track_data["dataset_type_id"] = self._dataset_type_id

            tracks.append(Track(**track_data))

        await Track.submit_many(session, tracks)
        self.logger.debug(f"Submitted {len(tracks)} Track records")

        return self.create_checkpoint(record=records[-1])
