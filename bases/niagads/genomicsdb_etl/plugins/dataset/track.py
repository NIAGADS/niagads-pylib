"""
TrackJSONLoader Plugin
- Loads a Track record from TrackRecord-compliant JSON file into the Track table.
"""

import json
from typing import Any, Dict, Iterator, Optional, Union

from niagads.common.reference.ontologies.models import OntologyTerm
from niagads.common.track.models.record import TrackRecord
from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.dataset.track import Track, TrackConcept
from niagads.database.genomicsdb.schema.reference.ontology import (
    OntologyTerm as DBOntologyTermRecord,
)
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import PathValidatorMixin
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.genomicsdb_etl.plugins.dataset.base import (
    TrackLoaderBase,
    TrackLoaderBaseParams,
)
from niagads.utils.string import xstr
from niagads.utils.sys import read_open_ctx
from pydantic import Field
from sqlalchemy.exc import NoResultFound

MESH_NAMESPACE = "MeSH_Descriptor"


class TrackJSONLoaderParams(TrackLoaderBaseParams, PathValidatorMixin):
    """Parameters for TrackJSONLoader plugin."""

    file: str = Field(
        ...,
        description="TrackRecord-compliant JSON file(s) to load",
    )

    dataset_type: str = Field(
        ..., description="ontology term or term CURIE for the dataset type"
    )


@PluginRegistry.register(
    metadata=PluginMetadata(
        version="1.0",
        description=f"Loads a TrackRecord-compliant JSON file into {Track.table_name()}.",
        affected_tables=[Track],
        load_strategy=ETLLoadStrategy.BULK,
        operation=ETLOperation.INSERT,
        is_large_dataset=False,
        parameter_model=TrackJSONLoaderParams,
    )
)
class TrackJSONLoader(TrackLoaderBase):
    """
    ETL plugin for loading a Track records from a TrackRecord-compliant JSON file.

    Supports loading from a single JSON file. The file should contain
    either single TrackRecord object.

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
        self._ontology_term_reference: dict[
            str, DBOntologyTermRecord
        ]  # map of provided value to DB record

    async def on_run_start(self, session):
        """Initialize dataset type and prepare for ETL run."""
        await super().on_run_start(session)
        if self.is_etl_run:
            if ":" in self._params.dataset_type:  # assume curie
                self._dataset_type_id = await DBOntologyTermRecord.find_primary_key(
                    session, curie=self._params.dataset_type
                )
            else:  # assume term
                self._dataset_type_id = await DBOntologyTermRecord.find_primary_key(
                    session, term=self._params.dataset_type
                )

    def _parse_json_file(self, file_path: str) -> Any:
        """Read JSON file and return parsed content."""
        with read_open_ctx(file_path) as fh:
            content = json.load(fh)
        self.logger.debug(f"Loaded JSON from {file_path}")
        return content

    async def __validate_ontology_terms(
        self, session, obj, *, fail_on_error: bool = True
    ):
        extracted_terms = OntologyTerm.extract_from_obj(obj)
        lookup_values = {}
        for ot in extracted_terms:
            if ot.curie is not None:
                lookup_values["source_id"] = ot.curie.replace("_", ":")
            if ot.term is not None:
                lookup_values["term"] = ot.term

            key = f"{ot.curie}|{ot.term}"  # still map against original input

            try:
                # basically, users may supply term, curie or both.  need to fill in what is missing
                # for preprocessing & sanity check.  Pulling out full record so that it can be manually reviewed
                self._ontology_term_reference[key] = DBOntologyTermRecord.fetch_record(
                    session, filters=lookup_values
                )
            except NoResultFound as err:
                if fail_on_error:
                    raise err
                else:
                    self._ontology_term_reference[key] = None

    async def preprocess(self) -> None:
        """
        Preprocess: Extract and validate ontology terms from all tracks.

        Iterates through all track JSON files and extracts all ontology terms
        from track records and nested models. Writes terms to a tab-delimited
        file for validation.
        """
        self.logger.info("Preprocessing: Extracting ontology terms from tracks...")

        track_json = self._parse_json_file(self._params.file)
        track_record = TrackRecord(**track_json)

        async with self.session_ctx() as session:
            self.__validate_ontology_terms(session, track_record, fail_on_error=False)

        # Write terms to file
        output_file_name = f"{self._name}_ontology_terms.txt"
        with open(output_file_name, "w") as f:
            print(
                "\t".join(
                    [
                        "user_term",
                        "user_curie",
                        "matched_term",
                        "matched_curie",
                        "primary_key",
                    ]
                )
            )
            term: DBOntologyTermRecord
            for key, term in self._ontology_term_reference:
                values = key.split("|")
                if term is not None:
                    values.append(term.term, term.source_id, term.ontology_term_id)
                else:
                    values.append(None, None, None)
                print("\t".join([xstr(v, null_str="NULL") for v in values]))

        self.logger.info(
            f"Preprocessing complete: Extracted {len(self._ontology_term_reference)} "
            f"unique ontology terms to {output_file_name}"
        )

    def extract(self) -> Iterator[TrackRecord]:
        track_json = self._parse_json_file(self._params.file)
        return TrackRecord(**track_json)

    async def transform(self, record: TrackRecord) -> TrackRecord:
        return record

    async def load(self, session, records: list[TrackRecord]):
        """note: expects a list of records due to ETL plugin implementation (of size batch-size) but
        in reality will be getting 1"""
        if len(records) != 1:
            raise RuntimeError(
                f"Unexpected number of tracks to be loaded: N != 1: {len(records)}"
            )
        track_record = records[0]

        # validate the ontology terms, and save mapping to DB
        # not point in continuing if not valid
        self.__validate_ontology_terms(session, track_record)

        track_data = track_record.model_dump(exclude=["id"], exclude_none=True)
        track_data["source_id"] = track_record.id
        track_data["run_id"] = self.run_id
        track_data["external_database_id"] = self.external_database_id
        track_data["dataset_type_id"] = self._dataset_type_id

        track: Track = Track(**track_data)
        track_id: int = await track.submit(session)

        # now we need to load the linking tables
        concepts: list[TrackConcept] = []
        for keyword in track_record.keywords:
            key = f"{keyword.curie}|{keyword.term}"
            keyword_pk: int = self._ontology_term_reference[key].ontology_term_id
            concepts.append(
                TrackConcept(track_id=track_id, ontology_term_id=keyword_pk)
            )

        """
        TrackConcept
        TrackContext
            -> term_id, concept_type (phenotype, biosample, experiment)
        """

        return self.create_checkpoint(record=track_record)
